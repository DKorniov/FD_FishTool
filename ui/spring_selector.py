# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds

class SpringSelectorWindow(QtWidgets.QDialog):
    def __init__(self, physics_manager, parent=None):
        """
        Окно селектора для настройки физики SpringMagic.
        :param physics_manager: Экземпляр core.physics_manager.PhysicsManager
        """
        super(SpringSelectorWindow, self).__init__(parent)
        self.physics_mgr = physics_manager
        self.setWindowTitle("SpringMagic Selector | FD_FishTool")
        self.setMinimumWidth(500)
        
        self.mapping = {}      # Хранит список контролов для каждой группы
        self.ui_inputs = {}    # Хранит объекты QLineEdit для обновления текста
        
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # 1. Блок параметров SpringMagic
        cfg_group = QtWidgets.QGroupBox("Параметры физики")
        cfg_lay = QtWidgets.QGridLayout(cfg_group)
        
        self.val_spring = QtWidgets.QDoubleSpinBox()
        self.val_spring.setRange(0.0, 1.0)
        self.val_spring.setSingleStep(0.1)
        self.val_spring.setValue(0.5)
        
        self.val_twist = QtWidgets.QDoubleSpinBox()
        self.val_twist.setRange(0.0, 1.0)
        self.val_twist.setSingleStep(0.1)
        self.val_twist.setValue(0.2)
        
        self.chk_loop = QtWidgets.QCheckBox("Loop (Цикличная анимация)")
        self.chk_loop.setChecked(True)
        
        cfg_lay.addWidget(QtWidgets.QLabel("Spring (Ratio):"), 0, 0)
        cfg_lay.addWidget(self.val_spring, 0, 1)
        cfg_lay.addWidget(QtWidgets.QLabel("Twist (Ratio):"), 0, 2)
        cfg_lay.addWidget(self.val_twist, 0, 3)
        cfg_lay.addWidget(self.chk_loop, 1, 0, 1, 4)
        layout.addWidget(cfg_group)

        # 2. Блок выбора контролов цепей (версия 5)
        rows = [
            ("SideFin", "Боковые плавники"),
            ("BellyFin", "Нижние брюшные"),
            ("SideFin2", "Боковые 2"),
            ("DorsalFin", "Верхние спинные"),
            ("HeadFin", "Нижние головные"),
            ("Tail", "Хвост (ветки)"),
            ("Extra", "Дополнительные")
        ]
        
        form = QtWidgets.QFormLayout()
        for key, label in rows:
            line = QtWidgets.QLineEdit()
            line.setReadOnly(True)
            line.setPlaceholderText("Выделите корневой контрол...")
            self.ui_inputs[key] = line
            
            btn = QtWidgets.QPushButton("Set")
            btn.setFixedWidth(60)
            # Передача ключа в метод назначения через лямбду
            btn.clicked.connect(lambda checked=False, k=key: self.assign(k))
            
            h_layout = QtWidgets.QHBoxLayout()
            h_layout.addWidget(line)
            h_layout.addWidget(btn)
            form.addRow(QtWidgets.QLabel(f"<b>{label}:</b>"), h_layout)
            
        layout.addLayout(form)

        # 3. Кнопка запуска полного цикла
        btn_run = QtWidgets.QPushButton("🚀 ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ ФИЗИКИ")
        btn_run.setMinimumHeight(60)
        btn_run.setStyleSheet("background-color: #d4a017; font-weight: bold; color: black; font-size: 13px;")
        btn_run.clicked.connect(self.execute_pipeline)
        layout.addWidget(btn_run)

    def assign(self, key):
        """
        Назначает выделенный контрол в группу и ищет симметричную пару.
        :param key: Ключ группы (напр. 'SideFin')
        """
        sel = cmds.ls(sl=True)
        if not sel:
            return
        
        root_ctrl = sel[0]
        # Используем метод симметрии из менеджера
        sym_ctrl = self.physics_mgr.get_symmetric_control(root_ctrl)
        
        roots = [root_ctrl]
        display_text = root_ctrl
        
        if sym_ctrl and cmds.objExists(sym_ctrl):
            roots.append(sym_ctrl)
            display_text += f" + {sym_ctrl} (Auto-Sym)"
            
        self.mapping[key] = roots
        self.ui_inputs[key].setText(display_text)
        self.ui_inputs[key].setStyleSheet("background-color: #2b4433; color: white;")

    def execute_pipeline(self):
        """
        Выполняет итеративный просчет всех анимаций для каждой группы.
        """
        if not self.mapping:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Назначьте хотя бы один контрол!")
            return
        
        all_proxies = []
        
        # Определяем наборы анимаций для разных групп по эталону
        fin_anims = ["plavnik_normal_move", "plavnik_normal_move2", "plavnik_wait_pose", "plavnik_crowded"]
        other_anims = ["normal_move", "wait_pose"]

        # Процесс: LAT -> Bind -> Apply (для каждого клипа)
        for key, roots in self.mapping.items():
            # Выбор списка анимаций в зависимости от группы
            anims = fin_anims if key in ["SideFin", "SideFin2", "BellyFin"] else other_anims
            
            for r in roots:
                # Вызов основного рабочего метода физики
                proxies = self.physics_mgr.process_spring_logic(
                    root_ctrl=r, 
                    anim_list=anims, 
                    spring_val=self.val_spring.value(), 
                    twist_val=self.val_twist.value(), 
                    is_loop=self.chk_loop.isChecked()
                )
                all_proxies.extend(proxies)

        # Финальное запекание на контролы в диапазоне 9-189
        self.physics_mgr.final_bake(all_proxies)
        
        QtWidgets.QMessageBox.information(self, "Success", "Все физические циклы запечены и очищены.")
        self.accept()