from __future__ import annotations

import json
from pathlib import Path

import config
from constants import UNITY_DIR
from prompts.system_prompts import SYSTEM_PROMPTS

from pipeline.context import PipelineContext
from pipeline.registry import STAGES, REQUIRES

from integrations import ollama
from integrations import comfyui
from integrations import trellis
from integrations import blender


class AssetPipeline:

    def __init__(
        self,
        ctx: PipelineContext,
        run_dir: str | Path | None = None,
    ):
        self.ctx = ctx

        self.current_model = None

        if run_dir is None:
            safe_name = (
                ctx.brief.lower()
                .replace(" ", "_")
                .replace(",", "")
            )

            run_dir = Path("runs") / safe_name

        self.run_dir = Path(run_dir)

        self.run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.checkpoint_path = self.run_dir / "context.json"

    def save_checkpoint(self):
        self.ctx.save(self.checkpoint_path)

    def validate_requirements(self, stage_name: str):
        required = REQUIRES.get(stage_name, [])

        for field_name in required:

            value = getattr(self.ctx, field_name)

            if value in [None, {}, [], ""]:
                raise RuntimeError(
                    f"Stage '{stage_name}' requires "
                    f"context field '{field_name}'"
                )

    def run_stage(self, stage_name: str):
        print(f"\n=== STAGE: {stage_name} ===")

        self.validate_requirements(stage_name)

        fn = getattr(self, f"stage_{stage_name}")

        fn()

        if stage_name not in self.ctx.completed_stages:
            self.ctx.completed_stages.append(stage_name)

        self.save_checkpoint()

    def run_all(self):
        for stage in STAGES:
            self.run_stage(stage)

    def run_from(self, stage_name: str):
        start = STAGES.index(stage_name)

        for stage in STAGES[start:]:
            self.run_stage(stage)

    def stage_style_enforcer(self):

        self.current_model = ollama.swap_model(
            self.current_model,
            config.config['ollama']['text_model'],
        )

        refined = ollama.chat(
            config.config['ollama']['text_model'],
            SYSTEM_PROMPTS["style_enforcer"],
            self.ctx.brief,
        )

        self.ctx.refined_brief = refined

        print(refined)

    def stage_prompt_writer(self):

        prompts = ollama.chat(
            config.config['ollama']['text_model'],
            SYSTEM_PROMPTS["prompt_writer"],
            self.ctx.refined_brief or "",
        )

        self.ctx.prompts = prompts

        print(prompts)

    def stage_generate_images(self):

        ollama.unload_model(config.config['ollama']['text_model'])

        self.current_model = None

        if not self.ctx.prompts:
            return

        self.ctx.images = comfyui.generate_image(self.ctx.prompts)

        comfyui.free_vram()

    def stage_critic(self):

        self.current_model = ollama.swap_model(
            self.current_model,
            config.config['ollama']['vision_model'],
        )

        critique_input = (
            f"Original brief:\n{self.ctx.brief}\n\n"
            f"Refined brief:\n{self.ctx.refined_brief}\n\n"
            f"Images:\n{json.dumps(self.ctx.images, indent=2)}\n\n"
            f"Prompts:\n{json.dumps(self.ctx.prompts, indent=2)}"
        )

        critique = ollama.chat_json(
            config.config['ollama']['vision_model'],
            SYSTEM_PROMPTS["critic"],
            critique_input,
        )

        self.ctx.critique = critique

        self.ctx.score = critique.get("score")

        print(json.dumps(critique, indent=2))

    def stage_refine_prompts(self):

        issues = self.ctx.critique.get("issues", [])

        if not issues:
            print("No issues detected")
            return

        self.current_model = ollama.swap_model(
            self.current_model,
            config.config['ollama']['text_model'],
        )


        refined = ollama.chat(
            config.config['ollama']['text_model'],
            SYSTEM_PROMPTS["prompt_refiner"],
            (
                f"Prompt:\n{self.ctx.prompts}\n\n"
                f"Issues:\n{json.dumps(issues, indent=2)}"
            ),
        )

        self.ctx.prompts = refined

        print(refined)

    def stage_generate_3d(self):

        best_image = (
            self.ctx.images.get("three_quarter")
            or next(iter(self.ctx.images.values()))
        )

        mesh_path = trellis.generate_3d(
            best_image,
            self.ctx.asset_type,
        )

        self.ctx.mesh_path = mesh_path

        print(mesh_path)

    def stage_blender_cleanup(self):

        self.current_model = ollama.swap_model(
            self.current_model,
            config.config['ollama']['text_model'],
        )

        script_path = blender.generate_cleanup_script(
            model=config.config['ollama']['text_model'],
            system_prompt=SYSTEM_PROMPTS["blender_scripter"],
            mesh_path=self.ctx.mesh_path or "",
            asset_type=self.ctx.asset_type,
        )

        self.ctx.blender_script_path = script_path

        success = blender.run_headless(script_path)

        if success:

            fbx_path = (
                Path(UNITY_DIR)
                / Path(self.ctx.mesh_path or "").with_suffix(".fbx").name
            )

            self.ctx.fbx_path = str(fbx_path)

            print(f"FBX exported: {fbx_path}")