# -*- coding: utf-8 -*-
import maya.cmds as cmds

class BoneNamePreparing:
    def __init__(self, bone_map):
        """
        Принимает словарь bone_map напрямую (из main_window.py).
        Пример: {"Root_M": "root_bone", ...}
        """
        self.meta_list = bone_map
        self.export_toggle = False

    def safe_parent(self, child, parent_node):
        """Безопасное переподчинение с проверкой существования"""
        if cmds.objExists(child) and cmds.objExists(parent_node):
            curr = cmds.listRelatives(child, parent=True)
            if curr and curr[0] == parent_node:
                return
            try:
                cmds.parent(child, parent_node)
            except Exception as e:
                print(f"FD_FishTool [Parent Info]: {child} -> {parent_node} | {e}")

    def execute(self):
        """Точка входа: определяет режим, переименовывает и перепаковывает"""
        self.check_and_rename_bones()
        
        if self.export_toggle:
            self.parent_for_export()
        else:
            self.parent_for_default()

    def check_and_rename_bones(self):
        """
        Сканирует джоинты. 
        Если находит 'Root_M' -> переключает в Export Mode.
        Если находит 'root_bone' -> переключает в Rig Mode.
        """
        all_jnts = cmds.ls(type='joint')
        self.export_toggle = False
        
        # Инвертированный словарь для возврата к риг-именам
        reverse_map = {v: k for k, v in self.meta_list.items()}

        for jnt in all_jnts:
            # 1. Проверка на Rig -> Export
            if jnt in self.meta_list:
                new_name = self.meta_list[jnt]
                cmds.rename(jnt, new_name)
                self.export_toggle = True
            
            # 2. Проверка на Export -> Rig
            elif jnt in reverse_map:
                new_name = reverse_map[jnt]
                cmds.rename(jnt, new_name)
                self.export_toggle = False

    def parent_for_export(self):
        """Иерархия для экспорта (используем имена после переименования)"""
        # Т.к. мы в Export Mode, Root_M уже стал root_bone, Head_M стал head
        self.safe_parent('root_bone', 'joints')
        self.safe_parent('Fcrg_bn_grp', 'head')
        self.safe_parent('fclRig_lctr_grp', 'FKXHead_M')
        
        if cmds.objExists('MotionSystem'):
            cmds.select('MotionSystem')
        print("FD_FishTool: Mode [EXPORT]. Names and hierarchy updated.")

    def parent_for_default(self):
        """Иерархия для риггинга (используем исходные имена)"""
        # Т.к. мы вернулись в Rig Mode, root_bone стал обратно Root_M
        self._return_to_rig_structure()
        print("FD_FishTool: Mode [RIGGING]. Names and hierarchy restored.")

    def _return_to_rig_structure(self):
        """Возврат узлов в дефолтные группы рига"""
        self.safe_parent('Root_M', 'DeformationSystem')
        # Здесь можно добавить возврат групп локаторов, если они вынимались