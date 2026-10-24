"""Scene graphs, lighting and cameras. Animation values run entirely in Rust."""

from functools import cached_property
from math import pi
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import (
    ConfigDict,
    Field,
    SerializationInfo,
    TypeAdapter,
    field_serializer,
    model_validator,
    validate_call,
)

from fframes import _native
from fframes.buffers import Buffers, ImageBuffer, VideoFrames
from fframes.lottie import Lottie, LottieBinding
from fframes.media import ImageBinding, VideoBinding
from fframes.models import Frames, Model, PositiveInt, Source
from fframes.shaders import ShaderBinding
from fframes.three_d.animation import Animation, Playback
from fframes.three_d.geometry import GeometryType
from fframes.three_d.types import (
    RGB,
    Coordinate,
    Direction,
    Matrix,
    Nonnegative,
    NonnegativeValue,
    Positive,
    PositiveValue,
    Quaternion,
    Scale,
    StaticDirection,
    Unit,
    UnitValue,
    Vec2,
    Vec3,
    Vector,
    VisibilityFrames,
)
from fframes.values import Duration, Start, endpoints

_matrix: TypeAdapter[Matrix] = TypeAdapter(Matrix)
_bounds: TypeAdapter[tuple[Vec3, Vec3]] = TypeAdapter(tuple[Vec3, Vec3])


class ImageTexture(Model):
    """Decode a color image or linear data map once."""

    kind: Literal["image"] = "image"
    source: Source | ImageBuffer
    srgb: bool = True


class VideoTexture(Model):
    """Decode video on the scene clock, with an optional smaller texture resolution."""

    kind: Literal["video"] = "video"
    source: Source | VideoFrames
    offset: Start = 0.0
    loop: bool = False
    size: tuple[PositiveInt, PositiveInt] | None = None


class SvgTexture(Model):
    """SVG frames rendered into a texture, holding the last frame after EOF."""

    kind: Literal["svg"] = "svg"
    frames: Frames
    fps: PositiveInt = 30
    size: tuple[PositiveInt, PositiveInt]
    fonts: tuple[Source, ...] = ()
    load_system_fonts: bool = False
    scenes: tuple["SceneBinding", ...] = ()
    images: tuple[ImageBinding, ...] = ()
    clips: tuple[VideoBinding, ...] = ()
    shaders: tuple[ShaderBinding, ...] = ()
    lotties: tuple[LottieBinding, ...] = ()


class LottieTexture(Model):
    """Render a Lottie animation onto a mesh on its scene's clock."""

    kind: Literal["lottie"] = "lottie"
    animation: Lottie
    size: tuple[PositiveInt, PositiveInt]


class PixelTexture(Model):
    """Straight RGBA8 pixels, copied once into native mipmaps during compilation."""

    kind: Literal["pixels"] = "pixels"
    size: tuple[PositiveInt, PositiveInt]
    pixels: tuple[Annotated[int, Field(ge=0, le=255)], ...]
    srgb: bool = True

    @model_validator(mode="after")
    def check_length(self) -> Self:
        """Reject padded or truncated pixel buffers."""
        if len(self.pixels) != self.size[0] * self.size[1] * 4:
            raise ValueError("pixels must contain width * height * 4 RGBA8 values")
        return self


class SceneTexture(Model):
    """Another 3D scene rendered as a texture, using the same local clock."""

    kind: Literal["scene"] = "scene"
    renderer: "Renderer"


class _CompositionTexture(Model):
    """Internal serialized plan produced by compose.Video.texture()."""

    kind: Literal["composition"] = "composition"
    plan: str = Field(repr=False)
    buffers: tuple[tuple[str, bytes], ...] = Field(default=(), exclude=True, repr=False)

    @field_serializer("plan")
    def transfer_buffers(self, plan: str, info: SerializationInfo[object]) -> str:
        """Retain nested payloads in the outer compilation context."""
        if self.buffers:
            context = info.context
            if not isinstance(context, Buffers):
                raise ValueError("binary media requires video or renderer compilation")
            context.data.update(self.buffers)
        return plan


