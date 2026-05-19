from pathlib import Path

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_API  = f"{OLLAMA_HOST}/api"
COMFYUI_HOST = "http://localhost:8188"
REQUEST_TIMEOUT     = 360
SWAP_SETTLE_TIME    = 1.5
MODEL_WARMUP_PROMPT = " "

WORKFLOW_PATH = Path("flux1_krea_dev.json")

OUTPUT_DIR       = Path("pipeline_output")
IMAGES_DIR       = OUTPUT_DIR / "images"
MESHES_DIR       = OUTPUT_DIR / "meshes"
SCRIPTS_DIR      = OUTPUT_DIR / "blender_scripts"
UNITY_DIR        = OUTPUT_DIR / "Unity_Export"
CONTEXTS_DIR     = OUTPUT_DIR / "contexts"
 
for _d in [IMAGES_DIR, MESHES_DIR, SCRIPTS_DIR, UNITY_DIR, CONTEXTS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

MAX_RETRIES = 3

TEXT_MODEL = "qwen3.5:9b"
 
CRITIC_MODEL = "llava:13b"