# Collection Transform Tool

Blender addon to apply world-space transforms (location, rotation, scale) to all objects
in a collection selected in the Outliner — as if the collection were a single rigid body.

> 100% vibe coded with Claude Code

## Installation

1. In Blender: **Edit > Preferences > Add-ons > Install…**
2. Select the `blender-collection-transform-tool` folder (or a `.zip` of it).
3. Enable **Object: Collection Transform Tool**.

## Usage

1. **Select a collection** in the Outliner (click on it).
2. Open the **N-panel** in the 3D Viewport (press `N`), go to the **Collection Transform** tab.
3. Choose a **Pivot** point: Collection Center or World Origin.
4. Enter the **delta values** to apply:
   - **Location**: world-space translation offset (in scene units)
   - **Rotation**: world-space rotation (degrees, XYZ Euler order, applied Z→Y→X)
   - **Scale**: per-axis scale factor (1.0 = no change)
5. Click **Apply Transform**.

The fields reset to their defaults after each apply. You can chain multiple operations.

## Example: rotate a collection 90° around world Z

1. Select `My_Collection` in the Outliner.
2. In **Collection Transform** tab, leave Location at `0 / 0 / 0` and Scale at `1 / 1 / 1`.
3. Set **Rotation Z** to `90°`.
4. Set **Pivot** to `Collection Center`.
5. Click **Apply Transform**.

All objects (visible, hidden, in sub-collections) rotate 90° around the collection's center,
on the world Z axis. Relative positions and local transforms are fully preserved.

## How it works

Only **root objects** (objects whose parent is not part of the collection) are transformed
directly. Child objects follow automatically via Blender's parent-child mechanism.

The world-space transform applied to each root object's `matrix_world` is:

```
full = T_translate  @  T_pivot  @  Rz @ Ry @ Rx  @  Sx @ Sy @ Sz  @  T_pivot_inv
```

- The pivot only affects rotation and scale, not translation.
- Undo/redo is handled natively by Blender (`Ctrl+Z` works as expected).

## Requirements

- Blender 5.0+
- No external dependencies.