TextureSource: TypeAlias = Annotated[
    ImageTexture
    | PixelTexture
    | VideoTexture
    | SvgTexture
    | SceneTexture
    | LottieTexture
    | _CompositionTexture,
    Field(discriminator="kind"),
]


class Texture(Model):
    """A repeating, mipmapped texture. UV transform is repeat * uv + offset."""

    source: TextureSource
    repeat: Vec2 = (1.0, 1.0)
    offset: Vec2 = (0.0, 0.0)


class Material(Model):
    """PBR material; hex colors are sRGB, RGB tuples are linear HDR intensities."""

    shading: Literal["standard", "unlit", "shadow_catcher", "normals"] = "standard"
    color: RGB = "#ffffff"
    opacity: UnitValue = 1.0
    metalness: UnitValue = 0.0
    roughness: UnitValue = 0.5
    emissive: RGB = "#000000"
    emissive_intensity: NonnegativeValue = 1.0
    clearcoat: UnitValue = 0.0
    clearcoat_roughness: UnitValue = 0.05
    reflection: UnitValue = 0.0
    env_intensity: NonnegativeValue = 1.0
    flat_shading: bool = False
    side: Literal["front", "back", "double"] = "front"
    blending: Literal["normal", "additive"] = "normal"
    transparent: bool = False
    depth_write: bool = False
    map: Texture | None = None
    emissive_map: Texture | None = None
    metal_rough_map: Texture | None = None
    normal_map: Texture | None = None
    normal_scale: NonnegativeValue = 1.0
    ao_map: Texture | None = None
    fog: bool = True


class Shadow(Model):
    """Directional-light shadow map. Point and spot lights do not cast shadows upstream."""

    map_size: Annotated[int, Field(ge=16, le=8192)] = 2048
    softness: Nonnegative = 1.5
    strength: Unit = 1.0
    bias: Nonnegative = 1.5
    bounds: tuple[Vec3, Vec3] | None = None


class LightSettings(Model):
    """Shared light color and intensity."""

    color: RGB = "#ffffff"
    intensity: NonnegativeValue = 1.0


class AmbientLight(LightSettings):
    """Uniform illumination from all directions."""

    kind: Literal["ambient"] = "ambient"


class HemisphereLight(Model):
    """Sky and ground illumination, interpolated by surface normal."""

    kind: Literal["hemisphere"] = "hemisphere"
    sky: RGB = "#ffffff"
    ground: RGB = "#444444"
    intensity: NonnegativeValue = 1.0


class DirectionalLight(LightSettings):
    """Parallel light rays travelling along direction, optionally casting shadows."""

    kind: Literal["directional"] = "directional"
    direction: Direction = (-1.0, -1.0, -1.0)
    shadow: Shadow | None = None


class AttenuatedLight(LightSettings):
    """Distance falloff shared by point and spot lights."""

    distance: NonnegativeValue = 0.0
    decay: NonnegativeValue = 2.0


class PointLight(AttenuatedLight):
    """Omnidirectional light at its node position; distance=0 has no cutoff."""

    kind: Literal["point"] = "point"


class SpotLight(AttenuatedLight):
    """A spotlight with a cone angle in radians."""

    kind: Literal["spot"] = "spot"
    direction: Direction = (0.0, -1.0, 0.0)
    angle: Annotated[float, Field(gt=0, le=pi / 2, allow_inf_nan=False)] = pi / 3
    penumbra: UnitValue = 0.0


LightType: TypeAlias = Annotated[
    AmbientLight | HemisphereLight | DirectionalLight | PointLight | SpotLight,
    Field(discriminator="kind"),
]


class Transform(Model):
    """Local transform: radians for Euler XYZ, quaternion in (x, y, z, w) order."""

    name: str | None = None
    position: Vector = (0.0, 0.0, 0.0)
    rotation: Vector = (0.0, 0.0, 0.0)
    quaternion: Quaternion | None = None
    scale: Scale = (1.0, 1.0, 1.0)
    visible: bool | VisibilityFrames = True

    @model_validator(mode="after")
    def check_rotation(self) -> Self:
        """Reject simultaneous Euler and quaternion inputs."""
        if self.quaternion is not None:
            if self.rotation != (0.0, 0.0, 0.0):
                raise ValueError("use rotation or quaternion, not both")
            if sum(v * v for v in self.quaternion) < 1e-12:
                raise ValueError("quaternion must have nonzero length")
        return self


