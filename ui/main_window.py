# -*- coding: utf-8 -*-
import os
import sys
import importlib
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
import maya.mel as mel

# Импорты внутренних модулей проекта (v3)
from FD_FishTool.core.meta_exporter import BoneNamePreparing
from FD_FishTool.core.validator import FishValidator
from FD_FishTool.core.anim_handler import AnimSyncManager

# НОВЫЕ ИМПОРТЫ (Интеграция v4)
from FD_FishTool.core.anim_manager import AnimManager
from FD_FishTool.ui.spring_selector import SpringSelectorWindow

class FD_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, parent=None):
        super(FD_MainWindow, self).__init__(parent)
        
        self.cfg = config
        self.validator = FishValidator(self.cfg)
        # Инициализируем менеджер анимаций из v4
        self.anim_mgr = AnimManager(self.cfg) 
        self.legacy_tool = None
        
        self.setWindowTitle("FD_FishTool v2.0 | Integrated Master")
        self.setMinimumSize(450, 800)
        
        self.init_ui()
        print("FD_FishTool: UI успешно инициализирован.")

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # Подключаем вкладки
        self.tabs.addTab(self.ui_rigging(), "Rigging")
        self.tabs.addTab(self.ui_animation(), "Animation")
        self.tabs.addTab(self.ui_export(), "Export")

        btn_settings = QtWidgets.QPushButton("⚙ Настройки Пайплайна")
        btn_settings.setMinimumHeight(40)
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)

    def ui_rigging(self):
        """Инструменты риггинга + Физика v4."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # Секция физики из v4
        sm_group = QtWidgets.QGroupBox("Physics Pipeline (v4)")
        sm_lay = QtWidgets.QVBoxLayout(sm_group)
        btn_sm = QtWidgets.QPushButton("🧬 OPEN SPRINGMAGIC SELECTOR")
        btn_sm.setMinimumHeight(50)
        btn_sm.setStyleSheet("background-color: #3d5a6b; font-weight: bold; color: white;")
        btn_sm.clicked.connect(self.open_spring_selector)
        sm_lay.addWidget(btn_sm)
        layout.addWidget(sm_group)

        layout.addSpacing(10)
        
        # AI Assistant (v3)
        ai_group = QtWidgets.QGroupBox("AI Rig Assistant")
        ai_lay = QtWidgets.QVBoxLayout(ai_group)
        self.ai_input = QtWidgets.QLineEdit()
        self.ai_input.setPlaceholderText("Напр: 'Исправь веса на плавниках'...")
        ai_lay.addWidget(self.ai_input)
        btn_ai = QtWidgets.QPushButton("✨ АНАЛИЗ И ЗАПУСК")
        btn_ai.clicked.connect(lambda: print(f"AI: Анализ запроса '{self.ai_input.text()}'"))
        ai_lay.addWidget(btn_ai)
        layout.addWidget(ai_group)

        layout.addStretch()
        return tab

    def ui_animation(self):
        """Объединенная вкладка: Вставка анимаций (v4) + Проверка (v3)."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # --- СЕКЦИЯ V4: ЗАГРУЗКА ПРЕСЕТОВ ---
        lib_group = QtWidgets.QGroupBox("Studio Library Presets (v4)")
        lib_lay = QtWidgets.QVBoxLayout(lib_group)
        
        h_btn_lay = QtWidgets.QHBoxLayout()
        btn_body = QtWidgets.QPushButton("🕺 Apply BODY Anim")
        btn_body.setToolTip("Загрузить стандартную анимацию тела")
        btn_body.clicked.connect(lambda: self.anim_mgr.apply_studio_anim("body_standart_anim.anim"))
        
        btn_face = QtWidgets.QPushButton("😀 Apply FACE Anim")
        btn_face.setToolTip("Загрузить стандартную анимацию лица")
        btn_face.clicked.connect(lambda: self.anim_mgr.apply_studio_anim("face_standart_anim.anim"))
        
        h_btn_lay.addWidget(btn_body)
        h_btn_lay.addWidget(btn_face)
        lib_lay.addLayout(h_btn_lay)
        layout.addWidget(lib_group)

        # --- СЕКЦИЯ V3: СИНХРОНИЗАЦИЯ (СТАРОЕ) ---
        sync_group = QtWidgets.QGroupBox("Animation Sync Checker (v3)")
        sync_lay = QtWidgets.QVBoxLayout(sync_group)
        
        self.anim_tree = QtWidgets.QTreeWidget()
        self.anim_tree.setHeaderLabels(["Статус", "Клип", "Эталон", "В Сцене"])
        self.anim_tree.itemClicked.connect(self.on_clip_click)
        sync_lay.addWidget(self.anim_tree)

        btn_sync = QtWidgets.QPushButton("🔄 СИНХРОНИЗИРОВАТЬ СПИСОК")
        btn_sync.setMinimumHeight(40)
        btn_sync.clicked.connect(self.refresh_anim_list)
        sync_lay.addWidget(btn_sync)
        
        layout.addWidget(sync_group)
        return tab

    def ui_export(self):
        """Техническая валидация и экспорт (v3 - без изменений)."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        val_group = QtWidgets.QGroupBox("1. Техническая проверка")
        val_lay = QtWidgets.QVBoxLayout(val_group)
        btn_validate = QtWidgets.QPushButton("🔍 ПРОВЕРИТЬ СЦЕНУ (OM2)")
        btn_validate.setFixedHeight(40)
        btn_validate.clicked.connect(self.run_validation)
        val_lay.addWidget(btn_validate)
        
        self.report_tree = QtWidgets.QTreeWidget()
        self.report_tree.setHeaderLabels(["Результат", "Описание"])
        val_lay.addWidget(self.report_tree)
        layout.addWidget(val_group)

        prep_group = QtWidgets.QGroupBox("2. Подготовка и Экспорт")
        prep_lay = QtWidgets.QVBoxLayout(prep_group)
        btn_toggle = QtWidgets.QPushButton("🔄 ПЕРЕКЛЮЧИТЬ ИМЕНА (RIG/EXPORT)")
        btn_toggle.setMinimumHeight(50)
        btn_toggle.setStyleSheet("background-color: #4e7a4e; color: white; font-weight: bold;")
        btn_toggle.clicked.connect(self.run_export_toggle)
        prep_lay.addWidget(btn_toggle)

        btn_legacy = QtWidgets.QPushButton("🚀 ЗАПУСТИТЬ PLAYRIX EXPORTER")
        btn_legacy.setMinimumHeight(80)
        btn_legacy.setStyleSheet("background-color: #d4a017; color: black; font-weight: bold;")
        btn_legacy.clicked.connect(self.launch_legacy_exporter)
        prep_lay.addWidget(btn_legacy)
        
        layout.addWidget(prep_group)
        return tab

    # --- ЛОГИКА (v3 сохранилась, v4 добавилась) ---

    def open_spring_selector(self):
        self.spring_win = SpringSelectorWindow(self.anim_mgr, parent=self)
        self.spring_win.show()

    def run_validation(self):
        self.report_tree.clear()
        errors, success = self.validator.validate_all()
        for msg in success:
            item = QtWidgets.QTreeWidgetItem(["✅ PASS", msg])
            item.setForeground(0, QtGui.QColor(120, 255, 120))
            self.report_tree.addTopLevelItem(item)
        for err in errors:
            item = QtWidgets.QTreeWidgetItem(["❌ ERROR", err])
            item.setForeground(0, QtGui.QColor(255, 120, 120))
            self.report_tree.addTopLevelItem(item)

    def run_export_toggle(self):
        bone_map = self.cfg.load_json("bone_map.json")
        exporter = BoneNamePreparing(bone_map)
        exporter.execute()
        mode = "EXPORT" if exporter.export_toggle else "RIG"
        cmds.inViewMessage(amg=f"FD_FishTool: Режим {mode}", pos='topCenter', fade=True)

    def launch_legacy_exporter(self):
        paths = self.cfg.load_json("paths.json")
        legacy_root = paths.get("legacy_exporter_path", "")
        if not legacy_root or not os.path.exists(legacy_root):
            QtWidgets.QMessageBox.critical(self, "Error", "Путь к экспортеру не найден!")
            return
        if legacy_root not in sys.path: sys.path.append(legacy_root)
        try:
            from playrix.export.main_dialog import MainDialog
            self.legacy_tool = MainDialog()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def refresh_anim_list(self):
        self.anim_tree.clear()
        ref_path = self.cfg.load_json("paths.json").get("animation_data")
        if not ref_path or not os.path.exists(ref_path): return
        manager = AnimSyncManager(ref_path)
        report = manager.compare()
        for d in report:
            item = QtWidgets.QTreeWidgetItem(self.anim_tree)
            item.setText(1, d["name"]); item.setText(2, d["ref_time"]); item.setText(3, d["scene_time"])
            if d["status"] == "OK":
                item.setText(0, "✅ OK"); item.setForeground(0, QtGui.QColor(120, 255, 120))
            elif d["status"] == "MISSING":
                item.setText(0, "❌ MISS"); item.setForeground(0, QtGui.QColor(255, 120, 120))
            else:
                item.setText(0, "➕ EXTRA"); item.setForeground(0, QtGui.QColor(120, 200, 255))

    def on_clip_click(self, item, col):
        time_text = item.text(3) if item.text(3) != "MISSING" else item.text(2)
        if "-" in time_text:
            try:
                start, end = [float(x) for x in time_text.split('-')]
                cmds.playbackOptions(min=start, max=end, ast=start, aet=end)
                cmds.currentTime(start)
            except: pass

    def open_settings(self):
        from FD_FishTool.ui.settings_window import SettingsWindow
        sw = SettingsWindow(self.cfg, parent=self)
        sw.exec_()