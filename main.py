
from pipeline import (
    ollama_swap,
    ollama_unload,
    llm_call,
    llm_call_json,
    comfyui_generate,
    comfyui_free_vram,
)
from prompts import SYSTEM_PROMPTS
from config import (
    MAX_RETRIES,
    TEXT_MODEL,
    CRITIC_MODEL
)
import json

def generate_prompt(brief: str, model: str = TEXT_MODEL):
    print("\n[1/5] Enforcing style...")
    current_model = ollama_swap(None, model)
 
    refined = llm_call(
        current_model,
        SYSTEM_PROMPTS["style_enforcer"],
        brief,
    )
    print(f"      Refined: {refined}")
    print("\n[2/5] Writing image prompts...")
    prompts = llm_call_json(
        current_model,
        SYSTEM_PROMPTS["prompt_writer"],
        refined,
    )
    print(f"      Views planned: {[k for k, v in prompts.items() if v and v != 'null']}")
 
    # Unload LLM before loading FLUX
    ollama_unload(current_model)
    current_model = None
    return refined, prompts

    
def generate_asset(brief: str, asset_type: str = "prop_small") -> dict:
    """
    Full pipeline: brief → style enforcement → image prompts → image generation
    → VLM critique (with retry) → 3D mesh → Blender cleanup → Unity .fbx
 
    Args:
        brief:      Plain-language description of the asset you want.
        asset_type: One of "character", "prop_small", "prop_large", "environment"
 
    Returns:
        dict with keys: brief, refined_brief, prompts, images, mesh, score
    """
    print(f"\n{'='*55}")
    print(f"  Asset: {brief}")
    print(f"  Type:  {asset_type}")
    print(f"{'='*55}")

    result = json.load(open("./test_prompt.json"))

    print(result)
 
    print("\n[3/5] Generating images + critique loop...")
 
    active_prompts = {k: v for k, v in result["prompts"].items() if v and v != "null"}
    images = {}
    critique = {"passed": False, "score": 0, "issues": [], "suggested_fix": ""}
    best_view_key = "three_quarter" if "three_quarter" in active_prompts else "front"
 
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n  Attempt {attempt}/{MAX_RETRIES}")
 
        for view, prompt_text in active_prompts.items():
            print(f"    → generating {view} view...")
            images[view] = comfyui_generate(prompt_text)
 
        result["images"] = images

        comfyui_free_vram()
 
        current_model = ollama_swap(None, CRITIC_MODEL)
 
        critique_input = (
            f"Original brief: {brief}\n"
            f"Refined brief: {refined}\n"
            f"Views generated: {list(images.keys())}\n"
            f"Best view filename: {images.get(best_view_key, 'N/A')}\n"
            f"Prompts used:\n{json.dumps(active_prompts, indent=2)}"
        )
 
        critique = llm_call_json(
            current_model,
            SYSTEM_PROMPTS["critic"],
            critique_input,
        )
 
        score = critique.get("score", 0)
        passed = critique.get("passed", False)
        issues = critique.get("issues", [])
        result["score"] = score
 
        print(f"    Critic score: {score}/10 — {'✓ passed' if passed else '✗ failed'}")
        if issues:
            print(f"    Issues: {issues}")
 
        if passed:
            ollama_unload(current_model)
            current_model = None
            break
 
        if attempt < MAX_RETRIES:
            print(f"    Refining prompt...")
            ollama_unload(current_model)
            current_model = ollama_swap(None, TEXT_MODEL)
 
            refined_prompt = llm_call(
                current_model,
                SYSTEM_PROMPTS["prompt_refiner"],
                f"Prompt: {active_prompts.get(best_view_key, '')}\n"
                f"Issues: {json.dumps(issues)}",
            )
            active_prompts[best_view_key] = refined_prompt
 
            ollama_unload(current_model)
            current_model = None
 
    return result
 


if __name__ == "__main__":
    generate_asset(
        brief="a wall-mounted communication terminal, old and visibly damaged",
        asset_type="prop_large",
    )