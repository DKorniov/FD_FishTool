# -*- coding: utf-8 -*-
import maya.cmds as cmds

class BoneNamePreparing():
    def __init__(self, bone_map):
        self.meta_list = bone_map # Словарь из bone_map.json
        self.export_toggle = False

    def safe_parent(self, child, parent_node):
        if cmds.objExists(child) and cmds.objExists(parent_node):
            curr = cmds.listRelatives(child, parent=True)
            if curr and curr[0] == parent_node: return
            try: cmds.parent(child, parent_node)
            except: pass

    def execute(self):
        self.check_and_rename_bones()
        if self.export_toggle: 
            self.parent_for_export()
        else: 
            self.parent_for_default()

    def check_and_rename_bones(self):
        all_jnts = cmds.ls(type='joint') or []
        self.export_toggle = False
        
        for jnt in all_jnts:
            for rig_n, exp_n in self.meta_list.items():
                if jnt == rig_n:
                    cmds.rename(rig_n, exp_n)
                    self.export_toggle = True
                elif jnt == exp_n:
                    cmds.rename(exp_n, rig_n)
                    self.export_toggle = False

    def parent_for_export(self):            
        self.safe_parent('root_bone', 'joints')
        self.safe_parent('Fcrg_bn_grp', 'head')
        self.safe_parent('fclRig_lctr_grp', 'FKXHead_M')
        if cmds.objExists('MotionSystem'): 
            cmds.select('MotionSystem')
        print('FD_FishTool: Prepared for Export.')

    def parent_for_default(self):            
        self.safe_parent('Root_M', 'DeformationSystem')
        self.safe_parent('Fcrg_bn_grp', 'joints')
        self.safe_parent('fclRig_lctr_grp', 'Setup_grp')
        print('FD_FishTool: Back to Rig state.')