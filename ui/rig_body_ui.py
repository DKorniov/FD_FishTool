# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds

from FD_FishTool.core.rig_body import BodyRigManager
from FD_FishTool.ui.weight_blender_ui import WeightBlenderWidget
from FD_FishTool.ui.easy_ease_ui import EasyEaseWidget

class MaterialPlacementDialog(QtWidgets.QDialog):
    """Диалоговое окно для последовательного назначения материалов."""
    def __init__(self, steps, callback, parent=None):
        super(MaterialPlacementDialog, self).__init__(parent)
        self.setWindowTitle("Назначение материалов")
        self.setMinimumSize(300, 160)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setModal(False)
        
        self.steps = steps
        self.callback = callback
        self.results = []
        self.step_idx = 0
        
        layout = QtWidgets.QVBoxLayout(self)
        self.lbl = QtWidgets.QLabel(f"<b>Шаг {self.step_idx + 1}/{len(self.steps)}:</b><br><br>{self.steps[0]}")
        self.lbl.setWordWrap(True)
        self.lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.lbl)
        
        self.btn_confirm = QtWidgets.QPushButton("Назначить выделенному (Далее)")
        self.btn_confirm.setFixedHeight(40)
        self.btn_confirm.setStyleSheet("background-color: #2e86c1; color: white; font-weight: bold;")
        self.btn_confirm.clicked.connect(self._confirm)
        layout.addWidget(self.btn_confirm)
        
        self.btn_skip = QtWidgets.QPushButton("Пропустить этот материал")
        self.btn_skip.clicked.connect(self._skip)
        layout.addWidget(self.btn_skip)

        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.close)
        layout.addWidget(self.btn_cancel)

    def _confirm(self):
        # Сохраняем текущее выделение (полигоны или объекты)
        sel = cmds.ls(sl=True, flatten=True)
        if not sel:
            cmds.warning("FD_FishTool: Ничего не выделено! Выделите полигоны или нажмите 'Пропустить'.")
            return
        self.results.append(sel)
        self._next_step()

    def _skip(self):
        self.results.append([])
        self._next_step()
        
    def _next_step(self):
        self.step_idx += 1
        cmds.select(clear=True) # Сбрасываем выделение для следующего шага
        if self.step_idx < len(self.steps):
            self.lbl.setText(f"<b>Шаг {self.step_idx + 1}/{len(self.steps)}:</b><br><br>{self.steps[self.step_idx]}")
        else:
            self.callback(self.results)
            self.close()



class AddBoneDialog(QtWidgets.QDialog):
    """Диалоговое окно для добавления кости в список UI (Аналог addBoneUI из оригинала)."""
    def __init__(self, bone_list, parent=None):
        super(AddBoneDialog, self).__init__(parent)
        self.setWindowTitle("Add Bone")
        self.resize(250, 300)
        self.all_bones = bone_list
        self.selected_bone = None

        layout = QtWidgets.QVBoxLayout(self)

        # Поле фильтра
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("Filter:"))
        self.filter_le = QtWidgets.QLineEdit()
        self.filter_le.textChanged.connect(self._filter_list)
        filter_layout.addWidget(self.filter_le)
        layout.addLayout(filter_layout)

        # Список костей
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(self.all_bones)
        self.list_widget.itemDoubleClicked.connect(self.accept) # Двойной клик заменяет ОК
        layout.addWidget(self.list_widget)

        # Кнопки
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("OK")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _filter_list(self, text):
        """Фильтрует список костей по ключевым словам (разделенным пробелом)."""
        self.list_widget.clear()
        if not text:
            self.list_widget.addItems(self.all_bones)
        else:
            words = text.lower().split()
            filtered = [b for b in self.all_bones if all(w in b.lower() for w in words)]
            self.list_widget.addItems(filtered)

    def accept(self):
        if self.list_widget.currentItem():
            self.selected_bone = self.list_widget.currentItem().text()
            super(AddBoneDialog, self).accept()

