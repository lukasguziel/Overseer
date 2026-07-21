"""A minimal fake ``bpy`` for CI (no Blender), the twin of the C4D-less tests.

Only the surface the code under test actually touches is modelled - object
hierarchy, categories, owning collections, selection, evaluated geometry, the
handful of ``bpy.context`` / ``bpy.data`` / ``bpy.ops`` bits ``blender/`` reads.
Everything else is a stub that returns something harmless.

Usage::

    fake = make_scene([{ "name": "Cube", "type": "MESH" }])
    install(fake)                      # sys.modules["bpy"] = fake
    ...                                # drive BScene / SceneAdapter / webapi
    uninstall()                        # remove it again (do this per test)

``make_scene`` assembles a synthetic hierarchy + collections from plain dicts so
a test never constructs the fake classes by hand.
"""
from __future__ import annotations

import contextlib
import sys

# ---------------------------------------------------------------------------
# data-block primitives
# ---------------------------------------------------------------------------


class _PropCollection(list):
    """A ``list`` that also answers Blender's ``.link()`` / ``.unlink()`` -
    used for ``collection.children`` (a ``bpy_prop_collection`` in Blender)."""

    def link(self, item) -> None:
        if item not in self:
            self.append(item)

    def unlink(self, item) -> None:
        with contextlib.suppress(ValueError):
            self.remove(item)


class _Mesh:
    """The throwaway mesh ``obj.to_mesh()`` hands back: only ``vertices`` and
    ``polygons`` (sized sequences) are read by ``readers.own_geo``."""

    def __init__(self, points: int, polys: int) -> None:
        self.vertices = [None] * points
        self.polygons = [None] * polys


