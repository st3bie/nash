import os
from dotenv import load_dotenv
from input_classifier import is_shell_command
from command_handler import run_command
from context_engine import retrieve_context
from llama_api import call_llama

load_dotenv()

session_history = []
MAX_HISTORY = 20

def ask_llm_with_context(user_input):
    # Build a context string from past interactions + file embeddings
    history_context = "\n\n".join(session_history[-MAX_HISTORY:])
    file_context = retrieve_context(user_input)
    prompt_context = history_context + "\n\n---\n\n" + file_context
    return call_llama(user_input, prompt_context)

def parse_suggestion(suggestion):
    if suggestion.startswith("```bash") or suggestion.startswith("```"):
        suggestion = suggestion.strip("```bash").strip("```").strip()
    return [line.strip() for line in suggestion.split("\n") if line.strip()]

def main():
    while True:
        user_input = input("nash > ").strip()
        if not user_input:
            continue

        # ───────────────────── Shell Command ─────────────────────
        if is_shell_command(user_input):
            output = run_command(user_input)
            print(output)

            session_history.append(f"USER: {user_input}\nOUTPUT: {output.strip()}")
            session_history[:] = session_history[-MAX_HISTORY:]

            # ── Try to auto-fix if command fails ──
            if any(err in output.lower() for err in ["not found", "error", "command not recognized", "fatal", "no such file"]):
                print("\n[!] Error detected, asking LLM for fix suggestion...")
                error_prompt = f"The user ran:\n{user_input}\n\nAnd got:\n{output}\n\nWhat could fix this?"
                suggestion = call_llama(error_prompt, "\n\n".join(session_history))
                print(f"\nLLM Fix Suggestion:\n{suggestion}")
            continue

        # ───────────────────── Natural Language ─────────────────────
        commands = call_llama(user_input, retrieve_context(user_input))
        print(f"\nLLM JSON Commands:\n{commands}")

        if all(is_shell_command(cmd.split()[0]) for cmd in commands):
            confirm = input("\nRun all suggested commands? [y/N] ").lower()
            if confirm == "y":
                for cmd in commands:
                    print(f"\n$ {cmd}")
                    output = run_command(cmd)
                    print(output)
                    session_history.append(f"USER: {cmd}\nOUTPUT: {output.strip()}")
                    session_history[:] = session_history[-MAX_HISTORY:]

if __name__ == "__main__":
    main()
