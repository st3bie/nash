import os
import requests
import subprocess
import shlex
from pathlib import Path
import re

HISTORY_FILE = Path.home() / ".nash_history"
API_KEY = os.environ.get("LLAMA_API_KEY")

if not API_KEY:
    key_file = Path.home() / ".nash_api_key"
    if key_file.exists():
        API_KEY = key_file.read_text().strip()
    else:
        print("Error: API key not found in environment or ~/.nash_api_key")
        exit(1)

BASE_URL = "https://api.llama.com/v1/chat/completions"
MODEL = "Llama-4-Maverick-17B-128E-Instruct-FP8"
MAX_HISTORY = 6
BLOCKED_PATTERNS = [r"rm\s+-rf\s+/", r"sudo", r"shutdown", r"reboot", r"clear", r"reset", r"chsh", r"zsh", r"bash", r":\s*\(\)"]


def chat_completion(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_completion_tokens": 128,
        "temperature": 0.3
    }

    response = requests.post(BASE_URL, headers=headers, json=payload)
    response.raise_for_status()

    try:
        return response.json()["completion_message"]["content"]["text"].strip()
    except KeyError:
        print("Error: Unexpected API response:")
        print(response.json())
        raise


def extract_command(text):
    match = re.search(r"```(?:bash)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    lines = text.strip().splitlines()
    for line in reversed(lines):
        if line.strip() and not line.strip().startswith("```"):
            return line.strip()
    return text.strip()


def is_command_safe(cmd):
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd):
            return False
    return True


def save_to_history(nl, cmd):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"# {nl}\n{cmd}\n")


def run_command(cmd):
    try:
        completed = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def suggest_fix(error_msg, chat_history):
    chat_history.append({
        "role": "user",
        "content": f"The previous command failed with this error:\n{error_msg}\nSuggest a fix as a single-line bash command."
    })

    response = chat_completion(chat_history[-(MAX_HISTORY + 2):])
    command = extract_command(response)

    if not is_command_safe(command):
        print("Suggested fix is unsafe and will not be run.")
        return None

    return command


def main():
    print("nash — context-aware shell assistant")

    chat_history = [
        {
            "role": "system",
            "content": (
                "You are a shell assistant. Translate user input into a valid single-line bash command. "
                "Respond only with the command, no explanations or formatting. Never return dangerous commands."
            )
        }
    ]

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in {"exit", "quit"}:
                break

            chat_history.append({"role": "user", "content": user_input})
            raw_response = chat_completion(chat_history[-(MAX_HISTORY + 1):])
            command = extract_command(raw_response)

            if not is_command_safe(command):
                print("Blocked unsafe command:")
                print(command)
                continue

            print(f"Command: {command}")
            confirm = input("Run this command? [y/N]: ").strip().lower()
            if confirm != "y":
                continue

            ret_code, stdout, stderr = run_command(command)

            if stdout:
                print(stdout)
            if stderr:
                print(stderr)

            chat_history.append({"role": "assistant", "content": command})
            chat_history.append({
                "role": "user",
                "content": f"Command exited with code {ret_code}.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            })

            if ret_code != 0:
                fix = suggest_fix(stderr or "Unknown error", chat_history)
                if fix:
                    print(f"Suggested fix: {fix}")
                    retry = input("Run suggested fix? [y/N]: ").strip().lower()
                    if retry == "y":
                        os.system(fix)
                        chat_history.append({"role": "assistant", "content": fix})

            save_to_history(user_input, command)

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
