# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
from FD_FishTool.core.face_rig_builder import FaceRigBuilder

class FacePlacementDialog(QtWidgets.QDialog):
    """Немодальный мастер выбора вертексов (250x350)."""
    def __init__(self, title, steps, callback, parent=None):
        super(FacePlacementDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(250, 350)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setModal(False)
        
        self.steps = steps
        self.callback = callback
        self.results = []
        self.step_idx = 0

        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(f"<b>Step {self.step_idx + 1} of {len(self.steps)}:</b><br>{self.steps[0]}")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: #5dade2; font-size: 10pt;")
        layout.addWidget(self.label)

        self.btn = QtWidgets.QPushButton("Confirm Vertex Selection")
        self.btn.setFixedHeight(45)
        self.btn.clicked.connect(self._confirm)
        layout.addWidget(self.btn)

    def _confirm(self):
        sel = cmds.ls(sl=True, fl=True)
        if not sel or ".vtx" not in sel[0]:
            cmds.warning("FaceRig: Select a vertex in the viewport!")
            return
            
        self.results.append(sel[0])
        self.step_idx += 1
        
        if self.step_idx < len(self.steps):
            self.label.setText(f"<b>Step {self.step_idx + 1} of {len(self.steps)}:</b><br>{self.steps[self.step_idx]}")
        else:
            try:
                self.callback(self.results)
            finally:
                self.close()

class FaceRigTab(QtWidgets.QWidget):
    """Вкладка Face Rig (Stage 4)."""
    def __init__(self, parent=None):
        super(FaceRigTab, self).__init__(parent)
        self.builder = FaceRigBuilder()
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        self.ai_log = QtWidgets.QTextEdit()
        self.ai_log.setReadOnly(True)
        self.ai_log.setStyleSheet("background-color: #1e1e1e; color: #81c784;")
        self.ai_log.setMaximumHeight(100)
        layout.addWidget(QtWidgets.QLabel("AI Log:"))
        layout.addWidget(self.ai_log)

        layout.addWidget(QtWidgets.QLabel("<b>Eyes Module:</b>"))
        self.btn_eyes = QtWidgets.QPushButton("Build Eyes (Auto-Mirror & Colors)")
        self.btn_eyes.setFixedHeight(40)
        self.btn_eyes.clicked.connect(self.run_eyes)
        layout.addWidget(self.btn_eyes)

        layout.addStretch()

    def run_eyes(self):
        steps = [
            "Right Upper Lid: INNER corner", "Right Upper Lid: CENTER", "Right Upper Lid: OUTER corner",
            "Right Lower Lid: INNER corner", "Right Lower Lid: CENTER", "Right Lower Lid: OUTER corner"
        ]
        self.active_dlg = FacePlacementDialog("Eyes Placement Guide", steps, self._finish_eyes)
        self.active_dlg.show()

    def _finish_eyes(self, vtxs):
        bones = [
            "mchFcrg_right_up_eyeShade1", "mchFcrg_right_up_eyeShade2", "mchFcrg_right_up_eyeShade3",
            "mchFcrg_right_dwn_eyeShade1", "mchFcrg_right_dwn_eyeShade2", "mchFcrg_right_dwn_eyeShade3"
        ]
        
        created_locs = []
        for v, b in zip(vtxs, bones):
            loc = self.builder.create_rig_unit(v, b)
            created_locs.append(loc)
            
        for loc in created_locs:
            self.builder.mirror_unit(loc)
            
        self.ai_log.append("> AI: Eyes Build Complete. Mirrored with RotateX=180. Colors applied.")
        self.builder.import_gui_library()
        cmds.select(cl=True)