class FakeObject:
    """A ``bpy.types.Object`` stand-in. Attributes are set by ``make_scene``."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.type = "MESH"
        self.parent = None
        self.children = []
        self.session_uid = 0
        self.users_collection = ()
        self.modifiers = []
        self.rigid_body = None
        self.matrix_world = None
        self.hide_viewport = False
        self._points = 0
        self._polys = 0
        self._selected = False

    # selection (real bpy takes an optional view_layer kwarg) ----------------
    def select_get(self, view_layer=None) -> bool:
        return self._selected

    def select_set(self, value, view_layer=None) -> None:
        self._selected = bool(value)

    # visibility ------------------------------------------------------------
    def visible_get(self) -> bool:
        return not self.hide_viewport

    # evaluated geometry ----------------------------------------------------
    def evaluated_get(self, _depsgraph):
        return self

    def to_mesh(self) -> _Mesh:
        return _Mesh(self._points, self._polys)

    def to_mesh_clear(self) -> None:
        pass

    def update_tag(self, **_kwargs) -> None:
        pass

    def __repr__(self) -> str:
        return "FakeObject(%r)" % self.name


class FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name
        self.name_full = name
        self.users = 0


class FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.objects = []
        self.children = _PropCollection()
        self.color_tag = "NONE"
        self.hide_viewport = False
        self.hide_render = False

    def __repr__(self) -> str:
        return "FakeCollection(%r)" % self.name


class _DataCollections:
    """``bpy.data.collections``: iterable + ``len`` + ``new`` / ``remove``.

    ``remove`` deletes the datablock and unlinks it from any parent's
    ``children`` (mirrors Blender freeing a collection)."""

    def __init__(self) -> None:
        self._items = []

    def new(self, name: str) -> FakeCollection:
        col = FakeCollection(name)
        self._items.append(col)
        return col

    def remove(self, col) -> None:
        for parent in [*self._items]:
            parent.children.unlink(col)
        if col in self._items:
            self._items.remove(col)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


# ---------------------------------------------------------------------------
# scene / context
# ---------------------------------------------------------------------------


class FakeScene:
    """``bpy.context.scene``: a flat ``objects`` list, a master ``collection``
    and dict-style custom properties (the journal round-trips through them)."""

    def __init__(self, name: str = "Scene") -> None:
        self.name = name
        self.objects = []
        self.collection = FakeCollection("Master Collection")
        self._props = {}

    def get(self, key, default=None):
        return self._props.get(key, default)

    def __getitem__(self, key):
        return self._props[key]

    def __setitem__(self, key, value) -> None:
        self._props[key] = value


class _ViewLayerObjects:
    def __init__(self) -> None:
        self.active = None


class _ViewLayer:
    def __init__(self) -> None:
        self.objects = _ViewLayerObjects()

    def update(self) -> None:
        pass


class _Workspace:
    def status_text_set(self, _text) -> None:
        pass


class _Screen:
    def __init__(self) -> None:
        self.areas = []


class _Depsgraph:
    pass


class FakeContext:
    def __init__(self, scene: FakeScene) -> None:
        self.scene = scene
        self.view_layer = _ViewLayer()
        self.screen = _Screen()
        self.workspace = _Workspace()
        self.window = None

    @property
    def selected_objects(self):
        return [o for o in self.scene.objects if o.select_get()]

    def evaluated_depsgraph_get(self) -> _Depsgraph:
        return _Depsgraph()

    @contextlib.contextmanager
    def temp_override(self, **_kwargs):
        yield


# ---------------------------------------------------------------------------
# ops / utils / path / app
# ---------------------------------------------------------------------------


class _Ed:
    def undo_push(self, message: str = "") -> None:
        pass


class _View3d:
    def view_selected(self, **_kwargs) -> None:
        pass


class _Ops:
    def __init__(self) -> None:
        self.ed = _Ed()
        self.view3d = _View3d()


class _Utils:
    def user_resource(self, _kind, path: str = "") -> str:
        return path


class _Path:
    @staticmethod
    def abspath(path: str, **_kwargs) -> str:
        return path

    @staticmethod
    def relpath(path: str, **_kwargs) -> str:
        return path


class _Timers:
    def __init__(self) -> None:
        self._registered = set()

    def is_registered(self, fn) -> bool:
        return fn in self._registered

    def register(self, fn, persistent: bool = False) -> None:
        self._registered.add(fn)


class _App:
    def __init__(self) -> None:
        self.timers = _Timers()


class FakeData:
    def __init__(self) -> None:
        self.filepath = ""
        self.objects = []
        self.materials = []
        self.collections = _DataCollections()
        self.images = []
        self.libraries = []


class FakeBpy:
    """The object injected as ``sys.modules['bpy']``."""

    def __init__(self) -> None:
        self.data = FakeData()
        self.context = FakeContext(FakeScene())
        self.ops = _Ops()
        self.utils = _Utils()
        self.path = _Path()
        self.app = _App()


# ---------------------------------------------------------------------------
# builder
# ---------------------------------------------------------------------------


def _collection_spec(spec):
    if isinstance(spec, str):
        return {"name": spec}
    return dict(spec)


def make_scene(objects, collections=None, filepath: str = "/proj/demo.blend",
               materials=None) -> FakeBpy:
    """Assemble a ``FakeBpy`` from plain dicts.

    ``objects`` items understand: ``name`` (required), ``type`` (default
    ``MESH``), ``parent`` (a name), ``collection`` (a name; else the object
    lands in the master collection), ``pts``/``polys`` (evaluated geometry),
    ``hidden``, ``selected``, ``modifiers`` (a list of objects with a ``type``
    attr) and ``session_uid``. ``collections`` items are names or dicts with
    ``name`` / ``color_tag`` / ``hide_viewport`` / ``hide_render``.
    """
    fake = FakeBpy()
    scene = fake.context.scene
    fake.data.filepath = filepath
    master = scene.collection

    for name in (materials or []):
        fake.data.materials.append(FakeMaterial(name))

    col_by_name = {}
    for raw in (collections or []):
        spec = _collection_spec(raw)
        col = fake.data.collections.new(spec["name"])
        col.color_tag = spec.get("color_tag", "NONE")
        col.hide_viewport = bool(spec.get("hide_viewport", False))
        col.hide_render = bool(spec.get("hide_render", False))
        master.children.link(col)
        col_by_name[spec["name"]] = col

    built = {}
    next_uid = 1
    for spec in objects:
        obj = FakeObject(spec["name"])
        obj.type = spec.get("type", "MESH")
        obj._points = int(spec.get("pts", 0))
        obj._polys = int(spec.get("polys", 0))
        obj.hide_viewport = bool(spec.get("hidden", False))
        obj._selected = bool(spec.get("selected", False))
        obj.modifiers = list(spec.get("modifiers", []))
        obj.session_uid = int(spec.get("session_uid", next_uid))
        next_uid += 1
        built[obj.name] = (obj, spec)

    for obj, spec in built.values():
        parent_name = spec.get("parent")
        if parent_name:
            parent = built[parent_name][0]
            obj.parent = parent
            parent.children.append(obj)
        col_name = spec.get("collection")
        if col_name and col_name in col_by_name:
            col = col_by_name[col_name]
            col.objects.append(obj)
            obj.users_collection = (col,)
        else:
            master.objects.append(obj)
            obj.users_collection = (master,)
        scene.objects.append(obj)
        fake.data.objects.append(obj)

    return fake


# ---------------------------------------------------------------------------
# install / uninstall
# ---------------------------------------------------------------------------


def install(fake: FakeBpy | None = None) -> FakeBpy:
    if fake is None:
        fake = FakeBpy()
    sys.modules["bpy"] = fake
    return fake


def uninstall() -> None:
    sys.modules.pop("bpy", None)


def reset() -> None:
    """Uninstall the fake and clear the cross-request scene cache the webapi
    parks on the ``overseer`` package, so nothing leaks between tests."""
    uninstall()
    with contextlib.suppress(Exception):
        import overseer
        getattr(overseer, "_scene_cache", {}).clear()
