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
    # Золотой набор анимаций для определения границ запекания
    IMPORTANT_ANIMS = [
        "normal_move", 
        "plavnik_normal_move", 
        "plavnik_normal_move2", 
        "wait_pose", 
        "plavnik_wait_pose", 
        "plavnik_crowded"
    ]

    def __init__(self, config_manager):
        self.cfg = config_manager
        paths = self.cfg.load_json("paths.json")
        self.etalon_path = paths.get("animation_data", "")
        self.anim_ranges = self._parse_etalon()

    def _parse_etalon(self):
        """Парсинг эталонного файла animation.txt."""
        ranges = {}
        if not self.etalon_path or not os.path.exists(self.etalon_path): 
            return ranges
        try:
            with open(self.etalon_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        ranges[parts[2]] = (float(parts[0]), float(parts[1]))
        except Exception as e:
            print(f"PhysicsManager: Ошибка чтения эталона: {e}")
        return ranges

    def get_symmetric_control(self, ctrl):
        """Определяет симметричную пару для Advanced Skeleton."""
        if "_R" in ctrl: return ctrl.replace("_R", "_L")
        if "_L" in ctrl: return ctrl.replace("_L", "_R")
        return None

    def get_chain_end(self, root):
        """Ищет кончик цепи (Gimble узел)."""
        children = cmds.listRelatives(root, ad=True, type="transform", fullPath=True) or []
        ctrls = [c for c in children if cmds.attributeQuery("Gimble_Visible", node=c, exists=True)]
        return ctrls[0] if ctrls else (children[0] if children else root)

    def create_aligned_locator(self, target_node):
        """Реализация LAT (Locator Alignment Tool)."""
        side_mult = -1.0 if "_L" in target_node else 1.0
        loc_name = "locAlign_" + target_node.split('|')[-1]
        
        if cmds.objExists(loc_name): cmds.delete(loc_name)
        
        loc = cmds.spaceLocator(n=loc_name)[0]
        # Выравнивание через временный констрейнт
        temp_pc = cmds.parentConstraint(target_node, loc)[0]
        cmds.delete(temp_pc)
        
        # Смещение WD 1.25
        cmds.move(1.25 * side_mult, 0, 0, loc, r=True, os=True, wd=True)
        return loc

    def process_spring_logic(self, root_ctrl, anim_list, spring_val, twist_val, is_loop):
        """
        Полный цикл физики: LAT -> Bind -> CopyKeys -> Apply.
        """
        end_node = self.get_chain_end(root_ctrl)
        loc = self.create_aligned_locator(end_node)
        
        # Сбор цепи nurbsCurve от выделенного контрола вниз
        chain = [root_ctrl]
        children = cmds.listRelatives(root_ctrl, ad=True, type="transform", fullPath=True) or []
        for child in children[::-1]:
            shapes = cmds.listRelatives(child, shapes=True) or []
            if any(cmds.nodeType(s) == "nurbsCurve" for s in shapes):
                chain.append(child)
                if child == end_node: break
        chain.append(loc)
        
        # Создание прокси
        py_chain = [pm.PyNode(n) for n in chain]
        pm.select(py_chain)
        sm_core.bindControls()
        
        proxy_chain = [n.name() + "_SpringProxy" for n in py_chain]
        
        for anim_name in anim_list:
            if anim_name not in self.anim_ranges: continue
            start, end = self.anim_ranges[anim_name]
            safe_frame = start - 30 
            
            # Технические кадры и Padding
            for f in [safe_frame, start-2, start-1, start, end, end+1]:
                cmds.currentTime(f)
                if f != safe_frame:
                    # Копирование позы из безопасного кадра
                    cmds.copyKey(proxy_chain, time=(safe_frame, safe_frame))
                    cmds.pasteKey(proxy_chain, time=(f, f), option="merge")
                else:
                    cmds.setKeyframe(proxy_chain, attribute='rotate')

            # Расчет SpringMagic
            cmds.playbackOptions(min=start, max=end, ast=start, aet=end)
            sm_settings = sm_core.Spring(ratio=1.0-spring_val, twistRatio=1.0-twist_val)
            sm_mgr = sm_core.SpringMagic(start, end, isLoop=is_loop)
            
            sm_objs = [pm.PyNode(p) for p in proxy_chain]
            sm_core.SpringMagicMaya(sm_objs, sm_settings, sm_mgr)

        return proxy_chain

    def final_bake(self, all_proxies):
        """Запекание в полезном диапазоне 9-189."""
        if not all_proxies: return
        starts, ends = [], []
        for name in self.IMPORTANT_ANIMS:
            if name in self.anim_ranges:
                starts.append(self.anim_ranges[name][0])
                ends.append(self.anim_ranges[name][1])
        
        if not starts: return
        f_start, f_end = min(starts) - 1, max(ends) + 1
        
        cmds.playbackOptions(min=f_start, max=f_end, ast=f_start, aet=f_end)
        pm.select([pm.PyNode(p) for p in all_proxies])
        sm_core.clearBind(f_start, f_end)
        
        locs = cmds.ls("locAlign_*")
        if locs: cmds.delete(locs)