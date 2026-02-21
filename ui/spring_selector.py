# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds
from springmagic import core as sm_core

class SpringSelectorWindow(QtWidgets.QDialog):
    def __init__(self, manager, parent=None):
        super(SpringSelectorWindow, self).__init__(parent)
        self.manager = manager
        self.setWindowTitle("SpringMagic HumanIK Selector")
        self.setMinimumWidth(500)
        self.mapping = {}
        self.ui_inputs = {}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        cfg_group = QtWidgets.QGroupBox("Параметры SpringMagic")
        cfg_lay = QtWidgets.QGridLayout(cfg_group)
        self.val_spring = QtWidgets.QDoubleSpinBox(); self.val_spring.setValue(0.5)
        self.val_twist = QtWidgets.QDoubleSpinBox(); self.val_twist.setValue(0.2)
        self.chk_loop = QtWidgets.QCheckBox("Loop"); self.chk_loop.setChecked(True)
        cfg_lay.addWidget(QtWidgets.QLabel("Spring:"), 0, 0); cfg_lay.addWidget(self.val_spring, 0, 1)
        cfg_lay.addWidget(QtWidgets.QLabel("Twist:"), 0, 2); cfg_lay.addWidget(self.val_twist, 0, 3)
        cfg_lay.addWidget(self.chk_loop, 1, 0); layout.addWidget(cfg_group)

        rows = [("SideFin", "Боковые"), ("HeadFin", "Головные"), ("SideFin2", "Боковые 2"),
                ("BellyFin", "Брюшные"), ("DorsalFin", "Спинные"), ("Tail", "Хвост"), ("Extra", "Доп")]
        
        form = QtWidgets.QFormLayout()
        for key, label in rows:
            line = QtWidgets.QLineEdit(); line.setReadOnly(True); line.setPlaceholderText("Не назначено")
            self.ui_inputs[key] = line
            btn = QtWidgets.QPushButton("Set")
            # Фикс KeyError: передаем ключ через именованный аргумент lambda
            btn.clicked.connect(lambda k=key: self.assign(k))
            h = QtWidgets.QHBoxLayout(); h.addWidget(line); h.addWidget(btn)
            form.addRow(QtWidgets.QLabel(label), h)
        layout.addLayout(form)

        btn_run = QtWidgets.QPushButton("🚀 ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ ФИЗИКИ")
        btn_run.setMinimumHeight(60)
        btn_run.setStyleSheet("background-color: #d4a017; font-weight: bold; color: black;")
        btn_run.clicked.connect(self.execute_pipeline)
        layout.addWidget(btn_run)

    def assign(self, key):
        sel = cmds.ls(sl=True)
        if not sel: return
        main = sel[0]
        sym = self.manager.get_symmetric_control(main)
        roots = [main]
        if sym and cmds.objExists(sym): roots.append(sym)
        self.mapping[key] = roots
        self.ui_inputs[key].setText(", ".join(roots))
        self.ui_inputs[key].setStyleSheet("background-color: #2b4433; color: white;")

    def execute_pipeline(self):
        if not self.mapping: return
        
        # 1-3. Локаторы и Bind ВСЕЙ цепочки
        all_roots = []
        for key in self.mapping:
            for r in self.mapping[key]:
                self.manager.setup_spring_target(r)
                # ФИКС: Выделяем всю цепь и жмем Bind
                self.manager.bind_chain_sequence(r)
                all_roots.append(r)
        
        # 4-6. Плавники (Side/Side2/Belly)
        fin_keys = ["SideFin", "SideFin2", "BellyFin"]
        fin_proxies = []
        for k in fin_keys:
            if k in self.mapping:
                for r in self.mapping[k]:
                    fin_proxies.extend(cmds.ls(f"{r}*_SpringProxy"))
        
        if fin_proxies:
            anims = ["plavnik_normal_move", "plavnik_normal_move2", "plavnik_wait_pose", "plavnik_crowded"]
            self.manager.set_tech_keys(fin_proxies, anims)
            cmds.select(fin_proxies)
            self.manager.apply_sm_to_selection(self.val_spring.value(), self.val_twist.value(), 
                                               self.chk_loop.isChecked(), anims)

        # 7-8. Остальное (Tail/Dorsal/Extra)
        other_keys = ["HeadFin", "DorsalFin", "Tail", "Extra"]
        other_proxies = []
        for k in other_keys:
            if k in self.mapping:
                for r in self.mapping[k]:
                    other_proxies.extend(cmds.ls(f"{r}*_SpringProxy"))
        
        if other_proxies:
            anims = ["normal_move", "wait_pose"]
            self.manager.set_tech_keys(other_proxies, anims)
            cmds.select(other_proxies)
            self.manager.apply_sm_to_selection(self.val_spring.value(), self.val_twist.value(), 
                                               self.chk_loop.isChecked(), anims)

        # 9. Финальный Bake
        max_end = 0
        for name, r in self.manager.anim_ranges.items(): max_end = max(max_end, r[1])
        cmds.playbackOptions(min=0, max=max_end, ast=0, aet=max_end)
        all_p = cmds.ls("*_SpringProxy")
        if all_p:
            cmds.select(all_p)
            sm_core.clearBind(0, max_end)
        
        QtWidgets.QMessageBox.information(self, "Готово", "Цепочки запечены.")
        self.accept()