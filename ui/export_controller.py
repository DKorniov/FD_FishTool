# -*- coding: utf-8 -*-
import os
import sys
import importlib
import json
from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools
import maya.cmds as cmds

class ExportController(QtWidgets.QWidget):
    def __init__(self, main_window, validator, bone_preparer, config, parent=None):
        super(ExportController, self).__init__(parent)
        self.main_window = main_window
        self.validator = validator
        self.bone_preparer = bone_preparer
        self.cfg = config
        
        self.init_ui()

    def init_ui(self):
        # 1. Динамическая загрузка интерфейса из .ui
        loader = QtUiTools.QUiLoader()
        ui_path = os.path.join(os.path.dirname(__file__), "export_tab.ui")
        file = QtCore.QFile(ui_path)
        
        if not file.open(QtCore.QFile.ReadOnly):
            cmds.warning(f"FD_FishTool: Не удалось найти или открыть файл UI: {ui_path}")
            return
            
        self.ui = loader.load(file, self)
        file.close()

        # Размещаем загруженный UI в текущем виджете
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # 2. Инициализация TreeWidget для отчетов
        self.report_tree = getattr(self.ui, 'report_tree', None)
        if self.report_tree:
            self.report_tree.setHeaderLabels(["Результат", "Описание"])

        # 3. Подключение базовых кнопок (если они есть в статичном UI)
        if hasattr(self.ui, 'btn_validate'):
            self.ui.btn_validate.clicked.connect(self.run_validation)
            
        if hasattr(self.ui, 'btn_toggle'):
            self.ui.btn_toggle.clicked.connect(self.run_export_toggle)
            
        if hasattr(self.ui, 'btn_legacy'):
            self.ui.btn_legacy.clicked.connect(self.launch_legacy_exporter)

        # 4. Построение динамических блоков из export_config.json
        self.build_dynamic_ui()

    def build_dynamic_ui(self):
        """Парсинг export_config.json для создания кастомных блоков интерфейса (чекбоксы/доп. настройки)."""
        config_path = os.path.join(self.cfg.data_path if self.cfg else "", "export_config.json")
        if not os.path.exists(config_path):
            return # Если конфига нет, работаем с базовым статичным UI

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                export_data = json.load(f)

            # Если в UI предусмотрен лэйаут для динамических элементов (например, dynamic_layout)
            dyn_layout = getattr(self.ui, 'dynamic_layout', None)
            if not dyn_layout:
                return

            # Генерируем элементы из конфига
            for block in export_data.get("blocks", []):
                group = QtWidgets.QGroupBox(block.get("title", "Настройки"))
                g_layout = QtWidgets.QVBoxLayout(group)
                
                for opt in block.get("options", []):
                    if opt["type"] == "checkbox":
                        cb = QtWidgets.QCheckBox(opt["label"])
                        cb.setChecked(opt.get("default", True))
                        # Присваиваем objectName для последующего доступа к состоянию
                        cb.setObjectName(opt["id"]) 
                        g_layout.addWidget(cb)
                        
                dyn_layout.addWidget(group)

        except Exception as e:
            cmds.warning(f"FD_FishTool: Ошибка при парсинге export_config.json: {e}")

    # --- ЛОГИКА ЭКСПОРТА И ВАЛИДАЦИИ ---

    def run_validation(self):
        if not self.report_tree:
            return
            
        errors, success = self.validator.validate_all()
        self.report_tree.clear()
        
        for msg in success:
            item = QtWidgets.QTreeWidgetItem(["✅ PASS", msg])
            item.setForeground(0, QtGui.QColor(120, 255, 120))
            self.report_tree.addTopLevelItem(item)
            
        for err in errors:
            item = QtWidgets.QTreeWidgetItem(["❌ ERROR", err])
            item.setForeground(0, QtGui.QColor(255, 120, 120))
            self.report_tree.addTopLevelItem(item)

    def run_export_toggle(self):
        self.bone_preparer.execute()

    def launch_legacy_exporter(self):
        """Запуск внешнего инструмента экспорта."""
        path = self.cfg.load_json("paths.json").get("legacy_exporter_path", "")
        if path and path not in sys.path:
            sys.path.append(path)
        
        try:
            import playrix.export.main_dialog as lex
            importlib.reload(lex)
            
            if hasattr(lex, 'show'):
                lex.show()
            elif hasattr(lex, 'MainDialog'):
                # Сохраняем инстанс в главном окне, чтобы сборщик мусора не закрыл его
                self.main_window.exporter_instance = lex.MainDialog()
                self.main_window.exporter_instance.show()
            else:
                cmds.warning("FD_FishTool: Не найден метод запуска в playrix.export.main_dialog")
        except Exception as e:
            cmds.warning(f"Ошибка при открытии экспортера: {e}")