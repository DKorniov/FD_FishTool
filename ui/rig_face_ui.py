# -*- coding: utf-8 -*-
import os
from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools
import maya.cmds as cmds
from FD_FishTool.core.face_rig_builder import FaceRigBuilder

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
    def __init__(self, parent=None):
        super(FaceRigController, self).__init__(parent)
        self.builder = FaceRigBuilder()
        self.ui = None
        self.dlg = None
        
        self._init_ui()
        self._setup_selector_grid()
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

        
        self.ui.group_selector.setStyleSheet("""
            /* Базовый стиль для всех кнопок селектора */
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 8px;
                border: 1px solid #333333;
                font-weight: bold;
            }

            /* Цвет при наведении */
            QPushButton:hover {
                background-color: #555555;
                border: 1px solid #777777;
            }

            /* Стили для конкретных групп кнопок (по тексту на кнопке) */
            
            /* Глаза и правые веки (Синие оттенки) */
            QPushButton[text*="R_"]{
                background-color: #2484d6;
            }
                                             
            /* Глаза и левые веки (Синие оттенки) */
            QPushButton[text*="L_"]{
                background-color: #d02173;
            }
            
            /* Брови (фиолетовые) */
            QPushButton[text*="Brow"] {
                background-color: #9d53d7;
            }
            
            /* Губы и рот (желтые оттенки) */
            QPushButton[text*="Lip"], QPushButton[text="Jaw"], QPushButton[text="Sync"], QPushButton[text="Emote"] {
                background-color: #d6bf55;
            }
            
            /* зубы (серые) */
            QPushButton[text="Teeth"] {
                background-color: #a0a0a0;
            }
        """)

    def _setup_selector_grid(self):
        """Программная генерация сетки кнопок для контроллеров и привязка их в .ui layout."""
        if not hasattr(self.ui, 'layout_selector_grid'):
            return

        # Уменьшаем расстояния между кнопками для компактности
        self.ui.layout_selector_grid.setSpacing(4)
        self.ui.layout_selector_grid.setContentsMargins(5, 5, 5, 5)

        ctrls = [
            (0,0,"R_Brow","R_Brow_ctrl"),(0,1,"L_Brow","L_Brow_ctrl"),
            (1,0,"R_Upp_Lid","R_Upp_EyeLid"),(1,1,"L_Upp_Lid","L_Upp_EyeLid"),(1,3,"Sync","Sync"),(1,4,"Upr_Lip","Upr_Lip"),
            (2,0,"R_Eye","R_Eye_ctrl"),(2,1,"L_Eye","L_Eye_ctrl"), (2,3,"Emote","Emote"), (2,4,"Lwr_Lip","Lwr_Lip"),
            (3,0,"R_Lwr_Lid","R_Lwr_EyeLid"),(3,1,"L_Lwr_Lid","L_Lwr_EyeLid"), (3,3,"Jaw","Jaw"),(3,4,"Teeth","gui_teeth")
        ]
        
        for r, c, l, n in ctrls:
            b = QtWidgets.QPushButton(l)
            
            # Убираем FixedSize. Даем адекватный минимум, чтобы текст не пропадал, 
            # и разрешаем тянуться по вертикали и горизонтали.
            b.setMinimumSize(65, 35)
            b.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            
            b.clicked.connect(lambda ch=False, name=n: self._on_selector_click(name))
            self.ui.layout_selector_grid.addWidget(b, r, c)

        # Делаем пустую колонку (индекс 2) "пружинистой", чтобы она не занимала лишнего места,
        # но при этом визуально отделяла левую часть лица от центральных элементов (Sync, Jaw и т.д.)
        self.ui.layout_selector_grid.setColumnStretch(2, 0) 
        # Даем больше веса колонкам с кнопками, чтобы они тянулись равномерно
        for i in [0, 1, 3, 4]:
            self.ui.layout_selector_grid.setColumnStretch(i, 1)

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