class RigBodyWidget(QtWidgets.QWidget):
    def __init__(self, config=None, parent=None):
        super(RigBodyWidget, self).__init__(parent)
        self.manager = BodyRigManager(config)
        self.setup_ui()
        self.refresh_mesh_list()

    def setup_ui(self):
        # 1. Загрузка интерфейса
        from PySide2 import QtUiTools, QtGui
        import os
        
        loader = QtUiTools.QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(__file__), "rig_body.ui")
        
        ui_file = QtCore.QFile(ui_file_path)
        ui_file.open(QtCore.QFile.ReadOnly)
        self.ui = loader.load(ui_file)
        ui_file.close()

        # 2. Установка в главный Layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui, stretch=1)

        # 3. Базовые контролы выбора меша
        if hasattr(self.ui, 'btn_get_mesh'):
            self.ui.btn_get_mesh.clicked.connect(self._get_mesh_from_sel)
        if hasattr(self.ui, 'mesh_combo'):
            self.mesh_combo = self.ui.mesh_combo

        # 4. СВОРАЧИВАЕМ ГАРМОШКУ (Accordion) И ДОБАВЛЯЕМ ИКОНКИ
        accordions = [
            ('btn_model_prepare', 'frame_model_prepare'),
            ('btn_bones_controls', 'frame_bones_controls'),
            ('btn_skinning', 'frame_skinning'),
            ('btn_stage_skin', 'frame_stage_skin'),
            ('btn_skin_animation', 'frame_skin_animation'),
            ('pushButton_16', 'frame_skinmagic'),
            ('btn_reskin', 'frame_reskin'),
            ('btn_texturing', 'frame_texturing'),
            ('btn_weigt_data', 'frame')
        ]
        
        # Загружаем иконки по безопасным абсолютным путям
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_right_path = os.path.normpath(os.path.join(current_dir, "..", "icons", "arrow_right.png"))
        icon_down_path = os.path.normpath(os.path.join(current_dir, "..", "icons", "arrow_down.png"))

        # Создаем "Умную" иконку: она сама меняет картинку в зависимости от состояния кнопки (Отжата/Нажата)
        accordion_icon = QtGui.QIcon()
        if os.path.exists(icon_right_path) and os.path.exists(icon_down_path):
            accordion_icon.addPixmap(QtGui.QPixmap(icon_right_path), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            accordion_icon.addPixmap(QtGui.QPixmap(icon_down_path), QtGui.QIcon.Normal, QtGui.QIcon.On)

        for btn_name, frame_name in accordions:
            if hasattr(self.ui, btn_name):
                btn = getattr(self.ui, btn_name)
                btn.setChecked(False)
                
                # Если иконки найдены, применяем их
                if not accordion_icon.isNull():
                    btn.setIcon(accordion_icon)
            
            # Принудительно скрываем сам фрейм при запуске
            if hasattr(self.ui, frame_name):
                getattr(self.ui, frame_name).setVisible(False)

        # 5. ПОДКЛЮЧАЕМ ВСЕ КНОПКИ
        self._connect_rig_manager()
        self._connect_skinmagic()

        # Запускаем слушатель выделения для списков весов
        self._setup_weight_ui_events()
           

    def refresh_mesh_list(self):
        if hasattr(self, 'mesh_combo'):
            self.mesh_combo.clear()
            self.mesh_combo.addItems(self.manager.get_all_meshes_in_scene())
            d = self.manager.find_default_mesh()
            if d: self.mesh_combo.setCurrentText(d)

    
    # БЛОК 1: ПОДКЛЮЧЕНИЕ ПАЙПЛАЙНА (RIG MANAGER)
    # =========================================================================
    def _connect_rig_manager(self):
        """Подключает кнопки подготовки модели, костей, стадий скиннинга и анимаций к BodyRigManager."""
        
        # --- Блок: Model Prepare ---
        if hasattr(self.ui, 'btn_import_sizecheck_mesh'): # Бывшая pushButton_9 ("let the clownFish out")
            self.ui.btn_import_sizecheck_mesh.clicked.connect(
                lambda *args: self.manager.import_sizecheck_mesh()
            )
            
        if hasattr(self.ui, 'btn_clean_model_all'): # Бывшая pushButton_4 ("clean all")
            self.ui.btn_clean_model_all.clicked.connect(
                lambda *args: self.manager.snap_pivot_to_zero_and_freeze()
            )
            
        if hasattr(self.ui, 'btn_check_model_all'): # Бывшая pushButton ("check all")
            self.ui.btn_check_model_all.clicked.connect(
                lambda *args: self.manager.check_model_symmetry(self.mesh_combo.currentText())
            )
            
        
        # --- Блок: Bones Controls ---
        if hasattr(self.ui, 'btn_advansedSceleton'): # Бывшая pushButton_5 ("open AS5")
            self.ui.btn_advansedSceleton.clicked.connect(
                lambda *args: self.manager.launch_advanced_skeleton()
            )
            
        if hasattr(self.ui, 'btn_bone_color'): # Бывшая pushButton_6 ("change bones color")
            self.ui.btn_bone_color.clicked.connect(self._change_bones_color)
            
        if hasattr(self.ui, 'btn_metaBones_Outliner_color'): # Бывшая pushButton_7 ("MEtabones Outliner")
            self.ui.btn_metaBones_Outliner_color.clicked.connect(
                lambda *args: self.manager.colorize_meta_bones_in_outliner()
            )
        if hasattr(self.ui, 'btn_default_bones_color'): # Сброс цвета костей
            self.ui.btn_default_bones_color.clicked.connect(
                lambda *args: self.manager.reset_bones_color(
                    all_bones=self.ui.for_all_bones_checkBox.isChecked() if hasattr(self.ui, 'for_all_bones_checkBox') else False
                )
            )
        if hasattr(self.ui, 'btn_texture_load'): 
            self.ui.btn_texture_load.clicked.connect(self._run_texture_load_logic)

        # --- Блок: Staged Skinning ---
        # Stage 1: Body
        if hasattr(self.ui, 'btn_stage1_select'): 
            self.ui.btn_stage1_select.clicked.connect(lambda *args: self.manager.select_stage_bones(1))
        if hasattr(self.ui, 'btn_stage1_add'):
            self.ui.btn_stage1_add.clicked.connect(
                lambda *args: self.manager.add_to_skin_logic(1, self.mesh_combo.currentText())
            )
            
        # Stage 2: Side Fins
        if hasattr(self.ui, 'btn_stage2_select'):
            self.ui.btn_stage2_select.clicked.connect(lambda *args: self.manager.select_stage_bones(2))
        if hasattr(self.ui, 'btn_stage2_add'):
            self.ui.btn_stage2_add.clicked.connect(
                lambda *args: self.manager.add_to_skin_logic(2, self.mesh_combo.currentText())
            )
            
        # Stage 3: Vert Fins
        if hasattr(self.ui, 'btn_stage3_select'):
            self.ui.btn_stage3_select.clicked.connect(lambda *args: self.manager.select_stage_bones(3))
        if hasattr(self.ui, 'btn_stage3_add'):
            self.ui.btn_stage3_add.clicked.connect(
                lambda *args: self.manager.add_to_skin_logic(3, self.mesh_combo.currentText())
            )
        
        # ОБНОВЛЕННЫЕ КОННЕКТЫ СПРАВКИ
        from FD_FishTool.ui.help_manager import HelpManager
        if hasattr(self.ui, 'btn_info_stage_skin'):
            self.ui.btn_info_stage_skin.clicked.connect(lambda: HelpManager.show_stage_skin_help(self))
        if hasattr(self.ui, 'btn_info_skin_animation'):
            self.ui.btn_info_skin_animation.clicked.connect(lambda: HelpManager.show_skin_anim_help(self))
        if hasattr(self.ui, 'btn_info_btn_adaptive_gradient'):
            self.ui.btn_info_btn_adaptive_gradient.clicked.connect(lambda: HelpManager.show_gradient_weight_help(self))

        

        # --- Блок: Adaptive Gradient ---
        if hasattr(self.ui, 'btn_Apply_adaptive_gradient'):
            self.ui.btn_Apply_adaptive_gradient.clicked.connect(
                lambda *args: self.manager.apply_topological_gradient(self.mesh_combo.currentText())
            )        

        # --- Блок: Test Animations ---
        if hasattr(self.ui, 'btn_body_test_anim'): # Бывшая pushButton_2
            self.ui.btn_body_test_anim.clicked.connect(
                lambda *args: self.manager.apply_test_animation("body_test_anim")
            )
            
        if hasattr(self.ui, 'btn_meta_test_anim'): # Бывшая pushButton_3
            self.ui.btn_meta_test_anim.clicked.connect(
                lambda *args: self.manager.apply_test_animation("META_test_anim")
            )
            
        if hasattr(self.ui, 'btn_delete_all_anim'): # Новая кнопка
            self.ui.btn_delete_all_anim.clicked.connect(
                lambda *args: self.manager.delete_all_test_animation()
            )
        
       

    def _get_mesh_from_sel(self, *args):
        """Берет выделенный во вьюпорте меш и делает его активным в ComboBox."""
        sel = cmds.ls(sl=True, type='transform')
        if sel and cmds.listRelatives(sel[0], s=True, type='mesh'):
            if self.mesh_combo.findText(sel[0]) == -1: 
                self.mesh_combo.addItem(sel[0])
            self.mesh_combo.setCurrentIndex(self.mesh_combo.findText(sel[0]))
        else:
            cmds.warning("FD_FishTool: Пожалуйста, выделите mesh (геометрию) в сцене.")

    def _run_model_check(self, *args):
        """Читает чекбоксы подготовки модели и передает в менеджер."""
        clean_hist = self.ui.checkBox.isChecked() if hasattr(self.ui, 'checkBox') else False
        freeze = self.ui.checkBox_2.isChecked() if hasattr(self.ui, 'checkBox_2') else False
        break_vtx = self.ui.checkBox_3.isChecked() if hasattr(self.ui, 'checkBox_3') else False
        symmetry = self.ui.checkBox_4.isChecked() if hasattr(self.ui, 'checkBox_4') else False
        print(f"FD_FishTool: Check Model -> Clean:{clean_hist}, Freeze:{freeze}, Vtx:{break_vtx}, Sym:{symmetry}")
    
    def _on_add_bone_clicked(self):
        """Открывает окно со списком всех костей меша и добавляет выбранную кость в UI-список."""
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        influences = SkinMagicCore.get_all_skin_influences()
        
        if not influences:
            cmds.warning("FD_FishTool: Сначала выделите вертексы на заскиненном меше!")
            return

        # Открываем наше диалоговое окно
        dialog = AddBoneDialog(influences, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted and dialog.selected_bone:
            bone = dialog.selected_bone
            
            # Проверяем, нет ли уже этой кости в списке
            existing_bones = [self.ui.bone_listBox.item(i).text() for i in range(self.ui.bone_listBox.count())]
            if bone not in existing_bones:
                self.ui.bone_listBox.addItem(bone)
                self.ui.value_listBox.addItem("0.0")
                
                # Выделяем только что добавленную кость
                last_index = self.ui.bone_listBox.count() - 1
                self.ui.bone_listBox.setCurrentRow(last_index)

    def _on_remove_bone_clicked(self):
        """Убирает кость из UI-списка (только если её вес равен 0.0). Ничего не удаляет из Maya."""
        if not hasattr(self.ui, 'bone_listBox') or not self.ui.bone_listBox.currentItem():
            return
            
        row = self.ui.bone_listBox.currentRow()
        weight_item = self.ui.value_listBox.item(row)
        
        # Защита: нельзя убрать кость из списка, если её вес > 0
        if weight_item and float(weight_item.text()) > 0.001:
            cmds.warning("FD_FishTool: Нельзя убрать кость из списка, так как на ней есть вес!")
            return
            
        # Удаляем из обоих списков (по индексу)
        self.ui.bone_listBox.takeItem(row)
        self.ui.value_listBox.takeItem(row)

    # =========================================================================
    # БЛОК 2: ПОДКЛЮЧЕНИЕ SKIN MAGIC CORE
    # =========================================================================
    def _connect_skinmagic(self):
        """Связывает кнопки Qt Designer с чистым ядром скиннинга SkinMagicCore."""
        try:
            from FD_FishTool.core.skin_magic_core import SkinMagicCore
        except ImportError:
            cmds.warning("FD_FishTool: Модуль core/skin_magic_core.py не найден!")
            return

        # 1. УТИЛИТЫ ВЫДЕЛЕНИЯ И COPY (Не меняют веса в сцене, обновление не нужно)
        simple_connections = {
            'grow_button': SkinMagicCore.grow_selection,
            'shrink_button': SkinMagicCore.shrink_selection,
            'ring_button': SkinMagicCore.ring_selection,
            'element_button': SkinMagicCore.element_selection,
            'wave_button': SkinMagicCore.wave_selection,
            'copyWeight_button': SkinMagicCore.copy_weight,
            'import_button': SkinMagicCore.import_vtx_weight,
            'export_button': SkinMagicCore.export_vtx_weight,         
            
            'weightBone_button': SkinMagicCore.select_weighted_bone,
            'InfVerts_button': SkinMagicCore.select_weighted_verts
        }
        for btn_name, func in simple_connections.items():
            if hasattr(self.ui, btn_name):
                getattr(self.ui, btn_name).clicked.connect(func)

        # 1.5. БАЗОВЫЕ МОДИФИКАЦИИ ВЕСОВ (Меняют веса, ТРЕБУЮТ ОБНОВЛЕНИЯ UI)
        refreshing_connections = {
            'pasteWeight_button': SkinMagicCore.paste_weight,
            'relax_button': SkinMagicCore.relax_weight,
            'rangeExt_button': SkinMagicCore.range_extend,
            'rangeShr_button': SkinMagicCore.range_shrink,
        }
        for btn_name, func in refreshing_connections.items():
            if hasattr(self.ui, btn_name):
                # Лямбда с f=func нужна, чтобы привязать правильную функцию к кнопке в цикле
                getattr(self.ui, btn_name).clicked.connect(
                    lambda checked=False, f=func: self._execute_and_refresh(f)
                )

        # 2. КНОПКИ УСТАНОВКИ ВЕСОВ (АБСОЛЮТНЫЕ ЗНАЧЕНИЯ)
        weight_buttons = {
            'w0_button': 0.0, 'w01_button': 0.1, 'w025_button': 0.25,
            'w05_button': 0.5, 'w075_button': 0.75, 'w09_button': 0.9, 'w1_button': 1.0
        }
        for btn_name, val in weight_buttons.items():
            if hasattr(self.ui, btn_name):
                getattr(self.ui, btn_name).clicked.connect(
                    lambda checked=False, v=val: self._apply_weight_and_refresh(val=v)
                )

        # 3. КНОПКИ +/- И КАСТОМНЫЙ ВЕС
        if hasattr(self.ui, 'plusWeight_button'):
            self.ui.plusWeight_button.clicked.connect(
                lambda: self._apply_weight_and_refresh(0.05, is_relative=True)
            )
        if hasattr(self.ui, 'minusWeight_button'):
            self.ui.minusWeight_button.clicked.connect(
                lambda: self._apply_weight_and_refresh(-0.05, is_relative=True)
            )
        if hasattr(self.ui, 'setWeight_button') and hasattr(self.ui, 'setWeight_lineEdit'):
            self.ui.setWeight_button.clicked.connect(
                lambda: self._apply_weight_and_refresh(float(self.ui.setWeight_lineEdit.text() or 1.0))
            )

        # 4. УПРАВЛЕНИЕ СПИСКОМ КОСТЕЙ В UI (+ Bone, - Bone)
        if hasattr(self.ui, 'addBone_button'):
            self.ui.addBone_button.clicked.connect(self._on_add_bone_clicked)
            
        if hasattr(self.ui, 'removeBone_button'):
            self.ui.removeBone_button.clicked.connect(self._on_remove_bone_clicked)
        
        # Подключаем жесткие кнопки
        for btn_name, val in weight_buttons.items():
            if hasattr(self.ui, btn_name):
                getattr(self.ui, btn_name).clicked.connect(
                    lambda checked=False, v=val: SkinMagicCore.set_vertex_weight(v, picked_joint_name=self._get_active_bone())
                )

        

        # 3. СЛОЖНЫЕ КНОПКИ CORE (Также используем враппер для Prune)
        if hasattr(self.ui, 'pruneWeight_button') and hasattr(self.ui, 'pruneWeight_lineEdit'):
            self.ui.pruneWeight_button.clicked.connect(
                lambda: self._execute_and_refresh(
                    SkinMagicCore.prune_weights, 
                    float(self.ui.pruneWeight_lineEdit.text() or 0.04)
                )
            )
        
        # 4. SCALE (УВЕЛИЧЕНИЕ/УМЕНЬШЕНИЕ ВЕСА В ПРОЦЕНТАХ)
        if hasattr(self.ui, 'rangeExt_button'):
            self.ui.rangeExt_button.clicked.connect(
                lambda: self._execute_and_refresh(SkinMagicCore.range_extend)
            )
        if hasattr(self.ui, 'rangeShr_button'):
            self.ui.rangeShr_button.clicked.connect(
                lambda: self._execute_and_refresh(SkinMagicCore.range_shrink)
            )

        # 5. УПРАВЛЕНИЕ КОСТЯМИ (+ Bone, - Bone)
        if hasattr(self.ui, 'addBone_button'):
            # Берем выделенную кость из вьюпорта и добавляем в скин
            self.ui.addBone_button.clicked.connect(
                lambda: self._execute_and_refresh(
                    SkinMagicCore.add_bone_to_skin, SkinMagicCore.get_selected_bone()
                )
            )
        if hasattr(self.ui, 'removeBone_button'):
            # Удаляем кость, выбранную в списке UI (если её вес 0)
            self.ui.removeBone_button.clicked.connect(
                lambda: self._execute_and_refresh(
                    SkinMagicCore.remove_bone_from_skin, self._get_active_bone()
                )
            )

        # 6. НАСТРОЙКИ ОТОБРАЖЕНИЯ (Vertex Size Slider)
        if hasattr(self.ui, 'weightVertexSize_Slider'):
            # Для слайдера используем сигнал valueChanged (он передает значение int)
            self.ui.weightVertexSize_Slider.valueChanged.connect(
                lambda val: SkinMagicCore.set_vertex_size(val)
            )
        if hasattr(self.ui, 'mirrorWeight_button'):
            self.ui.mirrorWeight_button.clicked.connect(self._run_mirror_logic)
        if hasattr(self.ui, 'checkInflunce_button') and hasattr(self.ui, 'checkInflunce_lineEdit'):
            self.ui.checkInflunce_button.clicked.connect(self._run_check_influence_logic)

        # Блок Swap Weight
        if hasattr(self.ui, 'swapLoadBoneA_pushButton'):
            self.ui.swapLoadBoneA_pushButton.clicked.connect(lambda: self._ui_load_bone('swapBoneA_lineEdit', 'A'))
        if hasattr(self.ui, 'swapLoadBoneB_pushButton'):
            self.ui.swapLoadBoneB_pushButton.clicked.connect(lambda: self._ui_load_bone('swapBoneB_lineEdit', 'B'))
        if hasattr(self.ui, 'swap_button'):
            self.ui.swap_button.clicked.connect(SkinMagicCore.swap_weight)
        if hasattr(self.ui, 'swapMerge_button'):
            self.ui.swapMerge_button.clicked.connect(SkinMagicCore.swap_merge_weight)

        # Блок Re-Skin
        if hasattr(self.ui, 'reSkinLoadBone_button'):
            self.ui.reSkinLoadBone_button.clicked.connect(self._ui_reskin_load_bone)
        if hasattr(self.ui, 'reSkinApply_button'):
            self.ui.reSkinApply_button.clicked.connect(self._run_reskin_logic)

        # Блок Warp
        if hasattr(self.ui, 'source_Vtx_button'):
            self.ui.source_Vtx_button.clicked.connect(self._ui_warp_load_vtx)
        if hasattr(self.ui, 'warp_button'):
            self.ui.warp_button.clicked.connect(self._run_warp_logic)


    # =========================================================================
    # ВНУТРЕННИЕ МЕТОДЫ-ПОМОЩНИКИ
    # =========================================================================
    def _run_mirror_logic(self):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        axis = 'X'
        if hasattr(self.ui, 'mirrorY_radioButton') and self.ui.mirrorY_radioButton.isChecked(): axis = 'Y'
        elif hasattr(self.ui, 'mirrorZ_radioButton') and self.ui.mirrorZ_radioButton.isChecked(): axis = 'Z'
        pos_to_neg = self.ui.mirror_checkBox.isChecked() if hasattr(self.ui, 'mirror_checkBox') else True
        part_mirror = self.ui.mirrorPart_checkBox.isChecked() if hasattr(self.ui, 'mirrorPart_checkBox') else False
        SkinMagicCore.mirror_weights(mirror_axis=axis, positive_to_negative=pos_to_neg, is_mirror_part=part_mirror)

    def _run_check_influence_logic(self):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        limit = int(self.ui.checkInflunce_lineEdit.text() or 4)
        cut_minor = self.ui.checkInflunce_cutMinor_checkBox.isChecked() if hasattr(self.ui, 'checkInflunce_cutMinor_checkBox') else True
        SkinMagicCore.check_influence(max_inf=limit, cut_minor=cut_minor)

    def _ui_load_bone(self, lineedit_name, slot):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        bone_name = SkinMagicCore.get_selected_bone()
        if bone_name and hasattr(self.ui, lineedit_name):
            getattr(self.ui, lineedit_name).setText(bone_name)
            if slot == 'A': SkinMagicCore._swap_bone_a = bone_name
            elif slot == 'B': SkinMagicCore._swap_bone_b = bone_name

    def _ui_reskin_load_bone(self):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        count = SkinMagicCore.reskin_pick_bone()
        if hasattr(self.ui, 'reSkin_label'):
            self.ui.reSkin_label.setText(str(count))

    def _run_reskin_logic(self):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        hold_bone = self.ui.reSkinHoldBone_checkBox.isChecked() if hasattr(self.ui, 'reSkinHoldBone_checkBox') else True
        SkinMagicCore.reskin_apply(hold_bone=hold_bone)
        if not hold_bone and hasattr(self.ui, 'reSkin_label'):
            self.ui.reSkin_label.setText("0")

    def _ui_warp_load_vtx(self):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        count = SkinMagicCore.load_source_vtx()
        if hasattr(self.ui, 'sVertexCount_label'):
            self.ui.sVertexCount_label.setText(str(count))

    def _run_warp_logic(self):
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        fine_copy = self.ui.warp_FineCopy_checkBox.isChecked() if hasattr(self.ui, 'warp_FineCopy_checkBox') else False
        hold_vtxs = self.ui.warp_HoldVtxs_checkBox.isChecked() if hasattr(self.ui, 'warp_HoldVtxs_checkBox') else True
        SkinMagicCore.warp_apply(is_fine_copy=fine_copy, hold_vtxs=hold_vtxs)
        if not hold_vtxs and hasattr(self.ui, 'sVertexCount_label'):
            self.ui.sVertexCount_label.setText("0")
    
    ## =========================================================================
    # БЛОК ОБНОВЛЕНИЯ СПИСКОВ ВЕСОВ (UI EVENTS)
    # =========================================================================
    def _setup_weight_ui_events(self):
        """Подключает синхронизацию списков и создает следилку за выделением в Maya."""
        # Синхронизация клика по списку костей
        if hasattr(self.ui, 'bone_listBox'):
            self.ui.bone_listBox.itemSelectionChanged.connect(self._on_bone_list_selected)
        
        # Создаем ScriptJob, который "слушает" клики в Maya
        self._sel_job = cmds.scriptJob(event=["SelectionChanged", self._on_maya_selection_changed], protected=True)

    def _refresh_weight_lists(self):
        """Читает актуальные веса из ядра и обновляет UI, сохраняя фокус выделения."""
        if not self.isVisible() or not hasattr(self.ui, 'bone_listBox'): return
        
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        bones, weights = SkinMagicCore.get_vertex_influences()
        
        # Запоминаем текущую выделенную кость, чтобы список не дергался
        selected_bone = self._get_active_bone()

        self.ui.bone_listBox.clear()
        if hasattr(self.ui, 'value_listBox'):
            self.ui.value_listBox.clear()
        
        if bones:
            self.ui.bone_listBox.addItems(bones)
            if hasattr(self.ui, 'value_listBox'):
                self.ui.value_listBox.addItems(weights)
            
            # Восстанавливаем выделение
            if selected_bone:
                items = self.ui.bone_listBox.findItems(selected_bone, QtCore.Qt.MatchExactly)
                if items:
                    self.ui.bone_listBox.setCurrentItem(items[0])
                    return
            
            # Если ничего не было выделено — выбираем первую кость
            self.ui.bone_listBox.setCurrentRow(0)

    def _on_maya_selection_changed(self):
        """Срабатывает при смене выделения во вьюпорте Maya."""
        try:
            self._refresh_weight_lists()
        except RuntimeError:
            pass # Игнорируем ошибку, если UI уже удален из памяти

    def _apply_weight_and_refresh(self, val, is_relative=False):
        """Враппер: Передает данные в ядро и принудительно обновляет UI."""
        from FD_FishTool.core.skin_magic_core import SkinMagicCore
        
        # 1. Вызываем математику
        SkinMagicCore.set_vertex_weight(
            weight_value=val, 
            picked_joint_name=self._get_active_bone(),
            is_relative=is_relative
        )
        # 2. Принудительно обновляем UI
        self._refresh_weight_lists()

    def _on_bone_list_selected(self):
        """Синхронизирует списки между собой и с вьюпортом Maya."""
        if not hasattr(self.ui, 'bone_listBox') or not self.ui.bone_listBox.currentItem(): return
        
        row = self.ui.bone_listBox.currentRow()
        
        # 1. Выделяем ту же строку в списке весов
        if hasattr(self.ui, 'value_listBox') and self.ui.value_listBox.count() > row:
            self.ui.value_listBox.setCurrentRow(row)
            
        # 2. Если стоит галочка Sync, выделяем кость прямо в Maya
        is_sync = self.ui.syncBone_checkBox.isChecked() if hasattr(self.ui, 'syncBone_checkBox') else False
        if is_sync:
            bone_name = self.ui.bone_listBox.currentItem().text()
            if cmds.objExists(bone_name):
                cmds.select(bone_name, replace=True)

    def _get_active_bone(self):
        """Отдает имя кости, выбранной в списке, чтобы кнопки знали, куда применять вес."""
        if hasattr(self.ui, 'bone_listBox') and self.ui.bone_listBox.currentItem():
            return self.ui.bone_listBox.currentItem().text()
        return None
    
    def _execute_and_refresh(self, core_func, *args, **kwargs):
        """Универсальный враппер: Выполняет любую функцию ядра и принудительно обновляет списки UI."""
        core_func(*args, **kwargs)
        self._refresh_weight_lists()
    
    def _change_bones_color(self, *args):
        """Открывает палитру и передает цвет выделенным костям."""
        # Быстрая проверка, чтобы не открывать палитру, если ничего не выделено
        sel = cmds.ls(sl=True, type='joint')
        if not sel:
            cmds.warning("FD_FishTool: Сначала выделите кости во вьюпорте!")
            return
            
        # Открываем стандартный диалог выбора цвета PyQt/PySide
        color = QtWidgets.QColorDialog.getColor()
        
        if color.isValid():
            # Maya принимает цвета в диапазоне 0.0 - 1.0 (а не 0-255)
            # У QColor есть удобные методы redF(), greenF(), blueF() для этого
            rgb_tuple = (color.redF(), color.greenF(), color.blueF())
            self.manager.set_bones_color(rgb_tuple)

    ## =========================================================================
    # БЛОК ТЕКСТУР И МАТЕРИАЛОВ (ПОСЛЕ НАЖАТИЯ КНОПКИ "LOAD TEXTURE")
    # =========================================================================

    def _run_texture_load_logic(self, *args):
        """Запускает процесс поиска текстуры, создания и распределения материалов."""
        
        # 1. ПРОВЕРКА НАЛИЧИЯ МЕША (Если ничего не выбрано - останавливаем скрипт)
        base_mesh = self.mesh_combo.currentText()
        if not base_mesh or not cmds.objExists(base_mesh):
            cmds.warning("FD_FishTool: ОШИБКА! Сначала выберите базовый меш в списке 'TargetMeshSelection'!")
            return

        mat_names = ["mat_opaque", "mat_transparent", "mat_overlap_eyes", "mat_overlap_teeth"]
        existing = [m for m in mat_names if cmds.objExists(m)]
        overwrite = True
        
        # 2. ПРОВЕРКА СУЩЕСТВУЮЩИХ МАТЕРИАЛОВ
        if existing:
            reply = QtWidgets.QMessageBox.question(
                self, "Материалы найдены", 
                "Материалы рыбы уже существуют в сцене. Перезаписать их и обновить текстуру?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            # Если пользователь нажал "Нет" - скрипт полностью останавливается
            if reply == QtWidgets.QMessageBox.No: 
                print("FD_FishTool: Операция отменена пользователем. Материалы оставлены без изменений.")
                return
            overwrite = True
        
        # 3. ПОИСК ТЕКСТУРЫ
        texture_path = None
        textures = self.manager.find_textures_in_project()
        
        if len(textures) == 1:
            texture_path = textures[0]
        elif len(textures) > 1:
            item, ok = QtWidgets.QInputDialog.getItem(self, "Выбор текстуры", "Найдено несколько текстур в sourceimages:", textures, 0, False)
            if ok and item: texture_path = item
            else: return
        else:
            # Если текстур нет или сцена Untitled - открываем проводник
            texture_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите текстуру рыбы", "", "Images (*.png *.jpg *.jpeg *.tif *.tga)")
            if not texture_path: return
        
        # 4. СОЗДАНИЕ МАТЕРИАЛОВ
        self.sgs = self.manager.create_fish_materials(texture_path, overwrite=overwrite)
        
        # 5. НАЗНАЧЕНИЕ MAT_OPAQUE НА БАЗОВЫЙ МЕШ
        self.manager.assign_material(base_mesh, self.sgs.get("mat_opaque", "mat_opaqueSG"))
        print(f"FD_FishTool: mat_opaque назначен на {base_mesh}.")
        
        # 6. ОЧИСТКА СТАРЫХ ОКОН (Защита от дублирования окон)
        if hasattr(self, 'mat_dialog') and self.mat_dialog:
            try:
                self.mat_dialog.close()
                self.mat_dialog.deleteLater()
            except:
                pass

        # 7. ЗАПУСК ДИАЛОГА ДЛЯ ОСТАЛЬНЫХ МАТЕРИАЛОВ
        steps = [
            "Выделите полигоны (Faces) или объекты для <b>Плавников</b><br>(mat_transparent)",
            "Выделите полигоны (Faces) или объекты для <b>Глаз</b><br>(mat_overlap_eyes)",
            "Выделите полигоны (Faces) или объекты для <b>Зубов</b><br>(mat_overlap_teeth)"
        ]
        self.mat_dialog = MaterialPlacementDialog(steps, self._on_materials_assigned, parent=self)
        self.mat_dialog.show()

    def _on_materials_assigned(self, results):
        """Коллбэк, который срабатывает после прохождения всех шагов диалога."""
        mats = ["mat_transparent", "mat_overlap_eyes", "mat_overlap_teeth"]
        for sel, mat_name in zip(results, mats):
            if sel:
                sg = self.sgs.get(mat_name, mat_name + "SG")
                self.manager.assign_material(sel, sg)
                print(f"FD_FishTool: {mat_name} назначен на {len(sel)} элементов.")
        
        cmds.select(clear=True)
        print("FD_FishTool: Настройка материалов успешно завершена!")

    ## =========================================================================
    # БЛОК окон подсказки
    # =========================================================================

          

    def _show_stage_skin_help(self, *args):
        title = "Справка | Staged Skinning"
        text = """
        <b>Поэтапный скиннинг (Staged Skinning)</b><br><br>
        Этот инструмент позволяет разбить сложный скиннинг рыбы на логические этапы:
        <ol>
            <li><b>Body (Тело)</b> — скиннинг основной массы без учета плавников.</li>
            <li><b>Side Fins (Боковые плавники)</b> — добавление весов локальным элементам.</li>
            <li><b>Vert Fins (Верхние/нижние плавники)</b> — финализация.</li>
        </ol>
        <i>*Используйте кнопки Select и Add для работы с выделенными вертексами.</i>
        """

        # Имя картинки или гифки (положишь в data/help/stage_skin_help.gif)
        #dlg = HelpDialog(title, text, image_filename="stage_skin_help.gif", parent=self)
        #dlg.exec_() # exec_() делает окно модальным, пока юзер его не закроет
        # Вызываем без картинки!
        dlg = HelpDialog(title, text, parent=self)
        dlg.exec_()

    def _show_skin_anim_help(self, *args):
        title = "Справка | Skin Animations"
        text = """
        <b>Тестовые анимации (Test Animations)</b><br><br>
        Инструмент накладывает на контролы ключи из файла <b>body_test_anim.json</b>.<br>
        Это позволяет быстро проверить, как деформируется меш (скиннинг) в крайних позах.<br><br>
        • Нажмите <b>Body</b> или <b>META</b> для загрузки пресета.<br>
        • При повторном нажатии анимация сбросится и перезапишется.<br>
        • Кнопка очистки вернет все контролы в Bind Pose.
        """
        # Вызываем без картинки!
        dlg = HelpDialog(title, text, parent=self)
        dlg.exec_()