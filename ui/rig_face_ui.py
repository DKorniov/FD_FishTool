# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
from FD_FishTool.core.face_rig_builder import FaceRigBuilder

class FaceSelectorWindow(QtWidgets.QDialog):
    def __init__(self, builder, parent=None, log_widget=None):
        super(FaceSelectorWindow, self).__init__(parent)
        self.builder = builder
        self.ai_log = log_widget
        self.setWindowTitle("Face Selector & SMART KEY")
        self.setMinimumSize(850, 550)
        self.setWindowFlags(QtCore.Qt.Window) # Maya-style window
        self.setModal(False)
        
        main_lay = QtWidgets.QHBoxLayout(self)
        sel_grp = QtWidgets.QGroupBox("Selector")
        self.grid = QtWidgets.QGridLayout(sel_grp)
        self._setup_grid()
        main_lay.addWidget(sel_grp, stretch=2)

        right_panel = QtWidgets.QVBoxLayout()
        right_panel.addWidget(QtWidgets.QLabel("<b>Driven Bones (Auto-load):</b>"))
        self.driven_list = QtWidgets.QListWidget()
        self.driven_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        right_panel.addWidget(self.driven_list)
        
        self.btn_key = QtWidgets.QPushButton("KEY")
        self.btn_key.setFixedHeight(60)
        self.btn_key.setStyleSheet("background-color: #d35400; color: white; font-weight: bold; font-size: 16pt;")
        self.btn_key.clicked.connect(self._do_key)
        right_panel.addWidget(self.btn_key)

        anim_grp = QtWidgets.QGroupBox("Test Tools")
        al = QtWidgets.QVBoxLayout(anim_grp)
        self.btn_gen = QtWidgets.QPushButton("Gen Test Anim")
        self.btn_gen.clicked.connect(self._run_anim)
        self.btn_clean = QtWidgets.QPushButton("Clean & Zero All")
        self.btn_clean.clicked.connect(self._run_clean)
        al.addWidget(self.btn_gen); al.addWidget(self.btn_clean)
        right_panel.addWidget(anim_grp)
        main_lay.addLayout(right_panel, stretch=1)

    def _setup_grid(self):
        ctrls = [(0,0,"L_Upp_Lid","L_Upp_EyeLid"),(0,2,"R_Upp_Lid","R_Upp_EyeLid"),
                 (1,0,"L_Lwr_Lid","L_Lwr_EyeLid"),(1,1,"Sync","Sync"),(1,2,"R_Lwr_Lid","R_Lwr_EyeLid"),
                 (2,1,"Upr_Lip","Upr_Lip"),(3,0,"Emote","Emote"),(3,1,"Lwr_Lip","Lwr_Lip"),
                 (3,2,"Jaw","Jaw"),(4,1,"Teeth","gui_teeth")]
        for r, c, l, n in ctrls:
            b = QtWidgets.QPushButton(l); b.setFixedSize(110, 50)
            b.clicked.connect(lambda ch=False, name=n: self._on_click(name))
            self.grid.addWidget(b, r, c)

    def _on_click(self, name):
        if not cmds.objExists(name): return
        cmds.select(name)
        self.driven_list.clear()
        bones = self.builder.get_driven_bones(name)
        if bones: self.driven_list.addItems(bones)

    def _do_key(self):
        sel = cmds.ls(sl=True)
        if not sel: return
        nodes = [self.driven_list.item(i).text() for i in range(self.driven_list.count())]
        if nodes:
            self.builder.ai_log = self.ai_log
            # Передаем только объект, каналы возьмем из JSON анимации
            self.builder.set_smart_key(sel[0], nodes)

    def _run_anim(self):
        self.builder.run_context_test_animation()
        if self.ai_log: self.ai_log.append("> AI: Test animation generated.")

    def _run_clean(self):
        self.builder.clean_test_animation()
        if self.ai_log: self.ai_log.append("> AI: Animation cleaned.")

class FacePlacementDialog(QtWidgets.QDialog):
    def __init__(self, title, steps, callback, parent=None):
        super(FacePlacementDialog, self).__init__(parent)
        self.setWindowTitle(title); self.setMinimumSize(250, 350)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint); self.setModal(False)
        self.steps = steps; self.callback = callback; self.results = []; self.step_idx = 0
        l = QtWidgets.QVBoxLayout(self)
        self.lbl = QtWidgets.QLabel("<b>Step {}:</b><br>{}".format(self.step_idx + 1, self.steps[0])); self.lbl.setWordWrap(True)
        l.addWidget(self.lbl)
        self.btn = QtWidgets.QPushButton("Confirm Selection"); self.btn.setFixedHeight(50); self.btn.clicked.connect(self._confirm)
        l.addWidget(self.btn)

    def _confirm(self):
        s = cmds.ls(sl=True, fl=True)
        if not s or ".vtx" not in s[0]: return
        self.results.append(s[0]); self.step_idx += 1
        if self.step_idx < len(self.steps): self.lbl.setText("<b>Step {}:</b><br>{}".format(self.step_idx + 1, self.steps[self.step_idx]))
        else: self.callback(self.results); self.close()

class FaceRigTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FaceRigTab, self).__init__(parent); self.builder = FaceRigBuilder(); self.selector = None; self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.ai_log = QtWidgets.QTextEdit(); self.ai_log.setReadOnly(True); self.ai_log.setMaximumHeight(80)
        self.ai_log.setStyleSheet("background-color: #1e1e1e; color: #81c784;")
        layout.addWidget(QtWidgets.QLabel("AI Log:")); layout.addWidget(self.ai_log)

        self.btn_gui = QtWidgets.QPushButton("Build Face GUI / Selector")
        self.btn_gui.setFixedHeight(45); self.btn_gui.setStyleSheet("background-color: #2e86c1; color: white; font-weight: bold;")
        self.btn_gui.clicked.connect(self.open_selector); layout.addWidget(self.btn_gui)

        g_geo = QtWidgets.QGroupBox("Stage 4: Geometry Generation")
        gl = QtWidgets.QVBoxLayout(g_geo)
        self.btn_eyes = QtWidgets.QPushButton("Build Eyes"); self.btn_eyes.clicked.connect(self.run_eyes); gl.addWidget(self.btn_eyes)
        mouth_l = QtWidgets.QHBoxLayout(); mouth_l.addWidget(QtWidgets.QLabel("Lip Pairs:")); self.pair_spin = QtWidgets.QSpinBox(); self.pair_spin.setRange(1, 3); mouth_l.addWidget(self.pair_spin)
        gl.addLayout(mouth_l); self.btn_mouth = QtWidgets.QPushButton("Build Mouth"); self.btn_mouth.clicked.connect(self.run_mouth); gl.addWidget(self.btn_mouth)
        brow_l = QtWidgets.QHBoxLayout(); brow_l.addWidget(QtWidgets.QLabel("Brows:")); self.brow_spin = QtWidgets.QSpinBox(); self.brow_spin.setRange(1, 3); self.brow_spin.setValue(2); brow_l.addWidget(self.brow_spin)
        gl.addLayout(brow_l); self.btn_brows = QtWidgets.QPushButton("Build Brows"); self.btn_brows.clicked.connect(self.run_brows); gl.addWidget(self.btn_brows)
        self.btn_jaw = QtWidgets.QPushButton("Create Jaw & Teeth"); self.btn_jaw.clicked.connect(self.run_jaw_teeth); gl.addWidget(self.btn_jaw)
        layout.addWidget(g_geo); layout.addStretch()

    def open_selector(self):
        if self.builder.import_gui_library():
            if not self.selector: self.selector = FaceSelectorWindow(self.builder, self, self.ai_log)
            self.selector.show()

    def run_eyes(self):
        s = ["R Up In", "R Up Mid", "R Up Out", "R Dw In", "R Dw Mid", "R Dw Out"]
        self.dlg = FacePlacementDialog("Eyes", s, self._finish_eyes); self.dlg.show()

    def _finish_eyes(self, v):
        b = ["mchFcrg_right_up_eyeShade1","mchFcrg_right_up_eyeShade2","mchFcrg_right_up_eyeShade3","mchFcrg_right_dwn_eyeShade1","mchFcrg_right_dwn_eyeShade2","mchFcrg_right_dwn_eyeShade3"]
        for vtx, bone in zip(v, b): l = self.builder.create_rig_unit(vtx, bone); self.builder.mirror_unit(l)

    def run_mouth(self):
        num = self.pair_spin.value(); s = ["Up Lip C", "Dw Lip C", "R Corner"]
        for i in range(num): sf = " {}".format(i+1) if i > 0 else ""; s.extend(["Pair{}: R UP Lip".format(sf), "Pair{}: R DW Lip".format(sf)])
        s.extend(["R UP Cheek", "R MID Cheek", "R DW Cheek"])
        self.dlg = FacePlacementDialog("Mouth", s, self._finish_mouth); self.dlg.show()

    def _finish_mouth(self, v):
        self.builder.create_rig_unit(v[0], "mchFcrg_cent_up_lip1"); self.builder.create_rig_unit(v[1], "mchFcrg_cent_dwn_lip1")
        lc = self.builder.create_rig_unit(v[2], "mchFcrg_right_corner_lip"); self.builder.mirror_unit(lc)
        idx = 3; num = self.pair_spin.value()
        for i in range(num):
            sf = "{}".format(i+1) if i > 0 else ""; u = self.builder.create_rig_unit(v[idx], "mchFcrg_right_up_lip{}".format(sf)); d = self.builder.create_rig_unit(v[idx+1], "mchFcrg_right_dwn_lip{}".format(sf))
            self.builder.mirror_unit(u); self.builder.mirror_unit(d); idx += 2
        for n in ["mchFcrg_right_up_cheek", "mchFcrg_right_cntr_cheek", "mchFcrg_right_dwn_cheek"]:
            l = self.builder.create_rig_unit(v[idx], n); self.builder.mirror_unit(l); idx += 1

    def run_brows(self):
        n = self.brow_spin.value(); s = ["Brow {} (R)".format(i+1) for i in range(n)]
        self.dlg = FacePlacementDialog("Brows", s, self._finish_brows); self.dlg.show()

    def _finish_brows(self, v):
        for i, vtx in enumerate(v): l = self.builder.create_rig_unit(vtx, f"mchFcrg_right_Brow{i+1}"); self.builder.mirror_unit(l)

    def run_jaw_teeth(self):
        self.builder.create_rig_unit(None, "mchFcrg_jaw", [0, 0, 0]); self.builder.create_rig_unit(None, "mchFcrg_teeth", [0, 1, 0])