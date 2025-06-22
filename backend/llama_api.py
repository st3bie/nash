import os
import requests
import json

def call_llama(prompt, context=""):
    headers = {
        "Authorization": f"Bearer {os.getenv('LLAMA_API_KEY')}",
        "Content-Type": "application/json"
    }

    system_message = {
        "role": "system",
        "content": (
            "You are a shell assistant. Respond ONLY in valid JSON like:\n"
            '{ "commands": ["command1", "command2"] }\n'
            "No explanations. No markdown. Just raw JSON."
        )
    }

    user_message = {
        "role": "user",
        "content": context + "\n" + prompt
    }

    payload = {
        "model": os.getenv("MODEL"),
        "messages": [system_message, user_message],
        "stream": False
    }

    response = requests.post(os.getenv("BASE_URL"), headers=headers, json=payload)

    try:
        content_block = response.json()["completion_message"]["content"]
        if isinstance(content_block, dict) and "text" in content_block:
            raw_text = content_block["text"]
        elif isinstance(content_block, str):
            raw_text = content_block
        else:
            return [f"Unexpected content format: {content_block}"]

        parsed = json.loads(raw_text)
        return parsed["commands"]

    except Exception as e:
        return [f"Error parsing LLaMA output: {e}\nRaw: {response.text}"]
