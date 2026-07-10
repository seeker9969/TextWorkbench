# TextCommands.py
# Defines the commands used by the Text workbench, using a single Task Panel
# (shown in the Tasks tab) to gather text/font/size/depth instead of a chain
# of separate popup dialogs.

import os
import platform

import FreeCAD as App
import FreeCADGui as Gui
import Draft

from PySide import QtCore, QtGui  # FreeCAD's Qt compatibility shim


# ---------------------------------------------------------------------------
# Settings persistence (remembers last font/size/depth between uses/restarts)
# ---------------------------------------------------------------------------

def _param_group():
    return App.ParamGet("User parameter:BaseApp/Preferences/Mod/TextWorkbench")


def _get_last_font():
    return _param_group().GetString("LastFont", "")


def _get_last_size():
    return _param_group().GetFloat("LastSize", 10.0)


def _get_last_depth():
    return _param_group().GetFloat("LastDepth", 2.0)


def _save_last_settings(font_file, size, depth=None):
    pg = _param_group()
    pg.SetString("LastFont", font_file)
    pg.SetFloat("LastSize", size)
    if depth is not None:
        pg.SetFloat("LastDepth", depth)


def _default_font():
    """Best-effort guess at a system font, used only if nothing's been picked before."""
    system = platform.system()
    if system == "Windows":
        candidates = [r"C:\Windows\Fonts\arial.ttf"]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""


def _starting_font():
    return _get_last_font() or _default_font()


# ---------------------------------------------------------------------------
# Geometry builders
# ---------------------------------------------------------------------------

def _build_shape_text(text, font_file, size):
    Draft.make_shapestring(String=text, FontFile=font_file, Size=size, Tracking=0)
    App.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")


def _build_embossed_text(text, font_file, size, depth):
    shapestring = Draft.make_shapestring(String=text, FontFile=font_file, Size=size, Tracking=0)
    App.ActiveDocument.recompute()

    extrusion = App.ActiveDocument.addObject("Part::Extrusion", "TextExtrude")
    extrusion.Base = shapestring
    extrusion.DirMode = "Normal"
    extrusion.LengthFwd = depth
    extrusion.Solid = True
    shapestring.Visibility = False

    App.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")


def _build_text_on_face(text, font_file, size, depth, face, point):
    if point is None:
        point = face.CenterOfMass

    try:
        u, v = face.Surface.parameter(point)
        normal = face.normalAt(u, v)
    except Exception:
        normal = face.normalAt(0, 0)
    normal.normalize()

    # Sink the text slightly *into* the surface before extruding, so the
    # resulting solid genuinely overlaps the part instead of merely
    # touching it at one perfectly coincident face. Fusing two solids that
    # only touch (zero-thickness contact) is a classic cause of OCCT's
    # "Resulting shape is invalid" error -- a small bite avoids that.
    bite = min(0.2, depth * 0.2)
    sunk_point = point - normal * bite
    extrude_depth = depth + bite

    shapestring = Draft.make_shapestring(String=text, FontFile=font_file, Size=size, Tracking=0)
    App.ActiveDocument.recompute()

    rotation = App.Rotation(App.Vector(0, 0, 1), normal)
    shapestring.Placement = App.Placement(sunk_point, rotation)
    App.ActiveDocument.recompute()

    extrusion = App.ActiveDocument.addObject("Part::Extrusion", "TextOnFaceExtrude")
    extrusion.Base = shapestring
    extrusion.DirMode = "Normal"
    extrusion.LengthFwd = extrude_depth
    extrusion.Solid = True
    shapestring.Visibility = False

    App.ActiveDocument.recompute()
    Gui.SendMsgToActiveView("ViewFit")

    return extrusion


def _fuse_into_target(text_solid, target_obj):
    """Boolean-union the freshly made text solid into the part it was placed on."""
    doc = App.ActiveDocument
    fusion = doc.addObject("Part::MultiFuse", "TextFusion")
    fusion.Shapes = [target_obj, text_solid]
    # Refine off by default: it adds real recompute cost on *every* nudge/
    # resize click since the whole fusion recomputes each time. Turn it on
    # manually (select TextFusion, tick Refine in the Data tab) once you're
    # done adjusting and just want a cleaner final result before export.
    fusion.Refine = False
    target_obj.Visibility = False
    text_solid.Visibility = False
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    return fusion


