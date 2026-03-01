# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om
import os

class FaceRigBuilder:
    """Логический движок для создания лицевого рига (Stage 4)."""
    def __init__(self):
        self.main_group = "fclRig_lctr_grp"
        self.setup_grp = "Setup_grp"

    def ensure_hierarchy(self):
        """Создает группы иерархии только при необходимости."""
        if not cmds.objExists(self.setup_grp):
            cmds.group(em=True, name=self.setup_grp)
        if not cmds.objExists(self.main_group):
            cmds.group(em=True, name=self.main_group, parent=self.setup_grp)

    def _apply_visual_settings(self, node, side):
        """Настраивает Drawing Overrides и Outliner Color."""
        cmds.setAttr(f"{node}.overrideEnabled", 1)
        cmds.setAttr(f"{node}.useOutlinerColor", 1)
        
        # 13=Red (R), 6=Blue (L), 17=Yellow (Center)
        if side == "right":
            cmds.setAttr(f"{node}.overrideColor", 13)
            cmds.setAttr(f"{node}.outlinerColor", 1, 0, 0)
        elif side == "left":
            cmds.setAttr(f"{node}.overrideColor", 6)
            cmds.setAttr(f"{node}.outlinerColor", 0, 0.6, 1)
        else: # center
            cmds.setAttr(f"{node}.overrideColor", 17)
            cmds.setAttr(f"{node}.outlinerColor", 1, 1, 0)

    def get_vertex_pos(self, vtx):
        """Получает точные WS-координаты вертекса."""
        sel = om.MSelectionList()
        sel.add(vtx)
        path, comp = sel.getComponent(0)
        it = om.MItMeshVertex(path, comp)
        p = it.position(om.MSpace.kWorld)
        return [p.x, p.y, p.z]

    def create_rig_unit(self, vtx, bone_name, pos_override=None):
        """Создает связку Locator (locAlign) -> Joint (mchFcrg)."""
        self.ensure_hierarchy()
        pos = pos_override if pos_override else self.get_vertex_pos(vtx)
        loc_name = bone_name.replace("mchFcrg_", "locAlign_fcrg_")
        
        if cmds.objExists(loc_name): cmds.delete(loc_name)
        
        loc = cmds.spaceLocator(name=loc_name)[0]
        cmds.xform(loc, t=(pos[0], pos[1], pos[2]), ws=True)
        cmds.parent(loc, self.main_group)
        
        # Визуал
        side = "center"
        if "right" in loc_name: side = "right"
        elif "left" in loc_name: side = "left"
        self._apply_visual_settings(loc, side)
        
        cmds.select(cl=True)
        joint = cmds.joint(name=bone_name)
        cmds.parent(joint, loc)
        cmds.setAttr(f"{joint}.t", 0, 0, 0)
        cmds.setAttr(f"{joint}.r", 0, 0, 0)
        cmds.setAttr(f"{joint}.jo", 0, 0, 0)
        return loc

    def mirror_unit(self, source_loc):
        """Зеркалит юнит на левую сторону: RotateX=180, Цвет=Blue."""
        if not cmds.objExists(source_loc): return None
        if "cent_" in source_loc or "teeth" in source_loc or "jaw" in source_loc:
            return None
            
        target_loc_name = source_loc.replace("right", "left")
        if cmds.objExists(target_loc_name): cmds.delete(target_loc_name)
            
        new_loc = cmds.duplicate(source_loc, name=target_loc_name, rc=True)[0]
        val_tx = cmds.getAttr(f"{new_loc}.tx")
        cmds.setAttr(f"{new_loc}.tx", -val_tx)
        cmds.setAttr(f"{new_loc}.rx", 180)
        self._apply_visual_settings(new_loc, "left")
        
        children = cmds.listRelatives(new_loc, children=True, type="joint") or []
        if children:
            mirrored_bone_name = target_loc_name.replace("locAlign_fcrg_", "mchFcrg_")
            cmds.rename(children[0], mirrored_bone_name)
        return new_loc

    def import_gui_library(self):
        if cmds.objExists("GUI_grp"): return True
        scripts_dir = cmds.internalVar(usd=True)
        lib_path = os.path.join(scripts_dir, "FD_FishTool", "data", "face_controls_library.ma")
        if os.path.exists(lib_path):
            cmds.file(lib_path, i=True, type="mayaAscii", rnn=True)
            return True
        return False