import json
import time

import requests

import config


def load_model(model: str):
    if "ollama.com" in config.OLLAMA_HOST:
        return
    print(f"[VRAM] loading {model}")

    requests.post(
        f"{config.OLLAMA_API}/generate",
        json={
            "model": model,
            "keep_alive": "10m",
            "prompt": " ",
        },
        timeout=60,
    )


def unload_model(model: str):
    if "ollama.com" in config.OLLAMA_HOST:
        return
    print(f"[VRAM] unloading {model}")

    requests.post(
        f"{config.OLLAMA_API}/generate",
        json={
            "model": model,
            "keep_alive": 0,
            "prompt": " ",
        },
        timeout=10,
    )

    time.sleep(config.SWAP_SETTLE_TIME)


def swap_model(current: str | None, next_model: str):
    if current:
        unload_model(current)

    load_model(next_model)

    return next_model


def chat(model: str, system: str, user: str) -> str:
    response = requests.post(
        f"{config.OLLAMA_API}/chat",
        headers=config.OLLAMA_HEADERS, 
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
        timeout=config.REQUEST_TIMEOUT,
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