# ---------------------------------------------------------------------------
# Helpers for adjusting text after it's already been placed (nudge, resize,
# cycle font). These work no matter which object you actually selected --
# the top Fusion, the Extrusion, or the ShapeString itself -- by searching
# downward through the dependency tree for the underlying ShapeString.
# ---------------------------------------------------------------------------

def _find_shapestring(obj, visited=None):
    if visited is None:
        visited = set()
    if obj.Name in visited:
        return None
    visited.add(obj.Name)
    if obj.TypeId == "Draft::ShapeString" or hasattr(obj, "FontFile"):
        return obj
    for child in getattr(obj, "OutList", []):
        found = _find_shapestring(child, visited)
        if found is not None:
            return found
    return None


def _selected_shapestring():
    sel = Gui.Selection.getSelection()
    if not sel:
        return None
    return _find_shapestring(sel[0])


_ALL_FONTS_CACHE = None


def _get_all_fonts():
    """Enumerate installed fonts via fc-list, cached for the session."""
    global _ALL_FONTS_CACHE
    if _ALL_FONTS_CACHE is not None:
        return _ALL_FONTS_CACHE
    fonts = []
    try:
        import subprocess
        result = subprocess.run(
            ["fc-list", "--format=%{file}\n"],
            capture_output=True, text=True, timeout=5,
        )
        fonts = sorted(set(
            line.strip() for line in result.stdout.splitlines()
            if line.strip().lower().endswith((".ttf", ".otf"))
        ))
    except Exception:
        fonts = []
    _ALL_FONTS_CACHE = fonts
    return fonts


NUDGE_STEP = 1.0   # mm per click, along the text's own local axes
RESIZE_STEP = 1.0  # mm per click


def _nudge(direction):
    sel = Gui.Selection.getSelection()
    if not sel:
        QtGui.QMessageBox.warning(
            None, "Nudge Text", "Select an object first (the text, its extrusion, or its fused part)."
        )
        return
    obj = sel[0]
    if not hasattr(obj, "Placement"):
        QtGui.QMessageBox.warning(
            None, "Nudge Text", "The selected object doesn't have a Placement to move."
        )
        return
    rotation = obj.Placement.Rotation
    local_x = rotation.multVec(App.Vector(1, 0, 0))
    local_y = rotation.multVec(App.Vector(0, 1, 0))
    delta = {
        "left": local_x * -NUDGE_STEP,
        "right": local_x * NUDGE_STEP,
        "up": local_y * NUDGE_STEP,
        "down": local_y * -NUDGE_STEP,
    }[direction]
    new_position = obj.Placement.Base + delta
    obj.Placement = App.Placement(new_position, rotation)
    App.ActiveDocument.recompute()


def _resize(bigger):
    ss = _selected_shapestring()
    if ss is not None:
        current = float(ss.Size)
        new_size = current + RESIZE_STEP if bigger else current - RESIZE_STEP
        ss.Size = max(0.5, new_size)
        App.ActiveDocument.recompute()
        return

    # Annotation Text (Draft::Text) has no Data.Size property -- its font
    # size lives on the ViewObject instead, since it's a display-only label.
    sel = Gui.Selection.getSelection()
    if sel and hasattr(sel[0], "ViewObject") and hasattr(sel[0].ViewObject, "FontSize"):
        vobj = sel[0].ViewObject
        current = float(vobj.FontSize)
        new_size = current + RESIZE_STEP if bigger else current - RESIZE_STEP
        vobj.FontSize = max(0.5, new_size)
        return

    QtGui.QMessageBox.warning(
        None, "Resize Text", "Select the text (or its fused part) first."
    )


def _find_extrusion(obj, visited=None):
    """Locate the Part::Extrusion object (the one with LengthFwd/depth) from
    whatever's selected -- the Extrusion itself, or a Fusion containing it."""
    if visited is None:
        visited = set()
    if obj.Name in visited:
        return None
    visited.add(obj.Name)
    if hasattr(obj, "LengthFwd"):
        return obj
    for child in getattr(obj, "OutList", []):
        found = _find_extrusion(child, visited)
        if found is not None:
            return found
    return None


def _selected_extrusion():
    sel = Gui.Selection.getSelection()
    if not sel:
        return None
    return _find_extrusion(sel[0])


DEPTH_STEP = 0.5  # mm per click


