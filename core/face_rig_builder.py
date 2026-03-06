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
                   "Emote", "Sync", "Jaw", "gui_teeth", "Lwr_Lip", "Upr_Lip",
                   "R_Brow_ctrl", "L_Brow_ctrl", "R_Eye_ctrl", "L_Eye_ctrl"]
        self.ai_log = None

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

    # --- МАРШРУТИЗАЦИЯ KEY ---
    def set_smart_key(self, driver_obj, driven_nodes_from_ui):
        config = self.load_json(self.config_path)
        if driver_obj not in config: return
        
        if driver_obj == "Jaw":
            self._process_jaw_sdk(driver_obj, driven_nodes_from_ui)
        elif driver_obj == "gui_teeth":
            self._process_teeth_sdk(driver_obj, driven_nodes_from_ui)
        elif "driven" in config[driver_obj]:
            self._process_linear_sdk(driver_obj, driven_nodes_from_ui)
        else:
            self._process_quadrant_sdk(driver_obj, config[driver_obj])

    # --- ИСПРАВЛЕННЫЙ МЕТОД ДЛЯ JAW (Cross-Mirroring) ---
    # --- ГИБРИДНЫЙ МЕТОД ДЛЯ JAW (Self + Cross Mirroring) ---
    def _process_jaw_sdk(self, driver_obj, driven_nodes):
        self._log("Processing JAW (Hybrid Mirroring: Self for Central, Cross for Paired)...")
        drv_at = driver_obj + ".tx"
        
        # 1. Захват данных из позы при TX = 1.0 (в словарь Python)
        captured_data = {}
        for n in driven_nodes:
            captured_data[n] = {
                'tx': cmds.getAttr(n + ".tx"), 'ty': cmds.getAttr(n + ".ty"), 'tz': cmds.getAttr(n + ".tz"),
                'rx': cmds.getAttr(n + ".rx"), 'ry': cmds.getAttr(n + ".ry"), 'rz': cmds.getAttr(n + ".rz")
            }
        
        # 2. Нейтраль (TX = 0)
        cmds.setAttr(drv_at, 0)
        self._hard_reset_driven_bones(driven_nodes)
        for n in driven_nodes: 
            self._key_6(drv_at, 0.0, n)
        
        # 3. Установка ключей для TX = 1.0
        cmds.setAttr(drv_at, 1.0)
        for n in driven_nodes:
            d = captured_data[n]
            for a in ['tx','ty','tz','rx','ry','rz']:
                cmds.setAttr(n + "." + a, d[a])
            self._key_6(drv_at, 1.0, n)
            
        # 4. ЗЕРКАЛО ДЛЯ TX = -1.0
        cmds.setAttr(drv_at, -1.0)
        # Очищаем сцену перед распределением зеркальной позы
        self._hard_reset_driven_bones(driven_nodes)
        
        for n in driven_nodes:
            # Проверка: центральная кость или парная?
            is_cent = any(x in n.lower() for x in ["cent", "jaw"])
            d = captured_data[n]
            
            if is_cent:
                # ЛОГИКА ДЛЯ ЦЕНТРАЛЬНЫХ (Зеркалят сами себя)
                # По вашему примеру: [1,1,1, 2,2,2] -> [-1, 1,1, 2,-2,-2]
                cmds.setAttr(n + ".tx", -d['tx'])
                cmds.setAttr(n + ".ty", d['ty'])
                cmds.setAttr(n + ".tz", d['tz'])
                cmds.setAttr(n + ".rx", d['rx'])
                cmds.setAttr(n + ".ry", -d['ry'])
                cmds.setAttr(n + ".rz", -d['rz'])
            else:
                # ЛОГИКА ДЛЯ ПАРНЫХ (Перенос на партнера)
                m_node = n
                if "right" in n: m_node = n.replace("right", "left")
                elif "left" in n: m_node = n.replace("left", "right")
                elif "R_" in n: m_node = n.replace("R_", "L_")
                elif "L_" in n: m_node = n.replace("L_", "R_")
                
                if cmds.objExists(m_node):
                    # По вашему примеру: T инвертируется по всем осям, R сохраняет знаки
                    cmds.setAttr(m_node + ".tx", -d['tx'])
                    cmds.setAttr(m_node + ".ty", -d['ty'])
                    cmds.setAttr(m_node + ".tz", -d['tz'])
                    cmds.setAttr(m_node + ".rx", d['rx'])
                    cmds.setAttr(m_node + ".ry", d['ry'])
                    cmds.setAttr(m_node + ".rz", d['rz'])

        # Фиксируем ключи для положения -1.0 для всех костей
        for n in driven_nodes:
            self._key_6(drv_at, -1.0, n)
            
        # Возвращаем в 1.0 для проверки
        cmds.setAttr(drv_at, 1.0)
        self._log("JAW Hybrid Mirroring Complete.")

    # --- ИСПРАВЛЕННЫЙ МЕТОД ДЛЯ TEETH ---
    def _process_teeth_sdk(self, driver_obj, driven_nodes):
        self._log("Processing TEETH (Linear Y [-1,1] / Inversion X)...")
        tx_val = cmds.getAttr(driver_obj + ".tx")
        ty_val = cmds.getAttr(driver_obj + ".ty")

        # 1. Логика Y (Подъем/Опускание) - теперь поддерживает весь диапазон [-1, 1]
        # Используем стандартный линейный процесс, так как он умеет работать с JSON и негативными значениями
        if abs(ty_val) > 0.001:
            self._process_linear_sdk(driver_obj, driven_nodes)
            # Если по X движения нет, выходим, чтобы не дублировать ключи
            if abs(tx_val) < 0.001: return

        # 2. Логика X (Наклон с инверсией RotateX)
        if abs(tx_val) > 0.001:
            drv_at = driver_obj + ".tx"
            proxies = self._create_proxies(driven_nodes, "tmp_teeth_")
            
            # Фундамент 0 (Стерильный сброс)
            cmds.setAttr(drv_at, 0)
            self._hard_reset_driven_bones(driven_nodes)
            for n in driven_nodes: self._key_6(drv_at, 0.0, n)
            
            # Рабочий ключ TX = 1.0 (Поза вперед)
            cmds.setAttr(drv_at, 1.0)
            self._snap_to(driven_nodes, proxies)
            for n in driven_nodes: self._key_6(drv_at, 1.0, n)
            
            # Авто-инверсия для TX = -1.0 (Наклон назад)
            cmds.setAttr(drv_at, -1.0)
            self._snap_to(driven_nodes, proxies) # Сначала возвращаем позу
            for n in driven_nodes:
                rx_val = cmds.getAttr(n + ".rx")
                cmds.setAttr(n + ".rx", rx_val * -1) # Инвертируем наклон
                self._key_6(drv_at, -1.0, n)
                
            cmds.delete(proxies)
            # Возвращаем контроллер в текущее положение пользователя
            cmds.setAttr(drv_at, tx_val)
            self._log("TEETH X-Inversion Processed.")

    # --- ЛИНЕЙНАЯ ЛОГИКА (ВЕКИ / SYNC) --- ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ
    # --- СТАБИЛЬНАЯ ВЕРСИЯ _process_linear_sdk (Branch 09) ---
    def _process_linear_sdk(self, driver_obj, driven_nodes):
        self._log("Linear SDK: Starting sterile process for {}...".format(driver_obj))
        curr_frame = int(cmds.currentTime(q=True))
        anim_data = self.load_json(self.anim_path)
        
        # 1. РАЗДЕЛЕНИЕ СТОРОН
        is_shared = driver_obj in ["Sync", "Jaw", "gui_teeth"]
        right_and_cent = [n for n in driven_nodes if "left" not in n] if is_shared else driven_nodes
        left_only = [n for n in driven_nodes if "left" in n] if is_shared else []

        channels = [ch for ch in ["tx", "ty"] if ch in anim_data.get(driver_obj, {})]
        # Сохраняем текущие позы контроллера
        saved_vals = {ch: cmds.getAttr(driver_obj + "." + ch) for ch in channels}

        # --- ШАГ 1: ЗАХВАТ ПРАВОЙ ПОЗЫ ---
        r_proxies = self._create_proxies(right_and_cent, "tmp_R_")

        # --- ШАГ 2: СТЕРИЛЬНЫЙ 0-ФУНДАМЕНТ (ПРАВО) ---
        for ch in channels: cmds.setAttr(driver_obj + "." + ch, 0)
        self._hard_reset_driven_bones(right_and_cent)

        for chan in channels:
            drv_at = "{}.{}".format(driver_obj, chan)
            for n in right_and_cent:
                curve = self._get_sdk_curve(n + ".tx", drv_at)
                has_zero = False
                if curve and cmds.objExists(curve):
                    keys = cmds.keyframe(curve, q=True, fc=True) or []
                    if any(abs(k - 0.0) < 0.001 for k in keys): has_zero = True
                
                if not has_zero:
                    self._key_6(drv_at, 0.0, n)

        # --- ШАГ 3: УСТАНОВКА РАБОЧИХ КЛЮЧЕЙ (ПРАВО) ---
        for ch, val in saved_vals.items(): cmds.setAttr(driver_obj + "." + ch, val)
        self._snap_to(right_and_cent, r_proxies)
        
        f_idx = None
        try: f_idx = anim_data[driver_obj]["frames"].index(curr_frame)
        except: pass

        for chan in channels:
            drv_at = "{}.{}".format(driver_obj, chan)
            target_v = anim_data[driver_obj][chan][f_idx] if f_idx is not None else saved_vals[chan]
            
            if abs(target_v) > 0.001:
                for n in right_and_cent: self._key_6(drv_at, target_v, n)

        # --- ШАГ 4: ЗЕРКАЛИРОВАНИЕ (ЛЕВО) ---
        m_ctrl = driver_obj
        if "R_" in driver_obj: m_ctrl = driver_obj.replace("R_", "L_")
        elif "L_" in driver_obj: m_ctrl = driver_obj.replace("L_", "R_")
        elif "right" in driver_obj: m_ctrl = driver_obj.replace("right", "left")
        elif "left" in driver_obj: m_ctrl = driver_obj.replace("left", "right")

        if m_ctrl != driver_obj and cmds.objExists(m_ctrl) or is_shared:
            target_driver = driver_obj if is_shared else m_ctrl
            
            # А. Подготовка левой позы
            self.mirror_drivens_logic(right_and_cent)
            
            # Поиск левых костей для не-shared контролов
            if not left_only:
                for b in right_and_cent:
                    new_b = b
                    if "right" in b: new_b = b.replace("right", "left")
                    elif "left" in b: new_b = b.replace("left", "right")
                    if new_b != b and cmds.objExists(new_b):
                        left_only.append(new_b)
            
            if left_only:
                l_prox = self._create_proxies(left_only, "tmp_L_")
                
                # Б. Чистый фундамент для левой стороны
                for ch in channels: 
                    l_at = target_driver + "." + ch
                    if cmds.objExists(l_at): cmds.setAttr(l_at, 0)
                
                self._hard_reset_driven_bones(left_only)
                
                for chan in channels:
                    l_drv_at = "{}.{}".format(target_driver, chan)
                    for ln in left_only: self._key_6(l_drv_at, 0.0, ln)
                
                # В. Рабочая зеркальная поза
                for chan in channels:
                    l_drv_at = "{}.{}".format(target_driver, chan)
                    # Для Sync и бровей берем текущее значение контроллера
                    l_target_v = saved_vals[chan] 
                    
                    if abs(l_target_v) > 0.001:
                        cmds.setAttr(l_drv_at, l_target_v)

                self._snap_to(left_only, l_prox)
                
                for chan in channels:
                    l_drv_at = "{}.{}".format(target_driver, chan)
                    l_target_v = saved_vals[chan]
                    
                    if abs(l_target_v) > 0.001:
                        for ln in left_only: self._key_6(l_drv_at, l_target_v, ln)
                
                cmds.delete(l_prox)

        cmds.delete(r_proxies)
        self._log("Linear Process Complete: {}".format(driver_obj))

    # --- КВАДРАНТНАЯ ЛОГИКА (EMOTE / LIPS) --- (БЕЗ ИЗМЕНЕНИЙ)
    def _process_quadrant_sdk(self, driver_obj, ctrl_config):
        self._log("Quadrant SDK Process: {}...".format(driver_obj))
        tx_val = cmds.getAttr(driver_obj + ".tx")
        ty_val = cmds.getAttr(driver_obj + ".ty")
        active_q = None
        if abs(ty_val) > 0.001: active_q = "pos_y" if ty_val > 0 else "neg_y"
        elif abs(tx_val) > 0.001: active_q = "pos_x" if tx_val > 0 else "neg_x"
        if not active_q: return

        src_q = active_q
        if not any("right" in b for b in ctrl_config.get(active_q, [])):
            for q, partner in self.mirror_map.get(driver_obj, {}).items():
                if partner == active_q: src_q = q; break

        r_bones = self.get_driven_bones(driver_obj, src_q)
        r_prox = self._create_proxies(r_bones, "tmp_quad_R_")

        all_bones = self.get_driven_bones(driver_obj)
        for chan in ["tx", "ty"]:
            drv_at = "{}.{}".format(driver_obj, chan)
            old_v = cmds.getAttr(drv_at); cmds.setAttr(drv_at, 0)
            self._hard_reset_driven_bones(all_bones)
            for n in all_bones: self._key_6(drv_at, 0.0, n)
            cmds.setAttr(drv_at, old_v)

        src_chan = "ty" if "y" in src_q else "tx"
        src_val = 1.5 if "pos" in src_q else -1.5 
        drv_at = "{}.{}".format(driver_obj, src_chan)
        self._snap_to(r_bones, r_prox)
        for n in r_bones: self._key_6(drv_at, src_val, n)

        mirror_q = self.mirror_map.get(driver_obj, {}).get(src_q)
        if mirror_q:
            self.mirror_drivens_logic(r_bones)
            l_bones = [b.replace("right", "left") if "right" in b else b for b in r_bones]
            l_bones = [b for b in l_bones if cmds.objExists(b)]
            l_prox = self._create_proxies(l_bones, "tmp_quad_L_")
            m_chan = "ty" if "y" in mirror_q else "tx"
            m_drv_at = "{}.{}".format(driver_obj, m_chan)
            m_val = 1.5 if "pos" in mirror_q else -1.5
            self._snap_to(l_bones, l_prox)
            for ln in l_bones: self._key_6(m_drv_at, m_val, ln)
            cmds.delete(l_prox)
        cmds.delete(r_prox)

    # --- ВСЕ ОСТАЛЬНЫЕ МЕТОДЫ (key_6, mirror_logic, ui_tools) --- (БЕЗ ИЗМЕНЕНИЙ)
    def _key_6(self, drv_at, drv_val, node):
        for a in ['tx','ty','tz','rx','ry','rz']:
            cmds.setDrivenKeyframe("{}.{}".format(node, a), cd=drv_at, dv=drv_val, v=cmds.getAttr("{}.{}".format(node, a)))

    def mirror_drivens_logic(self, nodes=None):
        """
        Зеркалирование позы костей. 
        Теперь Rotate копируется с сохранением знаков (Mirror Behavior).
        """
        # Если ноды не переданы, ищем по умолчанию все правые
        targets = nodes if nodes else cmds.ls('mchFcrg*right*', type='joint')
        
        for src in targets:
            # Умный поиск зеркального имени (R_ -> L_, right -> left, _R -> _L)
            dest = None
            if "right" in src: dest = src.replace("right", "left")
            elif "left" in src: dest = src.replace("left", "right")
            elif "R_" in src: dest = src.replace("R_", "L_")
            elif "L_" in src: dest = src.replace("L_", "R_")
            
            if dest and dest != src and cmds.objExists(dest):
                # 1. Зеркалирование транслейта (Мировая симметрия по X)
                pos = cmds.xform(src, q=True, t=True, ws=True)
                cmds.xform(dest, t=[-pos[0], pos[1], pos[2]], ws=True)
                
                # 2. Зеркалирование ротейта (Копирование знаков)
                # По просьбе: с +rx;+ry;+rz на +rx;+ry;+rz
                rot = cmds.xform(src, q=True, ro=True, os=True)
                cmds.xform(dest, ro=[rot[0], rot[1], rot[2]], os=True)
                
                self._log("Pose Mirrored: {} -> {} (Same Signs)".format(src, dest))

    def run_context_test_animation(self):
        self.clean_test_animation()
        sel = cmds.ls(sl=True); data = self.load_json(self.anim_path); to_anim = []
        
        # Группировка век
        if any("Lid" in x or "Eye" in x for x in sel):
            to_anim = ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid"]
        # НОВОЕ: Группировка бровей
        elif any("Brow" in x for x in sel):
            to_anim = ["R_Brow_ctrl", "L_Brow_ctrl"]
        # Группировка глаз (контроллеры взгляда)
        elif any("Eye_ctrl" in x for x in sel):
            to_anim = ["R_Eye_ctrl", "L_Eye_ctrl"]
        # Группировка губ
        elif any("Lip" in x for x in sel): 
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
        """Очистка ключей и сброс в ноль."""
        c = [x for x in self.test_ctrls if cmds.objExists(x)]
        if c: 
            cmds.cutKey(c, s=True)
            for ctrl in c:
                for a in ['tx','ty','tz','rx','ry','rz']:
                    if cmds.objExists(ctrl+"."+a) and cmds.getAttr(ctrl+"."+a, settable=True):
                        cmds.setAttr(ctrl+"."+a, 0)

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
    
    def build_and_connect_skin_bones(self):
        """
        Stage 4: Динамическая генерация скин-костей и их привязка к механике.
        """
        self._log("Stage 4: Запуск процесса Skin-Mapping...")
        
        # 1. Загрузка конфига
        map_path = os.path.join(self.config_dir, "bone_skin_map.json")
        all_map_data = self.load_json(map_path)
        # Берем исключения из stage_4, не меняя структуру основного файла
        face_exceptions = all_map_data.get("stage_4", {}).get("face_exceptions", {})

        # 2. Подготовка иерархии
        skin_grp = "Fcrg_bn_grp"
        if not cmds.objExists(skin_grp): cmds.group(em=True, name=skin_grp)
        
        cnstr_grp = "cnstrn_grp"
        if not cmds.objExists(cnstr_grp): cmds.group(em=True, name=cnstr_grp)

        # 3. Сканирование механических костей (MCH)
        mch_bones = cmds.ls("mchFcrg_*", type="joint")
        if not mch_bones:
            self._log("Механические кости mchFcrg_ не найдены. Пропуск.")
            return

        for mch in mch_bones:
            # А. Получаем имя скин-кости через транслятор
            skn_name = self._translate_mch_to_skin(mch, face_exceptions)
            
            # Б. Создание кости, если её нет
            if not cmds.objExists(skn_name):
                cmds.select(cl=True)
                skn = cmds.joint(name=skn_name)
                # Копируем положение
                cmds.delete(cmds.parentConstraint(mch, skn))
                cmds.makeIdentity(skn, apply=True, t=0, r=1, s=0)
                cmds.parent(skn, skin_grp)
                self._log("Создана кость: {}".format(skn_name))
            else:
                skn = skn_name

            # В. Подключение (Parent Constraint)
            if not self._is_constrained(mch, skn):
                pc = cmds.parentConstraint(mch, skn, mo=False, name=skn + "_pc_mch")[0]
                cmds.parent(pc, cnstr_grp)
                self._log("Связь: {} -> {}".format(mch, skn))

    def _translate_mch_to_skin(self, mch, exceptions):
        """Реализация правил именования допущений."""
        # 1. Исключения (из JSON)
        if mch in exceptions:
            return exceptions[mch]

        # Убираем основной префикс
        base = mch.replace("mchFcrg_", "")

        # 2. Правило Lips (cent -> center, убираем цифры в конце)
        if "cent_" in base and "lip" in base:
            res = base.replace("cent_", "center_")
            # Убираем цифру в конце (lip1 -> lip)
            return "".join([i for i in res if not i.isdigit()])

        # 3. Правило Brows (right_Brow1 -> Brow1_R)
        if "Brow" in base:
            if base.startswith("right_"):
                return base.replace("right_", "") + "_R"
            if base.startswith("left_"):
                return base.replace("left_", "") + "_L"

        # 4. Стандартное правило (просто удаление mchFcrg_)
        return base

    def _is_constrained(self, parent_node, child_node):
        """Проверка на существующий констрейн, чтобы не плодить дубликаты."""
        conns = cmds.listConnections(child_node, type="parentConstraint") or []
        for c in conns:
            drivers = cmds.parentConstraint(c, q=True, tl=True) or []
            if parent_node in drivers:
                return True
        return False