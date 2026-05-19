import argparse
import yaml
from pathlib import Path
from typing import Any, Dict

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--config", type=str, help="Path to the configuration YAML file")

parser.add_argument("--ollama-host", dest="ollama_host")
parser.add_argument("--ollama-api-key", dest="ollama_api_key")
parser.add_argument("--ollama-text-model", dest="ollama_text_model")
parser.add_argument("--ollama-vision-model", dest="ollama_vision_model")
parser.add_argument("--comfyui-host", dest="comfyui_host")
parser.add_argument("--comfyui-workflow-file", dest="comfyui_workflow_file")
parser.add_argument("--trellis-host", dest="trellis_host")

defaults = {
    "ollama": {
        "host": "http://localhost:11434",
        "api_key": "",
        "text_model": "gemma4:31b",
        "vision_model": "llava:13b",
    },
    "comfyui": {
        "host": "http://localhost:8188",
        "workflow_file": "flux1_krea_dev.json",
    },
    "trellis": {
        "host": "http://localhost:7860",
    },
}

def load_yaml(config_file: str = "config.yml"):
    file_config = {}
    if Path(config_file).exists():
        with open(config_file, "r") as f:
            raw_yaml = yaml.safe_load(f) or {}
            for section, values in raw_yaml.items():
                if isinstance(values, list):
                    flat = {}
                    for item in values:
                        if isinstance(item, dict):
                            flat.update(item)
                    file_config[section] = flat
                else:
                    file_config[section] = values
    return file_config


def load_config() -> Dict[str, Any]:
    args, _ = parser.parse_known_args()

    config_file = args.config if args.config else "config.yml"
    file_config = load_yaml(config_file)

    final_config = defaults.copy()
    
    for section, values in file_config.items():
        if section in final_config and isinstance(final_config[section], dict):
            final_config[section].update(values)
        else:
            final_config[section] = values

    for arg_name, val in vars(args).items():
        if val is not None and arg_name != "config":
            if "_" in arg_name:
                section, key = arg_name.split("_", 1)
                if section in final_config and isinstance(final_config[section], dict):
                    final_config[section][key] = val
            else:
                final_config[arg_name] = val

    return final_config

_config = load_config()

config = _config
