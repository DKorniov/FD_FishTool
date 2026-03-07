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
        Назначает выделенные контролы в группу.
        Если выделен 1 контрол - логика авто-цепи (поиск детей).
        Если выделено >1 контролов - ручная цепь в порядке выделения.
        """
        # Используем orderedSelection, чтобы гарантированно получить порядок кликов пользователя
        sel = cmds.ls(orderedSelection=True) or cmds.ls(selection=True)
        if not sel:
            return
        
        is_manual_chain = len(sel) > 1
        
        primary_chain = sel
        sym_chain = []
        
        # Поиск симметрии
        if is_manual_chain:
            # Для ручной цепи проверяем симметрию каждого элемента в порядке выделения
            for ctrl in primary_chain:
                sym = self.physics_mgr.get_symmetric_control(ctrl)
                if sym and cmds.objExists(sym):
                    sym_chain.append(sym)
                else:
                    # Если хотя бы у одного звена нет пары, симметричная цепь инвалидируется
                    sym_chain = []
                    break
        else:
            # Стандартная логика для 1 корневого контрола
            root_ctrl = primary_chain[0]
            sym = self.physics_mgr.get_symmetric_control(root_ctrl)
            if sym and cmds.objExists(sym):
                sym_chain = [sym]

        # Сохраняем цепи в mapping
        chains = [primary_chain]
        if sym_chain:
            chains.append(sym_chain)
            
        self.mapping[key] = chains
        
        # Обновляем текст в UI
        if is_manual_chain:
            display_text = f"Chain: {primary_chain[0]}... ({len(primary_chain)} ctrls)"
            if sym_chain:
                display_text += " + Sym"
        else:
            display_text = primary_chain[0]
            if sym_chain:
                display_text += f" + {sym_chain[0]} (Auto-Sym)"
                
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
        proxy_anim_map = {}
        
        fin_anims = ["plavnik_normal_move", "plavnik_normal_move2", "plavnik_wait_pose", "plavnik_crowded"]
        other_anims = ["normal_move", "wait_pose"]

        for key, chains in self.mapping.items():
            anims = fin_anims if key in ["SideFin", "SideFin2", "BellyFin", "HeadFin"] else other_anims
            
            for chain in chains:
                # Передаем цепь целиком в аргумент ctrl_chain
                proxies = self.physics_mgr.process_spring_logic(
                    ctrl_chain=chain, 
                    anim_list=anims, 
                    spring_val=self.val_spring.value(), 
                    twist_val=self.val_twist.value(), 
                    is_loop=self.chk_loop.isChecked()
                )
                all_proxies.extend(proxies)
                
                for p in proxies:
                    proxy_anim_map[p] = anims

        self.physics_mgr.final_bake(all_proxies, proxy_anim_map)
        
        QtWidgets.QMessageBox.information(self, "Success", "Все физические циклы запечены и очищены.")
        self.accept()