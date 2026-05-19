from pathlib import Path
import subprocess

import config
from integrations import ollama


def generate_cleanup_script(
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
        f"Output .fbx to: {config.UNITY_DIR}/"
    )
    script_content = ollama.chat(model, system_prompt, user_msg)

    # Strip markdown fences if present
    script_content = (
        script_content
        .removeprefix("```python")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    script_path = config.SCRIPTS_DIR / f"{Path(mesh_path).stem}_cleanup.py"
    script_path.write_text(script_content)
    print(f"  [Blender] script saved: {script_path}")
    return str(script_path)


def run_headless(script_path: str) -> bool:
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