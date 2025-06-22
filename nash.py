import os
import requests
import subprocess
import shlex
from pathlib import Path
import re
import shutil

# optional, may not be present on some installs
try:
    import readline
except ImportError:
    readline = None

from context_engine import build_prompt_with_context, index_files

# ─── Setup ────────────────────────────────────────────────────────────

os.environ["TOKENIZERS_PARALLELISM"] = "false"
HISTORY_FILE = Path.home() / ".nash_history"
API_KEY = os.environ.get("LLAMA_API_KEY")
BASE_URL = "https://api.llama.com/v1/chat/completions"
MODEL = "Llama-4-Maverick-17B-128E-Instruct-FP8"

BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/", r"sudo", r"shutdown", r"reboot",
    r"clear", r"reset", r"chsh", r"zsh", r"bash", r":\s*\(\)"
]

if not API_KEY:
    key_file = Path.home() / ".nash_api_key"
    if key_file.exists():
        API_KEY = key_file.read_text().strip()
    else:
        print("Error: API key not found in environment or ~/.nash_api_key")
        exit(1)

# ─── Inference-based Completion ───────────────────────────────────────

suggestions = []

def completer(text, state):
    global suggestions
    if state == 0:
        # 1) Tell the model to emit ONLY a bash snippet in ```
        system = {"role":"system", "content":
            "You are a bash shell assistant.  "
            "When given a partial command, reply with exactly one code block "
            "```bash\n<completed-command>\n``` and nothing else."
        }
        user = {"role":"user", "content": f"Partial command:\n```bash\n{text}```"}
        # 2) Call your existing chat_completion
        raw = chat_completion([system, user])
        # 3) Pull out the ```bash``` snippet
        cmd = extract_command(raw)
        # 4) Only keep it if it extends what the user typed
        suggestions = [cmd] if cmd.startswith(text) and cmd != text else []
    return suggestions[state] if state < len(suggestions) else None

# ─── Core Functions ───────────────────────────────────────────────────

def chat_completion(messages):
    resp = requests.post(
        BASE_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_completion_tokens": 128,
            "temperature": 0.3
        }
    )
    resp.raise_for_status()
    return resp.json()["completion_message"]["content"]["text"].strip()

def extract_command(text):
    m = re.search(r"```(?:bash)?\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    for line in reversed(text.splitlines()):
        if line and not line.startswith("```"):
            return line.strip()
    return text.strip()

def is_command_safe(cmd):
    return not any(re.search(p, cmd) for p in BLOCKED_PATTERNS)

def save_to_history(nl, cmd):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"# {nl}\n{cmd}\n")

def run_command(cmd):
    try:
        c = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        return c.returncode, c.stdout.strip(), c.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def suggest_fix(error_msg, user_input):
    repair = (
        f"The previous command failed with this error:\n{error_msg}\n"
        "Suggest a fix as a single-line bash command."
    )
    messages = build_prompt_with_context(f"{user_input}\n\n{repair}")
    resp = chat_completion(messages)
    fix = extract_command(resp)
    if not is_command_safe(fix):
        print("Suggested fix is unsafe and will not be run.")
        return None
    return fix

def looks_like_shell_command(inp):
    try:
        tok = shlex.split(inp)
        return bool(tok) and shutil.which(tok[0]) is not None
    except Exception:
        return False

# ─── Main Loop ────────────────────────────────────────────────────────

def main():
    print("nash — context-aware shell assistant")
    while True:
        try:
            index_files()
            user_input = input("> ").strip()
            if user_input.lower() in {"exit", "quit"}:
                break

            if looks_like_shell_command(user_input):
                command = user_input
            else:
                raw = chat_completion(build_prompt_with_context(user_input))
                command = extract_command(raw)

            if not is_command_safe(command):
                print("Blocked unsafe command:", command)
                continue

            # pressing Enter (empty input) will run; "n" skips
            confirm = input(
                f"\nRun this command:\n{command}\n\n"
                "Press Enter to run, or type 'n' to skip: "
            ).strip().lower()
            if confirm in {"n", "no"}:
                print("Command skipped.")
                save_to_history(user_input, command)
                continue

            print(f"Running: {command}")
            code, out, err = run_command(command)
            if out: print(out)
            if err: print(err)

            if code != 0 and not looks_like_shell_command(user_input):
                fix = suggest_fix(err or "Unknown error", user_input)
                if fix:
                    cf = input(
                        f"\nSuggested fix:\n{fix}\n\n"
                        "Press Enter to run, or type 'n' to skip: "
                    ).strip().lower()
                    if cf not in {"n", "no"}:
                        os.system(fix)
                    else:
                        print("Fix skipped.")

            save_to_history(user_input, command)

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
