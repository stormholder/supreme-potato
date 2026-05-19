import json
import time

import requests

import config
import constants

OLLAMA_CLOUD="ollama.com"

def load_model(model: str):
    ollama_host = config.config['ollama']['host']
    if OLLAMA_CLOUD in ollama_host:
        return
    print(f"[VRAM] loading {model}")

    requests.post(
        f"{ollama_host}/generate",
        json={
            "model": model,
            "keep_alive": "10m",
            "prompt": " ",
        },
        timeout=60,
    )


def unload_model(model: str):
    ollama_host = config.config['ollama']['host']
    if OLLAMA_CLOUD in ollama_host:
        return
    print(f"[VRAM] unloading {model}")

    requests.post(
        f"{ollama_host}/generate",
        json={
            "model": model,
            "keep_alive": 0,
            "prompt": " ",
        },
        timeout=10,
    )

    time.sleep(constants.SWAP_SETTLE_TIME)


def swap_model(current: str | None, next_model: str):
    if current:
        unload_model(current)

    load_model(next_model)

    return next_model


def chat(model: str, system: str, user: str) -> str:
    ollama_host = config.config['ollama']['host']
    headers={}
    if OLLAMA_CLOUD in ollama_host:
        ollama_api_key = config.config['ollama']['api_key']
        headers={"Authorization": f"Bearer {ollama_api_key}"}
    response = requests.post(
        f"{ollama_host}/api/chat",
        headers=headers, 
        json={
            "model": model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
        },
        timeout=constants.REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()["message"]["content"].strip()


def chat_json(model: str, system: str, user: str):
    raw = chat(model, system, user)

    cleaned = (
        raw
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    return json.loads(cleaned)