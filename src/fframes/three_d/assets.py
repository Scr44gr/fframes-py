"""Inspect model assets before selecting nodes or animation clips."""

from pydantic import ConfigDict, validate_call

from fframes import _native
from fframes.models import Index, Model, Source
from fframes.three_d.types import Nonnegative, Vec3


class ClipInfo(Model):
    """A named glTF animation, its duration in seconds and channel count."""

    name: str
    duration: Nonnegative
    channels: Index


class ModelInfo(Model):
    """Named glTF nodes, animation clips and undeformed world bounds."""

    nodes: tuple[str, ...]
    animations: tuple[ClipInfo, ...]
    meshes: Index
    bounds: tuple[Vec3, Vec3] | None


@validate_call(config=ConfigDict(strict=True))
def probe_model(source: Source) -> ModelInfo:
    """Read glTF/GLB and resolve local assets inside the model's directory."""
    return ModelInfo.model_validate_json(_native.model_info(str(source)))
