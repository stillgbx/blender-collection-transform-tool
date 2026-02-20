"""
Collection Transform Tool — Properties

All properties are stored on WindowManager: session-persistent, not saved with the .blend file.
This ensures they survive undo/redo without interfering with Blender's undo stack.
"""

import bpy
from bpy.props import FloatVectorProperty
from bpy.types import WindowManager


def register():
    # Transform inputs
    WindowManager.bctt_loc = FloatVectorProperty(
        name="Location",
        description="World-space translation delta to apply to the collection",
        size=3,
        default=(0.0, 0.0, 0.0),
        unit='LENGTH',
        subtype='XYZ',
    )
    WindowManager.bctt_rot = FloatVectorProperty(
        name="Rotation",
        description="World-space rotation to apply (degrees, XYZ Euler order)",
        size=3,
        default=(0.0, 0.0, 0.0),
        unit='ROTATION',
        subtype='EULER',
    )
    WindowManager.bctt_scale = FloatVectorProperty(
        name="Scale",
        description="World-space scale to apply to the collection",
        size=3,
        default=(1.0, 1.0, 1.0),
        subtype='XYZ',
        min=0.0001,
    )



def unregister():
    del WindowManager.bctt_loc
    del WindowManager.bctt_rot
    del WindowManager.bctt_scale
