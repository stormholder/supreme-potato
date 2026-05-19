import copy
import json
from pathlib import Path
import random
import time

import requests
import urllib.parse

import config


def load_workflow():
    return json.loads(Path(config.config['comfyui']['workflow_file']).read_text())


def patch_workflow(workflow: dict, prompt: str, seed: int):
    wf = copy.deepcopy(workflow)

    for node in wf.values():
        title = node.get("_meta", {}).get("title", "")
        class_type = node.get("class_type", "")

        if title == "Positive Prompt":
            node["inputs"]["text"] = prompt

        if class_type == "KSampler":
            node["inputs"]["seed"] = seed

    return wf


def generate_image(prompt: str, seed: int = -1):
    if seed == -1:
        seed = random.randint(0, 2**32)

    workflow = load_workflow()

    workflow = patch_workflow(
        workflow,
        prompt,
        seed,
    )

    response = requests.post(
        f"{config.config['comfyui']['host']}/prompt",
        json={"prompt": workflow},
        timeout=10,
    )

    response.raise_for_status()

    prompt_id = response.json()["prompt_id"]

    return poll(prompt_id)


def download_image(filename: str) -> bytes:
    """Download image bytes from ComfyUI output directory."""
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": "",
        "type": "output",
    })
    r = requests.get(f"{config.config['comfyui']['host']}/view?{params}", timeout=30)
    r.raise_for_status()
    return r.content


def poll(prompt_id: str):
    deadline = time.time() + 300

    while time.time() < deadline:

        history = requests.get(
            f"{config.config['comfyui']['host']}/history/{prompt_id}"
        ).json()

        if prompt_id in history:
            outputs = history[prompt_id]["outputs"]

            for node in outputs.values():
                if "images" in node:
                    return node["images"][0]["filename"]

        time.sleep(0.8)

    raise RuntimeError("ComfyUI timeout")


def free_vram():
    requests.post(f"{config.config['comfyui']['host']}/interrupt")
    requests.post(
        f"{config.config['comfyui']['host']}/queue",
        json={"clear": True},
    )

    requests.post(
        f"{config.config['comfyui']['host']}/free",
        json={
            "unload_models": True,
            "free_memory": True,
        },
    )