#!/usr/bin/env python3
import os
import sys
import subprocess
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion

# ─── 1) CONFIG ────────────────────────────────────────────────────────────────
LLAMA_API_KEY = os.environ.get('LLAMA_API_KEY')
LLAMA_API_URL = os.environ.get("LLAMA_API_URL", "https://api.llama.com/v1/chat/completions")
MODEL = os.environ.get("LLAMA_MODEL", "Llama-3.3-8B-Instruct")

SYSTEM_PROMPT = (
    "You are a helpful shell assistant. "
    "When given a partial command, suggest up to 5 valid shell commands "
    "that start with that prefix.  "
    "Respond with a JSON array of strings."
)

# ─── 2) CHAT COMPLETION WRAPPER ──────────────────────────────────────────────
def chat_completion(messages, model=MODEL, max_tokens=64, temperature=0.2, stream=False):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLAMA_API_KEY}",
        "Accept": "text/event-stream" if stream else "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    resp = requests.post(LLAMA_API_URL, json=payload, headers=headers, timeout=2.0)
    resp.raise_for_status()
    data = resp.json()
    # The assistant message is in data["choices"][0]["message"]["content"]
    return data["choices"][0]["message"]["content"]

# ─── 3) COMPLETER ─────────────────────────────────────────────────────────────
class LlamaChatCompleter(Completer):
    def get_completions(self, document, complete_event):
        prefix = document.text_before_cursor.strip()
        if not prefix:
            return

        # Build a minimal conversation
        messages = [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": f"Partial command: \"{prefix}\""},
        ]
        try:
            reply = chat_completion(messages)
            # Expecting a JSON array like ["ls", "ls -la", ...]
            suggestions = []
            try:
                import json as _json
                suggestions = _json.loads(reply)
            except:
                # fallback: split lines
                suggestions = [line for line in reply.splitlines() if line.startswith(prefix)]
            
            for cmd in suggestions:
                yield Completion(cmd, start_position=-len(prefix))
        except Exception:
            return

# ─── 4) MAIN REPL ────────────────────────────────────────────────────────────
def main():
    session = PromptSession(
        message="nash> ",
        completer=LlamaChatCompleter(),
        complete_while_typing=True,
    )

    while True:
        try:
            cmd = session.prompt().strip()
            if cmd in ("exit", "quit"):
                break

            # Execute and print output
            proc = subprocess.Popen(cmd, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            out, err = proc.communicate()
            if out: sys.stdout.write(out)
            if err: sys.stderr.write(err)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    main()
