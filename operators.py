"""
Collection Transform Tool — Operators

BCTT_OT_apply_transform: applies a world-space transform (location + rotation + scale)
to all root objects of the collection currently selected in the Outliner.

Real-time preview
-----------------
When `bctt_realtime` is ON, every value change triggers `_apply_realtime_preview()`:
  1. On first call, a snapshot of every root object's matrix_world is stored.
  2. On each subsequent call, originals are restored from the snapshot, then the
     current delta is re-applied from scratch (no accumulation, no drift).
  3. Live changes produce NO undo steps (direct Python writes to matrix_world).

Apply in realtime mode:
  - Restores originals from snapshot first (transparent).
  - Applies the transform fresh.
  - Returns FINISHED → Blender pushes one undo step (the final state).
  - Ctrl+Z restores the pre-preview state (no undo steps were pushed during preview). ✓

Reset in realtime mode:
  - Restores originals from snapshot.
  - Resets fields to 0/1.
  - No undo step (just cancelling a preview).

Toggling realtime OFF: restores originals and clears snapshot.

Pivot point
-----------
Reads `context.scene.tool_settings.transform_pivot_point`. All five modes:
  MEDIAN_POINT        Average of all object origins in the collection.
  BOUNDING_BOX_CENTER World-space bounding box center of the collection.
  CURSOR              Current 3D cursor position.
  INDIVIDUAL_ORIGINS  Each root object rotates/scales around its own origin.
  ACTIVE_ELEMENT      Active object's origin (falls back to median if none).

For pivot modes that depend on object positions, the pivot is always computed
from the ORIGINAL (snapshot) positions so it stays stable during live preview.
"""

import bpy
from bpy.types import Operator
from mathutils import Matrix, Vector


# ── Real-time preview state ───────────────────────────────────────────────────

# {obj_name: original_matrix_world}  — populated on first live-preview change
_preview: dict = {}
# Name of the collection that was snapshotted (used to detect collection changes)
_preview_collection: str = ""


# ── Collection helpers ────────────────────────────────────────────────────────

def _collect_all_objects(collection: bpy.types.Collection, result: set) -> None:
    """Recursively collect all objects from a collection and its sub-collections."""
    for obj in collection.objects:
        result.add(obj)
    for child_col in collection.children:
        _collect_all_objects(child_col, result)


def _get_root_objects(all_objects: set) -> list:
    """Objects whose parent is None or whose parent is NOT in the collection."""
    return [obj for obj in all_objects
            if obj.parent is None or obj.parent not in all_objects]


def _get_selected_collection(context: bpy.types.Context):
    """First Collection selected in the Outliner, or None."""
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

def _bounding_box_center_from_matrices(obj_matrix_pairs) -> Vector:
    """Bounding box center computed from (object, world_matrix) pairs."""
    inf = float('inf')
    mn = Vector((inf, inf, inf))
    mx = Vector((-inf, -inf, -inf))

    for obj, matrix in obj_matrix_pairs:
        if hasattr(obj, 'bound_box') and obj.bound_box:
            for v in obj.bound_box:
                world_v = matrix @ Vector(v)
                for i in range(3):
                    mn[i] = min(mn[i], world_v[i])
                    mx[i] = max(mx[i], world_v[i])
        else:
            co = matrix.translation
            for i in range(3):
                mn[i] = min(mn[i], co[i])
                mx[i] = max(mx[i], co[i])

    if mn.x == inf:
        return Vector((0.0, 0.0, 0.0))
    return (mn + mx) / 2


def _resolve_pivot(
    pivot_mode: str,
    context: bpy.types.Context,
    root_objects: list,
    snapshot: dict | None = None,
) -> Vector:
    """
    Resolve the pivot point for the given mode.
    When snapshot is provided, object-position-dependent pivots are computed
    from original positions (used during real-time preview).
    """
    if pivot_mode == 'CURSOR':
        return context.scene.cursor.location.copy()

    if pivot_mode == 'ACTIVE_ELEMENT':
        active = context.active_object
        if active is not None:
            if snapshot and active.name in snapshot:
                return snapshot[active.name].translation.copy()
            return active.matrix_world.translation.copy()
        # Fall through to MEDIAN_POINT

    # Build (object, matrix) pairs — use snapshot when available
    if snapshot:
        pairs = [(obj, snapshot[obj.name]) for obj in root_objects if obj.name in snapshot]
    else:
        pairs = [(obj, obj.matrix_world) for obj in root_objects]

    if not pairs:
        return Vector((0.0, 0.0, 0.0))

    if pivot_mode == 'BOUNDING_BOX_CENTER':
        return _bounding_box_center_from_matrices(pairs)

    # MEDIAN_POINT (default)
    total = Vector((0.0, 0.0, 0.0))
    for _, m in pairs:
        total += m.translation
    return total / len(pairs)


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
    """full = T_translate @ T_pivot @ RS @ T_pivot_inv"""
    T = Matrix.Translation(loc)
    T_pivot = Matrix.Translation(pivot)
    T_pivot_inv = Matrix.Translation(-pivot)
    return T @ T_pivot @ RS @ T_pivot_inv


