# InitGui.py
# Registers the "Text" workbench with FreeCAD's GUI.

import os

import FreeCAD as App
import FreeCADGui as Gui


class TextWorkbench(Gui.Workbench):
    MenuText = "Text"
    ToolTip = "Tools for creating text geometry and annotations"
    Icon = "Draft_ShapeString"  # reuse a built-in FreeCAD icon

    def Initialize(self):
        # Import here (not at module top-level) so FreeCAD only loads
        # this code once the workbench is actually activated.
        import TextCommands  # noqa: F401

        # TextCommands.py is a normal Python import, so it has a reliable
        # __file__ we can use to locate this folder (InitGui.py itself
        # does not get a __file__ set by FreeCAD's loader).
        self._module_dir = os.path.dirname(TextCommands.__file__)

        # Register our own bundled icons so command Pixmaps can reference
        # them by filename -- borrowed system icon-theme names (go-up,
        # zoom-in, etc.) turned out not to resolve reliably across setups.
        icon_dir = os.path.join(self._module_dir, "Resources", "icons")
        Gui.addIconPath(icon_dir)

        self.commands = [
            "CreateShapeText",
            "CreateEmbossedText",
            "CreateTextOnFace",
            "CreateAnnotationText",
            "FuseSelectedText",
        ]
        self.appendToolbar("Text Tools", self.commands)
        self.appendMenu("Text", self.commands)

        # Adjustment tools: nudge/resize/font-cycle whatever text object
        # is currently selected (works on the ShapeString, its Extrusion,
        # or a Fusion containing it).
        self.adjust_commands = [
            "NudgeTextLeft",
            "NudgeTextRight",
            "NudgeTextUp",
            "NudgeTextDown",
            "RotateText90",
            "TextBigger",
            "TextSmaller",
            "DepthMore",
            "DepthLess",
        ]
        self.appendToolbar("Text Adjust", self.adjust_commands)
        self.appendMenu("Text", self.adjust_commands)

    def Activated(self):
        version_file = os.path.join(getattr(self, "_module_dir", ""), "VERSION.txt")
        try:
            with open(version_file, "r") as f:
                App.Console.PrintMessage("TextWorkbench version: " + f.read())
        except Exception as e:
            App.Console.PrintMessage("TextWorkbench: version check failed (%s)\n" % e)

    def Deactivated(self):
        pass

    def ContextMenu(self, recipient):
        self.appendContextMenu("Text Tools", self.commands)
        self.appendContextMenu("Text Adjust", self.adjust_commands)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(TextWorkbench())
