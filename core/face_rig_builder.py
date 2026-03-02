# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.api.OpenMaya as om
import os
import json

class FaceRigBuilder:
    def __init__(self):
        self.main_group = "fclRig_lctr_grp"
        self.config_dir = os.path.join(cmds.internalVar(usd=True), "FD_FishTool", "data")
        self.anim_path = os.path.join(self.config_dir, "face_test_anim.json")
        self.config_path = os.path.join(self.config_dir, "face_rig_config.json")
        self.test_ctrls = ["R_Lwr_EyeLid", "L_Lwr_EyeLid", "L_Upp_EyeLid", "R_Upp_EyeLid", 
                           "Emote", "Sync", "Jaw", "gui_teeth", "Lwr_Lip", "Upr_Lip"]
        self.ai_log = None

    def _log(self, msg):
        formatted = "> AI: {}".format(msg)
        print(formatted)
        if self.ai_log: self.ai_log.append(formatted)

    # --- СИСТЕМА ПРОКСИ (БЕЗОПАСНЫЙ SNAP) ---
    def _create_proxies(self, nodes, prefix="tmp_"):
        proxies = []
        for n in nodes:
            loc = cmds.spaceLocator(name=prefix + n)[0]
            cmds.xform(loc, matrix=cmds.xform(n, q=True, matrix=True, ws=True), ws=True)
            proxies.append(loc)
        return proxies

    def _snap_to(self, nodes, targets):
        for n, t in zip(nodes, targets):
            cmds.xform(n, matrix=cmds.xform(t, q=True, matrix=True, ws=True), ws=True)

    # --- ГЛАВНАЯ ЛОГИКА KEY (11 ПУНКТОВ С ОЧИСТКОЙ) ---
    def set_smart_key(self, driver_attr, driven_nodes):
        drv_obj, attr = driver_attr.split('.')
        drv_val = cmds.getAttr(driver_attr)
        
        # 1. Запоминаем правую позицию
        r_proxies = self._create_proxies(driven_nodes, "proxy_R_")
        
        # 2-3. Проверка и установка 0 для правой стороны
        # ВАЖНО: Используем fc (floatChange) для запроса SDK
        existing = cmds.keyframe(driven_nodes[0], at='tx', q=True, fc=True) or []
        has_zero = any(abs(k - 0.0) < 0.001 for k in existing)

        if not has_zero:
            self._log("Zero key missing on Right side. Establishing clean Build Pose.")
            for n in driven_nodes: self._key_6(driver_attr, 0.0, n, zero=True)
            
        # 4-5. Возврат и ключ
        self._snap_to(driven_nodes, r_proxies)
        for n in driven_nodes: self._key_6(driver_attr, drv_val, n)

        # 6. Mirror Position (Зеркалим правую сторону на левую)
        side_pref = "L_" if "R_" in drv_obj else ("left" if "right" in drv_obj else None)
        if side_pref:
            m_ctrl = drv_obj.replace("R_", "L_").replace("right", "left")
            if cmds.objExists(m_ctrl):
                self._log("Mirroring to Left side: {}...".format(m_ctrl))
                self.mirror_drivens_logic(driven_nodes) # Копирует положение mch_R на mch_L
                
                l_bones = [b.replace("right", "left") for b in driven_nodes if "right" in b]
                l_bones = [b for b in l_bones if cmds.objExists(b)]
                
                if l_bones:
                    # 7. Запоминаем новую зеркальную позу левых костей
                    l_proxies = self._create_proxies(l_bones, "proxy_L_")
                    l_attr = "{}.{}".format(m_ctrl, attr)
                    l_val = cmds.getAttr(l_attr)
                    
                    # 8-9. Проверка и установка 0 для левого контрола
                    l_ex = cmds.keyframe(l_bones[0], at='tx', q=True, fc=True) or []
                    if not any(abs(k - 0.0) < 0.001 for k in l_ex):
                        self._log("Setting Zero key for Left control: {}".format(m_ctrl))
                        for ln in l_bones: self._key_6(l_attr, 0.0, ln, zero=True)
                    
                    # 10-11. Возврат и ключ для левой стороны
                    self._snap_to(l_bones, l_proxies)
                    for ln in l_bones: self._key_6(l_attr, l_val, ln)
                    cmds.delete(l_proxies)

        elif "Jaw" in drv_obj or "teeth" in drv_obj:
            if abs(drv_val) > 0.001: self._apply_jaw_inversion(driver_attr, drv_val, driven_nodes)

        cmds.delete(r_proxies)
        self._log("Smart KEY process finished.")

    def _key_6(self, drv_at, drv_val, node, zero=False):
        """Ставит ключ на 6 каналов, ПРЕДВАРИТЕЛЬНО ОЧИЩАЯ СВЯЗИ при установке 0."""
        attrs = ['tx','ty','tz','rx','ry','rz']
        for a in attrs:
            attr_full = "{}.{}".format(node, a)
            
            # Если мы ставим 0 (билд позу) и на канале есть связь, которая не является нашей кривой - удаляем её.
            # Это уберет BlendWeighted ноды.
            if zero:
                incoming = cmds.listConnections(attr_full, s=True, d=False)
                if incoming:
                    # Проверяем, не наша ли это уже SDK кривая
                    if not any(cmds.nodeType(x).startswith('animCurve') for x in incoming):
                        cmds.setAttr(attr_full, lock=False)
                        try: cmds.disconnectAttr(cmds.listConnections(attr_full, p=True)[0], attr_full)
                        except: pass

            v = 0 if zero else cmds.getAttr(attr_full)
            cmds.setDrivenKeyframe(attr_full, cd=drv_at, dv=drv_val, v=v)

    def mirror_drivens_logic(self, nodes=None):
        """Зеркалирование через инверсию мировой матрицы (самый точный способ)."""
        targets = nodes if nodes else cmds.ls('mchFcrg*right*', type='joint')
        for r in targets:
            if 'right' not in r: continue
            l = r.replace('right', 'left')
            if cmds.objExists(l):
                # Копируем позицию
                pos = cmds.xform(r, q=True, t=True, ws=True)
                cmds.xform(l, t=[-pos[0], pos[1], pos[2]], ws=True)
                
                # Копируем ротацию и инвертируем оси для симметрии
                # Для стандартного рига: Mirror Rotation X-axis
                rot = cmds.xform(r, q=True, ro=True, os=True)
                # Инвертируем Y и Z ротацию для сохранения симметричного поведения
                cmds.xform(l, ro=[rot[0], -rot[1], -rot[2]], os=True)

    # --- ОСТАЛЬНЫЕ МЕТОДЫ (Без изменений) ---
    def load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
        return {}

    def get_driven_bones(self, ctrl_name):
        config = self.load_json(self.config_path)
        if ctrl_name not in config: return []
        patterns = config[ctrl_name].get("driven", [])
        actual = []
        for p in patterns:
            found = cmds.ls(p, type="joint") if "*" in p else ([p] if cmds.objExists(p) else [])
            actual.extend(found)
        return sorted(list(set(actual)))

    def clean_test_animation(self):
        c = [x for x in self.test_ctrls if cmds.objExists(x)]
        if c: 
            cmds.cutKey(c, s=True)
            for ctrl in c:
                for a in ['tx','ty','tz','rx','ry','rz']:
                    if cmds.getAttr(ctrl+"."+a, settable=True): cmds.setAttr(ctrl+"."+a, 0)

    def run_context_test_animation(self):
        self.clean_test_animation()
        sel = cmds.ls(sl=True)
        if not sel: return
        data = self.load_json(self.anim_path)
        to_anim = []
        if any(x in sel for x in ["EyeLid"]): to_anim = [x for x in self.test_ctrls if "EyeLid" in x]
        elif any(x in sel for x in ["Lip"]): to_anim = ["Lwr_Lip", "Upr_Lip"]
        else: to_animate = [sel[0]]

        for ctrl in to_animate:
            if ctrl in data:
                d = data[ctrl]
                for i, f in enumerate(d.get("frames", [])):
                    if "ty" in d: cmds.setKeyframe(ctrl, at="ty", v=d["ty"][i], t=f)
                    if "tx" in d: cmds.setKeyframe(ctrl, at="tx", v=d["tx"][i], t=f)
        cmds.currentTime(1)

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
            sel = om.MSelectionList(); sel.add(vtx)
            path, comp = sel.getComponent(0); it = om.MItMeshVertex(path, comp)
            p = it.position(om.MSpace.kWorld); pos = [p.x, p.y, p.z]
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