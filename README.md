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

## Common gotchas

**"Create Embossed Text" vs "Create Text On Face"** — these sit right next to each other in the toolbar and it's easy to click the wrong one. **Create Embossed Text** always drops text flat at the world origin, ignoring any face you've selected. **Create Text On Face** is the one that actually reads your selected face and positions text there. If your text shows up floating at the origin instead of on the face you clicked, this is almost always why — check which object got created (`TextExtrude` vs `TextOnFaceExtrude`) to confirm.

**Selecting the wrong PartDesign feature to fuse with.** This one isn't really about this workbench — it trips people up in FreeCAD generally. If your part is a PartDesign `Body` (e.g. built with a Pad, then hollowed with a Thickness feature, maybe fillets after that), **every single feature in that Body's tree represents the complete shape up to that point** — not just what that one step added. `Pad` alone is the *solid* block, *before* it got hollowed out. If you fuse your text with `Pad` instead of with the *last* feature in that chain (e.g. `Thickness`, or a `Fillet` after it), you'll get your text welded onto a solid block instead of your actual hollow part — the walls will disappear and the whole thing will print solid.

**Rule of thumb:** always select the **last/bottom-most feature** in a Body's chain (the one FreeCAD calls the "Tip") when fusing text onto it, never an earlier step, even though earlier steps are still visible and selectable in the tree.

**Before exporting for 3D printing:**
1. Select **only** your final `Fusion` object (nothing else) in the tree.
2. With it selected, find the `Refine` property in the Data tab and turn it **on** — this cleans up the boolean result and is worth the one-time cost now that you're done adjusting (it's left off by default during editing purely for speed).
3. **File → Export...**, choose STL or 3MF, and export just that selected object.
4. Open the exported file fresh in your slicer. If your slicer reports "multiple objects" or "multiple parts," you likely exported more than just the one `Fusion` object, or fused the wrong feature per the gotcha above.

## Notes

- Font pickers need actual **font files** (`.ttf`/`.otf`), not just font names — browse to wherever fonts are installed on your system.
- If something doesn't work as expected, check **View → Panels → Report view** for error details, and feel free to open an issue on this repository.
