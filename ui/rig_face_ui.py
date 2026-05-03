# -*- coding: utf-8 -*-
import os
from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools
import maya.cmds as cmds
from FD_FishTool.core.face_rig_builder import FaceRigBuilder
from FD_FishTool.core.rig_body import BodyRigManager # Импортируем для градиента
from FD_FishTool.ui.help_manager import HelpManager # Для кнопок справки

class FacePlacementDialog(QtWidgets.QDialog):
    """Окно для последовательного выбора вертексов (сохранено без изменений)."""
    def __init__(self, title, steps, callback, parent=None):
        super(FacePlacementDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(250, 350)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setModal(False)
        self.steps = steps
        self.callback = callback
        self.results = []
        self.step_idx = 0
        
        l = QtWidgets.QVBoxLayout(self)
        self.lbl = QtWidgets.QLabel("<b>Step {}:</b><br>{}".format(self.step_idx + 1, self.steps[0]))
        self.lbl.setWordWrap(True)
        l.addWidget(self.lbl)
        
        self.btn = QtWidgets.QPushButton("Confirm Selection")
        self.btn.setFixedHeight(50)
        self.btn.clicked.connect(self._confirm)
        l.addWidget(self.btn)

    def _confirm(self):
        s = cmds.ls(sl=True, fl=True)
        if not s or ".vtx" not in s[0]: return
        self.results.append(s[0])
        self.step_idx += 1
        
        if self.step_idx < len(self.steps): 
            self.lbl.setText("<b>Step {}:</b><br>{}".format(self.step_idx + 1, self.steps[self.step_idx]))
        else: 
            self.callback(self.results)
            self.close()


class FaceRigController(QtWidgets.QWidget):
    """Единый MVC-контроллер для вкладки Face Rig."""
    def __init__(self, config=None, parent=None):
        super(FaceRigController, self).__init__(parent)
        self.cfg = config # Сохраняем конфиг
        self.builder = FaceRigBuilder()
        # Создаем экземпляр менеджера тела для доступа к функции градиента
        self.body_manager = BodyRigManager(config=self.cfg)
        self.ui = None
        self.dlg = None
        
        self._init_ui()
        
        self._connect_signals()

    def _init_ui(self):
        # Динамическая загрузка .ui файла
        ui_path = os.path.join(os.path.dirname(__file__), "face_rig_tab.ui")
        loader = QtUiTools.QUiLoader()
        file = QtCore.QFile(ui_path)
        
        if not file.open(QtCore.QFile.ReadOnly):
            cmds.warning(f"FD_FishTool: Не удалось найти файл UI: {ui_path}")
            return
            
        self.ui = loader.load(file, self)
        file.close()

        # Встраиваем загруженный интерфейс в текущий QWidget
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.ui)
        layout.setContentsMargins(0, 0, 0, 0)   

        # --- СИНХРОНИЗАЦИЯ UI ПРИ ЗАПУСКЕ ---
        # Жестко скрываем фрейм и отжимаем кнопку при старте
        if hasattr(self.ui, 'frame_driven_bones') and hasattr(self.ui, 'btn_driven_bones'):
            self.ui.frame_driven_bones.setVisible(False)
            self.ui.btn_driven_bones.setChecked(False)    
        

    

    def _connect_signals(self):
        if not self.ui: return
        
        # Интеграция библиотеки (Замена старого open_selector)
        self.ui.btn_init_library.clicked.connect(self._init_library)
        
        # Stage 4: Geometry Generation
        self.ui.btn_eyes.clicked.connect(self.run_eyes)
        self.ui.btn_mouth.clicked.connect(self.run_mouth)
        self.ui.btn_brows.clicked.connect(self.run_brows)
        self.ui.btn_jaw.clicked.connect(self.run_jaw_teeth)
        
        # Selector & SMART KEY
        self.ui.list_driven_bones.itemSelectionChanged.connect(self._on_driven_list_selection_changed)
        self.ui.btn_key.clicked.connect(self._do_key)
        
        # Test Tools
        self.ui.btn_gen_anim.clicked.connect(self._run_anim)
        self.ui.btn_clean_anim.clicked.connect(self._run_clean)

        # 1. Подключение кнопок справки
        if hasattr(self.ui, 'btn_info_driven'):
            self.ui.btn_info_driven.clicked.connect(lambda: HelpManager.show_driven_bones_help(self))
        if hasattr(self.ui, 'btn_info_anim_driven'):
            self.ui.btn_info_anim_driven.clicked.connect(lambda: HelpManager.show_face_anim_test_help(self))
        if hasattr(self.ui, 'btn_info_key_driven'):
            self.ui.btn_info_key_driven.clicked.connect(lambda: HelpManager.show_smart_key_help(self))
        if hasattr(self.ui, 'btn_info_gradient'):
            self.ui.btn_info_gradient.clicked.connect(lambda: HelpManager.show_gradient_weight_help(self))

                # 2. Подключение адаптивного градиента (Face-версия)
        if hasattr(self.ui, 'btn_Apply_adaptive_gradient_face'):
            self.ui.btn_Apply_adaptive_gradient_face.clicked.connect(self._apply_face_gradient)

        # --- ПОДКЛЮЧЕНИЕ СТАТИЧНЫХ КНОПОК ИЗ UI-ФАЙЛА ---
        selector_map = {
            'btn_sel_R_Brow': "R_Brow_ctrl",
            'btn_sel_L_Brow': "L_Brow_ctrl",
            'btn_sel_R_Upp_Lid': "R_Upp_EyeLid",
            'btn_sel_L_Upp_Lid': "L_Upp_EyeLid",
            'btn_sel_Sync': "Sync",
            'btn_sel_Upr_Lip': "Upr_Lip",
            'btn_sel_R_Eye': "R_Eye_ctrl",
            'btn_sel_L_Eye': "L_Eye_ctrl",
            'btn_sel_Emote': "Emote",
            'btn_sel_Lwr_Lip': "Lwr_Lip",
            'btn_sel_R_Lwr_Lid': "R_Lwr_EyeLid",
            'btn_sel_L_Lwr_Lid': "L_Lwr_EyeLid",
            'btn_sel_Jaw': "Jaw",
            'btn_sel_Teeth': "gui_teeth"
        }

        for btn_name, ctrl_name in selector_map.items():
            if hasattr(self.ui, btn_name):
                btn = getattr(self.ui, btn_name)
                btn.clicked.connect(lambda ch=False, n=ctrl_name: self._on_selector_click(n))
            else:
                cmds.warning(f"FD_FishTool: Кнопка {btn_name} не найдена в интерфейсе.")

    # --- МЕТОДЫ ЛОГИКИ СЕЛЕКТОРА ---

    def _init_library(self):
        """Загрузка библиотеки контроллеров и генерация/привязка скин-костей."""
        if self.builder.import_gui_library():
            self.builder.build_and_connect_skin_bones()
            cmds.inViewMessage(amg="<hl>Face GUI Library загружена, кости подключены.</hl>", pos="midCenter", fade=True)

    def _on_selector_click(self, name):
        if not cmds.objExists(name): return
        cmds.select(name)
        self.ui.list_driven_bones.clear()
        bones = self.builder.get_driven_bones(name)
        if bones: 
            self.ui.list_driven_bones.addItems(bones)
    
    def _on_driven_list_selection_changed(self):
        selected_items = self.ui.list_driven_bones.selectedItems()
        bone_names = [item.text() for item in selected_items]
    
        if bone_names:
            existing_bones = [b for b in bone_names if cmds.objExists(b)]
            if existing_bones:
                cmds.select(existing_bones)
        else:
            cmds.select(clear=True)

    def _do_key(self):
        sel = cmds.ls(sl=True)
        if not sel: return
        nodes = [self.ui.list_driven_bones.item(i).text() for i in range(self.ui.list_driven_bones.count())]
        if nodes:
            # Вызов логики Smart Key
            self.builder.set_smart_key(sel[0], nodes)

    def _run_anim(self):
        self.builder.run_context_test_animation()

    def _run_clean(self):
        self.builder.clean_test_animation()


    def _apply_face_gradient(self):
        """
        Умный запуск градиента: 
        1. Проверяет выбор меша во вкладке Rig Body.
        2. Если там пусто, берет выделение в сцене.
        """
        mesh_name = ""
        
        # 1. Пытаемся достучаться до вкладки Body через главное окно
        main_win = self.window() 
        
        if hasattr(main_win, 'rig_body_ui'):
            body_tab = main_win.rig_body_ui
            if hasattr(body_tab.ui, 'mesh_combo'):
                mesh_name = body_tab.ui.mesh_combo.currentText()
        
        # 2. Если во вкладке тела ничего не выбрано, берем выделение в Maya
        if not mesh_name:
            sel = cmds.ls(sl=True)
            if sel:
                mesh_name = sel[0]
            else:
                cmds.warning("FD_FishTool: Меш не выбран ни во вкладке Body, ни в сцене!")
                return

        # 3. Применение функции из ядра
        try:
            self.body_manager.apply_topological_gradient(mesh_name)
            cmds.inViewMessage(amg=f"<hl>Градиент применен к: {mesh_name}</hl>", pos="midCenter", fade=True)
        except Exception as e:
            cmds.warning(f"FD_FishTool: Ошибка градиента: {e}")

    # --- МЕТОДЫ ЛОГИКИ ГЕНЕРАЦИИ ГЕОМЕТРИИ (Stage 4) ---

    def run_eyes(self):
        s = ["R Up In", "R Up Mid", "R Up Out", "R Dw In", "R Dw Mid", "R Dw Out"]
        self.dlg = FacePlacementDialog("Eyes", s, self._finish_eyes)
        self.dlg.show()

    def _finish_eyes(self, v):
        b = ["mchFcrg_right_up_eyeShade1", "mchFcrg_right_up_eyeShade2", "mchFcrg_right_up_eyeShade3", 
             "mchFcrg_right_dwn_eyeShade1", "mchFcrg_right_dwn_eyeShade2", "mchFcrg_right_dwn_eyeShade3"]
        for vtx, bone in zip(v, b): 
            l = self.builder.create_rig_unit(vtx, bone)
            self.builder.mirror_unit(l)

    def run_mouth(self):
        num = self.ui.spin_lip_pairs.value()
        s = ["Up Lip C", "Dw Lip C", "R Corner"]
        for i in range(num): 
            sf = " {}".format(i+1) if i > 0 else ""
            s.extend(["Pair{}: R UP Lip".format(sf), "Pair{}: R DW Lip".format(sf)])
        s.extend(["R UP Cheek", "R MID Cheek", "R DW Cheek"])
        self.dlg = FacePlacementDialog("Mouth", s, self._finish_mouth)
        self.dlg.show()

    def _finish_mouth(self, v):
        self.builder.create_rig_unit(v[0], "mchFcrg_cent_up_lip1")
        self.builder.create_rig_unit(v[1], "mchFcrg_cent_dwn_lip1")
        lc = self.builder.create_rig_unit(v[2], "mchFcrg_right_corner_lip")
        self.builder.mirror_unit(lc)
        
        idx = 3
        num = self.ui.spin_lip_pairs.value()
        for i in range(num):
            sf = "{}".format(i+1) if i > 0 else ""
            u = self.builder.create_rig_unit(v[idx], "mchFcrg_right_up_lip{}".format(sf))
            d = self.builder.create_rig_unit(v[idx+1], "mchFcrg_right_dwn_lip{}".format(sf))
            self.builder.mirror_unit(u)
            self.builder.mirror_unit(d)
            idx += 2
            
        for n in ["mchFcrg_right_up_cheek", "mchFcrg_right_cntr_cheek", "mchFcrg_right_dwn_cheek"]:
            l = self.builder.create_rig_unit(v[idx], n)
            self.builder.mirror_unit(l)
            idx += 1

    def run_brows(self):
        n = self.ui.spin_brows.value()
        s = ["Brow {} (R)".format(i+1) for i in range(n)]
        self.dlg = FacePlacementDialog("Brows", s, self._finish_brows)
        self.dlg.show()

    def _finish_brows(self, v):
        for i, vtx in enumerate(v): 
            l = self.builder.create_rig_unit(vtx, f"mchFcrg_right_Brow{i+1}")
            self.builder.mirror_unit(l)

    def run_jaw_teeth(self):
        self.builder.create_rig_unit(None, "mchFcrg_jaw", [0, 0, 0])
        self.builder.create_rig_unit(None, "mchFcrg_teeth", [0, 1, 0])