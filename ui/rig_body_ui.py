# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds
from FD_FishTool.core.rig_body import BodyRigManager

class RigBodyWidget(QtWidgets.QWidget):
    def __init__(self, config=None, parent=None):
        super(RigBodyWidget, self).__init__(parent)
        self.manager = BodyRigManager(config)
        self.setup_ui()
        self.refresh_mesh_list()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5); layout.setSpacing(8)

        # 1. Target Mesh Selection
        mesh_group = QtWidgets.QGroupBox("Target Mesh Selection")
        mesh_lay = QtWidgets.QVBoxLayout(mesh_group)
        h_sel_lay = QtWidgets.QHBoxLayout()
        self.mesh_combo = QtWidgets.QComboBox(); self.mesh_combo.setEditable(True)
        btn_refresh = QtWidgets.QPushButton("🔄"); btn_refresh.setFixedWidth(30)
        btn_refresh.clicked.connect(self.refresh_mesh_list)
        btn_get = QtWidgets.QPushButton("Get Selected"); btn_get.clicked.connect(self._get_mesh_from_sel)
        h_sel_lay.addWidget(self.mesh_combo, 4); h_sel_lay.addWidget(btn_refresh, 0); h_sel_lay.addWidget(btn_get, 1)
        mesh_lay.addLayout(h_sel_lay)
        layout.addWidget(mesh_group)

        # 2. Staged Skinning
        stages_group = QtWidgets.QGroupBox("Staged Skinning Automation")
        stages_lay = QtWidgets.QVBoxLayout(stages_group)
        stages = [(1, "Stage 1: Body Line"), (2, "Stage 2: Vert Fins"), (3, "Stage 3: Side Fins"), (4, "Stage 4: Face")]
        for idx, label in stages:
            h_lay = QtWidgets.QHBoxLayout()
            h_lay.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"))
            h_lay.addStretch()
            btn_chk = QtWidgets.QPushButton("Select"); btn_chk.setFixedWidth(80)
            btn_add = QtWidgets.QPushButton("Add"); btn_add.setFixedWidth(80)
            btn_chk.clicked.connect(lambda *args, i=idx: self.manager.select_stage_bones(i))
            btn_add.clicked.connect(lambda *args, i=idx: self.manager.add_to_skin_logic(i, self.mesh_combo.currentText()))
            h_lay.addWidget(btn_chk); h_lay.addWidget(btn_add); stages_lay.addLayout(h_lay)
        layout.addWidget(stages_group)

        # 3. Weight Utilities
        util_group = QtWidgets.QGroupBox("Weight Utilities")
        util_lay = QtWidgets.QVBoxLayout(util_group)
        
        btn_gradient = QtWidgets.QPushButton("✨ Apply Hierarchical Blur Gradient")
        btn_gradient.setStyleSheet("background-color: #2e4a3e; color: #aaffaa; font-weight: bold;")
        btn_gradient.setToolTip("Размывает веса между Start и End костью по схеме 0.25/0.25/0.1")
        btn_gradient.clicked.connect(lambda: self.manager.apply_weight_gradient_logic(self.mesh_combo.currentText()))
        
        btn_weighted = QtWidgets.QPushButton("Select Influenced Bones")
        btn_weighted.clicked.connect(lambda: self.manager.select_weighted_bones(self.mesh_combo.currentText()))
        
        btn_clean = QtWidgets.QPushButton("Remove Zero Weight Bones")
        btn_clean.clicked.connect(lambda: self.manager.clean_weightless_bones(self.mesh_combo.currentText()))
        
        util_lay.addWidget(btn_gradient); util_lay.addWidget(btn_weighted); util_lay.addWidget(btn_clean)
        layout.addWidget(util_group)

        layout.addStretch()

    def refresh_mesh_list(self):
        self.mesh_combo.clear()
        all_meshes = self.manager.get_all_meshes_in_scene()
        self.mesh_combo.addItems(all_meshes)
        default = self.manager.find_default_mesh()
        if default:
            idx = self.mesh_combo.findText(default)
            if idx >= 0: self.mesh_combo.setCurrentIndex(idx)

    def _get_mesh_from_sel(self):
        sel = cmds.ls(sl=True, type='transform')
        if sel and cmds.listRelatives(sel[0], s=True, type='mesh'):
            if self.mesh_combo.findText(sel[0]) == -1: self.mesh_combo.addItem(sel[0])
            self.mesh_combo.setCurrentIndex(self.mesh_combo.findText(sel[0]))