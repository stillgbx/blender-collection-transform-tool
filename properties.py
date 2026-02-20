"""
Collection Transform Tool — Properties

All properties are stored on WindowManager: session-persistent, not saved with the .blend file.
This ensures they survive undo/redo without interfering with Blender's undo stack.
"""

import bpy
from bpy.props import BoolProperty, FloatVectorProperty
from bpy.types import WindowManager


def _update_preview_value(self, context):
    """Called when bctt_loc/rot/scale changes while realtime mode is ON."""
    if not self.bctt_realtime:
        return
    from .operators import _apply_realtime_preview
    _apply_realtime_preview(context)


def _update_realtime_toggle(self, context):
    """Called when bctt_realtime is toggled."""
    if not self.bctt_realtime:
        # Turned OFF: restore original positions if a preview was active
        from .operators import cancel_realtime_preview
        cancel_realtime_preview(context)


def register():
    # Bake transforms into mesh data after Apply
    WindowManager.bctt_apply_transforms = BoolProperty(
        name="Bake rotations",
        description=(
            "After applying, bake each object's local rotation into its mesh data "
            "(equivalent to Ctrl+A → Rotation). Each object's rotation_euler → (0,0,0)"
        ),
        default=False,
    )

    # Real-time preview toggle
    WindowManager.bctt_realtime = BoolProperty(
        name="Real-time Preview",
        description="Apply transform live while adjusting values (Ctrl+Z reverts to pre-preview state)",
        default=False,
        update=_update_realtime_toggle,
    )

    # Transform inputs
    WindowManager.bctt_loc = FloatVectorProperty(
        name="Location",
        description="World-space translation delta to apply to the collection",
        size=3,
        default=(0.0, 0.0, 0.0),
        unit='LENGTH',
        subtype='XYZ',
        update=_update_preview_value,
    )
    WindowManager.bctt_rot = FloatVectorProperty(
        name="Rotation",
        description="World-space rotation to apply (degrees, XYZ Euler order)",
        size=3,
        default=(0.0, 0.0, 0.0),
        unit='ROTATION',
        subtype='EULER',
        update=_update_preview_value,
    )
    WindowManager.bctt_scale = FloatVectorProperty(
        name="Scale",
        description="World-space scale to apply to the collection",
        size=3,
        default=(1.0, 1.0, 1.0),
        subtype='XYZ',
        min=0.0001,
        update=_update_preview_value,
    )


def unregister():
    del WindowManager.bctt_apply_transforms
    del WindowManager.bctt_realtime
    del WindowManager.bctt_loc
    del WindowManager.bctt_rot
    del WindowManager.bctt_scale
