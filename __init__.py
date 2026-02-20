"""
Collection Transform Tool - Blender Addon
Apply world-space transforms (location, rotation, scale) to a selected collection.
"""

bl_info = {
    "name": "Collection Transform Tool",
    "author": "stillgbx",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Collection Transform",
    "description": "Apply world-space transforms to all objects in a selected collection",
    "category": "Object",
}

from . import properties
from . import operators
from . import panels


def register():
    properties.register()
    operators.register()
    panels.register()


def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
