# -*- coding: utf-8 -*-
import os
from PySide2 import QtWidgets, QtCore, QtGui

class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, config_manager, parent=None):
        """
        Окно настроек конфигурации FD_FishTool.
        :param config_manager: Экземпляр core.config_manager.ConfigManager
        """
        super(SettingsWindow, self).__init__(parent)
        
        self.cfg = config_manager
        self.setWindowTitle("Настройки Пайплайна | FD_FishTool")
        self.setMinimumWidth(550)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Инициализация графического интерфейса настроек."""
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Группа путей проекта
        paths_group = QtWidgets.QGroupBox("Основные пути проекта")
        grid = QtWidgets.QGridLayout(paths_group)
        grid.setSpacing(10)

        # 1. Путь экспорта FBX
        grid.addWidget(QtWidgets.QLabel("Папка экспорта:"), 0, 0)
        self.export_path_ui = QtWidgets.QLineEdit()
        grid.addWidget(self.export_path_ui, 0, 1)
        btn_export = QtWidgets.QPushButton("Обзор")
        btn_export.clicked.connect(lambda: self.browse_folder(self.export_path_ui))
        grid.addWidget(btn_export, 0, 2)

        # 2. Файл эталона анимаций (animation.txt)
        grid.addWidget(QtWidgets.QLabel("Эталон анимаций (txt):"), 1, 0)
        self.anim_data_ui = QtWidgets.QLineEdit()
        grid.addWidget(self.anim_data_ui, 1, 1)
        btn_anim = QtWidgets.QPushButton("Файл")
        btn_anim.clicked.connect(lambda: self.browse_file(self.anim_data_ui, "Text Files (*.txt)"))
        grid.addWidget(btn_anim, 1, 2)

        # 3. Файл словаря костей (bone_map.json)
        grid.addWidget(QtWidgets.QLabel("Словарь имен (json):"), 2, 0)
        self.bone_map_ui = QtWidgets.QLineEdit()
        grid.addWidget(self.bone_map_ui, 2, 1)
        btn_bone = QtWidgets.QPushButton("Файл")
        btn_bone.clicked.connect(lambda: self.browse_file(self.bone_map_ui, "JSON Files (*.json)"))
        grid.addWidget(btn_bone, 2, 2)

        # 4. Путь к Legacy Exporter (папка scripts, содержащая playrix)
        grid.addWidget(QtWidgets.QLabel("Legacy Exporter (scripts):"), 3, 0)
        self.legacy_path_ui = QtWidgets.QLineEdit()
        self.legacy_path_ui.setPlaceholderText("Путь к папке scripts, где лежит 'playrix'...")
        grid.addWidget(self.legacy_path_ui, 3, 1)
        btn_legacy = QtWidgets.QPushButton("Обзор")
        btn_legacy.clicked.connect(lambda: self.browse_folder(self.legacy_path_ui))
        grid.addWidget(btn_legacy, 3, 2)

        main_layout.addWidget(paths_group)

        # Информационная плашка
        info_label = QtWidgets.QLabel(
            "<i>* Убедитесь, что FBXTool.exe находится в папке со старым экспортером.</i>"
        )
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        main_layout.addWidget(info_label)

        # Кнопки управления
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_save = QtWidgets.QPushButton("Применить")
        self.btn_save.setFixedHeight(30)
        self.btn_save.clicked.connect(self.save_settings)
        
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    # --- ЛОГИКА ---

    def browse_folder(self, line_edit):
        """Выбор папки через диалог."""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите директорию", line_edit.text())
        if dir_path:
            line_edit.setText(dir_path)

    def browse_file(self, line_edit, file_filter):
        """Выбор файла через диалог."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите файл", line_edit.text(), file_filter)
        if file_path:
            line_edit.setText(file_path)

    def load_settings(self):
        """Загрузка текущих значений из paths.json."""
        try:
            data = self.cfg.load_json("paths.json")
            self.export_path_ui.setText(data.get("export_path", ""))
            self.anim_data_ui.setText(data.get("animation_data", ""))
            self.bone_map_ui.setText(data.get("bone_map_file", ""))
            self.legacy_path_ui.setText(data.get("legacy_exporter_path", ""))
        except Exception as e:
            print(f"FD_FishTool: Ошибка загрузки настроек: {e}")

    def save_settings(self):
        """Сохранение всех полей в paths.json."""
        data = {
            "export_path": self.export_path_ui.text(),
            "animation_data": self.anim_data_ui.text(),
            "bone_map_file": self.bone_map_ui.text(),
            "legacy_exporter_path": self.legacy_path_ui.text()
        }
        
        try:
            self.cfg.save_json("paths.json", data)
            print("FD_FishTool: Настройки сохранены.")
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(e))