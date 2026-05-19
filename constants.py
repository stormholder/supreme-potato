
from pathlib import Path

REQUEST_TIMEOUT     = 360
MAX_RETRIES = 3
SWAP_SETTLE_TIME    = 1.5
MODEL_WARMUP_PROMPT = " "

TRI_TARGETS = {
    "character":    500,
    "prop_small":   150,
    "prop_large":   400,
    "environment":  400,
}

OUTPUT_DIR       = Path("pipeline_output")
IMAGES_DIR       = OUTPUT_DIR / "images"
MESHES_DIR       = OUTPUT_DIR / "meshes"
SCRIPTS_DIR      = OUTPUT_DIR / "blender_scripts"
UNITY_DIR        = OUTPUT_DIR / "Unity_Export"
CONTEXTS_DIR     = OUTPUT_DIR / "contexts"