def _apply_transform_to_objects(
    root_objects: list,
    loc: Vector,
    rot_rad: Vector,
    scale: Vector,
    pivot_mode: str,
    context: bpy.types.Context,
    snapshot: dict | None = None,
) -> None:
    """
    Apply the world-space transform to root_objects.
    snapshot: if provided, original matrices used for restoring before applying
              and for pivot computation.
    """
    RS = _build_rotation_scale(rot_rad, scale)

    if pivot_mode == 'INDIVIDUAL_ORIGINS':
        for obj in root_objects:
            orig = snapshot[obj.name] if snapshot and obj.name in snapshot else obj.matrix_world
            pivot_i = orig.translation.copy()
            full = _build_full_transform(loc, RS, pivot_i)
            obj.matrix_world = full @ orig
    else:
        pivot = _resolve_pivot(pivot_mode, context, root_objects, snapshot)
        full = _build_full_transform(loc, RS, pivot)
        for obj in root_objects:
            orig = snapshot[obj.name] if snapshot and obj.name in snapshot else obj.matrix_world
            obj.matrix_world = full @ orig


# ── Real-time preview functions ───────────────────────────────────────────────

def _apply_realtime_preview(context: bpy.types.Context) -> None:
    """
    Called by property update callbacks when realtime mode is ON.
    Takes a snapshot on first call, then restores + re-applies on every call.
    """
    global _preview_collection

    wm = context.window_manager
    collection = _get_selected_collection(context)
    if collection is None:
        return

    all_objects: set = set()
    _collect_all_objects(collection, all_objects)
    root_objects = _get_root_objects(all_objects)
    if not root_objects:
        return

    # Reset snapshot if the collection changed
    if collection.name != _preview_collection and _preview:
        _restore_objects_from_snapshot()
        _preview.clear()

    # Take snapshot on first call — mutate in place so imported references stay valid
    if not _preview:
        _preview_collection = collection.name
        _preview.update({obj.name: obj.matrix_world.copy() for obj in root_objects})

    loc = Vector(wm.bctt_loc)
    rot_rad = Vector(wm.bctt_rot)
    scale = Vector(wm.bctt_scale)
    pivot_mode = context.scene.tool_settings.transform_pivot_point

    _apply_transform_to_objects(root_objects, loc, rot_rad, scale, pivot_mode, context, _preview)

    context.view_layer.update()
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def _restore_objects_from_snapshot() -> None:
    """Restore all snapshotted objects to their original matrix_world."""
    for obj_name, orig_matrix in _preview.items():
        obj = bpy.data.objects.get(obj_name)
        if obj is not None:
            obj.matrix_world = orig_matrix.copy()


def cancel_realtime_preview(context: bpy.types.Context) -> None:
    """
    Public: restore originals, reset fields, clear snapshot.
    Called when realtime is toggled OFF or Reset is clicked.
    """
    global _preview, _preview_collection

    if _preview:
        _restore_objects_from_snapshot()
        context.view_layer.update()
        _preview.clear()
        _preview_collection = ""

    wm = context.window_manager
    wm.bctt_loc = (0.0, 0.0, 0.0)
    wm.bctt_rot = (0.0, 0.0, 0.0)
    wm.bctt_scale = (1.0, 1.0, 1.0)


# ── Bake transforms to mesh data ─────────────────────────────────────────────

def _bake_transforms_to_data(all_objects: set, context: bpy.types.Context) -> int:
    """
    Apply each object's current local rotation into its mesh/curve/… data
    (equivalent to Ctrl+A → Rotation in Blender), so rotation_euler → (0,0,0).
    Returns the number of objects processed.
    """
    count = 0
    for obj in all_objects:
        try:
            with context.temp_override(
                active_object=obj,
                selected_objects=[obj],
                selected_editable_objects=[obj],
            ):
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            count += 1
        except Exception:
            pass
    return count


# ── Operators ─────────────────────────────────────────────────────────────────

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
        global _preview, _preview_collection

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

        wm = context.window_manager
        loc = Vector(wm.bctt_loc)
        rot_rad = Vector(wm.bctt_rot)
        scale = Vector(wm.bctt_scale)

        is_noop = (
            loc.length_squared == 0.0
            and rot_rad.length_squared == 0.0
            and scale == Vector((1.0, 1.0, 1.0))
        )
        if is_noop:
            self.report({'INFO'}, "Nothing to apply (all values at default)")
            return {'CANCELLED'}

        pivot_mode = context.scene.tool_settings.transform_pivot_point

        # In realtime mode: restore originals first so the undo step captures
        # the pre-preview state, then apply fresh from the snapshot.
        snapshot = _preview.copy() if _preview else None

        if snapshot:
            _restore_objects_from_snapshot()
            _preview.clear()
            _preview_collection = ""

        _apply_transform_to_objects(root_objects, loc, rot_rad, scale, pivot_mode, context, snapshot)

        baked = 0
        if wm.bctt_apply_transforms:
            baked = _bake_transforms_to_data(all_objects, context)

        context.view_layer.update()

        wm.bctt_loc = (0.0, 0.0, 0.0)
        wm.bctt_rot = (0.0, 0.0, 0.0)
        wm.bctt_scale = (1.0, 1.0, 1.0)

        msg = (
            f"Transformed '{collection.name}' "
            f"({len(root_objects)} root object(s), {len(all_objects)} total)"
            f" — pivot: {pivot_mode}"
        )
        if baked:
            msg += f" — transforms baked on {baked} object(s)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class BCTT_OT_reset_preview(Operator):
    bl_idname = "bctt.reset_preview"
    bl_label = "Reset"
    bl_description = "Restore original positions and reset all values"
    bl_options = set()  # No undo: we are restoring, not modifying

    def execute(self, context: bpy.types.Context):
        cancel_realtime_preview(context)
        return {'FINISHED'}


classes = (
    BCTT_OT_apply_transform,
    BCTT_OT_reset_preview,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    global _preview, _preview_collection
    _preview.clear()
    _preview_collection = ""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
