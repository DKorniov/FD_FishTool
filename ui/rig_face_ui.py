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

        self.btn = QtWidgets.QPushButton("Confirm Selection")
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
            try: self.callback(self.results)
            finally: self.close()

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
        self.ai_log.setMaximumHeight(80)
        layout.addWidget(QtWidgets.QLabel("AI Log:"))
        layout.addWidget(self.ai_log)

        # Mouth Config
        m_group = QtWidgets.QGroupBox("Mouth Setup")
        m_lay = QtWidgets.QVBoxLayout(m_group)
        pair_lay = QtWidgets.QHBoxLayout()
        pair_lay.addWidget(QtWidgets.QLabel("Lip Pairs (1-3):"))
        self.pair_spin = QtWidgets.QSpinBox()
        self.pair_spin.setRange(1, 3)
        pair_lay.addWidget(self.pair_spin)
        m_lay.addLayout(pair_lay)
        self.btn_mouth = QtWidgets.QPushButton("Build Mouth & Cheeks")
        self.btn_mouth.clicked.connect(self.run_mouth)
        m_lay.addWidget(self.btn_mouth)
        layout.addWidget(m_group)

        # Brows Config
        b_group = QtWidgets.QGroupBox("Brows Setup")
        b_lay = QtWidgets.QVBoxLayout(b_group)
        b_pair_lay = QtWidgets.QHBoxLayout()
        b_pair_lay.addWidget(QtWidgets.QLabel("Brow Joints (1-3):"))
        self.brow_spin = QtWidgets.QSpinBox()
        self.brow_spin.setRange(1, 3)
        self.brow_spin.setValue(2)
        b_pair_lay.addWidget(self.brow_spin)
        b_lay.addLayout(b_pair_lay)
        self.btn_brows = QtWidgets.QPushButton("Build Brows")
        self.btn_brows.clicked.connect(self.run_brows)
        b_lay.addWidget(self.btn_brows)
        layout.addWidget(b_group)

        # Eyes & Extra
        self.btn_eyes = QtWidgets.QPushButton("Build Eyes")
        self.btn_eyes.clicked.connect(self.run_eyes)
        layout.addWidget(self.btn_eyes)

        self.btn_extra = QtWidgets.QPushButton("Create Jaw & Teeth (Manual)")
        self.btn_extra.clicked.connect(self.run_extra)
        layout.addWidget(self.btn_extra)

        layout.addStretch()

    def run_eyes(self):
        steps = ["R_Upper Inner", "R_Upper Center", "R_Upper Outer", "R_Lower Inner", "R_Lower Center", "R_Lower Outer"]
        self.active_dlg = FacePlacementDialog("Eyes Guide", steps, self._finish_eyes)
        self.active_dlg.show()

    def _finish_eyes(self, vtxs):
        bones = ["mchFcrg_right_up_eyeShade1", "mchFcrg_right_up_eyeShade2", "mchFcrg_right_up_eyeShade3",
                 "mchFcrg_right_dwn_eyeShade1", "mchFcrg_right_dwn_eyeShade2", "mchFcrg_right_dwn_eyeShade3"]
        for v, b in zip(vtxs, bones):
            loc = self.builder.create_rig_unit(v, b)
            self.builder.mirror_unit(loc)
        self.builder.import_gui_library()

    def run_brows(self):
        num = self.brow_spin.value()
        steps = [f"Select Brow Joint {i+1} (R side)" for i in range(num)]
        self.active_dlg = FacePlacementDialog("Brows Guide", steps, self._finish_brows)
        self.active_dlg.show()

    def _finish_brows(self, vtxs):
        for i, vtx in enumerate(vtxs):
            loc = self.builder.create_rig_unit(vtx, f"mchFcrg_right_Brow{i+1}")
            self.builder.mirror_unit(loc)
        self.ai_log.append(f"> AI: {len(vtxs)} Brows created and mirrored.")

    def run_mouth(self):
        num = self.pair_spin.value()
        steps = ["Upper Lip CENTER", "Lower Lip CENTER", "R Mouth Corner"]
        for i in range(num):
            suf = f" {i+1}" if i > 0 else ""
            steps.extend([f"Pair{suf}: R UPPER Lip", f"Pair{suf}: R LOWER Lip"])
        steps.extend(["R UPPER Cheek", "R CENTER Cheek", "R LOWER Cheek"])
        # УДАЛЕНО: Teeth Position
        self.active_dlg = FacePlacementDialog("Mouth Guide", steps, self._finish_mouth)
        self.active_dlg.show()

    def _finish_mouth(self, vtxs):
        num = self.pair_spin.value()
        self.builder.create_rig_unit(vtxs[0], "mchFcrg_cent_up_lip1")
        self.builder.create_rig_unit(vtxs[1], "mchFcrg_cent_dwn_lip1")
        loc_c = self.builder.create_rig_unit(vtxs[2], "mchFcrg_right_corner_lip")
        self.builder.mirror_unit(loc_c)
        idx = 3
        for i in range(num):
            suf = f"{i+1}" if i > 0 else ""
            l_u = self.builder.create_rig_unit(vtxs[idx], f"mchFcrg_right_up_lip{suf}")
            l_d = self.builder.create_rig_unit(vtxs[idx+1], f"mchFcrg_right_dwn_lip{suf}")
            self.builder.mirror_unit(l_u); self.builder.mirror_unit(l_d); idx += 2
        for name in ["mchFcrg_right_up_cheek", "mchFcrg_right_cntr_cheek", "mchFcrg_right_dwn_cheek"]:
            l_ch = self.builder.create_rig_unit(vtxs[idx], name)
            self.builder.mirror_unit(l_ch); idx += 1
        self.builder.import_gui_library()

    def run_extra(self):
        """Ручная установка челюсти и зубов в нулевые координаты."""
        self.builder.create_rig_unit(None, "mchFcrg_jaw", pos_override=[0, 0, 0])
        self.builder.create_rig_unit(None, "mchFcrg_teeth", pos_override=[0, 1, 0])
        self.ai_log.append("> AI: Jaw and Teeth targets created. Please move them manually.")