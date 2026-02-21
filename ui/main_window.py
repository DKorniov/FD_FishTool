# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds

# Импорты модулей core
from FD_FishTool.core.meta_exporter import BoneNamePreparing
from FD_FishTool.core.validator import FishValidator

class FD_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, parent=None):
        """
        Исправлено: теперь принимает 'config', как того требует main_app.py.
        config здесь — это словарь (bone_map.json).
        """
        super(FD_MainWindow, self).__init__(parent)
        
        # Сохраняем словарь конфигурации
        self.cfg = config 
        self.validator = FishValidator()
        
        self.setWindowTitle("FD_FishTool - Pipeline Master")
        self.setMinimumSize(400, 600)
        
        # Основной виджет и таб-система
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        self.tabs = QtWidgets.QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Инициализация вкладок
        self.init_rigging_tab()
        self.init_animation_tab()
        self.init_export_tab()
        
        print("FD_FishTool: UI Loaded successfully.")

    def init_rigging_tab(self):
        self.rig_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.rig_tab, "Rigging")
        layout = QtWidgets.QVBoxLayout(self.rig_tab)
        # Сюда можно вставить старый код кнопок риггинга
        layout.addWidget(QtWidgets.QLabel("Rigging Tools Space"))

    def init_animation_tab(self):
        self.anim_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.anim_tab, "Animation")
        layout = QtWidgets.QVBoxLayout(self.anim_tab)
        # Сюда можно вставить старый код кнопок анимации
        layout.addWidget(QtWidgets.QLabel("Animation Tools Space"))

    def init_export_tab(self):
        """Вкладка экспорта с валидацией и переключением имен"""
        self.export_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.export_tab, "Export")
        layout = QtWidgets.QVBoxLayout(self.export_tab)
        
        # --- Секция Валидации ---
        val_group = QtWidgets.QGroupBox("Technical Validation")
        val_layout = QtWidgets.QVBoxLayout(val_group)
        
        self.btn_validate = QtWidgets.QPushButton("Run Scene Check")
        self.btn_validate.setFixedHeight(40)
        self.btn_validate.clicked.connect(self.run_validation)
        val_layout.addWidget(self.btn_validate)
        
        self.report_tree = QtWidgets.QTreeWidget()
        self.report_tree.setHeaderLabels(["Status", "Description"])
        self.report_tree.setColumnWidth(0, 100)
        val_layout.addWidget(self.report_tree)
        
        layout.addWidget(val_group)
        
        # --- Секция Экспорта ---
        exp_group = QtWidgets.QGroupBox("Finalize & Export")
        exp_layout = QtWidgets.QVBoxLayout(exp_group)
        
        self.btn_toggle = QtWidgets.QPushButton("Toggle Rig / Export Naming")
        self.btn_toggle.setFixedHeight(50)
        self.btn_toggle.setStyleSheet("background-color: #445566; color: white; font-weight: bold;")
        self.btn_toggle.clicked.connect(self.run_export_toggle)
        exp_layout.addWidget(self.btn_toggle)
        
        self.btn_fbx = QtWidgets.QPushButton("Export FBX")
        self.btn_fbx.setFixedHeight(40)
        self.btn_fbx.setEnabled(False) # Активируется после успешной валидации
        exp_layout.addWidget(self.btn_fbx)
        
        layout.addWidget(exp_group)

    # --- МЕТОДЫ ЛОГИКИ ---

    def run_validation(self):
        """Вызов валидатора и обновление TreeWidget"""
        self.report_tree.clear()
        
        # Получаем детализированный отчет
        errors, success = self.validator.validate_all()
        
        # 1. Сначала выводим успехи (Зеленым) для прозрачности процесса
        for msg in success:
            item = QtWidgets.QTreeWidgetItem(["✅ PASS", msg])
            item.setForeground(0, QtGui.QColor(150, 255, 150))
            self.report_tree.addTopLevelItem(item)

        # 2. Выводим ошибки (Красным)
        for err in errors:
            item = QtWidgets.QTreeWidgetItem(["❌ ERROR", err])
            item.setForeground(0, QtGui.QColor(255, 150, 150))
            self.report_tree.addTopLevelItem(item)

        # 3. Управление кнопкой экспорта
        self.btn_fbx.setEnabled(len(errors) == 0)
        
        if errors:
            QtWidgets.QMessageBox.warning(self, "Validation", f"Найдено {len(errors)} критических ошибок!")

    def run_export_toggle(self):
        """Вызов логики переименования"""
        try:
            # Т.к. self.cfg уже является словарем (bone_map), передаем его напрямую
            exporter = BoneNamePreparing(self.cfg)
            exporter.execute()
            
            # Обновляем текст кнопки для наглядности
            mode = "EXPORT" if exporter.export_toggle else "RIG"
            self.btn_toggle.setText(f"Naming Mode: {mode} (Click to Switch)")
            
            cmds.inViewMessage(amg=f"FD_FishTool: Mode switched to <ud>{mode}</ud>", pos='topCenter', fade=True)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Toggle failed: {str(e)}")