class Group(Transform):
    """A pivot and visibility boundary for child nodes."""

    kind: Literal["group"] = "group"
    children: tuple["Node", ...] = ()


class Skin(Model):
    """Joint names in this scene and their column-major inverse bind matrices."""

    joints: Annotated[tuple[str, ...], Field(min_length=1)]
    inverse_bind_matrices: tuple[Matrix, ...]

    @model_validator(mode="after")
    def check_matrices(self) -> Self:
        """Every joint needs its own inverse bind transform."""
        if len(self.joints) != len(self.inverse_bind_matrices):
            raise ValueError("inverse_bind_matrices must have one matrix per joint")
        return self


class Instances(Model):
    """Rigid copies sharing geometry and material; matrices are column-major."""

    transforms: Annotated[tuple[Matrix, ...], Field(min_length=1)]
    colors: tuple[RGB, ...] = ()

    @model_validator(mode="after")
    def check_colors(self) -> Self:
        """Do not silently pad or discard instance colors."""
        if self.colors and len(self.colors) != len(self.transforms):
            raise ValueError("colors must be empty or have one color per instance")
        return self


class Mesh(Transform):
    """A geometry and material; transforms and material scalars may be animated."""

    kind: Literal["mesh"] = "mesh"
    geometry: GeometryType
    material: Material = Field(default_factory=Material)
    cast_shadow: bool = True
    receive_shadow: bool = True
    skin: Skin | None = None
    morph_weights: tuple[Coordinate, ...] = ()
    instances: Instances | None = None
    children: tuple["Node", ...] = ()

    @model_validator(mode="after")
    def check_instances(self) -> Self:
        """Upstream instancing applies only to rigid meshes."""
        if self.instances is not None and (self.skin is not None or self.morph_weights):
            raise ValueError("instances cannot be combined with skin or morph_weights")
        return self


class Light(Transform):
    """Position and orient a light in the node hierarchy."""

    kind: Literal["light"] = "light"
    light: LightType


class Particle(Model):
    """An emissive circular sprite, occluded by opaque geometry."""

    position: Vector
    size: PositiveValue = 0.05
    color: RGB = "#ffffff"
    opacity: UnitValue = 1.0


class Particles(Transform):
    """A batch of animated sprites, evaluated in native code."""

    kind: Literal["particles"] = "particles"
    items: tuple[Particle, ...]
    blending: Literal["normal", "additive"] = "additive"


class Pose(Transform):
    """Override a named model node after its animation clips are applied."""

    name: str


class MaterialOverride(Model):
    """Replace the material of a named mesh inside an imported model."""

    node: Annotated[str, Field(min_length=1)]
    material: Material


class Model3D(Transform):
    """glTF/GLB meshes, materials, skins and clips. External files stay within its directory."""

    kind: Literal["model"] = "model"
    source: Source
    animations: tuple[Playback, ...] = ()
    poses: tuple[Pose, ...] = ()
    materials: tuple[MaterialOverride, ...] = ()
    children: tuple["Node", ...] = ()

    @model_validator(mode="after")
    def check_materials(self) -> Self:
        """Keep each target unambiguous."""
        names = [item.node for item in self.materials]
        if len(names) != len(set(names)):
            raise ValueError("materials requires unique mesh node names")
        return self


Node: TypeAlias = Annotated[Group | Mesh | Light | Particles | Model3D, Field(discriminator="kind")]


class SoftBox(Model):
    """Rectangular area of light in the studio environment, expressed in radians."""

    direction: StaticDirection
    half_size: tuple[Positive, Positive] = (0.2, 0.4)
    color: RGB = (3.0, 3.0, 3.0)


class Studio(Model):
    """Procedural environment illumination; None uses upstream's studio softboxes."""

    kind: Literal["studio"] = "studio"
    intensity: NonnegativeValue = 1.0
    rotation: Coordinate = 0.0
    sky: RGB = (0.05, 0.055, 0.065)
    horizon: RGB = (0.12, 0.12, 0.13)
    ground: RGB = (0.02, 0.02, 0.022)
    softboxes: tuple[SoftBox, ...] | None = None


