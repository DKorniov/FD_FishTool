# -*- coding: utf-8 -*-
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds
import os
import re
import json
import xml.etree.ElementTree as ET

class FishValidator:
    def __init__(self, config_manager=None):
        self.cfg = config_manager
        self.errors = []
        self.success_log = []

    def validate_all(self):
        self.errors = []
        self.success_log = []
        
        # Данные из папки data (через ConfigManager)
        data_dir = self.cfg.data_path if self.cfg else ""
        
        # 1. Валидация нейминга (Логика из naming_subscript)
        self._check_naming_logic(data_dir)
        
        # 2. Валидация материалов (Логика из materials_subscript)
        self._check_materials_logic()
        
        # 3. Технический скан мешей (Кости в скине < 80 и Influence Max 4)
        meshes = cmds.ls(type='mesh', noIntermediate=True)
        for mesh in meshes:
            self._check_mesh_technical(mesh)
            
        return self.errors, self.success_log

    def _normalize(self, s):
        s = (s or "").strip().lower()
        s = re.sub(r"[ \-]+", "_", s)
        return re.sub(r"_+", "_", s)

    def _check_naming_logic(self, data_dir):
        xml_path = os.path.join(data_dir, "MetaLinks.xml")
        alias_path = os.path.join(data_dir, "bone_aliases.json")
        
        # Грузим эталон из XML
        etalon = []
        if os.path.exists(xml_path):
            try:
                root = ET.parse(xml_path).getroot()
                etalon = [mj.attrib.get("base") for mj in root.iter("MetaJoint") if mj.attrib.get("base")]
            except: pass
        
        # Грузим алиасы
        aliases_map = {}
        if os.path.exists(alias_path):
            try:
                with open(alias_path, 'r') as f:
                    raw_aliases = json.load(f)
                    for canon, variants in raw_aliases.items():
                        c_norm = self._normalize(canon)
                        for v in variants:
                            aliases_map[self._normalize(v)] = c_norm
            except: pass

        scene_joints = [self._normalize(j) for j in (cmds.ls(type='joint') or [])]
        etalon_norm = [self._normalize(e) for e in etalon]
        
        missing = []
        for e_n in etalon_norm:
            # Проверяем есть ли кость или её алиас в сцене
            found = (e_n in scene_joints)
            if not found:
                # Ищем среди ключей алиасов, чье значение = e_n
                found = any(alias_v for alias_v, canon in aliases_map.items() if canon == e_n and alias_v in scene_joints)
            
            if not found:
                # Находим исходное имя из XML для отчета
                orig_name = next((x for x in etalon if self._normalize(x) == e_n), e_n)
                missing.append(orig_name)

        if missing:
            for m in missing:
                self.errors.append(f"NAMING: Отсутствует обязательная кость: {m}")
        else:
            self.success_log.append("Naming: Все кости из MetaLinks.xml найдены (с учетом алиасов).")

    def _check_materials_logic(self):
        # Список из materials_subscript
        required_mats = ["mat_opaque", "mat_overlap_eyes", "mat_overlap_teeth", "mat_transparent"]
        scene_mats = cmds.ls(materials=True)
        
        valid_count = 0
        for rm in required_mats:
            if rm in scene_mats and cmds.nodeType(rm) == "phong":
                valid_count += 1
            else:
                self.errors.append(f"MAT: Материал '{rm}' (Phong) не найден в сцене.")
        
        if valid_count == len(required_mats):
            self.success_log.append("Materials: Все базовые материалы проекта созданы.")

    def _check_mesh_technical(self, mesh_node):
        transform = cmds.listRelatives(mesh_node, parent=True)[0]
        history = cmds.listHistory(mesh_node)
        skins = cmds.ls(history, type='skinCluster')
        
        if not skins: return

        # А) Проверка количества костей в СКИНЕ (< 80)
        influences = cmds.skinCluster(skins[0], q=True, inf=True) or []
        inf_count = len(influences)
        if inf_count >= 80:
            self.errors.append(f"LIMIT: Меш '{transform}' содержит {inf_count} костей в скине (Лимит < 80).")
        else:
            self.success_log.append(f"Skin Count: '{transform}' использует {inf_count} костей (OK).")

        # Б) Проверка Max 4 Influences (OpenMaya 2.0)
        self._scan_influences_om2(mesh_node, skins[0], transform)

    def _scan_influences_om2(self, mesh_name, skin_cluster, transform_name):
        sel = om.MSelectionList()
        sel.add(mesh_name)
        dag_path = sel.getDagPath(0)
        
        m_skin = om.MSelectionList()
        m_skin.add(skin_cluster)
        skin_fn = oma.MFnSkinCluster(m_skin.getDependNode(0))
        
        it_geo = om.MItGeometry(dag_path)
        bad_vtx = 0
        while not it_geo.isDone():
            weights, _ = skin_fn.getWeights(dag_path, it_geo.currentItem())
            if len([w for w in weights if w > 0.001]) > 4:
                bad_vtx += 1
            it_geo.next()
            
        if bad_vtx > 0:
            self.errors.append(f"INFLUENCE: '{transform_name}' имеет {bad_vtx} вершин с влиянием > 4 костей.")
        else:
            self.success_log.append(f"Influence Check: '{transform_name}' прошел проверку (Max 4).")