from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import json


@dataclass
class PipelineContext:
    brief: str
    asset_type: str
    refined_brief: Optional[str] = None
    prompts: Optional[str] = None
    images: dict = field(default_factory=dict)
    critique: dict = field(default_factory=dict)
    mesh_path: Optional[str] = None
    blender_script_path: Optional[str] = None
    fbx_path: Optional[str] = None
    score: Optional[int] = None
    completed_stages: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def save(self, path: str | Path):
        path = Path(path)

        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(
            json.dumps(asdict(self), indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "PipelineContext":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)