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
3. Set the **Pivot point** in the 3D Viewport header (the addon reads it automatically).
4. Enter the **delta values** to apply:
   - **Location**: world-space translation offset (in scene units)
   - **Rotation**: world-space rotation (degrees, XYZ Euler order, applied Z→Y→X)
   - **Scale**: per-axis scale factor (1.0 = no change)
5. Click **Apply Transform**.

The fields reset to their defaults after each apply. You can chain multiple operations.

## Example: rotate a collection 90° around world Z

1. Select `My_Collection` in the Outliner.
2. Set the Blender **Pivot** to `Median Point` (in the viewport header).
3. In **Collection Transform** tab, leave Location at `0 / 0 / 0` and Scale at `1 / 1 / 1`.
4. Set **Rotation Z** to `90°`.
5. Click **Apply Transform**.

All objects (visible, hidden, in sub-collections) rotate 90° around the collection's center,
on the world Z axis. Relative positions and local transforms are fully preserved.

## Pivot point

The addon uses **Blender's native pivot selector** (viewport header). The current pivot is
displayed as read-only info in the panel. Five modes are supported:

| Pivot | Behaviour |
|---|---|
| Median Point | Average of all object origins in the collection |
| Bounding Box Center | Center of the world-space bounding box |
| 3D Cursor | Current 3D cursor position |
| Individual Origins | Each root object rotates/scales around its own origin |
| Active Element | Active object's origin (falls back to Median if none) |

Changing the pivot in the viewport header is immediately reflected in the panel.

## Real-time Preview

Enable **Real-time Preview** in the panel to see the result live while dragging sliders:

- The first value change takes a snapshot of all object positions.
- Each subsequent change restores from the snapshot and re-applies the delta — no drift.
- The panel shows **"Previewing — not committed"** while preview is active.
- The Apply button becomes **Commit** (+ a **↺ Reset** button to cancel the preview).

**Undo behaviour**: live preview changes produce no undo steps. `Ctrl+Z` after Commit
returns directly to the pre-preview state.

Toggling Real-time Preview **OFF** automatically restores original positions and resets the fields.

## Bake rotations (Apply to mesh data)

Enable **Bake rotations** before clicking Apply to also bake each object's local rotation
into its mesh data (equivalent to `Ctrl+A → Rotation` in Blender):

- Each object's `rotation_euler` is reset to `(0°, 0°, 0°)` after the transform.
- Applied to **all objects** in the collection (including sub-collections).
- This is a **destructive** operation on mesh data — modifiers that depend on local
  rotation may behave differently afterwards.

## How it works

Only **root objects** (objects whose parent is not part of the collection) are transformed
directly via `matrix_world`. Child objects follow automatically via Blender's parent-child
mechanism.

The world-space transform applied to each root object is:

```
full = T_translate  @  T_pivot  @  Rz @ Ry @ Rx  @  Sx @ Sy @ Sz  @  T_pivot_inv
```

- The pivot only affects rotation and scale, not translation.
- For **Individual Origins**, each root object uses its own origin as pivot.
- Undo/redo is handled natively by Blender (`Ctrl+Z` works as expected).

## Requirements

- Blender 5.0+
- No external dependencies.
