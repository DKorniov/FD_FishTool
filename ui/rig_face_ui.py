# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
from FD_FishTool.core.face_rig_builder import FaceRigBuilder

class FaceSelectorWindow(QtWidgets.QDialog):
    def __init__(self, builder, parent=None):
        super(FaceSelectorWindow, self).__init__(parent)
        self.builder = builder
        self.setWindowTitle("Face Control Selector & Tools")
        self.setMinimumSize(850, 550)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setModal(False)

        main_layout = QtWidgets.QHBoxLayout(self)

        # ЛЕВО: Селектор
        selector_group = QtWidgets.QGroupBox("Interactive Face Selector")
        self.grid = QtWidgets.QGridLayout(selector_group)
        self._setup_selector_buttons()
        main_layout.addWidget(selector_group, stretch=1)

        # ПРАВО: Списки и Инструменты
        right_panel = QtWidgets.QVBoxLayout()
        
        right_panel.addWidget(QtWidgets.QLabel("<b>Driver (Control):</b>"))
        self.driver_list = QtWidgets.QListWidget()
        right_panel.addWidget(self.driver_list)
        btn_load_driver = QtWidgets.QPushButton("Load Selected to Driver")
        btn_load_driver.clicked.connect(lambda: self._load_to_list(self.driver_list))
        right_panel.addWidget(btn_load_driver)

        right_panel.addWidget(QtWidgets.QLabel("<b>Driven (Mechanical Bones):</b>"))
        self.driven_list = QtWidgets.QListWidget()
        right_panel.addWidget(self.driven_list)
        btn_load_driven = QtWidgets.QPushButton("Load Selected to Driven")
        btn_load_driven.clicked.connect(lambda: self._load_to_list(self.driven_list))
        right_panel.addWidget(btn_load_driven)

        # Анимация и Зеркало
        act_group = QtWidgets.QGroupBox("Animation & Rig Tools")
        act_lay = QtWidgets.QVBoxLayout(act_group)
        
        self.btn_gen_anim = QtWidgets.QPushButton("Gen Test Anim")
        self.btn_gen_anim.setFixedHeight(35)
        self.btn_gen_anim.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_gen_anim.clicked.connect(self.builder.run_context_test_animation)

        self.btn_clean_anim = QtWidgets.QPushButton("Clean Test Anim")
        self.btn_clean_anim.clicked.connect(self.builder.clean_test_animation)
        
        self.btn_mirror_pos = QtWidgets.QPushButton("Mirror Driven Pos (R -> L)")
        self.btn_mirror_pos.clicked.connect(self.builder.mirror_drivens_logic)

        self.btn_key = QtWidgets.QPushButton("KEY")
        self.btn_key.setFixedHeight(40)
        self.btn_key.setStyleSheet("background-color: #d35400; color: white; font-weight: bold;")
        
        act_lay.addWidget(self.btn_gen_anim)
        act_lay.addWidget(self.btn_clean_anim)
        act_lay.addWidget(self.btn_mirror_pos)
        act_lay.addWidget(self.btn_key)
        
        right_panel.addWidget(act_group)
        main_layout.addLayout(right_panel, stretch=1)

    def _setup_selector_buttons(self):
        # (Row, Col, Label, Internal_Name)
        controls = [
            (0, 0, "L_Upp_Lid", "L_Upp_EyeLid"), (0, 2, "R_Upp_Lid", "R_Upp_EyeLid"),
            (1, 0, "L_Lwr_Lid", "L_Lwr_EyeLid"), (1, 1, "Sync", "Sync"), (1, 2, "R_Lwr_Lid", "R_Lwr_EyeLid"),
            (2, 1, "Upr_Lip", "Upr_Lip"),
            (3, 0, "Emote", "Emote"), (3, 1, "Lwr_Lip", "Lwr_Lip"), (3, 2, "Jaw", "Jaw"),
            (4, 1, "Teeth", "gui_teeth")
        ]
        for r, c, label, name in controls:
            btn = QtWidgets.QPushButton(label)
            btn.setFixedSize(110, 55)
            # checked=False перехватывает булево значение из сигнала clicked
            btn.clicked.connect(lambda checked=False, n=name: self._select_in_maya(n))
            self.grid.addWidget(btn, r, c)

    def _select_in_maya(self, name):
        if cmds.objExists(name):
            cmds.select(name)
        else:
            cmds.warning(f"Control '{name}' not found.")

    def _load_to_list(self, list_widget):
        list_widget.clear()
        sel = cmds.ls(sl=True)
        if sel: list_widget.addItems(sel)

class FacePlacementDialog(QtWidgets.QDialog):
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
        self.label = QtWidgets.QLabel(f"<b>Step {self.step_idx + 1}:</b><br>{self.steps[0]}")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.btn = QtWidgets.QPushButton("Confirm Selection")
        self.btn.setFixedHeight(50); self.btn.clicked.connect(self._confirm)
        layout.addWidget(self.btn)

    def _confirm(self):
        sel = cmds.ls(sl=True, fl=True)
        if not sel or ".vtx" not in sel[0]: return
        self.results.append(sel[0])
        self.step_idx += 1
        if self.step_idx < len(self.steps):
            self.label.setText(f"<b>Step {self.step_idx + 1}:</b><br>{self.steps[self.step_idx]}")
        else:
            try: self.callback(self.results)
            finally: self.close()

class FaceRigTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FaceRigTab, self).__init__(parent)
        self.builder = FaceRigBuilder()
        self.selector_win = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        self.ai_log = QtWidgets.QTextEdit()
        self.ai_log.setReadOnly(True)
        self.ai_log.setStyleSheet("background-color: #1e1e1e; color: #81c784;")
        self.ai_log.setMaximumHeight(80)
        layout.addWidget(self.ai_log)

        # GUI
        gui_group = QtWidgets.QGroupBox("GUI Setup")
        gui_lay = QtWidgets.QVBoxLayout(gui_group)
        self.btn_open = QtWidgets.QPushButton("Build Face GUI (Selector)")
        self.btn_open.setFixedHeight(45)
        self.btn_open.setStyleSheet("background-color: #2e86c1; color: white; font-weight: bold;")
        self.btn_open.clicked.connect(self.run_open_selector)
        gui_lay.addWidget(self.btn_open)
        layout.addWidget(gui_group)

        # Geometry
        build_group = QtWidgets.QGroupBox("Geometry Build")
        build_lay = QtWidgets.QVBoxLayout(build_group)
        
        self.btn_eyes = QtWidgets.QPushButton("Build Eyes")
        self.btn_eyes.clicked.connect(self.run_eyes)
        build_lay.addWidget(self.btn_eyes)

        self.pair_spin = QtWidgets.QSpinBox(); self.pair_spin.setRange(1, 3)
        build_lay.addWidget(QtWidgets.QLabel("Lip Pairs:"))
        build_lay.addWidget(self.pair_spin)
        self.btn_mouth = QtWidgets.QPushButton("Build Mouth & Cheeks")
        self.btn_mouth.clicked.connect(self.run_mouth)
        build_lay.addWidget(self.btn_mouth)

        self.brow_spin = QtWidgets.QSpinBox(); self.brow_spin.setRange(1, 3); self.brow_spin.setValue(2)
        build_lay.addWidget(QtWidgets.QLabel("Brow Joints:"))
        build_lay.addWidget(self.brow_spin)
        self.btn_brows = QtWidgets.QPushButton("Build Brows")
        self.btn_brows.clicked.connect(self.run_brows)
        build_lay.addWidget(self.btn_brows)

        self.btn_jaw = QtWidgets.QPushButton("Create Jaw & Teeth (Manual)")
        self.btn_jaw.clicked.connect(self.run_jaw_teeth)
        build_lay.addWidget(self.btn_jaw)

        layout.addWidget(build_group)
        layout.addStretch()

    def run_open_selector(self):
        if self.builder.import_gui_library():
            if not self.selector_win:
                self.selector_win = FaceSelectorWindow(self.builder, self)
            self.selector_win.show()

    def run_eyes(self):
        steps = ["R Upper Inner", "R Upper Center", "R Upper Outer", "R Lower Inner", "R Lower Center", "R Lower Outer"]
        self.dlg = FacePlacementDialog("Eyes", steps, self._finish_eyes)
        self.dlg.show()

    def _finish_eyes(self, vtxs):
        bones = ["mchFcrg_right_up_eyeShade1", "mchFcrg_right_up_eyeShade2", "mchFcrg_right_up_eyeShade3",
                 "mchFcrg_right_dwn_eyeShade1", "mchFcrg_right_dwn_eyeShade2", "mchFcrg_right_dwn_eyeShade3"]
        for v, b in zip(vtxs, bones):
            loc = self.builder.create_rig_unit(v, b)
            self.builder.mirror_unit(loc)

    def run_mouth(self):
        num = self.pair_spin.value()
        steps = ["Upper Lip CENTER", "Lower Lip CENTER", "R Mouth Corner"]
        for i in range(num):
            suffix = f" {i+1}" if i > 0 else ""
            steps.extend([f"Pair{suffix}: R UPPER Lip", f"Pair{suffix}: R LOWER Lip"])
        steps.extend(["R UPPER Cheek", "R CENTER Cheek", "R LOWER Cheek"])
        self.dlg = FacePlacementDialog("Mouth", steps, self._finish_mouth)
        self.dlg.show()

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

    def run_brows(self):
        num = self.brow_spin.value()
        steps = [f"Brow Joint {i+1} (R side)" for i in range(num)]
        self.dlg = FacePlacementDialog("Brows", steps, self._finish_brows)
        self.dlg.show()

    def _finish_brows(self, vtxs):
        for i, vtx in enumerate(vtxs):
            loc = self.builder.create_rig_unit(vtx, f"mchFcrg_right_Brow{i+1}")
            self.builder.mirror_unit(loc)

    def run_jaw_teeth(self):
        self.builder.create_rig_unit(None, "mchFcrg_jaw", pos_override=[0, 0, 0])
        self.builder.create_rig_unit(None, "mchFcrg_teeth", pos_override=[0, 1, 0])