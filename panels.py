"""
Collection Transform Tool — UI Panel

Location: View3D > Sidebar (N) > Collection Transform
"""

import bpy
from bpy.types import Panel

from .operators import _get_selected_collection


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

        # ── Pivot — mirrors the Blender viewport header selector ──────────────
        layout.prop(context.scene.tool_settings, "transform_pivot_point", text="Pivot")

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

        # ── Apply button ──────────────────────────────────────────────────────
        row = layout.row()
        row.scale_y = 1.6
        row.enabled = collection is not None
        row.operator("bctt.apply_transform", icon='OBJECT_ORIGIN')


classes = (BCTT_PT_main,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
