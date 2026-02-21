# -*- coding: utf-8 -*-
import os
import sys
import importlib
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds

from FD_FishTool.core.meta_exporter import BoneNamePreparing
from FD_FishTool.core.validator import FishValidator
from FD_FishTool.core.anim_manager import AnimManager
from FD_FishTool.ui.spring_selector import SpringSelectorWindow

class FD_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, parent=None):
        super(FD_MainWindow, self).__init__(parent)
        self.cfg = config
        self.validator = FishValidator(self.cfg)
        self.anim_mgr = AnimManager(self.cfg) # config_manager передается корректно
        
        bone_map = self.cfg.load_json("bone_map.json")
        self.bone_preparer = BoneNamePreparing(bone_map)
        
        self.setWindowTitle("FD_FishTool v2.0 | Master")
        self.setMinimumSize(500, 800)
        self.init_ui()
        self.refresh_anim_list()

    def init_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        self.tabs = QtWidgets.QTabWidget(); layout.addWidget(self.tabs)

        self.tabs.addTab(self.ui_rigging_tab(), "Rigging")
        self.tabs.addTab(self.ui_animation_tab(), "Animation")
        self.tabs.addTab(self.ui_export_tab(), "Export")

    def ui_rigging_tab(self):
        tab = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(tab)
        val_group = QtWidgets.QGroupBox("Валидация"); v_lay = QtWidgets.QVBoxLayout(val_group)
        btn_v = QtWidgets.QPushButton("🔍 RUN VALIDATION"); btn_v.setMinimumHeight(40)
        btn_v.clicked.connect(self.run_validation)
        self.val_report = QtWidgets.QTextEdit(); self.val_report.setReadOnly(True)
        v_lay.addWidget(btn_v); v_lay.addWidget(self.val_report); lay.addWidget(val_group)
        
        prep_group = QtWidgets.QGroupBox("Bone Prep"); p_lay = QtWidgets.QHBoxLayout(prep_group)
        btn_e = QtWidgets.QPushButton("EXPORT MODE"); btn_e.clicked.connect(self.bone_preparer.execute)
        btn_r = QtWidgets.QPushButton("RIG MODE"); btn_r.clicked.connect(self.bone_preparer.execute)
        p_lay.addWidget(btn_e); p_lay.addWidget(btn_r); lay.addWidget(prep_group)
        return tab

    def ui_animation_tab(self):
        tab = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(tab)
        
        lib_group = QtWidgets.QGroupBox("Studio Library Presets")
        l_lay = QtWidgets.QVBoxLayout(lib_group)
        # Пути теперь соответствуют: data/studio_lib/body_standart_anim.anim
        btn_b = QtWidgets.QPushButton("🕺 Select Set & Apply BODY Anim")
        btn_b.clicked.connect(lambda: self.anim_mgr.apply_studio_anim("body_standart_anim.anim"))
        btn_f = QtWidgets.QPushButton("😀 Select Set & Apply FACE Anim")
        btn_f.clicked.connect(lambda: self.anim_mgr.apply_studio_anim("face_standart_anim.anim"))
        l_lay.addWidget(btn_b); l_lay.addWidget(btn_f); lay.addWidget(lib_group)

        sm_group = QtWidgets.QGroupBox("Physics Pipeline")
        s_lay = QtWidgets.QVBoxLayout(sm_group)
        btn_sm = QtWidgets.QPushButton("🧬 OPEN SPRINGMAGIC SELECTOR")
        btn_sm.setMinimumHeight(50); btn_sm.setStyleSheet("background-color: #3d5a6b; color: white; font-weight: bold;")
        btn_sm.clicked.connect(self.open_spring_selector)
        s_lay.addWidget(btn_sm); lay.addWidget(sm_group)

        self.anim_tree = QtWidgets.QTreeWidget(); self.anim_tree.setHeaderLabels(["Clip Name", "Range"])
        self.anim_tree.itemClicked.connect(self.on_clip_click); lay.addWidget(self.anim_tree)
        return tab

    def ui_export_tab(self):
        tab = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(tab)
        btn = QtWidgets.QPushButton("🚀 PLAYRIX EXPORTER"); btn.setMinimumHeight(80); btn.setStyleSheet("background-color: #d4a017; color: black; font-weight: bold;")
        btn.clicked.connect(self.run_legacy_exporter); lay.addWidget(btn); return tab

    def open_spring_selector(self):
        self.swin = SpringSelectorWindow(self.anim_mgr, self); self.swin.show()

    def refresh_anim_list(self):
        self.anim_tree.clear()
        for name, r in self.anim_mgr.anim_ranges.items():
            QtWidgets.QTreeWidgetItem(self.anim_tree, [name, f"{int(r[0])}-{int(r[1])}"])

    def on_clip_click(self, item, col):
        self.anim_mgr.set_timeline(item.text(0))

    def run_validation(self):
        errs, logs = self.validator.validate_all()
        self.val_report.clear()
        for l in logs: self.val_report.append(f"<span style='color:green;'>OK: {l}</span>")
        for e in errs: self.val_report.append(f"<span style='color:red;'>ERR: {e}</span>")

    def run_legacy_exporter(self):
        path = self.cfg.load_json("paths.json").get("legacy_exporter_path", "")
        if path and path not in sys.path: sys.path.append(path)
        try:
            import playrix.export.main_dialog as lex; importlib.reload(lex); lex.show()
        except Exception as e: cmds.warning(str(e))