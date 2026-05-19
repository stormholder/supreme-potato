from pathlib import Path

import requests

import config
from integrations import comfyui


def generate_3d(image_filename: str, asset_type: str) -> str:
    """
    Submit an image to a locally running Trellis server for mesh generation.
    Returns path to the saved .glb file.

    Trellis setup: https://github.com/microsoft/TRELLIS
    Default port: 7860. Run AFTER unloading FLUX to free VRAM.

    tri_targets are used as the simplify parameter — Trellis interprets
    lower values as more aggressive decimation.
    """
    from prompts.system_prompts import TRI_TARGETS
    tri_target = TRI_TARGETS.get(asset_type, 300)

    image_bytes = comfyui.download_image(image_filename)

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

    out_path = config.MESHES_DIR / f"{Path(image_filename).stem}.glb"
    out_path.write_bytes(response.content)
    print(f"  [3D] mesh saved: {out_path}")
    return str(out_path)