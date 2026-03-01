# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds
from FD_FishTool.core.rig_body import BodyRigManager
from FD_FishTool.ui.weight_blender_ui import WeightBlenderWidget
from FD_FishTool.ui.easy_ease_ui import EasyEaseWidget

class RigBodyWidget(QtWidgets.QWidget):
    def __init__(self, config=None, parent=None):
        super(RigBodyWidget, self).__init__(parent)
        self.manager = BodyRigManager(config)
        self.setup_ui()
        self.refresh_mesh_list()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5); layout.setSpacing(10)

        # 1. Mesh Selector
        mesh_group = QtWidgets.QGroupBox("Target Mesh Selection")
        ml = QtWidgets.QVBoxLayout(mesh_group); hl = QtWidgets.QHBoxLayout()
        self.mesh_combo = QtWidgets.QComboBox()
        btn_get = QtWidgets.QPushButton("Get Selected"); btn_get.clicked.connect(self._get_mesh_from_sel)
        hl.addWidget(self.mesh_combo, 4); hl.addWidget(btn_get, 1); ml.addLayout(hl); layout.addWidget(mesh_group)

        # 2. Staged Skinning (Все кнопки восстановлены)
        stages_group = QtWidgets.QGroupBox("Staged Skinning Automation")
        sl = QtWidgets.QVBoxLayout(stages_group)
        for idx, lbl in [(1,"Body"),(2,"Vert Fins"),(3,"Side Fins"),(4,"Face")]:
            h = QtWidgets.QHBoxLayout(); h.addWidget(QtWidgets.QLabel(f"<b>Stage {idx}: {lbl}</b>"))
            b1 = QtWidgets.QPushButton("Select"); b2 = QtWidgets.QPushButton("Add")
            b1.clicked.connect(lambda *a, i=idx: self.manager.select_stage_bones(i))
            b2.clicked.connect(lambda *a, i=idx: self.manager.add_to_skin_logic(i, self.mesh_combo.currentText()))
            h.addWidget(b1); h.addWidget(b2); sl.addLayout(h)
        layout.addWidget(stages_group)

        # 3. AnimBot Sliders Layout (Изолированный блок)
        self.blender_ui = WeightBlenderWidget(self.manager, lambda: self.mesh_combo.currentText())
        slider_group = QtWidgets.QGroupBox("Interactive Curve Control")
        vl = QtWidgets.QVBoxLayout(slider_group); vl.addWidget(self.blender_ui); layout.addWidget(slider_group)

        # В метод setup_ui класса RigBodyWidget:
        self.ease_ui = EasyEaseWidget(self.manager, lambda: self.mesh_combo.currentText())
        ease_group = QtWidgets.QGroupBox("Easy Ease Control (test version 1.0)")
        vl = QtWidgets.QVBoxLayout(ease_group); vl.addWidget(self.ease_ui); layout.addWidget(ease_group)

        # 4. Weight Utilities (Все кнопки восстановлены)
        util_group = QtWidgets.QGroupBox("Weight Utilities")
        ul = QtWidgets.QVBoxLayout(util_group)
        btn_apply = QtWidgets.QPushButton("🌀 Apply Adaptive Gradient (XL)"); btn_apply.setStyleSheet("background-color: #2e4a3e; color: #aaffaa; font-weight: bold; height: 35px;")
        btn_apply.clicked.connect(lambda: self.manager.apply_topological_gradient(self.mesh_combo.currentText()))
        btn_weighted = QtWidgets.QPushButton("Select Influenced Bones"); btn_weighted.clicked.connect(lambda: self.manager.select_weighted_bones(self.mesh_combo.currentText()))
        btn_clean = QtWidgets.QPushButton("Remove Zero Weight Bones"); btn_clean.clicked.connect(lambda: self.manager.clean_weightless_bones(self.mesh_combo.currentText()))
        ul.addWidget(btn_apply); ul.addWidget(btn_weighted); ul.addWidget(btn_clean); layout.addWidget(util_group)
        
        layout.addStretch()

    def _get_mesh_from_sel(self):
        sel = cmds.ls(sl=True, type='transform')
        if sel and cmds.listRelatives(sel[0], s=True, type='mesh'):
            if self.mesh_combo.findText(sel[0]) == -1: self.mesh_combo.addItem(sel[0])
            self.mesh_combo.setCurrentIndex(self.mesh_combo.findText(sel[0]))

    def refresh_mesh_list(self):
        self.mesh_combo.clear(); self.mesh_combo.addItems(self.manager.get_all_meshes_in_scene())
        d = self.manager.find_default_mesh()
        if d: self.mesh_combo.setCurrentText(d)