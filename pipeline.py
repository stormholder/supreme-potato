"""
pipeline.py
LLM calls, Ollama model management, and ComfyUI integration.
All network I/O lives here. main.py and other modules import from this file.
"""

import copy
import json
from pathlib import Path
import random
import subprocess
import time
import urllib.parse

import requests
import config


for _dir in [config.OUTPUT_IMAGES_DIR, config.OUTPUT_3D_DIR, config.OUTPUT_BLENDER_DIR, config.OUTPUT_UNITY_DIR]:
    _dir.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Ollama — model management
# ---------------------------------------------------------------------------

def ollama_load(model: str) -> None:
    """Pre-warm a model into VRAM. Blocks until the model responds."""
    print(f"  [VRAM] loading {model}...")
    try:
        requests.post(
            f"{config.OLLAMA_API}/generate",
            json={"model": model, "keep_alive": "10m", "prompt": config.MODEL_WARMUP_PROMPT},
            timeout=60,  # loading a fresh model can take time
        )
    except requests.exceptions.Timeout:
        print(f"  [VRAM] warning: load timeout for {model} — may still be loading")


def ollama_unload(model: str) -> None:
    """Evict a model from VRAM immediately."""
    print(f"  [VRAM] unloading {model}...")
    try:
        requests.post(
            f"{config.OLLAMA_API}/generate",
            json={"model": model, "keep_alive": 0, "prompt": config.MODEL_WARMUP_PROMPT},
            timeout=10,
        )
        time.sleep(config.SWAP_SETTLE_TIME)
    except requests.exceptions.RequestException as e:
        print(f"  [VRAM] warning: unload failed for {model}: {e}")


def ollama_swap(unload: str | None, load: str) -> str:
    """
    Unload the current model (if any) then load the next one.
    Returns the name of the newly loaded model.
    """
    if unload:
        ollama_unload(unload)
    ollama_load(load)
    print(f"  [VRAM] active model: {load}")
    return load


def ollama_check() -> list[dict]:
    """Return list of models currently loaded in VRAM."""
    try:
        r = requests.get(f"{config.OLLAMA_API}/ps", timeout=5)
        return r.json().get("models", [])
    except requests.exceptions.RequestException:
        return []


# ---------------------------------------------------------------------------
# Ollama — inference
# ---------------------------------------------------------------------------

def llm_call(model: str, system: str, user: str) -> str:
    """
    Send a chat request to Ollama. Returns the assistant's reply as a string.
    Raises RuntimeError on network or API failure.
    """
    try:
        response = requests.post(
            f"{config.OLLAMA_API}/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            },
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()

    except requests.exceptions.Timeout:
        raise RuntimeError(f"LLM call timed out after {config.REQUEST_TIMEOUT}s (model: {model})")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"LLM call failed: {e}")
    except KeyError as e:
        raise RuntimeError(f"Unexpected Ollama response format: {e}")


def llm_call_json(model: str, system: str, user: str, retries: int = 2) -> dict:
    """
    Like llm_call but expects and parses JSON output.
    Retries up to `retries` times on parse failure.
    Raises RuntimeError if all attempts fail.
    """
    for attempt in range(1, retries + 1):
        raw = llm_call(model, system, user)
        # Strip markdown fences if the model added them despite instructions
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  [JSON] parse failed (attempt {attempt}/{retries}): {e}")
            if attempt == retries:
                raise RuntimeError(
                    f"Model {model} returned invalid JSON after {retries} attempts.\n"
                    f"Raw output:\n{raw}"
                )
    return {}  # unreachable, satisfies type checkers


# ---------------------------------------------------------------------------
# ComfyUI — image generation
# ---------------------------------------------------------------------------

def _load_workflow() -> dict:
    """Load the ComfyUI workflow JSON from disk. Raises if not found."""
    if not config.WORKFLOW_PATH.exists():
        raise FileNotFoundError(
            f"ComfyUI workflow not found at {config.WORKFLOW_PATH}.\n"
            "Export it from ComfyUI: Settings → Enable Dev Mode → Save (API Format)"
        )
    return json.loads(config.WORKFLOW_PATH.read_text())


def _patch_workflow(workflow: dict, positive_prompt: str, seed: int) -> dict:
    """
    Return a copy of the workflow with the prompt and seed patched in.
    Finds nodes by their _meta.title — name your nodes in ComfyUI!
    """
    wf = copy.deepcopy(workflow)

    for node in wf.values():
        title = node.get("_meta", {}).get("title", "")
        class_type = node.get("class_type", "")

        if title == "Positive Prompt":
            node["inputs"]["text"] = positive_prompt

        if class_type == "KSampler":
            node["inputs"]["seed"] = seed

    return wf


