# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om
import os
import re

class FaceRigBuilder:
    def __init__(self):
        self.main_group = "fclRig_lctr_grp"
        self.setup_grp = "Setup_grp"
        # Полный список контролов для манипуляций
        self.all_test_ctrls = [
            "R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid", 
            "Emote", "Sync", "Jaw", "gui_teeth", "Lwr_Lip", "Upr_Lip"
        ]
        self.eyelid_group = ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid"]
        self.lip_group = ["Lwr_Lip", "Upr_Lip"]

    def ensure_hierarchy(self):
        if not cmds.objExists(self.setup_grp):
            cmds.group(em=True, name=self.setup_grp)
        if not cmds.objExists(self.main_group):
            cmds.group(em=True, name=self.main_group, parent=self.setup_grp)

    def _apply_visual_settings(self, node, side):
        cmds.setAttr(f"{node}.overrideEnabled", 1)
        cmds.setAttr(f"{node}.useOutlinerColor", 1)
        if side == "right":
            cmds.setAttr(f"{node}.overrideColor", 13) # Red
            cmds.setAttr(f"{node}.outlinerColor", 1, 0, 0)
        elif side == "left":
            cmds.setAttr(f"{node}.overrideColor", 6) # Blue
            cmds.setAttr(f"{node}.outlinerColor", 0, 0.6, 1)
        else: # center
            cmds.setAttr(f"{node}.overrideColor", 17) # Yellow
            cmds.setAttr(f"{node}.outlinerColor", 1, 1, 0)

    def get_vertex_pos(self, vtx):
        sel = om.MSelectionList()
        sel.add(vtx)
        path, comp = sel.getComponent(0)
        it = om.MItMeshVertex(path, comp)
        p = it.position(om.MSpace.kWorld)
        return [p.x, p.y, p.z]

    def create_rig_unit(self, vtx, bone_name, pos_override=None):
        self.ensure_hierarchy()
        pos = pos_override if pos_override else self.get_vertex_pos(vtx)
        loc_name = bone_name.replace("mchFcrg_", "locAlign_fcrg_")
        if cmds.objExists(loc_name): cmds.delete(loc_name)
        loc = cmds.spaceLocator(name=loc_name)[0]
        cmds.xform(loc, t=(pos[0], pos[1], pos[2]), ws=True)
        cmds.parent(loc, self.main_group)
        side = "right" if "right" in loc_name else ("left" if "left" in loc_name else "center")
        self._apply_visual_settings(loc, side)
        cmds.select(cl=True)
        joint = cmds.joint(name=bone_name)
        cmds.parent(joint, loc)
        for attr in [".t", ".r", ".jo"]: cmds.setAttr(joint + attr, 0, 0, 0)
        return loc

    def mirror_unit(self, source_loc):
        if not cmds.objExists(source_loc) or any(x in source_loc for x in ["cent_", "teeth", "jaw"]): return
        target = source_loc.replace("right", "left")
        if cmds.objExists(target): cmds.delete(target)
        new_loc = cmds.duplicate(source_loc, name=target, rc=True)[0]
        cmds.setAttr(f"{new_loc}.tx", -cmds.getAttr(f"{new_loc}.tx"))
        cmds.setAttr(f"{new_loc}.rx", 180)
        self._apply_visual_settings(new_loc, "left")
        child = cmds.listRelatives(new_loc, children=True, type="joint")
        if child: cmds.rename(child[0], target.replace("locAlign_fcrg_", "mchFcrg_"))

    # --- ЗЕРКАЛИРОВАНИЕ ПОЛОЖЕНИЯ КОСТЕЙ (Face_drivens_mirror.py) ---
    def mirror_drivens_logic(self):
        """Зеркалирует положение mch костей с правой стороны на левую."""
        all_joints = cmds.ls('mchFcrg*right*', type='joint')
        if not all_joints:
            cmds.warning("No right-side mechanical joints found.")
            return

        for start_bone in all_joints:
            end_bone = start_bone.replace('right', 'left')
            if not cmds.objExists(end_bone): continue
            
            # Получаем позицию и вращение
            ws_pos = cmds.xform(start_bone, q=True, t=True, ws=True)
            os_rot = cmds.xform(start_bone, q=True, r=True, os=True)
            
            # Применяем к левой стороне с инверсией X
            cmds.xform(end_bone, t=(-ws_pos[0], ws_pos[1], ws_pos[2]), ws=True)
            cmds.xform(end_bone, ro=os_rot, os=True)
        
        print("> AI: Drivens positions mirrored (Right to Left).")

    # --- ТЕСТОВАЯ АНИМАЦИЯ И ОЧИСТКА ---
    def clean_test_animation(self):
        """Удаляет ключи и возвращает атрибуты в 0."""
        existing = [c for c in self.all_test_ctrls if cmds.objExists(c)]
        if not existing: return
        
        cmds.cutKey(existing, s=True)
        for ctrl in existing:
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                if cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    try: cmds.setAttr(f"{ctrl}.{attr}", 0)
                    except: pass
        print("> AI: Test animation cleaned. Attributes reset to 0.")

    def run_context_test_animation(self):
        self.clean_test_animation()
        sel = cmds.ls(sl=True)
        if not sel: return
        
        if any(c in sel for c in self.eyelid_group): self._anim_eyelids()
        elif any(c in sel for c in self.lip_group): self._anim_lips()
        elif "Sync" in sel: self._anim_sync()
        elif "Emote" in sel: self._anim_emote()
        elif "Jaw" in sel: self._anim_jaw()
        elif "gui_teeth" in sel: self._anim_teeth()

    def _anim_eyelids(self):
        ctrls = [c for c in self.eyelid_group if cmds.objExists(c)]
        cmds.setKeyframe(ctrls, t=1)
        cmds.currentTime(3); cmds.move(0, 4.479, 0, ["R_Upp_EyeLid", "L_Upp_EyeLid"], r=True, os=True, wd=True); cmds.setKeyframe(ctrls, t=3)
        cmds.currentTime(5); cmds.move(0, 2.246, 0, ["L_Lwr_EyeLid", "R_Lwr_EyeLid"], r=True, os=True, wd=True); cmds.setKeyframe(ctrls, t=5)
        cmds.currentTime(7); cmds.move(0, -3.305, 0, ["R_Upp_EyeLid", "L_Upp_EyeLid"], r=True, os=True, wd=True); cmds.setKeyframe(ctrls, t=7)
        cmds.currentTime(9); cmds.move(0, -4.293, 0, ["L_Lwr_EyeLid", "R_Lwr_EyeLid"], r=True, os=True, wd=True); cmds.setKeyframe(ctrls, t=9)

    def _anim_sync(self):
        c = "Sync"
        cmds.setKeyframe(c, t=1)
        cmds.currentTime(3); cmds.move(0, -2.780, 0, c, r=True); cmds.setKeyframe(c, t=3)
        cmds.currentTime(5); cmds.move(0, 3.426, 0, c, r=True); cmds.setKeyframe(c, t=5)
        cmds.currentTime(6); cmds.setAttr(f"{c}.tx", 0); cmds.setAttr(f"{c}.ty", 0); cmds.setKeyframe(c, at=["tx", "ty"], t=6)
        cmds.currentTime(8); cmds.move(4.928, 0, 0, c, r=True); cmds.setKeyframe(c, t=8)
        cmds.currentTime(10); cmds.move(-13.599, 0, 0, c, r=True); cmds.setKeyframe(c, t=10)

    def _anim_lips(self):
        ctrls = [c for c in self.lip_group if cmds.objExists(c)]
        cmds.setKeyframe(ctrls, t=1)
        cmds.currentTime(3); cmds.move(0, 4.259, 0, ctrls, r=True); cmds.setKeyframe(ctrls, t=3)
        cmds.currentTime(5); cmds.move(0, -7.169, 0, ctrls, r=True); cmds.setKeyframe(ctrls, t=5)

    def _anim_emote(self):
        c = "Emote"; cmds.setKeyframe(c, t=1)
        cmds.currentTime(3); cmds.move(0, 4.200, 0, c, r=True); cmds.setKeyframe(c, t=3)
        cmds.currentTime(5); cmds.move(0, -7.427, 0, c, r=True); cmds.setKeyframe(c, t=5)

    def _anim_jaw(self):
        c = "Jaw"; cmds.setKeyframe(c, t=1)
        cmds.currentTime(3); cmds.move(6.676, 0, 0, c, r=True); cmds.setKeyframe(c, t=3)
        cmds.currentTime(5); cmds.move(-5.456, 0, 0, c, r=True); cmds.setKeyframe(c, t=5)

    def _anim_teeth(self):
        c = "gui_teeth"; cmds.setKeyframe(c, t=1)
        cmds.currentTime(3); cmds.move(0, 3.015, 0, c, r=True); cmds.setKeyframe(c, t=3)
        cmds.currentTime(4); cmds.setAttr(f"{c}.ty", 0); cmds.setKeyframe(c, t=4)
        cmds.currentTime(6); cmds.move(5.268, 0, 0, c, r=True); cmds.setKeyframe(c, t=6)
        cmds.currentTime(8); cmds.move(-8.072, 0, 0, c, r=True); cmds.setKeyframe(c, t=8)

    def import_gui_library(self):
        if cmds.objExists("GUI_grp"): return True
        scripts_dir = cmds.internalVar(usd=True)
        lib_path = os.path.join(scripts_dir, "FD_FishTool", "data", "face_controls_library.ma")
        if os.path.exists(lib_path):
            cmds.file(lib_path, i=True, type="mayaAscii", rnn=True)
            return True
        return False