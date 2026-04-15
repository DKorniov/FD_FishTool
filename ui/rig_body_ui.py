# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds

from FD_FishTool.core.rig_body import BodyRigManager
from FD_FishTool.ui.weight_blender_ui import WeightBlenderWidget
from FD_FishTool.ui.easy_ease_ui import EasyEaseWidget

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
        from PySide2 import QtUiTools
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

        # 4. СВОРАЧИВАЕМ ГАРМОШКУ (Accordion) ПО УМОЛЧАНИЮ
        accordions = [
            'btn_model_prepare', 'btn_bones_controls', 'btn_skinning', 
            'btn_stage_skin', 'btn_skin_animation', 'pushButton_16', # pushButton_16 это кнопка SkinMagic
            'btn_reskin', 'btn_clean_up'
        ]
        for btn_name in accordions:
            if hasattr(self.ui, btn_name):
                getattr(self.ui, btn_name).setChecked(False)

        # 5. ПОДКЛЮЧАЕМ ВСЕ КНОПКИ
        self._connect_rig_manager()
        self._connect_skinmagic()

        # Запускаем слушатель выделения для списков весов
        self._setup_weight_ui_events()

        # 6. Встраиваем кастомные слайдеры (AnimBot / EasyEase) вниз окна
        '''self.blender_ui = WeightBlenderWidget(self.manager, lambda: self.mesh_combo.currentText())
        slider_group = QtWidgets.QGroupBox("Interactive Curve Control")
        vl = QtWidgets.QVBoxLayout(slider_group)
        vl.addWidget(self.blender_ui)
        main_layout.addWidget(slider_group)

        self.ease_ui = EasyEaseWidget(self.manager, lambda: self.mesh_combo.currentText())
        ease_group = QtWidgets.QGroupBox("Easy Ease Control (test version 1.0)")
        vl2 = QtWidgets.QVBoxLayout(ease_group)
        vl2.addWidget(self.ease_ui)
        main_layout.addWidget(ease_group)'''

    

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
        
        # --- Блок: Target Mesh Selection ---
        if hasattr(self.ui, 'btn_get_mesh'):
            self.ui.btn_get_mesh.clicked.connect(self._get_mesh_from_sel)
            
        # --- Блок: Model Prepare ---
        if hasattr(self.ui, 'pushButton_9'): # "let the clownFish out"
            self.ui.pushButton_9.clicked.connect(lambda *args: print("FD_FishTool: Выпускаем рыбу-клоуна! (Заглушка)"))
        if hasattr(self.ui, 'pushButton_4'): # "check all"
            self.ui.pushButton_4.clicked.connect(self._run_model_check)
            
        # --- Блок: Bones Controls ---
        if hasattr(self.ui, 'pushButton_5'): # "open AS5"
            self.ui.pushButton_5.clicked.connect(lambda *args: print("FD_FishTool: Открытие AS5..."))
        if hasattr(self.ui, 'pushButton_6'): # "change bones color"
            self.ui.pushButton_6.clicked.connect(lambda *args: print("FD_FishTool: Изменение цвета костей..."))
        if hasattr(self.ui, 'pushButton_7'): # "MEtabones Outliner"
            self.ui.pushButton_7.clicked.connect(lambda *args: print("FD_FishTool: Открытие MEtabones Outliner..."))
        if hasattr(self.ui, 'btn_texture_load'): 
            self.ui.btn_texture_load.clicked.connect(lambda *args: print("FD_FishTool: Загрузка текстур..."))

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

        # --- Блок: Adaptive Gradient ---
        if hasattr(self.ui, 'btn_Apply_adaptive_gradient'):
            self.ui.btn_Apply_adaptive_gradient.clicked.connect(
                lambda *args: self.manager.apply_topological_gradient(self.mesh_combo.currentText())
            )

        # --- Блок: Clean Up (Weight Utilities) ---
        if hasattr(self.ui, 'btn_clean_weightless_bones'):
            self.ui.btn_clean_weightless_bones.clicked.connect(
                lambda *args: self.manager.clean_weightless_bones(self.mesh_combo.currentText())
            )

        # --- Блок: Test Animations ---
        if hasattr(self.ui, 'pushButton_2'): # "Body Animation test"
            self.ui.pushButton_2.clicked.connect(lambda *args: print("FD_FishTool: Тест анимации тела..."))
        if hasattr(self.ui, 'pushButton_3'): # "META Animation test"
            self.ui.pushButton_3.clicked.connect(lambda *args: print("FD_FishTool: Тест META-анимации..."))

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
            
            # Кнопки Clean Up из нижней части интерфейса
            'misc_runButton': SkinMagicCore.remove_unknown_nodes,
            'misc_runButton_6': SkinMagicCore.clean_custom_attrs,
            'misc_runButton_3': SkinMagicCore.mesh_cleanup,
            'misc_runButton_5': SkinMagicCore.clean_weightless_bones,
            'misc_runButton_7': SkinMagicCore.delete_non_skin_history,
            'misc_runButton_8': SkinMagicCore.build_weight_map,
            
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