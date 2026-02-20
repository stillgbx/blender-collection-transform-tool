"""
Collection Transform Tool — Operators

BCTT_OT_apply_transform: applies a world-space transform (location + rotation + scale)
to all root objects of the collection currently selected in the Outliner.

Pivot point
-----------
The pivot used for rotation and scale is read from Blender's own
`context.scene.tool_settings.transform_pivot_point`, so it matches the pivot
the user has selected in the 3D Viewport header. All five Blender pivot modes
are supported:

  MEDIAN_POINT       Average of all object origins in the collection.
  BOUNDING_BOX_CENTER  Center of the world-space bounding box of the collection.
  CURSOR             Current 3D cursor position.
  INDIVIDUAL_ORIGINS Each root object rotates/scales around its own origin.
  ACTIVE_ELEMENT     Active object's origin (falls back to median if none).

Algorithm (uniform pivot modes)
--------------------------------
Only "root" objects are transformed directly: objects whose parent is either None
or not part of the collection (recursively). Child objects follow automatically
via Blender's parent-child mechanism.

    full = T_translate  @  T_pivot  @  R  @  S  @  T_pivot_inv

Where:
  - T_translate  : world translation matrix
  - T_pivot      : translate to pivot origin
  - R            : Rz @ Ry @ Rx  (world XYZ Euler order, Z applied outermost)
  - S            : per-axis scale
  - T_pivot_inv  : translate back from pivot origin

The pivot only affects R and S, not T_translate.

Algorithm (INDIVIDUAL_ORIGINS)
-------------------------------
Each root object uses its own world origin as pivot. Translation is still uniform.
Pivots are captured before any object is modified to avoid ordering issues.

Undo is handled entirely by Blender via bl_options = {'UNDO'}.
"""

import bpy
from bpy.types import Operator
from mathutils import Matrix, Vector


# ── Collection helpers ────────────────────────────────────────────────────────

def _collect_all_objects(collection: bpy.types.Collection, result: set) -> None:
    """Recursively collect all objects from a collection and its sub-collections."""
    for obj in collection.objects:
        result.add(obj)
    for child_col in collection.children:
        _collect_all_objects(child_col, result)


def _get_root_objects(all_objects: set) -> list:
    """
    Return objects whose parent is None or whose parent is NOT in the collection.
    These are the only objects that need to be transformed directly.
    """
    return [obj for obj in all_objects
            if obj.parent is None or obj.parent not in all_objects]


def _get_selected_collection(context: bpy.types.Context):
    """
    Return the first Collection selected in the Outliner, or None.
    Uses context.temp_override to read selected_ids from the Outliner area.
    """
    for area in context.screen.areas:
        if area.type != 'OUTLINER':
            continue
        for region in area.regions:
            if region.type != 'WINDOW':
                continue
            with context.temp_override(area=area, region=region):
                for item in getattr(context, 'selected_ids', []):
                    if isinstance(item, bpy.types.Collection):
                        return item
    return None


# ── Pivot helpers ─────────────────────────────────────────────────────────────

def _median_center(objects) -> Vector:
    """Average of world origins of the given objects."""
    if not objects:
        return Vector((0.0, 0.0, 0.0))
    total = Vector((0.0, 0.0, 0.0))
    for obj in objects:
        total += obj.matrix_world.translation
    return total / len(objects)


def _bounding_box_center(objects) -> Vector:
    """World-space center of the bounding box encompassing all objects."""
    inf = float('inf')
    mn = Vector((inf, inf, inf))
    mx = Vector((-inf, -inf, -inf))

    for obj in objects:
        if hasattr(obj, 'bound_box') and obj.bound_box:
            for v in obj.bound_box:
                world_v = obj.matrix_world @ Vector(v)
                for i in range(3):
                    mn[i] = min(mn[i], world_v[i])
                    mx[i] = max(mx[i], world_v[i])
        else:
            # Empties, lights, cameras: use origin only
            co = obj.matrix_world.translation
            for i in range(3):
                mn[i] = min(mn[i], co[i])
                mx[i] = max(mx[i], co[i])

    if mn.x == inf:
        return Vector((0.0, 0.0, 0.0))
    return (mn + mx) / 2


# ── Core transform ────────────────────────────────────────────────────────────

