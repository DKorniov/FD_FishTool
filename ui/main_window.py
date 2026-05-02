# -*- coding: utf-8 -*-
import os
import sys
import importlib
from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools
import maya.cmds as cmds
import json


# Импорты ядра
from FD_FishTool.core.meta_exporter import BoneNamePreparing
from FD_FishTool.core.validator import FishValidator
from FD_FishTool.core.anim_handler import AnimSyncManager
from FD_FishTool.core.anim_manager import AnimManager
from FD_FishTool.core.physics_manager import PhysicsManager
from FD_FishTool.ui.rig_face_ui import FaceRigTab



# Импорты UI (Абсолютные пути для исключения ModuleNotFoundError)
from FD_FishTool.ui.rig_body_ui import RigBodyWidget
from FD_FishTool.ui.spring_selector import SpringSelectorController

class FD_MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, parent=None):
        super(FD_MainWindow, self).__init__(parent)
        self.cfg = config
        self.validator = FishValidator(self.cfg)
        self.anim_mgr = AnimManager(self.cfg) 
        self.physics_mgr = PhysicsManager(self.cfg)
        
        # Подготовка костей для ренейма
        bone_map = self.cfg.load_json("bone_map.json")
        self.bone_preparer = BoneNamePreparing(bone_map)
        
        self.setWindowTitle("FD_FishTool v2.1 | Rigging Master")
        self.setMinimumSize(500, 850)
        
        self.init_ui()
        
        self.refresh_anim_list()
        self.face_tab = FaceRigTab()
        if hasattr(self.ui, 'tabs'):
            self.ui.tabs.addTab(self.face_tab, "Face Rig")
    
    def init_ui(self):
        # 1. Загружаем визуальный интерфейс из файла .ui
        from PySide2 import QtUiTools
        loader = QtUiTools.QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(__file__), "main_window.ui")
        
        ui_file = QtCore.QFile(ui_file_path)
        ui_file.open(QtCore.QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # 2. Устанавливаем загруженный интерфейс
        self.setCentralWidget(self.ui.centralWidget())

        # 3. Настраиваем вкладки (Tab Widget)
        # Очищаем стандартные вкладки (Tab 1, Tab 2), которые Designer создает по умолчанию
        if hasattr(self.ui, 'tabs'):
            self.ui.tabs.clear()
            # Добавляем наши старые вкладки, написанные на Python
            self.ui.tabs.addTab(self.ui_rigging_tab(), "Rigging")
            self.ui.tabs.addTab(self.ui_animation_tab(), "Animation")
            self.ui.tabs.addTab(self.ui_export_tab(), "Export")

        # 4. Подключаем кнопку настроек
        if hasattr(self.ui, 'btn_settings'):
            self.ui.btn_settings.clicked.connect(self.open_settings)

    '''def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # Подключение вкладок (Animation и Export не тронуты)
        self.tabs.addTab(self.ui_rigging_tab(), "Rigging")
        self.tabs.addTab(self.ui_animation_tab(), "Animation")
        self.tabs.addTab(self.ui_export_tab(), "Export")

        # Настройки снизу
        btn_settings = QtWidgets.QPushButton("⚙ Настройки Пайплайна")
        btn_settings.setMinimumHeight(40)
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)'''

    def ui_rigging_tab(self):
        """Вкладка риггинга: Здесь мы работаем над телом и ИИ."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Виджет логики тела (наш новый модуль)
        self.rig_body_ui = RigBodyWidget(config=self.cfg)
        layout.addWidget(self.rig_body_ui,1)
        
        # AI Rig Assistant
        '''ai_group = QtWidgets.QGroupBox("AI Rig Assistant")
        ai_lay = QtWidgets.QVBoxLayout(ai_group)
        self.ai_input = QtWidgets.QLineEdit()
        self.ai_input.setPlaceholderText("Напр: 'Исправь веса на хвосте'...")
        ai_lay.addWidget(self.ai_input)
        btn_ai = QtWidgets.QPushButton("✨ АНАЛИЗ СЦЕНЫ")
        btn_ai.clicked.connect(lambda: print(f"AI Analysing: {self.ai_input.text()}"))
        ai_lay.addWidget(btn_ai)
        layout.addWidget(ai_group)'''

        #layout.addStretch()
        return tab

    def ui_animation_tab(self):
        """Вкладка анимации: Полная интеграция Studio Library, Physics Pipeline и AnimAssist."""
        # Путь к файлу .ui
        ui_path = os.path.join(os.path.dirname(__file__), "anim_tab.ui")
        
        # Динамическая загрузка интерфейса
        loader = QtUiTools.QUiLoader()
        file = QtCore.QFile(ui_path)
        
        if not file.open(QtCore.QFile.ReadOnly):
            cmds.warning(f"FD_FishTool: Не удалось найти или открыть файл UI: {ui_path}")
            return QtWidgets.QWidget()
            
        tab = loader.load(file, self)
        file.close()

        # --- 1. STUDIO LIBRARY PRESETS ---
        # Подключение кнопок выделения сетов (новые функции)
        tab.btn_select_body.clicked.connect(lambda: self.anim_mgr.select_studio_set("body"))
        tab.btn_select_face.clicked.connect(lambda: self.anim_mgr.select_studio_set("face"))
        
        # Подключение кнопок наложения анимации
        tab.btn_apply_body.clicked.connect(lambda: self.anim_mgr.apply_studio_anim("body_standart_anim.anim"))
        tab.btn_apply_face.clicked.connect(lambda: self.anim_mgr.apply_studio_anim("face_standart_anim.anim"))
        
        # Глобальная очистка всей анимации в сцене (включая сброс в Bind Pose)
        tab.btn_clear_all_animation.clicked.connect(self.on_delete_all_animation_clicked)
        
        # Подключение централизованной справки
        try:
            from FD_FishTool.ui.help_manager import HelpManager
            # Подключаем все кнопки справки здесь
            tab.btn_info_stuidio_anims.clicked.connect(lambda: HelpManager.show_studio_library_help(self))
            tab.btn_info_spring_selector.clicked.connect(lambda: HelpManager.show_physics_help(self))
        except ImportError:
            cmds.warning("FD_FishTool: Модуль help_manager не найден. Справка будет недоступна.")

        # --- 2. PHYSICS PIPELINE (SpringMagic) ---
        try:
            from FD_FishTool.ui.spring_selector import SpringSelectorController
            # Инициализируем контроллер для управления динамическими цепочками
            self.spring_controller = SpringSelectorController(tab, self.physics_mgr, parent=self)
        except ImportError:
            cmds.warning("FD_FishTool: Модуль spring_selector не найден.")
        
        # Начальное состояние панели (скрыта, завязано на сигнал toggled в UI)
        tab.frame_spring_magic.setVisible(False)
        tab.btn_spring_magic.setChecked(False)

        # Логика смены визуального стиля кнопки при раскрытии фрейма
        def on_spring_btn_toggled(checked):
            if checked:
                tab.btn_spring_magic.setStyleSheet("background-color: #5b7a8b; color: white; font-weight: bold;")
            else:
                tab.btn_spring_magic.setStyleSheet("background-color: #3d5a6b; color: white; font-weight: bold;")
                
        tab.btn_spring_magic.toggled.connect(on_spring_btn_toggled)

        # --- 3. ANIMATION LIST (AnimAssist & Tree) ---
        # Сохраняем ссылку на дерево для корректной работы метода refresh_anim_list
        self.anim_tree = tab.tree_anim_list
        self.anim_tree.itemClicked.connect(self.on_clip_click)

        # Подключение кнопок AnimAssist Management (загрузка эталона в ноду)
        try:
            from FD_FishTool.core import anim_handler
            tab.btn_load_anim_list.clicked.connect(anim_handler.AnimationHandler.load_etalon_animations)
        except Exception as e:
            print(f"FD_FishTool Warning: Could not connect AnimAssist button: {e}")

        # Кнопки управления списком и синхронизация
        tab.btn_sync_list.clicked.connect(self.refresh_anim_list)
        
        # Сохраняем ссылки на кнопки для управления их доступностью (Enabled/Disabled)
        self.btn_load_missing = tab.btn_load_missing
        self.btn_clear_list = tab.btn_clear_list
        
        self.btn_load_missing.clicked.connect(self.on_load_missing_clicked)
        self.btn_clear_list.clicked.connect(self.on_clear_list_clicked)

       
        

        return tab

    def ui_export_tab(self):
        """Вкладка экспорта: Полный возврат к v2.0."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Секция валидации
        val_group = QtWidgets.QGroupBox("Техническая проверка")
        val_lay = QtWidgets.QVBoxLayout(val_group)
        btn_validate = QtWidgets.QPushButton("🔍 ПРОВЕРИТЬ СЦЕНУ")
        btn_validate.setFixedHeight(40)
        btn_validate.clicked.connect(self.run_validation)
        val_lay.addWidget(btn_validate)
        
        self.report_tree = QtWidgets.QTreeWidget()
        self.report_tree.setHeaderLabels(["Результат", "Описание"])
        val_lay.addWidget(self.report_tree)
        layout.addWidget(val_group)

        # Секция подготовки и экспорта
        prep_group = QtWidgets.QGroupBox("Подготовка")
        prep_lay = QtWidgets.QVBoxLayout(prep_group)
        btn_toggle = QtWidgets.QPushButton("🔄 RIG/EXPORT TOGGLE")
        btn_toggle.setMinimumHeight(50)
        btn_toggle.setStyleSheet("background-color: #4e7a4e; color: white; font-weight: bold;")
        btn_toggle.clicked.connect(self.run_export_toggle)
        prep_lay.addWidget(btn_toggle)

        btn_legacy = QtWidgets.QPushButton("🚀 PLAYRIX EXPORTER")
        btn_legacy.setMinimumHeight(80)
        btn_legacy.setStyleSheet("background-color: #d4a017; color: black; font-weight: bold;")
        btn_legacy.clicked.connect(self.launch_legacy_exporter)
        prep_lay.addWidget(btn_legacy)
        
        layout.addWidget(prep_group)
        return tab

    

    def run_validation(self):
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
        """Исправленный метод запуска Playrix Exporter."""
        path = self.cfg.load_json("paths.json").get("legacy_exporter_path", "")
        if path and path not in sys.path:
            sys.path.append(path)
        
        try:
            import playrix.export.main_dialog as lex
            importlib.reload(lex)
            
            # Проверка способа запуска: функция show() или класс MainDialog()
            if hasattr(lex, 'show'):
                lex.show()
            elif hasattr(lex, 'MainDialog'):
                # Сохраняем ссылку на экземпляр, чтобы окно не закрылось сразу
                self.exporter_instance = lex.MainDialog()
                self.exporter_instance.show()
            else:
                cmds.warning("FD_FishTool: Не найден метод запуска в playrix.export.main_dialog")
        except Exception as e:
            cmds.warning(f"Ошибка при открытии экспортера: {e}")

    def refresh_anim_list(self):
        """Загрузка списка: статусы из .txt, структура из .json."""
        self.anim_tree.clear()
        ref_path = self.cfg.load_json("paths.json").get("animation_data")
        if not ref_path: return
        
        # Получаем "плоские" данные и статусы через txt
        manager = AnimSyncManager(ref_path)
        report = manager.compare()
        
        # Словарь для быстрого поиска: каноничное имя -> данные
        report_map = {}
        for d in report:
            canon = manager.get_canonical_name(d["name"])
            report_map[canon] = d
            
        # Путь к JSON-файлу (ищем в той же папке, что и animation.txt)
        data_dir = os.path.dirname(ref_path)
        etalon_json_path = os.path.join(data_dir, "anim_etalon.json")
        


        processed_canons = set()
        
        # Сохраняем список недостающих для кнопки
        self.missing_animations = [d for d in report if d["status"] == "MISSING"]
        
        # Логика доступности кнопок
        has_missing = len(self.missing_animations) > 0
        has_any_in_scene = any(d["status"] in ["OK", "EXTRA"] for d in report)
        
        self.btn_load_missing.setEnabled(has_missing)
        self.btn_clear_list.setEnabled(has_any_in_scene)


        try:
            with open(etalon_json_path, 'r', encoding='utf-8') as f:
                etalon_data = json.load(f)
                
            for group_dict in etalon_data.get("clips", []):
                for group_name, clips in group_dict.items():
                    # Создаем папку (группу)
                    g_item = QtWidgets.QTreeWidgetItem(self.anim_tree)
                    g_item.setText(0, group_name.upper())
                    
                    # Стилизация заголовка группы
                    font = g_item.font(0)
                    font.setBold(True)
                    for col in range(4):
                        g_item.setFont(col, font)
                        g_item.setBackground(col, QtGui.QColor(70, 70, 70))
                    g_item.setExpanded(True)
                    
                    # Добавляем клипы в группу
                    for clip in clips:
                        canon = manager.get_canonical_name(clip.get("name", ""))
                        if canon in report_map:
                            d = report_map[canon]
                            self._add_anim_item(g_item, d)
                            processed_canons.add(canon)
        except Exception as e:
            cmds.warning(f"FD_FishTool: Не удалось прочитать anim_etalon.json, вывод плоским списком. Ошибка: {e}")
            # Fallback к плоскому списку, если JSON не найден или сломан
            for d in report:
                self._add_anim_item(self.anim_tree, d)
            return

        # Добавляем все, что есть в сцене/txt, но не попало в JSON (Extra или новые)
        extra_canons = set(report_map.keys()) - processed_canons
        if extra_canons:
            e_group = QtWidgets.QTreeWidgetItem(self.anim_tree)
            e_group.setText(0, "ВНЕ КАТЕГОРИЙ / EXTRA")
            font = e_group.font(0)
            font.setBold(True)
            for col in range(4):
                e_group.setFont(col, font)
                e_group.setBackground(col, QtGui.QColor(80, 40, 40))
            e_group.setExpanded(True)
            
            for canon in sorted(list(extra_canons)):
                self._add_anim_item(e_group, report_map[canon])

    def _add_anim_item(self, parent, data):
        """Вспомогательный метод добавления клипа в UI"""
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setText(1, data["name"])
        item.setText(2, data["ref_time"])
        item.setText(3, data["scene_time"])
        
        if data["status"] == "OK":
            item.setText(0, "✅ OK")
            item.setForeground(0, QtGui.QColor(120, 255, 120))
        elif data["status"] == "MISSING":
            item.setText(0, "❌ MISS")
            item.setForeground(0, QtGui.QColor(255, 120, 120))
        else:
            item.setText(0, "➕ EXTRA")
            item.setForeground(0, QtGui.QColor(120, 200, 255))

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

    def on_clear_list_clicked(self):
        res = cmds.confirmDialog(
            title='FD_FishTool',
            message='Вы уверены, что хотите полностью очистить список анимаций в сцене?',
            button=['Да', 'Нет'], defaultButton='Да', cancelButton='Нет', dismissString='Нет'
        )
        if res == 'Да':
            from FD_FishTool.core.anim_handler import AnimationHandler
            AnimationHandler.clear_animations()
            self.refresh_anim_list()

    def on_load_missing_clicked(self):
        if hasattr(self, 'missing_animations') and self.missing_animations:
            from FD_FishTool.core.anim_handler import AnimationHandler
            AnimationHandler.load_missing_clips(self.missing_animations)
            self.refresh_anim_list()
    
    def on_delete_all_animation_clicked(self):
        """Обработчик удаления всей анимации из сцены с защитой от случайного нажатия."""
        res = cmds.confirmDialog(
            title='ВНИМАНИЕ | FD_FishTool',
            message='Вы уверены, что хотите полностью УДАЛИТЬ ВСЮ анимацию со всех объектов в сцене?\n\nЭто действие затронет все контролы.',
            button=['Да, удалить', 'Отмена'], 
            defaultButton='Отмена', 
            cancelButton='Отмена', 
            dismissString='Отмена'
        )
        if res == 'Да, удалить':
            # Оборачиваем удаление в Undo Chunk, чтобы можно было отменить по Ctrl+Z
            cmds.undoInfo(openChunk=True, chunkName="FD_DeleteAllAnimation")
            try:
                from FD_FishTool.core.anim_handler import AnimationHandler
                AnimationHandler.delete_all_scene_animation()
                cmds.inViewMessage(amg="<hl>Вся анимация удалена со сцены</hl>", pos="midCenter", fade=True)
            except Exception as e:
                cmds.warning(f"FD_FishTool: Ошибка при удалении анимации: {e}")
            finally:
                cmds.undoInfo(closeChunk=True)