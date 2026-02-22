# -*- coding: utf-8 -*-
import maya.cmds as cmds
import os
import json
import maya.mel as mel
from PySide2 import QtWidgets, QtCore

# Импорт оригинальных компонентов Studio Library
try:
    import mutils
    from mutils.animation import Animation, PasteOption
    from mutils.selectionset import SelectionSet
except ImportError:
    cmds.warning("FD_FishTool: Пакет 'mutils' не найден!")

# Импорт ядра SpringMagic
try:
    from springmagic import core as sm_core
except ImportError:
    cmds.warning("FD_FishTool: SpringMagic core не найден!")

class AnimManager:
    def __init__(self, config_manager):
        self.cfg = config_manager
        paths = self.cfg.load_json("paths.json")
        self.etalon_path = paths.get("animation_data", "")
        self.lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "studio_lib")
        self.anim_ranges = self._parse_etalon()

    def _parse_etalon(self):
        ranges = {}
        if not self.etalon_path or not os.path.exists(self.etalon_path): 
            return ranges
        with open(self.etalon_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    ranges[parts[2]] = (float(parts[0]), float(parts[1]))
        return ranges

    def apply_studio_anim(self, anim_folder):
        """
        Универсальный метод для Тела и Лица.
        Исправлена ошибка дублирования путей для mutils.
        """
        is_body = "body" in anim_folder.lower()
        set_folder = "AS_body_set.set" if is_body else "AS_face_set.set"
        
        # Для SelectionSet и Animation передаем пути к ПАПКАМ
        set_dir = os.path.join(self.lib_path, set_folder)
        anim_dir = os.path.join(self.lib_path, anim_folder)

        # 1. ШАГ: Селекция
        if os.path.exists(set_dir):
            print(f"FD_FishTool: Selecting controls for {set_folder}...")
            # SelectionSet.fromPath ожидает путь к папке .set или файлу .json
            # Чтобы избежать PermissionError папки, проверяем наличие set.json
            set_file = os.path.join(set_dir, "set.json")
            sel_set = SelectionSet.fromPath(set_file)
            sel_set.select()
        else:
            cmds.error(f"Set directory missing: {set_dir}")
            return

        # 2. ШАГ: Наложение анимации
        if os.path.exists(anim_dir):
            print(f"FD_FishTool: Transferring keys from {anim_folder}...")
            # ФИКС: Animation.fromPath ожидает путь к ПАПКЕ .anim
            # Метод внутри сам добавит 'pose.json'
            anim_obj = Animation.fromPath(anim_dir)
            anim_obj.load(
                objects=cmds.ls(sl=True),
                option=PasteOption.ReplaceCompletely,
                timeRange=True
            )
            
            # 3. ШАГ: Установка таймлайна
            clip_name = "normal_move" if is_body else "smile"
            self.set_timeline(clip_name)
            
            QtWidgets.QMessageBox.information(None, "FD_FishTool", f"Готово! Анимация наложена (Clip: {clip_name}).")
        else:
            cmds.error(f"Anim directory missing: {anim_dir}")

    def set_timeline(self, anim_name):
        if anim_name in self.anim_ranges:
            start, end = self.anim_ranges[anim_name]
            cmds.playbackOptions(min=start, max=end, ast=start, aet=end)
            cmds.currentTime(start)
            return True
        return False

    def get_symmetric_control(self, ctrl):
        if "_R" in ctrl: return ctrl.replace("_R", "_L")
        if "_L" in ctrl: return ctrl.replace("_L", "_R")
        return None

    def get_chain_end(self, root):
        children = cmds.listRelatives(root, ad=True, type="transform", fullPath=True) or []
        ctrls = [c for c in children if cmds.attributeQuery("Gimble_Visible", node=c, exists=True)]
        return ctrls[0] if ctrls else (children[0] if children else root)

    def setup_spring_target(self, root_ctrl):
        side_mult = -1.0 if "_L" in root_ctrl else 1.0
        end_node = self.get_chain_end(root_ctrl)
        short_name = end_node.split('|')[-1]
        loc_name = f"SM_target_{short_name}"
        if not cmds.objExists(loc_name):
            loc = cmds.spaceLocator(n=loc_name)[0]
            cmds.matchTransform(loc, end_node)
            cmds.move(1.0 * side_mult, 0, 0, loc, r=True, os=True)
            cmds.parent(loc, end_node)
        return loc_name

    def bind_chain_sequence(self, root_ctrl):
        end_node = self.get_chain_end(root_ctrl)
        loc_name = "SM_target_" + end_node.split('|')[-1]
        full_chain = []
        curr = end_node
        while curr:
            full_chain.append(curr)
            if curr == root_ctrl: break
            parents = cmds.listRelatives(curr, parent=True, type="transform")
            curr = parents[0] if parents else None
        full_chain.reverse()
        if cmds.objExists(loc_name): full_chain.append(loc_name)
        cmds.select(full_chain)
        sm_core.bindControls()

    def set_tech_keys(self, proxy_bones, anim_list):
        if not proxy_bones: return
        for anim in anim_list:
            if anim in self.anim_ranges:
                s, e = self.anim_ranges[anim]
                for f in [s-1, s, e, e+1]:
                    cmds.setKeyframe(proxy_bones, time=f, attribute='rotate')

    def apply_sm_to_selection(self, spring, twist, loop, anim_list):
        objs = cmds.ls(sl=True)
        if not objs: return
        sm_settings = sm_core.Spring(ratio=1.0-spring, twistRatio=1.0-twist)
        for anim in anim_list:
            if anim in self.anim_ranges:
                s, e = self.anim_ranges[anim]
                cmds.playbackOptions(min=s, max=e, ast=s, aet=e)
                sm_mgr = sm_core.SpringMagic(s, e, isLoop=loop)
                sm_core.SpringMagicMaya(objs, sm_settings, sm_mgr)