def _build_rotation_scale(rot_rad: Vector, scale: Vector) -> Matrix:
    """Build the combined R @ S matrix (no translation, no pivot)."""
    Rx = Matrix.Rotation(rot_rad.x, 4, 'X')
    Ry = Matrix.Rotation(rot_rad.y, 4, 'Y')
    Rz = Matrix.Rotation(rot_rad.z, 4, 'Z')
    R = Rz @ Ry @ Rx

    Sx = Matrix.Scale(scale.x, 4, (1.0, 0.0, 0.0))
    Sy = Matrix.Scale(scale.y, 4, (0.0, 1.0, 0.0))
    Sz = Matrix.Scale(scale.z, 4, (0.0, 0.0, 1.0))
    S = Sx @ Sy @ Sz

    return R @ S


def _build_full_transform(loc: Vector, RS: Matrix, pivot: Vector) -> Matrix:
    """
    Combine translation + rotation/scale-around-pivot into a single 4x4 matrix.
    full = T_translate @ T_pivot @ RS @ T_pivot_inv
    """
    T = Matrix.Translation(loc)
    T_pivot = Matrix.Translation(pivot)
    T_pivot_inv = Matrix.Translation(-pivot)
    return T @ T_pivot @ RS @ T_pivot_inv


# ── Operator ──────────────────────────────────────────────────────────────────

class BCTT_OT_apply_transform(Operator):
    bl_idname = "bctt.apply_transform"
    bl_label = "Apply Transform"
    bl_description = (
        "Apply the world-space transform to all objects in the collection "
        "selected in the Outliner, using the current Blender pivot point"
    )
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return True

    def execute(self, context: bpy.types.Context):
        # ── Resolve collection ────────────────────────────────────────────────
        collection = _get_selected_collection(context)
        if collection is None:
            self.report({'ERROR'}, "No collection selected in the Outliner")
            return {'CANCELLED'}

        all_objects: set = set()
        _collect_all_objects(collection, all_objects)
        root_objects = _get_root_objects(all_objects)

        if not root_objects:
            self.report({'WARNING'}, f"Collection '{collection.name}' contains no objects")
            return {'CANCELLED'}

        # ── Read UI values ────────────────────────────────────────────────────
        wm = context.window_manager
        loc = Vector(wm.bctt_loc)
        rot_rad = Vector(wm.bctt_rot)   # already in radians (unit='ROTATION')
        scale = Vector(wm.bctt_scale)

        is_noop = (
            loc.length_squared == 0.0
            and rot_rad.length_squared == 0.0
            and scale == Vector((1.0, 1.0, 1.0))
        )
        if is_noop:
            self.report({'INFO'}, "Nothing to apply (all values at default)")
            return {'CANCELLED'}

        # ── Resolve Blender pivot point ───────────────────────────────────────
        RS = _build_rotation_scale(rot_rad, scale)
        pivot_mode = context.scene.tool_settings.transform_pivot_point

        if pivot_mode == 'INDIVIDUAL_ORIGINS':
            # Capture each root object's own origin before modifying anything
            pivots = {obj: obj.matrix_world.translation.copy() for obj in root_objects}
            for obj in root_objects:
                full = _build_full_transform(loc, RS, pivots[obj])
                obj.matrix_world = full @ obj.matrix_world

        else:
            if pivot_mode == 'CURSOR':
                pivot = context.scene.cursor.location.copy()
            elif pivot_mode == 'BOUNDING_BOX_CENTER':
                pivot = _bounding_box_center(all_objects)
            elif pivot_mode == 'ACTIVE_ELEMENT':
                active = context.active_object
                pivot = (active.matrix_world.translation.copy()
                         if active is not None
                         else _median_center(all_objects))
            else:  # MEDIAN_POINT (default)
                pivot = _median_center(all_objects)

            full = _build_full_transform(loc, RS, pivot)
            for obj in root_objects:
                obj.matrix_world = full @ obj.matrix_world

        context.view_layer.update()

        # ── Reset UI fields ───────────────────────────────────────────────────
        wm.bctt_loc = (0.0, 0.0, 0.0)
        wm.bctt_rot = (0.0, 0.0, 0.0)
        wm.bctt_scale = (1.0, 1.0, 1.0)

        self.report(
            {'INFO'},
            f"Transformed '{collection.name}' "
            f"({len(root_objects)} root object(s), {len(all_objects)} total)"
            f" — pivot: {pivot_mode}"
        )
        return {'FINISHED'}


classes = (BCTT_OT_apply_transform,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
