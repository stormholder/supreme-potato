import config

from pipeline.asset_pipeline import AssetPipeline
from pipeline.context import PipelineContext


if __name__ == "__main__":
    ctx = PipelineContext(
        brief="ammo crate",
        asset_type="prop_small",
    )
    pipe = AssetPipeline(ctx)
    pipe.run_stage("style_enforcer")
    pipe.run_stage("prompt_writer")