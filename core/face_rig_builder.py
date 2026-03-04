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

        # Маппинг перекрестного зеркалирования для джойстиков      
        # ТЕПЕРЬ ВСЕ ДЖОЙСТИКИ РАБОТАЮТ ОДИНАКОВО
        # pos_y (Right Up/Smile) <-> pos_x (Left Up/Smile)
        # neg_x (Right Down/Sad) <-> neg_y (Left Down/Sad)
        self.mirror_map = {
            "Emote": {"pos_y": "pos_x", "pos_x": "pos_y", "neg_x": "neg_y", "neg_y": "neg_x"},
            "Upr_Lip": {"pos_y": "pos_x", "pos_x": "pos_y", "neg_x": "neg_y", "neg_y": "neg_x"},
            "Lwr_Lip": {"pos_y": "pos_x", "pos_x": "pos_y", "neg_x": "neg_y", "neg_y": "neg_x"}
        }

    def _log(self, msg):
        formatted = "> AI: {}".format(msg)
        print(formatted)
        if self.ai_log: self.ai_log.append(formatted)

    def load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
        return {}

    def get_driven_bones(self, ctrl_name, quadrant=None):
        config = self.load_json(self.config_path)
        if ctrl_name not in config: return []
        patterns = []
        node_cfg = config[ctrl_name]
        if quadrant:
            patterns = node_cfg.get(quadrant, [])
        elif "driven" in node_cfg:
            patterns = node_cfg["driven"]
        else:
            for q in ["pos_y", "neg_y", "pos_x", "neg_x"]:
                patterns.extend(node_cfg.get(q, []))
        actual = []
        for p in patterns:
            found = cmds.ls(p, type="joint") if "*" in p else ([p] if cmds.objExists(p) else [])
            actual.extend(found)
        return sorted(list(set(actual)))

    def _get_sdk_curve(self, driven_attr, driver_attr):
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
        attrs = ['tx','ty','tz','rx','ry','rz']
        for n in nodes:
            for a in attrs:
                full_at = "{}.{}".format(n, a)
                if cmds.objExists(full_at) and cmds.getAttr(full_at, settable=True):
                    cmds.setAttr(full_at, 0)

    # --- MAIN SDK LOGIC ---
    def set_smart_key(self, driver_obj, driven_nodes_from_ui):
        config = self.load_json(self.config_path)
        if driver_obj not in config: return
        if "driven" in config[driver_obj]:
            self._process_linear_sdk(driver_obj, driven_nodes_from_ui)
        else:
            self._process_quadrant_sdk(driver_obj, config[driver_obj])

    # --- ЛИНЕЙНАЯ ЛОГИКА (ВЕКИ / SYNC) --- ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ
    def _process_linear_sdk(self, driver_obj, driven_nodes):
        self._log("Linear SDK: Запуск стерильного процесса для {}...".format(driver_obj))
        curr_frame = int(cmds.currentTime(q=True))
        anim_data = self.load_json(self.anim_path)
        
        # 1. РАЗДЕЛЕНИЕ СТОРОН
        # Для Sync/Jaw драйвер один на обе стороны, поэтому в первой части работаем только с правыми/центр костями
        is_shared = driver_obj in ["Sync", "Jaw", "gui_teeth"]
        right_and_cent = [n for n in driven_nodes if "left" not in n] if is_shared else driven_nodes
        left_only = [n for n in driven_nodes if "left" in n] if is_shared else []

        channels = [ch for ch in ["tx", "ty"] if ch in anim_data.get(driver_obj, {})]

        # --- ШАГ 1: ЗАХВАТ ПРАВОЙ ПОЗЫ ---
        r_proxies = self._create_proxies(right_and_cent, "tmp_R_")

        # --- ШАГ 2: СТЕРИЛЬНЫЙ 0-ФУНДАМЕНТ (ПРАВО) ---
        saved_vals = {ch: cmds.getAttr(driver_obj + "." + ch) for ch in channels}
        
        # Сброс контроллера и костей в абсолютный 0
        for ch in channels: cmds.setAttr(driver_obj + "." + ch, 0)
        self._hard_reset_driven_bones(right_and_cent)

        # Ставим 0-ключи
        for chan in channels:
            drv_at = "{}.{}".format(driver_obj, chan)
            for n in right_and_cent:
                # Проверяем наличие ключа в 0, чтобы не дублировать
                curve = self._get_sdk_curve(n + ".tx", drv_at)
                has_zero = False
                if curve and cmds.objExists(curve):
                    keys = cmds.keyframe(curve, q=True, fc=True) or []
                    if any(abs(k - 0.0) < 0.001 for k in keys): has_zero = True
                
                if not has_zero:
                    self._key_6(drv_at, 0.0, n)

        # --- ШАГ 3: УСТАНОВКА РАБОЧИХ КЛЮЧЕЙ (ПРАВО) ---
        # Сначала возвращаем драйвер в позу
        for ch, val in saved_vals.items(): cmds.setAttr(driver_obj + "." + ch, val)
        # Затем возвращаем кости из прокси
        self._snap_to(right_and_cent, r_proxies)
        
        f_idx = None
        try: f_idx = anim_data[driver_obj]["frames"].index(curr_frame)
        except: pass

        for chan in channels:
            drv_at = "{}.{}".format(driver_obj, chan)
            target_v = anim_data[driver_obj][chan][f_idx] if f_idx is not None else saved_vals[chan]
            
            # Записываем ключ только если канал активен (>0), защищая "чистый ноль"
            if abs(target_v) > 0.001:
                for n in right_and_cent: self._key_6(drv_at, target_v, n)

        # --- ШАГ 4: ЗЕРКАЛИРОВАНИЕ (ЛЕВО) ---
        m_ctrl = driver_obj.replace("R_", "L_").replace("right", "left")
        if m_ctrl != driver_obj and cmds.objExists(m_ctrl) or is_shared:
            target_driver = driver_obj if is_shared else m_ctrl
            
            # А. Подготовка левой позы
            self.mirror_drivens_logic(right_and_cent)
            if not left_only:
                left_only = [b.replace("right", "left") for b in right_and_cent if "right" in b and cmds.objExists(b)]
            
            if left_only:
                l_prox = self._create_proxies(left_only, "tmp_L_")
                
                # Б. Чистый фундамент для левой стороны
                # Обнуляем драйвер и кости
                for ch in channels: cmds.setAttr(target_driver + "." + ch, 0)
                self._hard_reset_driven_bones(left_only)
                
                # Ставим 0-ключи
                for chan in channels:
                    l_drv_at = "{}.{}".format(target_driver, chan)
                    for ln in left_only: self._key_6(l_drv_at, 0.0, ln)
                
                # В. Рабочая зеркальная поза (ИСПРАВЛЕННЫЙ ПОРЯДОК)
                # 1. Сначала ставим драйвер в рабочее значение (это заставит SDK сбросить кости в 0)
                for chan in channels:
                    l_drv_at = "{}.{}".format(target_driver, chan)
                    l_target_v = saved_vals[chan] if is_shared else 0
                    if not is_shared and f_idx is not None:
                        l_target_v = anim_data.get(target_driver, {}).get(chan, [0])[f_idx]
                    
                    if abs(l_target_v) > 0.001:
                        cmds.setAttr(l_drv_at, l_target_v)

                # 2. ТЕПЕРЬ возвращаем позу из прокси (она перезапишет нули от SDK)
                self._snap_to(left_only, l_prox)
                
                # 3. Теперь записываем рабочие ключи
                for chan in channels:
                    l_drv_at = "{}.{}".format(target_driver, chan)
                    l_target_v = saved_vals[chan] if is_shared else 0
                    if not is_shared and f_idx is not None:
                        l_target_v = anim_data.get(target_driver, {}).get(chan, [0])[f_idx]

                    if abs(l_target_v) > 0.001:
                        for ln in left_only: self._key_6(l_drv_at, l_target_v, ln)
                
                cmds.delete(l_prox)

        # Очистка
        cmds.delete(r_proxies)
        self._log("Linear SDK Process Complete (Fixed Mirroring Sequence).")

    def _process_quadrant_sdk(self, driver_obj, ctrl_config):
        self._log("Quadrant SDK Process: {}...".format(driver_obj))
        tx_val = cmds.getAttr(driver_obj + ".tx")
        ty_val = cmds.getAttr(driver_obj + ".ty")
        
        # 1. Определение активного квадранта (с приоритетом оси Y)
        active_q = None
        if abs(ty_val) > 0.001: active_q = "pos_y" if ty_val > 0 else "neg_y"
        elif abs(tx_val) > 0.001: active_q = "pos_x" if tx_val > 0 else "neg_x"
        
        if not active_q:
            self._log("Error: Контроллер в нуле. Сначала задайте позу.")
            return

        # 2. Поиск "правого" источника
        # Если мы в "левом" квадранте, ищем его правую пару
        src_q = active_q
        if not any("right" in b for b in ctrl_config.get(active_q, [])):
            for q, partner in self.mirror_map.get(driver_obj, {}).items():
                if partner == active_q: src_q = q; break

        # 3. ЗАХВАТ ПОЗЫ ПРАВОЙ СТОРОНЫ
        r_bones = self.get_driven_bones(driver_obj, src_q)
        r_prox = self._create_proxies(r_bones, "tmp_quad_R_")

        # 4. ГЛОБАЛЬНЫЙ СБРОС (Бетонируем 0)
        all_bones = self.get_driven_bones(driver_obj)
        for chan in ["tx", "ty"]:
            drv_at = "{}.{}".format(driver_obj, chan)
            old_v = cmds.getAttr(drv_at); cmds.setAttr(drv_at, 0)
            self._hard_reset_driven_bones(all_bones)
            for n in all_bones: self._key_6(drv_at, 0.0, n)
            cmds.setAttr(drv_at, old_v)

        # 5. УСТАНОВКА РАБОЧИХ КЛЮЧЕЙ (ПРАВО)
        src_chan = "ty" if "y" in src_q else "tx"
        src_val = 1.5 if "pos" in src_q else -1.5 
        drv_at = "{}.{}".format(driver_obj, src_chan)
        
        self._snap_to(r_bones, r_prox)
        for n in r_bones: self._key_6(drv_at, src_val, n)

        # 6. ПЕРЕКРЕСТНОЕ ЗЕРКАЛИРОВАНИЕ (ЛЕВО)
        mirror_q = self.mirror_map.get(driver_obj, {}).get(src_q)
        if mirror_q:
            self._log("Mirroring {} -> {}".format(src_q, mirror_q))
            self.mirror_drivens_logic(r_bones)
            l_bones = [b.replace("right", "left") if "right" in b else b for b in r_bones]
            l_bones = [b for b in l_bones if cmds.objExists(b)]
            l_prox = self._create_proxies(l_bones, "tmp_quad_L_")
            
            m_chan = "ty" if "y" in mirror_q else "tx"
            m_drv_at = "{}.{}".format(driver_obj, m_chan)
            
            # УБРАНА ИНВЕРСИЯ: Знак теперь определяется именем квадранта цели (pos/neg)
            m_val = 1.5 if "pos" in mirror_q else -1.5
            
            self._snap_to(l_bones, l_prox)
            for ln in l_bones: self._key_6(m_drv_at, m_val, ln)
            cmds.delete(l_prox)

        cmds.delete(r_prox)
        self._log("Quadrant SDK complete.")

    def _key_6(self, drv_at, drv_val, node):
        for a in ['tx','ty','tz','rx','ry','rz']:
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

    # --- UI HELPERS ---
    def run_context_test_animation(self):
        self.clean_test_animation()
        sel = cmds.ls(sl=True); data = self.load_json(self.anim_path); to_anim = []
        if any("Lid" in x or "Eye" in x for x in sel):
            to_anim = ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid"]
        elif any("Lip" in x for x in sel): to_anim = ["Lwr_Lip", "Upr_Lip"]
        else: to_anim = sel if sel else []
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
                    if cmds.getAttr(ctrl+"."+a, settable=True): cmds.setAttr(ctrl+"."+a, 0)

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

    def mirror_unit(self, source_loc):
        if not cmds.objExists(source_loc) or any(x in source_loc for x in ["cent_", "teeth", "jaw"]): return
        target = source_loc.replace("right", "left")
        if cmds.objExists(target): cmds.delete(target)
        new_loc = cmds.duplicate(source_loc, name=target, rc=True)[0]
        cmds.setAttr(new_loc+".tx", -cmds.getAttr(new_loc+".tx")); cmds.setAttr(new_loc+".rx", 180)
        cmds.setAttr(new_loc+".overrideColor", 6)
        child = cmds.listRelatives(new_loc, children=True, type="joint")
        if child: cmds.rename(child[0], target.replace("locAlign_fcrg_", "mchFcrg_"))