def _poll_comfyui(prompt_id: str, poll_interval: float = 0.8, timeout: float = 300) -> str:
    """
    Poll ComfyUI history until the prompt is complete.
    Returns the output image filename.
    Raises RuntimeError on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            history = requests.get(
                f"{config.COMFYUI_HOST}/history/{prompt_id}", timeout=5
            ).json()
        except requests.exceptions.RequestException:
            time.sleep(poll_interval)
            continue

        if prompt_id in history:
            for node_output in history[prompt_id]["outputs"].values():
                if "images" in node_output:
                    return node_output["images"][0]["filename"]

        time.sleep(poll_interval)

    raise RuntimeError(f"ComfyUI timed out after {timeout}s for prompt {prompt_id}")


def comfyui_generate(positive_prompt: str, seed: int = -1) -> str:
    """
    Submit a generation job to ComfyUI and wait for it to finish.
    Returns the output image filename (relative to ComfyUI's output directory).
    """
    if seed == -1:
        seed = random.randint(0, 2**32)

    workflow = _load_workflow()
    patched  = _patch_workflow(workflow, positive_prompt, seed)

    try:
        response = requests.post(
            f"{config.COMFYUI_HOST}/prompt",
            json={"prompt": patched},
            timeout=10,
        )
        response.raise_for_status()
        prompt_id = response.json()["prompt_id"]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"ComfyUI submission failed: {e}")

    return _poll_comfyui(prompt_id)


def comfyui_free_vram() -> None:
    """Ask ComfyUI to unload its models — free VRAM before loading next stage."""
    try:
        requests.post(
            f"{config.COMFYUI_HOST}/free",
            json={"unload_models": True, "free_memory": True},
            timeout=10,
        )
        time.sleep(1.0)
        print("  [VRAM] ComfyUI models unloaded")
    except requests.exceptions.RequestException as e:
        print(f"  [VRAM] warning: ComfyUI free failed: {e}")


def comfyui_download_image(filename: str) -> bytes:
    """Download image bytes from ComfyUI output directory."""
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": "",
        "type": "output",
    })
    r = requests.get(f"{config.COMFYUI_HOST}/view?{params}", timeout=30)
    r.raise_for_status()
    return r.content


# ---------------------------------------------------------------------------
# 3D generation — Trellis
# ---------------------------------------------------------------------------

def generate_3d(image_filename: str, asset_type: str) -> str:
    """
    Submit an image to a locally running Trellis server for mesh generation.
    Returns path to the saved .glb file.

    Trellis setup: https://github.com/microsoft/TRELLIS
    Default port: 7860. Run AFTER unloading FLUX to free VRAM.

    tri_targets are used as the simplify parameter — Trellis interprets
    lower values as more aggressive decimation.
    """
    from prompts import TRI_TARGETS
    tri_target = TRI_TARGETS.get(asset_type, 300)

    image_bytes = comfyui_download_image(image_filename)

    try:
        response = requests.post(
            "http://localhost:7860/generate",
            files={"image": (image_filename, image_bytes, "image/png")},
            data={
                "simplify":     tri_target,
                "texture_size": 256,    # PSX-appropriate resolution
                "output_format": "glb",
            },
            timeout=300,  # 3D generation is slow
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Trellis generation failed: {e}")

    out_path = config.OUTPUT_3D_DIR / f"{Path(image_filename).stem}.glb"
    out_path.write_bytes(response.content)
    print(f"  [3D] mesh saved: {out_path}")
    return str(out_path)


# ---------------------------------------------------------------------------
# Blender — headless mesh cleanup
# ---------------------------------------------------------------------------

def generate_blender_script(
    model: str,
    system_prompt: str,
    mesh_path: str,
    asset_type: str,
) -> str:
    """
    Ask the LLM to write a bpy cleanup script for this mesh.
    Saves the script to blender_scripts/ and returns the path.
    Assumes the correct LLM is already loaded.
    """
    user_msg = (
        f"Write a bpy script to process this mesh file: {mesh_path}\n"
        f"Asset type: {asset_type}\n"
        f"Output .fbx to: {config.OUTPUT_UNITY_DIR}/"
    )
    script_content = llm_call(model, system_prompt, user_msg)

    # Strip markdown fences if present
    script_content = (
        script_content
        .removeprefix("```python")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    script_path = config.OUTPUT_BLENDER_DIR / f"{Path(mesh_path).stem}_cleanup.py"
    script_path.write_text(script_content)
    print(f"  [Blender] script saved: {script_path}")
    return str(script_path)


def run_blender_headless(script_path: str) -> bool:
    """
    Run Blender in headless mode to execute the cleanup script.
    Returns True on success, False on failure.
    Requires 'blender' to be on your PATH.
    """
    print(f"  [Blender] running headless: {script_path}")
    result = subprocess.run(
        ["blender", "--background", "--python", script_path],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  [Blender] error:\n{result.stderr[-500:]}")  # last 500 chars
        return False

    print("  [Blender] export complete")
    return True