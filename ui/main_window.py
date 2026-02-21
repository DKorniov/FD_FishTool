# -*- coding: utf-8 -*-
import os
import sys
import importlib
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
import maya.mel as mel

# Импорты внутренних модулей проекта
from FD_FishTool.core.meta_exporter import BoneNamePreparing
from FD_FishTool.core.validator import FishValidator
from FD_FishTool.core.anim_handler import AnimSyncManager

class FD_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, parent=None):
        """
        Инициализация главного окна.
        :param config: Экземпляр ConfigManager из main_app.py.
        """
        super(FD_MainWindow, self).__init__(parent)
        
        self.cfg = config
        self.validator = FishValidator(self.cfg)
        self.legacy_tool = None
        
        self.setWindowTitle("FD_FishTool v2.0 | Pipeline Master")
        self.setMinimumSize(450, 700)
        
        self.init_ui()
        print("FD_FishTool: UI успешно инициализирован.")

    def init_ui(self):
        """Сборка основного интерфейса."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Главная таб-система
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self.ui_rigging(), "Rigging")
        self.tabs.addTab(self.ui_animation(), "Animation")
        self.tabs.addTab(self.ui_export(), "Export")

        # Кнопка глобальных настроек
        btn_settings = QtWidgets.QPushButton("⚙ Настройки Пайплайна")
        btn_settings.setMinimumHeight(40)
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)

    # --- ВКЛАДКИ ---

    def ui_rigging(self):
        """Инструменты риггинга."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        btn_spring = QtWidgets.QPushButton("🚀 ПРИМЕНИТЬ SPRING MAGIC")
        btn_spring.setMinimumHeight(60)
        btn_spring.setStyleSheet("background-color: #3d5a6b; font-weight: bold; color: white;")
        btn_spring.clicked.connect(self.run_spring_magic)
        layout.addWidget(btn_spring)

        layout.addSpacing(20)
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
        """Синхронизация анимаций с эталоном."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        self.anim_tree = QtWidgets.QTreeWidget()
        self.anim_tree.setHeaderLabels(["Статус", "Клип", "Эталон (инфо)", "В Сцене (инфо)"])
        self.anim_tree.setAlternatingRowColors(True)
        self.anim_tree.itemClicked.connect(self.on_clip_click)
        layout.addWidget(self.anim_tree)

        btn_sync = QtWidgets.QPushButton("🔄 СИНХРОНИЗИРОВАТЬ СПИСОК")
        btn_sync.setMinimumHeight(50)
        btn_sync.clicked.connect(self.refresh_anim_list)
        layout.addWidget(btn_sync)
        return tab

    def ui_export(self):
        """Техническая валидация и экспорт."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Секция валидации
        val_group = QtWidgets.QGroupBox("1. Техническая проверка")
        val_lay = QtWidgets.QVBoxLayout(val_group)
        
        self.btn_validate = QtWidgets.QPushButton("🔍 ПРОВЕРИТЬ СЦЕНУ (OM2)")
        self.btn_validate.setFixedHeight(40)
        self.btn_validate.clicked.connect(self.run_validation)
        val_lay.addWidget(self.btn_validate)
        
        self.report_tree = QtWidgets.QTreeWidget()
        self.report_tree.setHeaderLabels(["Результат", "Описание"])
        self.report_tree.setColumnWidth(0, 120)
        val_lay.addWidget(self.report_tree)
        layout.addWidget(val_group)

        # Секция подготовки
        prep_group = QtWidgets.QGroupBox("2. Подготовка и Экспорт")
        prep_lay = QtWidgets.QVBoxLayout(prep_group)
        
        self.btn_toggle = QtWidgets.QPushButton("🔄 ПЕРЕКЛЮЧИТЬ ИМЕНА (RIG/EXPORT)")
        self.btn_toggle.setMinimumHeight(50)
        self.btn_toggle.setStyleSheet("background-color: #4e7a4e; color: white; font-weight: bold;")
        self.btn_toggle.clicked.connect(self.run_export_toggle)
        prep_lay.addWidget(self.btn_toggle)

        # Кнопка запуска Legacy Exporter
        btn_legacy = QtWidgets.QPushButton("🚀 ЗАПУСТИТЬ PLAYRIX EXPORTER")
        btn_legacy.setMinimumHeight(80)
        btn_legacy.setStyleSheet("background-color: #d4a017; color: black; font-weight: bold; font-size: 13px;")
        btn_legacy.clicked.connect(self.launch_legacy_exporter)
        prep_lay.addWidget(btn_legacy)
        
        layout.addWidget(prep_group)
        layout.addStretch()
        return tab

    # --- ЛОГИКА ---

    def run_validation(self):
        """Запуск FishValidator (проверка костей <80, весов и материалов)."""
        self.report_tree.clear()
        # FishValidator возвращает (errors, success_log)
        errors, success = self.validator.validate_all()
        
        # Вывод успехов (зеленым)
        for msg in success:
            item = QtWidgets.QTreeWidgetItem(["✅ PASS", msg])
            item.setForeground(0, QtGui.QColor(120, 255, 120))
            self.report_tree.addTopLevelItem(item)

        # Вывод ошибок (красным)
        for err in errors:
            item = QtWidgets.QTreeWidgetItem(["❌ ERROR", err])
            item.setForeground(0, QtGui.QColor(255, 120, 120))
            self.report_tree.addTopLevelItem(item)
            
        if errors:
            QtWidgets.QMessageBox.warning(self, "Validation Failed", f"Найдено {len(errors)} проблем!")

    def run_export_toggle(self):
        """Переключение нейминга через BoneNamePreparing."""
        bone_map = self.cfg.load_json("bone_map.json")
        exporter = BoneNamePreparing(bone_map)
        exporter.execute()
        
        mode = "EXPORT" if exporter.export_toggle else "RIG"
        cmds.inViewMessage(amg=f"FD_FishTool: Режим <ud>{mode}</ud>", pos='topCenter', fade=True)

    def launch_legacy_exporter(self):
        """Динамический запуск старого экспортера Playrix."""
        paths = self.cfg.load_json("paths.json")
        legacy_root = paths.get("legacy_exporter_path", "")

        if not legacy_root or not os.path.exists(legacy_root):
            QtWidgets.QMessageBox.critical(self, "Error", "Укажите путь к папке 'scripts' со старым экспортером в настройках!")
            return

        # Добавляем путь в sys.path, если его там нет
        if legacy_root not in sys.path:
            sys.path.append(legacy_root)

        try:
            # Импорт согласно структуре: playrix.export.main_dialog
            from playrix.export.main_dialog import MainDialog
            self.legacy_tool = MainDialog()
            print("FD_FishTool: Legacy Playrix Exporter запущен.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import Error", f"Не удалось запустить скрипт: {str(e)}")

    def refresh_anim_list(self):
        """Обновление списка анимаций через AnimSyncManager."""
        self.anim_tree.clear()
        ref_path = self.cfg.load_json("paths.json").get("animation_data")
        
        if not ref_path or not os.path.exists(ref_path):
            return

        manager = AnimSyncManager(ref_path)
        report = manager.compare()

        for d in report:
            item = QtWidgets.QTreeWidgetItem(self.anim_tree)
            item.setText(1, d["name"])
            item.setText(2, d["ref_time"])
            item.setText(3, d["scene_time"])

            st = d["status"]
            if st == "OK":
                item.setText(0, "✅ OK")
                item.setForeground(0, QtGui.QColor(120, 255, 120))
            elif st == "MISSING":
                item.setText(0, "❌ MISS")
                item.setForeground(0, QtGui.QColor(255, 120, 120))
            else: # EXTRA
                item.setText(0, "➕ EXTRA")
                item.setForeground(0, QtGui.QColor(120, 200, 255))

    def on_clip_click(self, item, col):
        """Установка таймлайна при клике на анимацию."""
        time_text = item.text(3) if item.text(3) != "MISSING" else item.text(2)
        if "-" in time_text:
            try:
                start, end = [float(x) for x in time_text.split('-')]
                cmds.playbackOptions(min=start, max=end, ast=start, aet=end)
                cmds.currentTime(start)
            except: pass

    def run_spring_magic(self):
        if mel.eval('exists "SpringMagic"'):
            mel.eval("SpringMagic;")
        else:
            cmds.warning("SpringMagic не найден.")

    def open_settings(self):
        """Окно настроек."""
        from FD_FishTool.ui.settings_window import SettingsWindow
        sw = SettingsWindow(self.cfg, parent=self)
        sw.exec_()