# Text Workbench for FreeCAD

A dedicated "Text" workbench for creating and adjusting text geometry: flat outlines, extruded/embossed 3D text, and text placed directly onto a picked face on your model.

## Install

### Easiest way: FreeCAD's Addon Manager

1. Open FreeCAD.
2. Go to **Tools → Addon Manager**.
3. Click the small menu/gear icon in the Addon Manager window and choose **"Install custom addon"** (or "Install from URL," wording varies slightly by FreeCAD version).
4. Paste this repository's URL:
   ```
   https://github.com/seeker9969/TextWorkbench
   ```
5. Click install, then fully restart FreeCAD.
6. Open the workbench dropdown (top toolbar) and select **Text**.

That's it — no manual folders, no copying files. FreeCAD finds the right install location for your OS and FreeCAD version automatically.

### Manual install (advanced / offline use)

If you'd rather install it by hand, or don't want to use the Addon Manager:

1. Find your FreeCAD `Mod` folder:
   - **Windows:** `%APPDATA%\FreeCAD\Mod\`
   - **macOS:** `~/Library/Application Support/FreeCAD/Mod/`
   - **Linux:** `~/.local/share/FreeCAD/Mod/` (older versions: `~/.FreeCAD/Mod/`; newer versions may use a versioned subfolder like `v1-1/Mod/`)

   If the `Mod` folder doesn't exist, create it.

2. Download this repository (Code → Download ZIP on GitHub, or `git clone`) and copy the whole `TextWorkbench` folder into that `Mod` folder, so you end up with:
   ```
   Mod/TextWorkbench/InitGui.py
   Mod/TextWorkbench/TextCommands.py
   Mod/TextWorkbench/package.xml
   Mod/TextWorkbench/Resources/
   ```

3. Restart FreeCAD and select **Text** from the workbench dropdown.

## The tools

- **Create Text Shape** — a flat outline of text from any font file (`.ttf`/`.otf`). Pure 2D geometry, no thickness — like a stencil outline. Useful for laser/vinyl cutting, or as a starting profile for your own custom extrusion.
- **Create Embossed Text** — same as above, but automatically extruded into a solid at the origin. Position it yourself afterward.
- **Create Text On Face** — click a face on your part first, then run this. The text is automatically rotated to lie flush against that face and positioned at the exact point you clicked, then extruded into a solid.
- **Create Annotation Text** — a plain text label (not real geometry) for notes/callouts in the 3D view.
- **Union Selected** — select two or more solids (e.g. your text and your part) and fuse them into one. This is always a manual, deliberate step — nothing fuses automatically. Do all your adjusting first, then fuse once at the end.

All four creation tools open a **Task Panel** in the Tasks tab instead of a chain of popup boxes — fill in text, font (with a Browse button), size, and depth (where applicable) all in one place. Your last-used font/size/depth are remembered automatically, even across restarts.

## Adjusting text after it's placed

A second toolbar/menu group, **Text Adjust**, lets you tweak text you've already created — before or after fusing it:

- **Nudge Left / Right / Up / Down** — moves whatever's selected 1mm along its own local orientation (not the global axes), so it works correctly even for text on an angled face. Works on any object with a Placement (ShapeString, Extrusion, Fusion, or Annotation Text).
- **Text Bigger / Smaller** — grows/shrinks the text by 1mm per click. Works on both extruded text (`Size` property) and Annotation Text (`FontSize`), and greys out if neither applies to the current selection.
- **Depth Thicker / Thinner** — increases/decreases how far extruded text protrudes, by 0.5mm per click. Only applies to extruded/embossed text — greys out for flat Text Shape and Annotation Text, since those have no thickness by design.

**How selection works:** click on *any* related object in the tree first — the underlying `ShapeString`, its `Extrusion`, or a `Fusion` it's been merged into. The tools search automatically to find what they need; no need to dig through the tree for the exact object every time.

**Recommended workflow:** build your part, use Create Text On Face, then use the Text Adjust tools to nudge/resize/deepen the text until it looks right — all of this is fast since nothing is fused yet. Only once you're happy, select the text + your part and click **Union Selected**. Fusing is a real boolean operation and can take a few seconds on complex text, so doing it once at the end (rather than after every adjustment) keeps things responsive.

## Notes

- Font pickers need actual **font files** (`.ttf`/`.otf`), not just font names — browse to wherever fonts are installed on your system.
- If something doesn't work as expected, check **View → Panels → Report view** for error details, and feel free to open an issue on this repository.
