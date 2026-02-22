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

        # 1. Выбор меша
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

        # 2. Поэтапный скиннинг
        skin_group = QtWidgets.QGroupBox("Staged Skinning")
        skin_lay = QtWidgets.QVBoxLayout(skin_group)
        stages = [
            (1, "Stage 1: Main Body Line"),
            (2, "Stage 2: Vertical Fins"),
            (3, "Stage 3: Side Fins"),
            (4, "Stage 4: Face Details")
        ]
        for idx, label in stages:
            h_lay = QtWidgets.QHBoxLayout()
            h_lay.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"))
            h_lay.addStretch()
            btn_chk = QtWidgets.QPushButton("Select Bones"); btn_chk.setFixedWidth(90)
            btn_add = QtWidgets.QPushButton("Add Influence"); btn_add.setFixedWidth(90)
            
            btn_chk.clicked.connect(lambda *args, i=idx: self.manager.select_stage_bones(i))
            btn_add.clicked.connect(lambda *args, i=idx: self.manager.add_to_skin_logic(i, self.mesh_combo.currentText()))
            
            h_lay.addWidget(btn_chk); h_lay.addWidget(btn_add)
            skin_lay.addLayout(h_lay)
        layout.addWidget(skin_group)

        # 3. Утилиты
        util_group = QtWidgets.QGroupBox("Utilities")
        util_lay = QtWidgets.QVBoxLayout(util_group)
        btn_weighted = QtWidgets.QPushButton("Select Influenced Bones")
        btn_weighted.clicked.connect(lambda: self.manager.select_weighted_bones(self.mesh_combo.currentText()))
        btn_clean = QtWidgets.QPushButton("Remove Zero Weight Bones")
        btn_clean.setToolTip("Очищает skinCluster от костей с 0 весом (принудительно)")
        btn_clean.clicked.connect(lambda: self.manager.clean_weightless_bones(self.mesh_combo.currentText()))
        
        util_lay.addWidget(btn_weighted)
        util_lay.addWidget(btn_clean)
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
        if sel:
            shapes = cmds.listRelatives(sel[0], s=True, type='mesh')
            if shapes:
                if self.mesh_combo.findText(sel[0]) == -1: self.mesh_combo.addItem(sel[0])
                self.mesh_combo.setCurrentIndex(self.mesh_combo.findText(sel[0]))