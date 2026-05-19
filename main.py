import config

from constants import CONTEXTS_DIR, IMAGES_DIR, MESHES_DIR, SCRIPTS_DIR, UNITY_DIR
from pipeline.asset_pipeline import AssetPipeline
from pipeline.context import PipelineContext

if __name__ == "__main__":
    for _d in [IMAGES_DIR, MESHES_DIR, SCRIPTS_DIR, UNITY_DIR, CONTEXTS_DIR]:
        _d.mkdir(parents=True, exist_ok=True)

    ctx = PipelineContext(
        brief="ammo crate",
        asset_type="prop_small",
    )
    pipe = AssetPipeline(ctx)
    pipe.run_stage("style_enforcer")
    pipe.run_stage("prompt_writer")