"""
Collection Transform Tool — UI Panel

Location: View3D > Sidebar (N) > Collection Transform
"""

import bpy
from bpy.types import Panel

from .operators import _get_selected_collection, _preview


_PIVOT_ICON = {
    'BOUNDING_BOX_CENTER': 'PIVOT_BOUNDBOX',
    'CURSOR':              'PIVOT_CURSOR',
    'INDIVIDUAL_ORIGINS':  'PIVOT_INDIVIDUAL',
    'MEDIAN_POINT':        'PIVOT_MEDIAN',
    'ACTIVE_ELEMENT':      'PIVOT_ACTIVE',
}
_PIVOT_LABEL = {
    'BOUNDING_BOX_CENTER': "Bounding Box Center",
    'CURSOR':              "3D Cursor",
    'INDIVIDUAL_ORIGINS':  "Individual Origins",
    'MEDIAN_POINT':        "Median Point",
    'ACTIVE_ELEMENT':      "Active Element",
}


class BCTT_PT_main(Panel):
    bl_label = "Collection Transform"
    bl_idname = "BCTT_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Collection Transform"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        wm = context.window_manager

        # ── Selected collection info ──────────────────────────────────────────
        collection = _get_selected_collection(context)
        box = layout.box()
        col = box.column(align=True)
        if collection is not None:
            col.label(text="Collection:", icon='OUTLINER_COLLECTION')
            col.label(text=f"  {collection.name}")
        else:
            col.label(text="Select a collection in the Outliner", icon='INFO')

        layout.separator(factor=0.5)

        # ── Pivot (read-only) ─────────────────────────────────────────────────
        pivot_id = context.scene.tool_settings.transform_pivot_point
        layout.label(
            text=f"Pivot: {_PIVOT_LABEL.get(pivot_id, pivot_id)}",
            icon=_PIVOT_ICON.get(pivot_id, 'PIVOT_MEDIAN'),
        )

        layout.separator(factor=0.5)

        # ── Real-time preview toggle ──────────────────────────────────────────
        row = layout.row()
        row.prop(
            wm, "bctt_realtime",
            text="Real-time Preview",
            icon='PLAY' if not wm.bctt_realtime else 'PAUSE',
            toggle=True,
        )
        if wm.bctt_realtime and _preview:
            layout.label(text="Previewing — not committed", icon='INFO')

        layout.separator(factor=0.5)

        # ── Location ──────────────────────────────────────────────────────────
        box = layout.box()
        box.label(text="Location (world delta):", icon='CON_LOCLIKE')
        col = box.column(align=True)
        col.prop(wm, "bctt_loc", index=0, text="X")
        col.prop(wm, "bctt_loc", index=1, text="Y")
        col.prop(wm, "bctt_loc", index=2, text="Z")

        layout.separator(factor=0.5)

        # ── Rotation ──────────────────────────────────────────────────────────
        box = layout.box()
        box.label(text="Rotation (world, XYZ order):", icon='CON_ROTLIKE')
        col = box.column(align=True)
        col.prop(wm, "bctt_rot", index=0, text="X")
        col.prop(wm, "bctt_rot", index=1, text="Y")
        col.prop(wm, "bctt_rot", index=2, text="Z")

        layout.separator(factor=0.5)

        # ── Scale ─────────────────────────────────────────────────────────────
        box = layout.box()
        box.label(text="Scale (world):", icon='CON_SIZELIKE')
        col = box.column(align=True)
        col.prop(wm, "bctt_scale", index=0, text="X")
        col.prop(wm, "bctt_scale", index=1, text="Y")
        col.prop(wm, "bctt_scale", index=2, text="Z")

        layout.separator()

        # ── Bake option ───────────────────────────────────────────────────────
        layout.prop(wm, "bctt_apply_transforms", icon='MESH_DATA')

        layout.separator(factor=0.5)

        # ── Apply / Reset buttons ─────────────────────────────────────────────
        has_collection = collection is not None
        in_preview = wm.bctt_realtime and bool(_preview)

        if in_preview:
            row = layout.row(align=True)
            row.scale_y = 1.6
            apply_btn = row.operator("bctt.apply_transform", text="Commit", icon='CHECKMARK')
            row.operator("bctt.reset_preview", text="", icon='LOOP_BACK')
        else:
            row = layout.row()
            row.scale_y = 1.6
            row.enabled = has_collection
            row.operator("bctt.apply_transform", icon='OBJECT_ORIGIN')


classes = (BCTT_PT_main,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