def _adjust_depth(bigger):
    ext = _selected_extrusion()
    if ext is None:
        QtGui.QMessageBox.warning(
            None, "Text Depth",
            "No depth to adjust here. This only applies to extruded/embossed "
            "text (Create Embossed Text or Create Text On Face) -- flat text "
            "(Create Text Shape) and Annotation Text have no thickness by design.",
        )
        return
    current = float(ext.LengthFwd)
    new_depth = current + DEPTH_STEP if bigger else current - DEPTH_STEP
    ext.LengthFwd = max(0.1, new_depth)
    App.ActiveDocument.recompute()


def _depth_applicable():
    """True if the current selection resolves to something with an
    adjustable extrusion depth (used to grey out the Depth buttons)."""
    return _selected_extrusion() is not None


def _resize_applicable():
    """True if the current selection resolves to a ShapeString (Data.Size)
    or an Annotation Text (ViewObject.FontSize) -- used to grey out the
    Resize buttons when neither applies."""
    if _selected_shapestring() is not None:
        return True
    sel = Gui.Selection.getSelection()
    return bool(sel and hasattr(sel[0], "ViewObject") and hasattr(sel[0].ViewObject, "FontSize"))


def _cycle_font():
    ss = _selected_shapestring()
    if ss is None:
        QtGui.QMessageBox.warning(
            None, "Next Font", "Select the text (or its fused part) first."
        )
        return
    fonts = _get_all_fonts()
    if not fonts:
        QtGui.QMessageBox.warning(
            None, "Next Font",
            "Couldn't enumerate installed fonts (fc-list not available). "
            "Use the font Browse button in the Task Panel instead.",
        )
        return
    try:
        idx = fonts.index(ss.FontFile)
    except ValueError:
        idx = -1
    ss.FontFile = fonts[(idx + 1) % len(fonts)]
    App.ActiveDocument.recompute()


# ---------------------------------------------------------------------------
# Task Panel: one form, shown in the Tasks tab, used by all geometry commands
# ---------------------------------------------------------------------------

class TextTaskPanel:
    """
    mode: "shape"    -> flat outline only
          "embossed" -> extruded solid, floats at origin
          "onface"   -> extruded solid, placed on a pre-selected face
    """

    def __init__(self, mode, face=None, point=None, target_obj=None):
        self.mode = mode
        self.face = face
        self.point = point
        self.target_obj = target_obj

        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Text Settings")
        layout = QtGui.QVBoxLayout(self.form)

        layout.addWidget(QtGui.QLabel("Text:"))
        self.text_edit = QtGui.QLineEdit()
        layout.addWidget(self.text_edit)

        layout.addWidget(QtGui.QLabel("Font file:"))
        font_row = QtGui.QHBoxLayout()
        self.font_edit = QtGui.QLineEdit()
        self.font_edit.setText(_starting_font())
        font_row.addWidget(self.font_edit)
        browse_btn = QtGui.QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_font)
        font_row.addWidget(browse_btn)
        layout.addLayout(font_row)

        layout.addWidget(QtGui.QLabel("Font size (mm):"))
        self.size_spin = QtGui.QDoubleSpinBox()
        self.size_spin.setRange(0.1, 1000.0)
        self.size_spin.setDecimals(2)
        self.size_spin.setValue(_get_last_size())
        layout.addWidget(self.size_spin)

        self.depth_spin = None
        if self.mode in ("embossed", "onface"):
            label = "Extrude depth (mm):" if self.mode == "embossed" else "Emboss depth (mm):"
            layout.addWidget(QtGui.QLabel(label))
            self.depth_spin = QtGui.QDoubleSpinBox()
            self.depth_spin.setRange(0.01, 1000.0)
            self.depth_spin.setDecimals(2)
            self.depth_spin.setValue(_get_last_depth())
            layout.addWidget(self.depth_spin)

        if self.mode == "onface":
            hint = QtGui.QLabel(
                "Text will be placed at the point you clicked on the selected face. "
                "Use the Union Selected button afterward, once you're happy with "
                "position/size/font/depth, to fuse it into the part."
            )
            hint.setWordWrap(True)
            layout.addWidget(hint)

        layout.addStretch()
        self.text_edit.setFocus()

    def browse_font(self):
        start_dir = os.path.dirname(self.font_edit.text()) if self.font_edit.text() else ""
        font_file, _ = QtGui.QFileDialog.getOpenFileName(
            self.form, "Choose font file", start_dir, "Font files (*.ttf *.otf)"
        )
        if font_file:
            self.font_edit.setText(font_file)

    def getStandardButtons(self):
        # PySide6 (used by FreeCAD 1.1+) returns a Flag enum object when you
        # OR two QDialogButtonBox buttons together, and plain int() rejects
        # that combined object even though it accepts each button alone.
        # Convert each individually, then OR the resulting integers.
        def _as_int(value):
            try:
                return int(value)
            except TypeError:
                return int(value.value)

        return _as_int(QtGui.QDialogButtonBox.Ok) | _as_int(QtGui.QDialogButtonBox.Cancel)

    def accept(self):
        text = self.text_edit.text().strip()
        font_file = self.font_edit.text().strip()
        size = self.size_spin.value()
        depth = self.depth_spin.value() if self.depth_spin else None

        if not text:
            QtGui.QMessageBox.warning(self.form, "Text", "Please enter some text.")
            return False
        if not font_file or not os.path.exists(font_file):
            QtGui.QMessageBox.warning(self.form, "Text", "Please choose a valid font file.")
            return False

        _save_last_settings(font_file, size, depth)

        if self.mode == "shape":
            _build_shape_text(text, font_file, size)
        elif self.mode == "embossed":
            _build_embossed_text(text, font_file, size, depth)
        elif self.mode == "onface":
            _build_text_on_face(text, font_file, size, depth, self.face, self.point)

        Gui.Control.closeDialog()
        return True

    def reject(self):
        Gui.Control.closeDialog()
        return True


