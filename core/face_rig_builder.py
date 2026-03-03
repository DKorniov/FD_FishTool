# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om
import os
import json

class FaceRigBuilder(object):
    def __init__(self):
        self.config_dir = os.path.join(cmds.internalVar(usd=True), "FD_FishTool", "data")
        self.config_path = os.path.join(self.config_dir, "face_rig_config.json")
        self.anim_path = os.path.join(self.config_dir, "face_test_anim.json")
        self.test_ctrls = ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid", 
                           "Emote", "Sync", "Jaw", "gui_teeth", "Lwr_Lip", "Upr_Lip"]
        self.ai_log = None

    def _log(self, msg):
        formatted = "> AI: {}".format(msg)
        print(formatted)
        if self.ai_log: self.ai_log.append(formatted)

    def load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
        return {}

    def _get_sdk_curve(self, driven_attr, driver_attr):
        """Находит кривую SDK между конкретными атрибутами."""
        curves = cmds.listConnections(driven_attr, s=True, d=False, type='animCurve') or []
        for c in curves:
            inputs = cmds.listConnections(c + ".input", s=True, d=False, p=True) or []
            if driver_attr in inputs: return c
        return None

    def _create_proxies(self, nodes, prefix="proxy_"):
        proxies = []
        for n in nodes:
            loc = cmds.spaceLocator(name=prefix + n)[0]
            cmds.xform(loc, matrix=cmds.xform(n, q=True, matrix=True, ws=True), ws=True)
            proxies.append(loc)
        return proxies

    def _snap_to(self, nodes, targets):
        for n, t in zip(nodes, targets):
            cmds.xform(n, matrix=cmds.xform(t, q=True, matrix=True, ws=True), ws=True)

    def _hard_reset_driven_bones(self, nodes):
        """Принудительно обнуляет все 6 каналов трансформации костей."""
        attrs = ['tx','ty','tz','rx','ry','rz']
        for n in nodes:
            for a in attrs:
                full_at = "{}.{}".format(n, a)
                if cmds.objExists(full_at) and cmds.getAttr(full_at, settable=True):
                    cmds.setAttr(full_at, 0)

    # --- УНИВЕРСАЛЬНАЯ ЛОГИКА KEY (11 ШАГОВ) ---
    def set_smart_key(self, driver_obj, driven_nodes):
        curr_frame = int(cmds.currentTime(q=True))
        anim_data = self.load_json(self.anim_path)
        
        if driver_obj not in anim_data:
            self._log("Error: {} not found in test anim config.".format(driver_obj))
            return

        # Находим все каналы, которые есть у этого контрола (tx, ty)
        channels = [ch for ch in ["tx", "ty"] if ch in anim_data[driver_obj]]
        self._log("Processing KEY for {} (Axes: {})".format(driver_obj, channels))

        # 1. ЗАПОМИНАЕМ ПРАВУЮ ПОЗУ (Прокси)
        r_proxies = self._create_proxies(driven_nodes, "proxy_R_")

        # 2. ПРОХОД 0: ГАРАНТИРУЕМ ЧИСТЫЙ НОЛЬ ДЛЯ ВСЕХ КАНАЛОВ
        for chan in channels:
            drv_at = "{}.{}".format(driver_obj, chan)
            # Проверяем наличие ключа в 0 через кривую (по tx первой кости)
            curve = self._get_sdk_curve(driven_nodes[0] + ".tx", drv_at)
            existing_0 = cmds.keyframe(curve, q=True, fc=True) if curve else []
            
            if not any(abs(k - 0.0) < 0.001 for k in existing_0):
                self._log("Step: Establishing ABSOLUTE ZERO for {}".format(drv_at))
                # Сохраняем текущее значение контроллера
                saved_v = cmds.getAttr(drv_at)
                # Сбрасываем всё в 0
                cmds.setAttr(drv_at, 0)
                self._hard_reset_driven_bones(driven_nodes)
                # Ставим ключ (Volume 0)
                for n in driven_nodes: self._key_6(drv_at, 0.0, n)
                # Возвращаем значение контроллера
                cmds.setAttr(drv_at, saved_v)

        # 3. ПРОХОД POSE: СТАВИМ РАБОЧИЙ КЛЮЧ
        self._snap_to(driven_nodes, r_proxies)
        try: f_idx = anim_data[driver_obj]["frames"].index(curr_frame)
        except: f_idx = None

        for chan in channels:
            drv_at = "{}.{}".format(driver_obj, chan)
            # Берем значение драйвера из конфига (или текущее)
            target_drv_v = anim_data[driver_obj][chan][f_idx] if f_idx is not None else cmds.getAttr(drv_at)
            # Ставим рабочий ключ (только если значение не 0, чтобы не портить билд-позу)
            if abs(target_drv_v) > 0.001:
                for n in driven_nodes: self._key_6(drv_at, target_drv_v, n)

        # 4. ЗЕРКАЛИРОВАНИЕ И ПОВТОР ДЛЯ ЛЕВОЙ СТОРОНЫ
        # Определяем зеркальный драйвер (для век это L_ контрол, для Sync это тот же Sync)
        is_side_ctrl = driver_obj.startswith("R_") or "right" in driver_obj
        m_driver_obj = driver_obj.replace("R_", "L_").replace("right", "left") if is_side_ctrl else driver_obj
        
        self._log("Step: Mirroring position...")
        self.mirror_drivens_logic(driven_nodes)
        
        l_bones = [b.replace("right", "left") for b in driven_nodes if "right" in b]
        l_bones = [b for b in l_bones if cmds.objExists(b)]
        
        if l_bones and cmds.objExists(m_driver_obj):
            l_proxies = self._create_proxies(l_bones, "proxy_L_")
            
            # Проход 0 для левой стороны
            for chan in channels:
                l_drv_at = "{}.{}".format(m_driver_obj, chan)
                l_curve = self._get_sdk_curve(l_bones[0] + ".tx", l_drv_at)
                if not any(abs(k - 0.0) < 0.001 for k in (cmds.keyframe(l_curve, q=True, fc=True) if l_curve else [])):
                    self._log("Step: Mirror ABSOLUTE ZERO for {}".format(l_drv_at))
                    old_lv = cmds.getAttr(l_drv_at); cmds.setAttr(l_drv_at, 0)
                    self._hard_reset_driven_bones(l_bones)
                    for ln in l_bones: self._key_6(l_drv_at, 0.0, ln)
                    cmds.setAttr(l_drv_at, old_lv)
            
            # Проход Pose для левой стороны
            self._snap_to(l_bones, l_proxies)
            for chan in channels:
                l_drv_at = "{}.{}".format(m_driver_obj, chan)
                l_target_drv_v = anim_data[m_driver_obj][chan][f_idx] if f_idx is not None else cmds.getAttr(l_drv_at)
                if abs(l_target_drv_v) > 0.001:
                    for ln in l_bones: self._key_6(l_drv_at, l_target_drv_v, ln)
            
            cmds.delete(l_proxies)

        # ОСОБАЯ ЛОГИКА JAW (Инверсия)
        elif driver_obj in ["Jaw", "gui_teeth"]:
            # Берем активный канал для инверсии
            # ...
            pass

        cmds.delete(r_proxies)
        self._log("Smart KEY process finished successfully.")

    def _key_6(self, drv_at, drv_val, node):
        attrs = ['tx','ty','tz','rx','ry','rz']
        for a in attrs:
            cmds.setDrivenKeyframe("{}.{}".format(node, a), cd=drv_at, dv=drv_val, v=cmds.getAttr("{}.{}".format(node, a)))

    def mirror_drivens_logic(self, nodes=None):
        targets = nodes if nodes else cmds.ls('mchFcrg*right*', type='joint')
        for r in targets:
            if 'right' not in r: continue
            l = r.replace('right', 'left')
            if cmds.objExists(l):
                pos = cmds.xform(r, q=True, t=True, ws=True)
                cmds.xform(l, t=[-pos[0], pos[1], pos[2]], ws=True)
                rot = cmds.xform(r, q=True, ro=True, os=True)
                cmds.xform(l, ro=[rot[0], -rot[1], -rot[2]], os=True)

    def run_context_test_animation(self):
        """Анимация для всех выделенных контролов (группирует веки)."""
        self.clean_test_animation()
        sel = cmds.ls(sl=True); data = self.load_json(self.anim_path); to_anim = []
        
        # Если выбрано любое веко - анимируем всю группу
        if any(x in sel for x in ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid"]):
            to_anim = ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid"]
        elif any(x in sel for x in ["Lwr_Lip", "Upr_Lip"]):
            to_anim = ["Lwr_Lip", "Upr_Lip"]
        else:
            to_anim = sel if sel else []

        for ctrl in to_anim:
            if ctrl in data:
                d = data[ctrl]
                for i, f in enumerate(d.get("frames", [])):
                    if "ty" in d: cmds.setKeyframe(ctrl, at="ty", v=d["ty"][i], t=f)
                    if "tx" in d: cmds.setKeyframe(ctrl, at="tx", v=d["tx"][i], t=f)
        cmds.currentTime(1)

    def clean_test_animation(self):
        c = [x for x in self.test_ctrls if cmds.objExists(x)]
        if c: 
            cmds.cutKey(c, s=True)
            for ctrl in c:
                for a in ['tx','ty','tz','rx','ry','rz']:
                    if cmds.getAttr(ctrl+"."+a, settable=True):
                        try: cmds.setAttr(ctrl+"."+a, 0)
                        except: pass

    def get_driven_bones(self, ctrl_name):
        config = self.load_json(self.config_path)
        if ctrl_name not in config: return []
        patterns = config[ctrl_name].get("driven", [])
        actual = []
        for p in patterns:
            found = cmds.ls(p, type="joint") if "*" in p else ([p] if cmds.objExists(p) else [])
            actual.extend(found)
        return sorted(list(set(actual)))

    def import_gui_library(self):
        lib = os.path.join(self.config_dir, "face_controls_library.ma")
        if os.path.exists(lib) and not cmds.objExists("GUI_grp"):
            cmds.file(lib, i=True, type="mayaAscii", rnn=True)
        return cmds.objExists("GUI_grp")

    def create_rig_unit(self, vtx, bone_name, pos_override=None):
        if not cmds.objExists("fclRig_lctr_grp"):
            if not cmds.objExists("Setup_grp"): cmds.group(em=True, name="Setup_grp")
            cmds.group(em=True, name="fclRig_lctr_grp", parent="Setup_grp")
        if vtx:
            sel = om.MSelectionList(); sel.add(vtx); path, comp = sel.getComponent(0)
            it = om.MItMeshVertex(path, comp); p = it.position(om.MSpace.kWorld); pos = [p.x, p.y, p.z]
        else: pos = pos_override or [0, 0, 0]
        loc = cmds.spaceLocator(name=bone_name.replace("mchFcrg_", "locAlign_fcrg_"))[0]
        cmds.xform(loc, t=pos, ws=True); cmds.parent(loc, "fclRig_lctr_grp")
        cmds.setAttr(loc+".overrideEnabled", 1); col = 13 if "right" in loc else (6 if "left" in loc else 17)
        cmds.setAttr(loc+".overrideColor", col)
        cmds.select(cl=True); j = cmds.joint(name=bone_name); cmds.parent(j, loc)
        for a in [".t",".r",".jo"]: cmds.setAttr(j+a, 0,0,0)
        return loc