class EnvironmentPixels(Model):
    """A linear HDR panorama in row-major RGB order; compilation copies its data."""

    size: tuple[PositiveInt, PositiveInt]
    pixels: tuple[tuple[Nonnegative, Nonnegative, Nonnegative], ...]

    @model_validator(mode="after")
    def check_length(self) -> Self:
        """Reject incomplete panorama data."""
        if len(self.pixels) != self.size[0] * self.size[1]:
            raise ValueError("environment pixels must contain width * height RGB values")
        return self


class EnvironmentMap(Model):
    """Equirectangular HDR or color image used for image-based lighting."""

    kind: Literal["map"] = "map"
    source: Source | EnvironmentPixels
    intensity: NonnegativeValue = 1.0
    rotation: Coordinate = 0.0


class EnvironmentBackground(Model):
    """Show the scene's environment behind its geometry."""

    kind: Literal["environment"] = "environment"
    blur: Unit = 0.0


class LinearFog(Model):
    """Blend toward color between near and far world-space distances."""

    kind: Literal["linear"] = "linear"
    color: RGB
    near: Nonnegative = 1.0
    far: Positive = 100.0

    @model_validator(mode="after")
    def check_range(self) -> Self:
        """Reject an empty or inverted fog interval."""
        if self.far <= self.near:
            raise ValueError("fog far must be greater than near")
        return self


class ExponentialFog(Model):
    """Exponential squared fog with a world-space density."""

    kind: Literal["exp2"] = "exp2"
    color: RGB
    density: Nonnegative = 0.02


class Reflector(Model):
    """One reflection plane per scene. Materials opt in through reflection."""

    point: Vec3 = (0.0, 0.0, 0.0)
    normal: StaticDirection = (0.0, 1.0, 0.0)
    scale: Annotated[float, Field(ge=0.1, le=1, allow_inf_nan=False)] = 0.5


class Scene(Model):
    """Reusable hierarchy. Identical geometry recipes share native allocations."""

    nodes: tuple[Node, ...] = ()
    animations: tuple[Animation, ...] = ()
    background: RGB | EnvironmentBackground | None = None
    environment: Annotated[Studio | EnvironmentMap, Field(discriminator="kind")] | None = None
    fog: Annotated[LinearFog | ExponentialFog, Field(discriminator="kind")] | None = None
    reflector: Reflector | None = None


class SceneFrames(Model):
    """Complete scene states, selected at fps and held after the last frame.

    Use for topology, hierarchy or material changes. Animations within each
    state keep the renderer's clock. Native compilation shares repeated geometry.
    """

    frames: Annotated[tuple[Scene, ...], Field(min_length=1)]
    fps: PositiveInt = 30


class Focus(Model):
    """Depth of field: distance in world units, far-background blur in pixels at 1080p."""

    distance: PositiveValue | None = None
    point: Vector | None = None
    blur: NonnegativeValue = 8.0

    @model_validator(mode="after")
    def check_target(self) -> Self:
        """Select one focus definition, with no silently replaced parameter."""
        if (self.distance is None) == (self.point is None):
            raise ValueError("focus requires exactly one of distance or point")
        return self


class Orbit(Model):
    """Orbit around the camera target: azimuth and elevation are in degrees."""

    distance: PositiveValue
    azimuth: Coordinate = 0.0
    elevation: Coordinate = 0.0


class Camera(Model):
    """Y-up camera looking at target. fov is in degrees; roll is in radians."""

    position: Vector = (0.0, 0.0, 5.0)
    orbit: Orbit | None = None
    target: Vector = (0.0, 0.0, 0.0)
    up: StaticDirection = (0.0, 1.0, 0.0)
    fov: PositiveValue = 45.0
    ortho_height: PositiveValue | None = None
    near: Positive = 0.1
    far: Positive = 1000.0
    roll: Coordinate = 0.0
    shift: Vec2 = (0.0, 0.0)
    focus: Focus | None = None

    @model_validator(mode="after")
    def check_frustum(self) -> Self:
        """Reject singular projection settings."""
        if self.near >= self.far:
            raise ValueError("camera near must be smaller than far")
        low, high = endpoints(self.fov)
        if low < 0.001 or high > 179.999:
            raise ValueError("camera fov must stay between 0.001 and 179.999 degrees")
        if self.orbit is not None and self.position != (0.0, 0.0, 5.0):
            raise ValueError("orbit computes position; provide orbit or position")
        if self.orbit is None and self.position == self.target:
            raise ValueError("camera position and target must differ")
        return self


