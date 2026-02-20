# AGENTS.md — Collection Transform Tool Blender Addon

Instructions for AI agents (LLMs) working on this project.

---

## Project Context

Blender addon (Python) that applies world-space transforms (location, rotation, scale)
to all objects in a collection selected in the Outliner.

- **Minimum Blender**: 5.0+
- **Code language**: English (docstrings, variables, comments)
- **Documentation language**: English (README.md, AGENTS.md, inline comments)
- **Communication language with the user**: French

---

## File Architecture

```
blender-collection-transform-tool/
├── __init__.py      # bl_info, register/unregister (import order matters)
├── properties.py    # WindowManager properties: loc, rot, scale, pivot
├── operators.py     # CTT_OT_apply_transform + core math helpers
├── panels.py        # CTT_PT_main (View3D > Sidebar > Collection Transform)
├── README.md        # User documentation
└── AGENTS.md        # This file
```

---

## Code Conventions

### Python / Blender API

- Use **type annotations** in signatures.
- Prefix internal helpers with `_`.
- Blender classes follow `CTT_OT_xxx`, `CTT_PT_xxx` naming.
- `bl_idname` uses the `ctt.` prefix (e.g. `ctt.apply_transform`).

### Properties Storage

Properties are stored on `bpy.types.WindowManager`:
- Session-persistent (survives undo), not saved with the `.blend` file.
- `ctt_loc` (FloatVector 3): translation delta in world space.
- `ctt_rot` (FloatVector 3): rotation in **radians** (stored with `unit='ROTATION'`, displayed as degrees by Blender).
- `ctt_scale` (FloatVector 3): per-axis scale, min 0.0001, default (1,1,1).
- `ctt_pivot` (Enum): `'COLLECTION_CENTER'` or `'WORLD_ORIGIN'`.

### Core Transform Algorithm

Only **root objects** are transformed (objects whose parent is not in the collection).
The world-space transform matrix is:

```
full = T_translate  @  T_pivot  @  R  @  S  @  T_pivot_inv
```

Where:
- `T_translate = Matrix.Translation(loc)`
- `R = Rz @ Ry @ Rx` (XYZ Euler, world axes — Z applied last = outermost)
- `S = Sx @ Sy @ Sz` (per-axis scale via `Matrix.Scale`)
- `T_pivot` / `T_pivot_inv` only affect rotation and scale, not translation

Applied via: `obj.matrix_world = full @ obj.matrix_world`

### Undo Handling

- **No custom undo stack** — Blender handles undo natively.
- Operators use `bl_options = {'UNDO'}`.
- WindowManager properties survive undo (intentional — they are UI state, not scene data).
- Fields reset to defaults after each apply (prevents accidental double-apply).

### Outliner Collection Detection

`_get_selected_collection(context)` iterates `context.screen.areas` to find the Outliner,
then uses `context.temp_override(area=area, region=region)` to read `context.selected_ids`.
Returns the first `bpy.types.Collection` found, or `None`.

---

## Modification Rules

### Before Modifying Code

1. **Read the file** in its entirety before editing it.
2. Keep all `bpy.types.WindowManager` property additions/deletions in sync between
   `properties.register()` and `properties.unregister()`.

### After Each Modification

1. **Reload the addon** in Blender (Edit > Preferences > Add-ons) to verify no errors.
2. **Update README.md** if a new feature or operator is added.
3. **Update this file** if the file architecture or conventions change.

### What NOT to Do

- **Never** use external dependencies — no imports beyond Blender's stdlib + mathutils.
- **Never** store transform state on `Scene` (avoids polluting saved files).
- **Never** implement a custom undo stack — `bl_options = {'UNDO'}` is sufficient.
- **Never** use `update=` callbacks on properties to apply transforms live — this breaks
  undo and causes hard-to-debug state drift.
- **Never** use `bpy.ops` inside `execute()` for object transforms — set `matrix_world` directly.
- **Never** break Blender 5.0+ compatibility without discussion.
