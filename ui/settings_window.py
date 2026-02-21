from PySide2 import QtWidgets, QtCore
import os
import json

class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, config_manager, parent=None):
        super(SettingsWindow, self).__init__(parent)
        self.cfg = config_manager
        self.setWindowTitle("FD_FishTool Настройки")
        self.setMinimumWidth(500)
        
        layout = QtWidgets.QVBoxLayout(self)
        grid = QtWidgets.QGridLayout()
        layout.addLayout(grid)

        # Папка экспорта
        grid.addWidget(QtWidgets.QLabel("Папка экспорта:"), 0, 0)
        self.export_ui = QtWidgets.QLineEdit(self.cfg.load_json("paths.json").get("export_path", ""))
        grid.addWidget(self.export_ui, 0, 1)
        btn_exp = QtWidgets.QPushButton("...")
        btn_exp.clicked.connect(self.browse_dir)
        grid.addWidget(btn_exp, 0, 2)

        # JSON костей
        grid.addWidget(QtWidgets.QLabel("JSON костей:"), 1, 0)
        self.bone_ui = QtWidgets.QLineEdit(self.cfg.load_json("paths.json").get("bone_map_file", ""))
        grid.addWidget(self.bone_ui, 1, 1)
        btn_bone = QtWidgets.QPushButton("...")
        btn_bone.clicked.connect(lambda: self.browse_bone_file())
        grid.addWidget(btn_bone, 1, 2)

        # Animation Reference TXT
        grid.addWidget(QtWidgets.QLabel("Эталон анимаций (txt):"), 2, 0)
        self.anim_ui = QtWidgets.QLineEdit(self.cfg.load_json("paths.json").get("animation_data", ""))
        grid.addWidget(self.anim_ui, 2, 1)
        btn_anim = QtWidgets.QPushButton("...")
        btn_anim.clicked.connect(lambda: self.browse_anim_file())
        grid.addWidget(btn_anim, 2, 2)

        save_btn = QtWidgets.QPushButton("СОХРАНИТЬ КОНФИГ")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

    def browse_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if path: self.export_ui.setText(path)

    def browse_bone_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Bone Map JSON", "", "JSON (*.json)")
        if path: self.bone_ui.setText(path)

    def browse_anim_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Animation Reference", "", "Text (*.txt)")
        if path: self.anim_ui.setText(path)

    def save_settings(self):
        data = self.cfg.load_json("paths.json")
        data["export_path"] = self.export_ui.text()
        data["bone_map_file"] = self.bone_ui.text()
        data["animation_data"] = self.anim_ui.text()
        self.cfg.save_json("paths.json", data)
        self.accept()