class Bloom(Model):
    """Glow from HDR highlights, applied before tone mapping."""

    threshold: Nonnegative = 1.0
    strength: Nonnegative = 0.8
    radius: Unit = 0.6


class RenderSettings(Model):
    """3D rasterizer settings, independent of the enclosing SVG backend."""

    device: Literal["cpu", "gpu", "auto"] = "auto"
    antialias: bool = True
    exposure: Positive = 1.0
    tone_mapping: Literal["aces", "neutral", "linear"] = "aces"
    bloom: Bloom | None = None
    motion_samples: Annotated[int, Field(ge=1, le=64)] = 1
    shutter: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] = 0.5


class Renderer(Model):
    """Compile a scene and camera. fps applies to standalone previews; videos supply their clock."""

    scene: Scene | SceneFrames
    camera: Camera = Camera()
    size: tuple[PositiveInt, PositiveInt] = (1280, 720)
    fps: PositiveInt = 30
    settings: RenderSettings = RenderSettings()

    @cached_property
    def _compiled(self) -> "_native.Renderer3D":
        buffers = Buffers()
        plan = self.model_dump_json(context=buffers)
        return _native.compile_3d(plan, buffers.data)

    @validate_call(config=ConfigDict(strict=True))
    def rgba(self, time: Start = 0.0) -> bytes:
        """Straight-alpha RGBA8; allocates one Python bytes buffer on readback."""
        return self._compiled.rgba(time)

    @property
    def uses_gpu(self) -> bool:
        """Report the device actually selected; device='gpu' fails if unavailable."""
        return self._compiled.uses_gpu()

    @validate_call(config=ConfigDict(strict=True))
    def project(self, point: Vec3, *, time: Start = 0.0) -> Vec3 | None:
        """World point to (pixel x, pixel y, depth), or None behind the camera."""
        return self._compiled.project(point, time)

    @validate_call(config=ConfigDict(strict=True))
    def world_position(self, name: str, *, time: Start = 0.0) -> Vec3:
        """World-space position of a uniquely named node."""
        return self._compiled.world_position(name, time)

    @validate_call(config=ConfigDict(strict=True))
    def local_to_world(self, name: str, point: Vec3, *, time: Start = 0.0) -> Vec3:
        """Transform a point from a named node's local coordinates to world coordinates."""
        return self._compiled.local_to_world(name, point, time)

    @validate_call(config=ConfigDict(strict=True))
    def world_matrix(self, name: str, *, time: Start = 0.0) -> Matrix:
        """Return the node's column-major world transform."""
        return _matrix.validate_python(tuple(self._compiled.world_matrix(name, time)))

    @validate_call(config=ConfigDict(strict=True))
    def bounds(self, name: str, *, time: Start = 0.0) -> tuple[Vec3, Vec3] | None:
        """World bounds of a subtree's undeformed geometry, or None for an empty subtree."""
        bounds = self._compiled.bounds(name, time)
        return None if bounds is None else _bounds.validate_python(bounds)

    @validate_call(config=ConfigDict(strict=True))
    def pixel_size(self, point: Vec3, size: Positive, *, time: Start = 0.0) -> float:
        """Project a world-space size into pixels at point's depth."""
        return self._compiled.pixel_size(point, size, time)


class SceneBinding(Model):
    """Expose a 3D render as href='scene:name' in the low-level SVG API."""

    name: Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
    renderer: Renderer
    start_at: Start = 0.0
    duration: Duration | None = None


for _schema in (
    SvgTexture,
    SceneTexture,
    Texture,
    Material,
    Group,
    Mesh,
    Model3D,
    Scene,
    Renderer,
    SceneBinding,
):
    _schema.model_rebuild()
