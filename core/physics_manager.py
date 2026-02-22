# -*- coding: utf-8 -*-
import maya.cmds as cmds
import os
import pymel.core as pm

try:
    from springmagic import core as sm_core
except ImportError:
    sm_core = None
    cmds.warning("FD_FishTool: SpringMagic core не найден!")

class PhysicsManager:
    IMPORTANT_ANIMS = [
        "normal_move", "plavnik_normal_move", "plavnik_normal_move2", 
        "wait_pose", "plavnik_wait_pose", "plavnik_crowded"
    ]

    def __init__(self, config_manager):
        self.cfg = config_manager
        paths = self.cfg.load_json("paths.json")
        self.etalon_path = paths.get("animation_data", "")
        self.anim_ranges = self._parse_etalon()

    def _parse_etalon(self):
        ranges = {}
        if not self.etalon_path or not os.path.exists(self.etalon_path): 
            return ranges
        try:
            with open(self.etalon_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        ranges[parts[2]] = (float(parts[0]), float(parts[1]))
        except: pass
        return ranges

    def get_symmetric_control(self, ctrl):
        if "_R" in ctrl: return ctrl.replace("_R", "_L")
        if "_L" in ctrl: return ctrl.replace("_L", "_R")
        return None

    def get_chain_end(self, root):
        children = cmds.listRelatives(root, ad=True, type="transform", fullPath=True) or []
        ctrls = [c for c in children if cmds.attributeQuery("Gimble_Visible", node=c, exists=True)]
        return ctrls[0] if ctrls else (children[0] if children else root)

    def setup_spring_target(self, root_ctrl):
        """LAT - Locator Alignment Tool: Создание и смещение локатора на 1.254."""
        side_mult = -1.0 if "_L" in root_ctrl else 1.0
        end_node = self.get_chain_end(root_ctrl)
        short_name = end_node.split('|')[-1]
        loc_name = f"locAlign_{short_name}"
        
        if cmds.objExists(loc_name): cmds.delete(loc_name)
        
        loc = cmds.spaceLocator(n=loc_name)[0]
        temp_pc = cmds.parentConstraint(end_node, loc)[0]
        cmds.delete(temp_pc)
        
        cmds.move(1.254053 * side_mult, 0, 0, loc, r=True, os=True, wd=True)
        return loc

    def bind_chain_sequence(self, root_ctrl):
        if not sm_core: return
        end_node = self.get_chain_end(root_ctrl)
        short_end = end_node.split('|')[-1]
        loc_name = f"locAlign_{short_end}"

        chain = [root_ctrl]
        children = cmds.listRelatives(root_ctrl, ad=True, type="transform", fullPath=True) or []
        for child in children[::-1]:
            shapes = cmds.listRelatives(child, shapes=True) or []
            if any(cmds.nodeType(s) == "nurbsCurve" for s in shapes):
                chain.append(child)
                if child == end_node: break
        
        if cmds.objExists(loc_name): chain.append(loc_name)
        
        pm_chain = [pm.PyNode(n) for n in chain if cmds.objExists(n)]
        pm.select(pm_chain)
        sm_core.bindControls()

    def set_tech_keys(self, proxy_bones, anim_list):
        """Установка ключей Padding и выполнение Copy/Paste Merge из вашего лога."""
        if not proxy_bones: return
        
        ref_frames = {
            "plavnik_normal_move": 40, "plavnik_normal_move2": 70, 
            "plavnik_wait_pose": 130, "plavnik_crowded": 160, 
            "normal_move": 10, "wait_pose": 100
        }

        for anim in anim_list:
            if anim not in self.anim_ranges: continue
            s, e = self.anim_ranges[anim]
            ref_f = ref_frames.get(anim, s)

            # 1. Простановка ключей на границах
            for f in [s-1, s, e, e+1]:
                cmds.setKeyframe(proxy_bones, time=(f, f), attribute='rotate')

            # 2. Логика Copy/Paste Merge из Mel-лога
            cmds.copyKey(proxy_bones, time=(ref_f, ref_f))
            cmds.pasteKey(proxy_bones, time=(s, s), option="merge")
            cmds.pasteKey(proxy_bones, time=(e, e), option="merge")

    def apply_sm_to_selection(self, spring, twist, loop, anim_list):
        if not sm_core: return
        objs_str = cmds.ls(sl=True, long=True)
        if not objs_str: return
        
        objs_pm = [pm.PyNode(o) for o in objs_str if cmds.objExists(o)]
        if not objs_pm: return

        sm_settings = sm_core.Spring(ratio=1.0-spring, twistRatio=1.0-twist)
        for anim in anim_list:
            if anim in self.anim_ranges:
                s, e = self.anim_ranges[anim]
                cmds.playbackOptions(min=s, max=e, ast=s, aet=e)
                sm_mgr = sm_core.SpringMagic(s, e, isLoop=loop)
                try:
                    sm_core.SpringMagicMaya(objs_pm, sm_settings, sm_mgr)
                except Exception as ex:
                    print(f"FD_FishTool SM Error on {anim}: {ex}")

    def final_bake_all(self):
        if not sm_core: return
        starts = [self.anim_ranges[n][0] for n in self.IMPORTANT_ANIMS if n in self.anim_ranges]
        ends = [self.anim_ranges[n][1] for n in self.IMPORTANT_ANIMS if n in self.anim_ranges]
        if not starts or not ends: return

        f_start, f_end = min(starts) - 1, max(ends) + 1
        all_p = [pm.PyNode(p) for p in cmds.ls("*_SpringProxy", long=True)]
        if all_p:
            pm.select(all_p)
            sm_core.clearBind(f_start, f_end)
        
        locs = cmds.ls("locAlign_*", long=True)
        if locs: cmds.delete(locs)