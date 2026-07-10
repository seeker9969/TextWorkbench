# Text Workbench for FreeCAD

A minimal custom workbench that gives you a dedicated "Text" tab with three tools:

- **Create Text Shape** — a flat outline of text from any font file (.ttf/.otf). Pure geometry, hollow (like a stencil outline).
- **Create Embossed Text** — same as above, but automatically extruded into a solid. Use Boolean Union/Cut afterward to emboss or engrave it onto a part.
- **Create Text On Face** — select a face on your part first (click on it in the 3D view), then run this tool. The text is automatically rotated to lie flush against that face and positioned at the point you clicked, then extruded into a solid ready for Boolean Union (emboss) or Cut (engrave).
- **Create Annotation Text** — a plain 2D label for notes/callouts. Not real geometry — just a visual marker in the 3D view.

### Using "Create Text On Face"

1. Click directly on a face of your part in the 3D view (this both selects the face *and* records the exact point you clicked).
2. Run **Create Text On Face** from the Text menu/toolbar.
3. In the Task Panel that opens, enter your text, confirm/browse the font, set size and emboss depth.
4. There's a checkbox: **"Automatically fuse text into the part (Boolean Union)"** — checked by default. Leave it checked and clicking OK will place the text *and* weld it into your part in one step, producing a single `TextFusion` object. Uncheck it if you'd rather keep the text as a separate solid to position/inspect first.
5. If it's checked and the fuse runs automatically, you're done — no need to manually select objects and run Union afterward.
6. If you left it unchecked, or want more control (e.g. Cut instead of Union for engraving), select the text solid + your part and use the **Union** button that's built into this workbench's toolbar (or **Part → Boolean → Cut** for engraving).

## Install

1. Find your FreeCAD `Mod` folder:
   - **Windows:** `%APPDATA%\FreeCAD\Mod\`
   - **macOS:** `~/Library/Application Support/FreeCAD/Mod/`
   - **Linux:** `~/.local/share/FreeCAD/Mod/` (older versions: `~/.FreeCAD/Mod/`; newer versions may use a versioned subfolder like `v1-1/Mod/`)

## Adjusting text after it's placed

A second toolbar/menu group, **Text Adjust**, lets you tweak text you've already created:

- **Nudge Left / Right / Up / Down** — moves the text 1mm along its own local orientation (not the global axes), so it works correctly even for text placed on an angled or rotated face.
- **Text Bigger / Smaller** — grows or shrinks the text's `Size` property by 1mm per click.
- **Next Font** — cycles through every font installed on your system (via `fc-list`), one click at a time.

**How selection works for these:** click on *any* related object in the tree first — the `ShapeString` itself, its `Extrusion`, or even a `Fusion` it's been merged into — the tools will search downward automatically to find the actual text object to modify. No need to dig into the tree to find the exact ShapeString every time.

   If the `Mod` folder doesn't exist, create it.

2. Copy this whole `TextWorkbench` folder into that `Mod` folder, so you end up with:
   ```
   Mod/TextWorkbench/InitGui.py
   Mod/TextWorkbench/TextCommands.py
   ```

3. Restart FreeCAD.

4. Open the workbench dropdown (top toolbar, usually says "Start" or the last-used workbench) and select **Text**.

## Using it

- Make sure you have an active document open (File > New) before using any of the tools — they need somewhere to place the text.
- All three geometry tools now open a **Task Panel** in the Tasks tab (left side, next to "Model") instead of a chain of popup boxes. Fill in the text, font (Browse button included), size, and depth (if applicable) all in one place, then click OK.
- Your last-used font, size, and depth are remembered automatically (even across restarts), so after the first use you usually just need to type the text and hit OK.
- Text appears at the origin (0,0,0) for the plain Shape/Embossed tools — use the Draft "Move" tool or the object's Placement property to reposition it afterward.
- For embossing onto a curved or offset face, you may want to adjust `DirMode` or `Placement` on the `TextExtrude` object it creates, or manually position and cut/union it with your part.

## Notes

- This only works with **installed font files**, not font *names* — FreeCAD needs the actual `.ttf`/`.otf` file path.
- If a dialog doesn't appear (older/newer FreeCAD versions sometimes package Qt differently), let me know your FreeCAD version and I'll adjust the `PySide` import in `TextCommands.py`.
