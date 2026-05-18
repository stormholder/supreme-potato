from pathlib import Path

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_API  = f"{OLLAMA_HOST}/api"
COMFYUI_HOST = "http://localhost:8188"
REQUEST_TIMEOUT     = 360
SWAP_SETTLE_TIME    = 1.5
MODEL_WARMUP_PROMPT = " "

WORKFLOW_PATH = Path("flux1_krea_dev.json")

OUTPUT_IMAGES_DIR  = Path("output_images")
OUTPUT_3D_DIR      = Path("output_3d")
OUTPUT_BLENDER_DIR = Path("blender_scripts")
OUTPUT_UNITY_DIR   = Path("Unity_Export")
MAX_RETRIES = 3

TEXT_MODEL = "qwen3.5:9b"
 
CRITIC_MODEL = "llava:13b"