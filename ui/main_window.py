from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
import maya.mel as mel
import os

from FD_FishTool.core.meta_exporter import BoneNamePreparing
from FD_FishTool.core.anim_handler import AnimSyncManager

class FD_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, parent=None):
        super(FD_MainWindow, self).__init__(parent)
        self.cfg = config
        self.setWindowTitle("FD_FishTool v2.0 | Final Sync")
        self.setMinimumSize(450, 650)
        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # Регистрация всех вкладок
        self.tabs.addTab(self.ui_rigging(), "Rigging")
        self.tabs.addTab(self.ui_animation(), "Animation")
        self.tabs.addTab(self.ui_export(), "Export")

        # Кнопка настроек
        btn_settings = QtWidgets.QPushButton("⚙ Настройки Пайплайна")
        btn_settings.setMinimumHeight(40)
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)

    def ui_rigging(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        btn_spring = QtWidgets.QPushButton("🚀 ПРИМЕНИТЬ SPRING MAGIC")
        btn_spring.setMinimumHeight(60)
        btn_spring.setStyleSheet("background-color: #3d5a6b; font-weight: bold; font-size: 13px;")
        btn_spring.clicked.connect(self.run_spring_magic)
        layout.addWidget(btn_spring)

        layout.addSpacing(25)
        ai_group = QtWidgets.QGroupBox("AI Assistant")
        ai_lay = QtWidgets.QVBoxLayout(ai_group)
        self.ai_input = QtWidgets.QLineEdit()
        self.ai_input.setPlaceholderText("Напр: 'Создай риг для плавников'...")
        ai_lay.addWidget(self.ai_input)
        btn_ai = QtWidgets.QPushButton("✨ АНАЛИЗ И ЗАПУСК")
        btn_ai.clicked.connect(lambda: print(f"AI Brain: Analyzing {self.ai_input.text()}"))
        ai_lay.addWidget(btn_ai)
        layout.addWidget(ai_group)

        layout.addStretch()
        return tab

    def ui_animation(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        self.anim_tree = QtWidgets.QTreeWidget()
        self.anim_tree.setHeaderLabels(["Статус", "Клип", "Эталон (инфо)", "В Сцене (инфо)"])
        self.anim_tree.itemClicked.connect(self.on_clip_click)
        layout.addWidget(self.anim_tree)

        btn_sync = QtWidgets.QPushButton("🔄 СИНХРОНИЗИРОВАТЬ СПИСОК")
        btn_sync.setMinimumHeight(50)
        btn_sync.setStyleSheet("font-weight: bold;")
        btn_sync.clicked.connect(self.refresh_anim_list)
        layout.addWidget(btn_sync)
        return tab

    def ui_export(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        btn = QtWidgets.QPushButton("🔄 ПЕРЕКЛЮЧИТЬ РЕЖИМ ЭКСПОРТА")
        btn.setMinimumHeight(120)
        btn.setStyleSheet("background-color: #4e7a4e; font-size: 16px; font-weight: bold;")
        btn.clicked.connect(self.run_export_toggle)
        layout.addWidget(btn)
        layout.addStretch()
        return tab

    # --- ЛОГИКА ---
    def on_clip_click(self, item, col):
        # Переключение таймлайна для удобства (даже если кадры не важны для проверки)
        time_text = item.text(3) if item.text(3) != "MISSING" else item.text(2)
        if "-" in time_text:
            try:
                start, end = [float(x) for x in time_text.split('-')]
                cmds.playbackOptions(min=start, max=end, animationStartTime=start, animationEndTime=end)
                cmds.currentTime(start)
            except: pass

    def run_spring_magic(self):
        if mel.eval('exists "SpringMagic"'):
            mel.eval("SpringMagic;")
        else:
            cmds.warning("Скрипт SpringMagic не найден в путях Maya.")

    def refresh_anim_list(self):
        self.anim_tree.clear()
        ref_path = self.cfg.load_json("paths.json").get("animation_data")
        if not ref_path or not os.path.exists(ref_path):
            cmds.warning("Укажите верный путь к animation.txt в настройках!")
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

    def run_export_toggle(self):
        bone_map = self.cfg.load_json("bone_map.json")
        BoneNamePreparing(bone_map).execute()

    def open_settings(self):
        from FD_FishTool.ui.settings_window import SettingsWindow
        self.sw = SettingsWindow(self.cfg, parent=self)
        self.sw.exec_()