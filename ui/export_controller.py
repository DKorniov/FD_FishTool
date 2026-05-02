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
        # ... (код загрузки .ui файла остается прежним)
        
        loader = QtUiTools.QUiLoader()
        ui_path = os.path.join(os.path.dirname(__file__), "export_tab.ui")
        file = QtCore.QFile(ui_path)
        
        if not file.open(QtCore.QFile.ReadOnly):
            cmds.warning(f"FD_FishTool: Не удалось найти файл UI: {ui_path}")
            return
            
        self.ui = loader.load(file, self)
        file.close()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # --- ПОДКЛЮЧЕНИЕ КНОПОК СПРАВКИ ---
        try:
            from FD_FishTool.ui.help_manager import HelpManager
            
            # Подключаем кнопку инфо для валидации
            if hasattr(self.ui, 'btn_info_validate'):
                self.ui.btn_info_validate.clicked.connect(
                    lambda: HelpManager.show_export_help(self)
                )
            
            # Подключаем кнопку инфо для подготовки
            if hasattr(self.ui, 'btn_info_preparation'):
                self.ui.btn_info_preparation.clicked.connect(
                    lambda: HelpManager.show_export_preparation_help(self)
                )
        except ImportError:
            cmds.warning("FD_FishTool: HelpManager не найден, справка экспорта недоступна.")

        # --- ПОДКЛЮЧЕНИЕ ОСТАЛЬНЫХ КНОПОК ---
        if hasattr(self.ui, 'btn_validate'):
            self.ui.btn_validate.clicked.connect(self.run_validation)
            
        if hasattr(self.ui, 'btn_toggle'):
            self.ui.btn_toggle.clicked.connect(self.run_export_toggle)
            
        if hasattr(self.ui, 'btn_legacy'):
            self.ui.btn_legacy.clicked.connect(self.launch_legacy_exporter)

        self.report_tree = getattr(self.ui, 'report_tree', None)
        if self.report_tree:
            self.report_tree.setHeaderLabels(["Результат", "Описание"])

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
        """Запуск валидации с интеллектуальной подсветкой и авто-раскрытием групп."""
        if not self.report_tree:
            return
            
        # 1. Получаем данные из ядра
        errors, success = self.validator.validate_all()
        self.report_tree.clear()
        
        # 2. Загружаем конфигурацию групп
        config_path = os.path.join(self.cfg.data_path if self.cfg else "", "validation_config.json")
        groups_data = []
        default_title = "Прочие проверки"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    v_config = json.load(f)
                    groups_data = v_config.get("groups", [])
                    default_title = v_config.get("default_group", default_title)
            except Exception as e:
                cmds.warning(f"FD_FishTool: Ошибка чтения validation_config.json: {e}")

        group_items = {}
        group_has_errors = {} # Словарь для отслеживания ошибок в каждой группе

        def get_or_create_group(title):
            """Создает заголовок группы и инициализирует статус ошибки."""
            if title not in group_items:
                g_item = QtWidgets.QTreeWidgetItem(self.report_tree, [title, ""])
                group_items[title] = g_item
                group_has_errors[title] = False # По умолчанию считаем, что ошибок нет
            return group_items[title]

        def add_result_to_tree(status_text, message, is_error):
            """Добавляет результат и помечает группу как проблемную, если есть ошибка."""
            target_group_title = default_title
            for g in groups_data:
                if any(kw in message for kw in g.get("keywords", [])):
                    target_group_title = g.get("title", default_title)
                    break
            
            parent = get_or_create_group(target_group_title)
            
            # Если хотя бы один элемент в группе — ошибка, помечаем всю группу
            if is_error:
                group_has_errors[target_group_title] = True
            
            item = QtWidgets.QTreeWidgetItem(parent, [status_text, message])
            color = QtGui.QColor(255, 120, 120) if is_error else QtGui.QColor(120, 255, 120)
            item.setForeground(0, color)

        # 3. Заполняем данные
        # Важно: сначала обрабатываем успехи, потом ошибки (или наоборот), 
        # флаг group_has_errors корректно обновится в любом случае.
        for msg in success:
            add_result_to_tree("✅ PASS", msg, is_error=False)
            
        for err in errors:
            add_result_to_tree("❌ ERROR", err, is_error=True)

        # 4. ФИНАЛЬНАЯ СТИЛИЗАЦИЯ ГРУПП
        for title, g_item in group_items.items():
            has_error = group_has_errors[title]
            
            # Настройка цвета: темно-красный для ошибок, темно-зеленый для успеха
            bg_color = QtGui.QColor(80, 40, 40) if has_error else QtGui.QColor(40, 70, 40)
            
            font = g_item.font(0)
            font.setBold(True)
            
            for col in range(2):
                g_item.setFont(col, font)
                g_item.setBackground(col, bg_color)
                g_item.setForeground(col, QtGui.QColor(240, 240, 240)) # Белый текст для читаемости
            
            # Логика раскрытия: раскрываем только если есть ошибки
            g_item.setExpanded(has_error)

        # Подгоняем колонки
        for col in range(2):
            self.report_tree.resizeColumnToContents(col)

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