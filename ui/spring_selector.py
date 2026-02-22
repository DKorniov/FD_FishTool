# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds

class SpringSelectorWindow(QtWidgets.QDialog):
    def __init__(self, physics_manager, parent=None):
        """Окно селектора физики, работающее через PhysicsManager."""
        super(SpringSelectorWindow, self).__init__(parent)
        self.manager = physics_manager
        self.setWindowTitle("SpringMagic Physics Selector | v6")
        self.setMinimumWidth(500)
        self.mapping = {}
        self.ui_inputs = {}
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Настройки SpringMagic
        cfg_group = QtWidgets.QGroupBox("Параметры симуляции")
        cfg_lay = QtWidgets.QGridLayout(cfg_group)
        self.val_spring = QtWidgets.QDoubleSpinBox(); self.val_spring.setValue(0.5)
        self.val_twist = QtWidgets.QDoubleSpinBox(); self.val_twist.setValue(0.2)
        self.chk_loop = QtWidgets.QCheckBox("Loop"); self.chk_loop.setChecked(True)
        
        cfg_lay.addWidget(QtWidgets.QLabel("Spring:"), 0, 0); cfg_lay.addWidget(self.val_spring, 0, 1)
        cfg_lay.addWidget(QtWidgets.QLabel("Twist:"), 0, 2); cfg_lay.addWidget(self.val_twist, 0, 3)
        cfg_lay.addWidget(self.chk_loop, 1, 0)
        layout.addWidget(cfg_group)

        # Категории контролов
        rows = [("SideFin", "Боковые"), ("HeadFin", "Головные"), ("BellyFin", "Брюшные"), 
                ("DorsalFin", "Спинные"), ("Tail", "Хвост"), ("Extra", "Доп")]
        
        form = QtWidgets.QFormLayout()
        for key, label in rows:
            line = QtWidgets.QLineEdit(); line.setReadOnly(True); line.setPlaceholderText("Не назначено")
            self.ui_inputs[key] = line
            btn = QtWidgets.QPushButton("Set")
            # Используем *args, чтобы поглотить сигнал checked и избежать KeyError
            btn.clicked.connect(lambda *args, k=key: self.assign(k))
            h = QtWidgets.QHBoxLayout(); h.addWidget(line); h.addWidget(btn)
            form.addRow(QtWidgets.QLabel(label), h)
        layout.addLayout(form)

        # Кнопка запуска
        btn_run = QtWidgets.QPushButton("🚀 ЗАПУСТИТЬ ПОЛНЫЙ ЦИКЛ ФИЗИКИ")
        btn_run.setMinimumHeight(60); btn_run.setStyleSheet("background-color: #d4a017; font-weight: bold; color: black;")
        btn_run.clicked.connect(self.execute_physics)
        layout.addWidget(btn_run)

    def assign(self, key):
        """Привязка выделенных контролов к категории."""
        sel = cmds.ls(sl=True, long=True)
        if not sel: return
        main = sel[0]
        sym = self.manager.get_symmetric_control(main)
        roots = [main]
        if sym and cmds.objExists(sym): roots.append(sym)
        self.mapping[key] = roots
        self.ui_inputs[key].setText(", ".join([r.split('|')[-1] for r in roots]))
        self.ui_inputs[key].setStyleSheet("background-color: #2b4433; color: white;")

    def execute_physics(self):
        """Последовательный запуск симуляции через PhysicsManager."""
        if not self.mapping: 
            QtWidgets.QMessageBox.warning(self, "Внимание", "Назначьте хотя бы одну цепочку!")
            return
        
        # 1. Подготовка: LAT и Bind
        for key in self.mapping:
            for root in self.mapping[key]:
                self.manager.setup_spring_target(root)
                self.manager.bind_chain_sequence(root)
        
        # 2. Симуляция Плавников (Side/Belly)
        fin_keys = ["SideFin", "BellyFin"]
        fin_anims = ["plavnik_normal_move", "plavnik_normal_move2", "plavnik_wait_pose", "plavnik_crowded"]
        self._simulate_group_logic(fin_keys, fin_anims)

        # 3. Остальное (Tail/Dorsal/Extra)
        other_keys = ["HeadFin", "DorsalFin", "Tail", "Extra"]
        other_anims = ["normal_move", "wait_pose"]
        self._simulate_group_logic(other_keys, other_anims)

        # 4. Финальное запекание
        self.manager.final_bake_all()
        QtWidgets.QMessageBox.information(self, "Готово", "Полный цикл физики завершен.")
        self.accept()

    def _simulate_group_logic(self, keys, anims):
        """Сбор прокси и запуск симуляции."""
        proxies = []
        for k in keys:
            if k in self.mapping:
                for r in self.mapping[k]:
                    short = r.split(':')[-1].split('|')[-1]
                    found = cmds.ls(f"*{short}*_SpringProxy", long=True)
                    proxies.extend(found)
        
        if proxies:
            proxies = list(set(proxies))
            self.manager.set_tech_keys(proxies, anims)
            cmds.select(proxies, replace=True)
            self.manager.apply_sm_to_selection(
                self.val_spring.value(), 
                self.val_twist.value(), 
                self.chk_loop.isChecked(), 
                anims
            )