def _show_task_panel(mode, face=None, point=None, target_obj=None):
    panel = TextTaskPanel(mode, face=face, point=point, target_obj=target_obj)
    Gui.Control.showDialog(panel)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

class CreateShapeText:
    """Create a flat text outline (Draft ShapeString) from a chosen font."""

    def GetResources(self):
        return {
            "Pixmap": "Draft_ShapeString",
            "MenuText": "Create Text Shape",
            "ToolTip": "Create a flat outline shape from text, using any font file",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _show_task_panel("shape")


class CreateEmbossedText:
    """Create text and extrude it into a solid, ready to emboss/engrave onto a part."""

    def GetResources(self):
        return {
            "Pixmap": "Part_Extrude",
            "MenuText": "Create Embossed Text",
            "ToolTip": "Create 3D solid text (extruded), ready to fuse or cut into a part",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _show_task_panel("embossed")


class CreateTextOnFace:
    """Create embossed text mapped onto a pre-selected face, at the picked point."""

    def GetResources(self):
        return {
            "Pixmap": "Draft_SelectPlane",
            "MenuText": "Create Text On Face",
            "ToolTip": "Select a face (click a point on it) first, then run this to place text there",
        }

    def IsActive(self):
        if App.ActiveDocument is None:
            return False
        for sel in Gui.Selection.getSelectionEx():
            for name in sel.SubElementNames:
                if name.startswith("Face"):
                    return True
        return False

    def Activated(self):
        face = None
        picked_point = None
        parent_obj = None

        for sel in Gui.Selection.getSelectionEx():
            for i, name in enumerate(sel.SubElementNames):
                if name.startswith("Face"):
                    face = sel.SubObjects[i]
                    parent_obj = sel.Object
                    # PartDesign features (like Pad) live "inside" a Body and
                    # shouldn't be referenced directly by Part-level features
                    # such as Part::MultiFuse -- FreeCAD calls this a scope
                    # violation and produces an invalid shape. Redirect to the
                    # enclosing Body instead, which is the correct object to
                    # fuse against from outside PartDesign.
                    body = parent_obj.getParentGeoFeatureGroup()
                    if body is not None and body.TypeId == "PartDesign::Body":
                        parent_obj = body
                    if sel.PickedPoints and i < len(sel.PickedPoints):
                        picked_point = sel.PickedPoints[i]
                    break
            if face is not None:
                break

        if face is None:
            QtGui.QMessageBox.warning(
                None, "Text On Face", "Select a face first (click on it in the 3D view), then run this tool."
            )
            return

        _show_task_panel("onface", face=face, point=picked_point, target_obj=parent_obj)


class FuseSelectedText:
    """Boolean-union two or more selected solids into one (built-in, no
    dependency on the Part workbench's own commands being registered)."""

    def GetResources(self):
        return {
            "Pixmap": "union.svg",
            "MenuText": "Union Selected",
            "ToolTip": "Select two or more solids, then fuse them into one",
        }

    def IsActive(self):
        if App.ActiveDocument is None:
            return False
        return len(Gui.Selection.getSelection()) >= 2

    def Activated(self):
        objs = Gui.Selection.getSelection()
        if len(objs) < 2:
            QtGui.QMessageBox.warning(
                None, "Union Selected", "Select two or more solid objects first."
            )
            return

        # Redirect any PartDesign features (Pad, Pocket, etc.) to their
        # enclosing Body -- fusing them directly causes a scope violation.
        resolved = []
        for obj in objs:
            body = obj.getParentGeoFeatureGroup()
            if body is not None and body.TypeId == "PartDesign::Body":
                if body not in resolved:
                    resolved.append(body)
            elif obj not in resolved:
                resolved.append(obj)
        objs = resolved

        if len(objs) < 2:
            QtGui.QMessageBox.warning(
                None, "Union Selected",
                "After resolving PartDesign Bodies, fewer than two distinct "
                "solids remain. Select two or more separate solids/parts.",
            )
            return

        doc = App.ActiveDocument
        fusion = doc.addObject("Part::MultiFuse", "Fusion")
        fusion.Shapes = objs
        fusion.Refine = False
        for obj in objs:
            obj.Visibility = False
        doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")


class NudgeTextLeft:
    def GetResources(self):
        return {"Pixmap": "nudge_left.svg", "MenuText": "Nudge Left",
                 "ToolTip": "Move the selected text left (1mm, along its own orientation)"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _nudge("left")


class NudgeTextRight:
    def GetResources(self):
        return {"Pixmap": "nudge_right.svg", "MenuText": "Nudge Right",
                 "ToolTip": "Move the selected text right (1mm, along its own orientation)"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _nudge("right")


class NudgeTextUp:
    def GetResources(self):
        return {"Pixmap": "nudge_up.svg", "MenuText": "Nudge Up",
                 "ToolTip": "Move the selected text up (1mm, along its own orientation)"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _nudge("up")


class NudgeTextDown:
    def GetResources(self):
        return {"Pixmap": "nudge_down.svg", "MenuText": "Nudge Down",
                 "ToolTip": "Move the selected text down (1mm, along its own orientation)"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _nudge("down")


class TextBigger:
    def GetResources(self):
        return {"Pixmap": "zoom_in.svg", "MenuText": "Text Bigger",
                 "ToolTip": "Increase the selected text's size by 1mm"}

    def IsActive(self):
        return App.ActiveDocument is not None and _resize_applicable()

    def Activated(self):
        _resize(bigger=True)


class TextSmaller:
    def GetResources(self):
        return {"Pixmap": "zoom_out.svg", "MenuText": "Text Smaller",
                 "ToolTip": "Decrease the selected text's size by 1mm"}

    def IsActive(self):
        return App.ActiveDocument is not None and _resize_applicable()

    def Activated(self):
        _resize(bigger=False)


class DepthMore:
    def GetResources(self):
        return {"Pixmap": "depth_more.svg", "MenuText": "Depth Thicker",
                 "ToolTip": "Increase how far the selected text protrudes/embosses by 0.5mm"}

    def IsActive(self):
        return App.ActiveDocument is not None and _depth_applicable()

    def Activated(self):
        _adjust_depth(bigger=True)


class DepthLess:
    def GetResources(self):
        return {"Pixmap": "depth_less.svg", "MenuText": "Depth Thinner",
                 "ToolTip": "Decrease how far the selected text protrudes/embosses by 0.5mm"}

    def IsActive(self):
        return App.ActiveDocument is not None and _depth_applicable()

    def Activated(self):
        _adjust_depth(bigger=False)


class NextFont:
    def GetResources(self):
        return {"Pixmap": "next_font.svg", "MenuText": "Next Font",
                 "ToolTip": "Cycle the selected text to the next installed font"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        _cycle_font()


class ChooseFontPanel:
    """Task panel showing every installed font, each rendered in its own
    typeface, so you can actually see what you're picking instead of
    blindly clicking through them one at a time."""

    def __init__(self, shapestring):
        self.shapestring = shapestring
        self.selected_font = shapestring.FontFile

        self.form = QtGui.QWidget()
        self.form.setWindowTitle("Choose Font")
        layout = QtGui.QVBoxLayout(self.form)

        layout.addWidget(QtGui.QLabel("Filter:"))
        self.filter_edit = QtGui.QLineEdit()
        self.filter_edit.textChanged.connect(self.apply_filter)
        layout.addWidget(self.filter_edit)

        self.list_widget = QtGui.QListWidget()
        self.list_widget.setMinimumHeight(300)
        layout.addWidget(self.list_widget)

        hint = QtGui.QLabel("Loading previews may take a moment if you have many fonts installed.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._font_ids = []  # keep application-font IDs alive/removable
        self._populate(shapestring.String if hasattr(shapestring, "String") else "AaBbCc 123")

        layout.addStretch()

    def _populate(self, sample_text):
        fonts = _get_all_fonts()
        if not fonts:
            self.list_widget.addItem("No fonts found (fc-list unavailable)")
            return

        current_row = 0
        for i, font_path in enumerate(fonts):
            family = None
            try:
                font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    self._font_ids.append(font_id)
                    families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        family = families[0]
            except Exception:
                family = None

            label = sample_text if sample_text.strip() else "AaBbCc 123"
            filename = os.path.basename(font_path)
            display_name = f"{family} ({filename})" if family else filename
            item = QtGui.QListWidgetItem(f"{display_name}:  {label}")
            item.setData(QtCore.Qt.UserRole, font_path)
            if family:
                item.setFont(QtGui.QFont(family, 13))
            self.list_widget.addItem(item)

            if font_path == self.selected_font:
                current_row = i

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(current_row)

    def apply_filter(self, text):
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def getStandardButtons(self):
        def _as_int(value):
            try:
                return int(value)
            except TypeError:
                return int(value.value)
        return _as_int(QtGui.QDialogButtonBox.Ok) | _as_int(QtGui.QDialogButtonBox.Cancel)

    def accept(self):
        item = self.list_widget.currentItem()
        if item is not None:
            font_path = item.data(QtCore.Qt.UserRole)
            if font_path:
                self.shapestring.FontFile = font_path
                App.ActiveDocument.recompute()
        Gui.Control.closeDialog()
        return True

    def reject(self):
        Gui.Control.closeDialog()
        return True


class ChooseFont:
    def GetResources(self):
        return {"Pixmap": "choose_font.svg", "MenuText": "Choose Font",
                 "ToolTip": "Browse installed fonts with a live preview of each"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        ss = _selected_shapestring()
        if ss is None:
            QtGui.QMessageBox.warning(
                None, "Choose Font", "Select the text (or its fused part) first."
            )
            return
        Gui.Control.showDialog(ChooseFontPanel(ss))


class CreateAnnotationText:
    """Create a simple 2D annotation label (not real geometry)."""

    def GetResources(self):
        return {
            "Pixmap": "Draft_Text",
            "MenuText": "Create Annotation Text",
            "ToolTip": "Create a 2D annotation text label (view-only, not solid geometry)",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        text, ok = QtGui.QInputDialog.getText(None, "Annotation Text", "Enter text:")
        if not ok or not text:
            return
        Draft.make_text([text], placement=App.Vector(0, 0, 0))
        App.ActiveDocument.recompute()
        Gui.SendMsgToActiveView("ViewFit")


Gui.addCommand("CreateShapeText", CreateShapeText())
Gui.addCommand("CreateEmbossedText", CreateEmbossedText())
Gui.addCommand("CreateTextOnFace", CreateTextOnFace())
Gui.addCommand("FuseSelectedText", FuseSelectedText())
Gui.addCommand("NudgeTextLeft", NudgeTextLeft())
Gui.addCommand("NudgeTextRight", NudgeTextRight())
Gui.addCommand("NudgeTextUp", NudgeTextUp())
Gui.addCommand("NudgeTextDown", NudgeTextDown())
Gui.addCommand("TextBigger", TextBigger())
Gui.addCommand("TextSmaller", TextSmaller())
Gui.addCommand("DepthMore", DepthMore())
Gui.addCommand("DepthLess", DepthLess())
Gui.addCommand("NextFont", NextFont())
Gui.addCommand("ChooseFont", ChooseFont())
Gui.addCommand("CreateAnnotationText", CreateAnnotationText())
