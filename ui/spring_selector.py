# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds

class SpringSelectorWindow(QtWidgets.QDialog):
    def __init__(self, manager, parent=None):
        super(SpringSelectorWindow, self).__init__(parent)
        self.manager = manager
        self.setWindowTitle("SpringMagic Pipeline | Master")
        self.setMinimumWidth(500)
        self.mapping = {}
        self.ui_inputs = {}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Settings
        cfg_group = QtWidgets.QGroupBox("Физика")
        cfg_lay = QtWidgets.QGridLayout(cfg_group)
        self.val_spring = QtWidgets.QDoubleSpinBox(); self.val_spring.setValue(0.5)
        self.val_twist = QtWidgets.QDoubleSpinBox(); self.val_twist.setValue(0.2)
        self.chk_loop = QtWidgets.QCheckBox("Loop"); self.chk_loop.setChecked(True)
        cfg_lay.addWidget(QtWidgets.QLabel("Spring:"), 0, 0); cfg_lay.addWidget(self.val_spring, 0, 1)
        cfg_lay.addWidget(QtWidgets.QLabel("Twist:"), 0, 2); cfg_lay.addWidget(self.val_twist, 0, 3)
        cfg_lay.addWidget(self.chk_loop, 1, 0); layout.addWidget(cfg_group)

        rows = [("SideFin", "Боковые"), ("BellyFin", "Брюшные"), ("Tail", "Хвост"), ("DorsalFin", "Спинные"), ("Extra", "Доп")]
        form = QtWidgets.QFormLayout()
        for key, label in rows:
            line = QtWidgets.QLineEdit(); line.setReadOnly(True)
            self.ui_inputs[key] = line
            btn = QtWidgets.QPushButton("Set")
            btn.clicked.connect(lambda checked=False, k=key: self.assign(k))
            h = QtWidgets.QHBoxLayout(); h.addWidget(line); h.addWidget(btn)
            form.addRow(QtWidgets.QLabel(label), h)
        layout.addLayout(form)

        btn_run = QtWidgets.QPushButton("🚀 ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ")
        btn_run.setMinimumHeight(60); btn_run.setStyleSheet("background-color: #d4a017; font-weight: bold;")
        btn_run.clicked.connect(self.execute)
        layout.addWidget(btn_run)

    def assign(self, key):
        sel = cmds.ls(sl=True)
        if not sel: return
        main = sel[0]; sym = self.manager.get_symmetric_control(main)
        roots = [main]
        if sym and cmds.objExists(sym): roots.append(sym)
        self.mapping[key] = roots
        self.ui_inputs[key].setText(", ".join(roots))
        self.ui_inputs[key].setStyleSheet("background-color: #2b4433; color: white;")

    def execute(self):
        all_proxies = []
        fin_anims = ["plavnik_normal_move", "plavnik_normal_move2", "plavnik_wait_pose", "plavnik_crowded"]
        other_anims = ["normal_move", "wait_pose"]

        for key, roots in self.mapping.items():
            # Выбираем список анимаций в зависимости от группы
            anims = fin_anims if key in ["SideFin", "SideFin2", "BellyFin"] else other_anims
            for r in roots:
                proxies = self.manager.process_spring_logic(r, anims, self.val_spring.value(), self.val_twist.value(), self.chk_loop.isChecked())
                all_proxies.extend(proxies)

        self.manager.final_bake(all_proxies)
        QtWidgets.QMessageBox.information(self, "Success", "Рыба полностью запечена по твоей методике!")
        self.accept()