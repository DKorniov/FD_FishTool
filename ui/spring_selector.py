# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds

class SpringSelectorController(QtCore.QObject):
    def __init__(self, ui_tab, physics_manager, parent=None):
        super(SpringSelectorController, self).__init__(parent)
        self.ui = ui_tab
        self.physics_mgr = physics_manager
        
        # Список словарей с виджетами для каждой строки
        self.rows = [] 
        
        # Коннектим базовые кнопки
        self.ui.btn_add_chain.clicked.connect(self.add_chain_row)
        self.ui.btn_sm_execute.clicked.connect(self.execute_pipeline)
        self.ui.btn_sm_clean_anim.clicked.connect(self.clean_selected_chains_animation)
        
        # Первая строка создается автоматически
        self.add_chain_row()

    def add_chain_row(self):
        """Создает новую строку управления и добавляет её в интерфейс."""
        row_data = {}
        
        lbl = QtWidgets.QLabel(f"Цепочка:")
        
        combo = QtWidgets.QComboBox()
        combo.addItems(["Fin (Плавники)", "Body (Тело/Хвост)"])
        
        le = QtWidgets.QLineEdit()
        le.setReadOnly(True)
        le.setPlaceholderText("Выберите контролы...")
        
        btn_sel = QtWidgets.QPushButton("Выбрать")
        btn_sel.clicked.connect(lambda: self.assign_selection(row_data))
        
        btn_del = QtWidgets.QPushButton("❌")
        btn_del.setFixedWidth(30)
        btn_del.setToolTip("Удалить эту цепочку")
        btn_del.clicked.connect(lambda: self.remove_chain_row(row_data))
        
        row_idx = self.ui.gridLayout_sm_bones.rowCount()
        self.ui.gridLayout_sm_bones.addWidget(lbl, row_idx, 0)
        self.ui.gridLayout_sm_bones.addWidget(combo, row_idx, 1)
        self.ui.gridLayout_sm_bones.addWidget(le, row_idx, 2)
        self.ui.gridLayout_sm_bones.addWidget(btn_sel, row_idx, 3)
        self.ui.gridLayout_sm_bones.addWidget(btn_del, row_idx, 4)
        
        row_data.update({
            "widgets": [lbl, combo, le, btn_sel, btn_del],
            "combo": combo,
            "le": le,
            "chains": [] # ВАЖНО: Теперь это список списков (может содержать и левую, и правую цепь)
        })
        self.rows.append(row_data)

    def remove_chain_row(self, row_data):
        """Удаляет строку из интерфейса и из памяти."""
        if len(self.rows) <= 1:
            return 
            
        for widget in row_data["widgets"]:
            self.ui.gridLayout_sm_bones.removeWidget(widget)
            widget.deleteLater()
            
        if row_data in self.rows:
            self.rows.remove(row_data)

    def assign_selection(self, row_data):
        """Назначает выделенные объекты строке и автоматически ищет симметрию."""
        sel = cmds.ls(selection=True)
        if not sel:
            QtWidgets.QMessageBox.warning(self.ui, "Ошибка", "Выберите контролы в сцене!")
            return
        
        # 1. Формируем основную цепь из выделенного
        chain_main = sel
        chain_sym = []
        
        # 2. Проверяем, есть ли симметричные контролы для каждого выделенного
        for ctrl in chain_main:
            sym_ctrl = self.physics_mgr.get_symmetric_control(ctrl)
            if sym_ctrl and cmds.objExists(sym_ctrl):
                chain_sym.append(sym_ctrl)
                
        # 3. Сохраняем в строку как список цепочек
        chains_list = [chain_main]
        
        # Если симметричная цепь собралась полностью, добавляем и её как отдельную цепь
        if chain_sym and len(chain_sym) == len(chain_main):
            chains_list.append(chain_sym)
            
        row_data["chains"] = chains_list
        
        # 4. Обновляем текст в UI
        display_names = [n.split('|')[-1] for n in chain_main]
        text = ", ".join(display_names)
        
        if len(chains_list) > 1:
            text += " (+ Симметрия)"
            
        row_data["le"].setText(text)

    def execute_pipeline(self):
        """Просчет физики для всех заполненных цепочек."""
        valid_rows = [r for r in self.rows if r.get("chains")]
        
        if not valid_rows:
            QtWidgets.QMessageBox.warning(self.ui, "Ошибка", "Назначьте контролы хотя бы для одной цепочки!")
            return
        
        all_proxies = []
        proxy_anim_map = {}
        
        fin_anims = self.physics_mgr.FIN_ANIMS
        body_anims = self.physics_mgr.BODY_ANIMS

        # Проходим по каждой строке в UI
        for row in valid_rows:
            is_fin = row["combo"].currentIndex() == 0
            anims = fin_anims if is_fin else body_anims
            
            # Проходим по всем цепям внутри строки (Основная + Симметричная)
            for chain in row["chains"]:
                proxies = self.physics_mgr.process_spring_logic(
                    ctrl_chain=chain, 
                    anim_list=anims, 
                    spring_val=self.ui.val_spring.value(), 
                    twist_val=self.ui.val_twist.value(), 
                    is_loop=self.ui.chk_loop.isChecked()
                )
                
                all_proxies.extend(proxies)
                for p in proxies:
                    proxy_anim_map[p] = anims
                    
        if all_proxies:
            self.physics_mgr.final_bake(all_proxies, proxy_anim_map)
            QtWidgets.QMessageBox.information(self.ui, "Успех", f"Физика просчитана (с учетом симметрии)!")
            
            # Очищаем инпуты после успешного просчета
            for row in self.rows:
                row["chains"] = []
                row["le"].clear()
    
    def clean_selected_chains_animation(self):
        """Удаляет анимацию для всех контролов во всей иерархии выбранных цепей."""
        nodes_to_clean = []
        
        for row in self.rows:
            # chains содержит списки: [главная_цепь] или [главная_цепь, симметричная_цепь]
            for chain in row.get("chains", []):
                for root_ctrl in chain:
                    if not cmds.objExists(root_ctrl):
                        continue
                        
                    # Добавляем корневой контрол
                    nodes_to_clean.append(root_ctrl)
                    
                    # Используем логику PhysicsManager для поиска всей цепочки вниз
                    end_node = self.physics_mgr.get_chain_end(root_ctrl)
                    
                    # Собираем всех детей-трансформов
                    children = cmds.listRelatives(root_ctrl, ad=True, type="transform", fullPath=True) or []
                    
                    # Проходим по детям в обратном порядке (как в PhysicsManager), 
                    # чтобы собрать цепь от корня к кончику
                    for child in children[::-1]:
                        shapes = cmds.listRelatives(child, shapes=True) or []
                        # Проверяем, что это контроллер (имеет nurbsCurve)
                        if any(cmds.nodeType(s) == "nurbsCurve" for s in shapes):
                            nodes_to_clean.append(child)
                            # Если дошли до конца (Gimble), прекращаем сбор
                            if child == end_node:
                                break
        
        if not nodes_to_clean:
            QtWidgets.QMessageBox.information(self.ui, "Инфо", "В селекторе нет назначенных цепочек для очистки.")
            return

        # Убираем дубликаты (на случай пересечения иерархий)
        nodes_to_clean = list(set(nodes_to_clean))
        
        res = cmds.confirmDialog(
            title='Очистка цепочек | FD_FishTool',
            message=f'Вы уверены, что хотите сбросить анимацию для {len(nodes_to_clean)} контролов (все выбранные цепи целиком)?',
            button=['Да', 'Отмена'], defaultButton='Отмена', cancelButton='Отмена'
        )
        
        if res == 'Да':
            from FD_FishTool.core.anim_handler import AnimationHandler
            cmds.undoInfo(openChunk=True)
            try:
                # Вызываем сброс для расширенного списка нод
                AnimationHandler.reset_nodes_animation(nodes_to_clean)
                cmds.inViewMessage(amg="Анимация выбранных цепочек (иерархий) очищена", pos="midCenter", fade=True)
            finally:
                cmds.undoInfo(closeChunk=True)