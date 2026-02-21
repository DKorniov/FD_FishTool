# -*- coding: utf-8 -*-
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

class FishValidator:
    def __init__(self):
        self.errors = []

    def validate(self):
        """Основной метод проверки. Возвращает список строк-ошибок."""
        self.errors = []
        self._check_bone_limit()
        self._check_materials()
        
        # Проверка скина на всех видимых мешах
        meshes = cmds.ls(type='mesh', noIntermediate=True)
        for m in meshes:
            self._check_skin_influences(m)
            
        return self.errors

    def _check_bone_limit(self):
        joints = cmds.ls(type='joint')
        if len(joints) >= 80:
            self.errors.append(f"CRITICAL: {len(joints)} костей в сцене. Лимит для экспорта < 80.")

    def _check_skin_influences(self, mesh_name):
        """API 2.0: Проверка Max 4 Influence на вершину"""
        sel = om.MSelectionList()
        try: sel.add(mesh_name)
        except: return
        
        dag = sel.getDagPath(0)
        skin_clusters = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not skin_clusters: return

        m_skin = om.MSelectionList()
        m_skin.add(skin_clusters[0])
        skin_fn = oma.MFnSkinCluster(m_skin.getDependNode(0))
        
        it_geo = om.MItGeometry(dag)
        while not it_geo.isDone():
            weights, _ = skin_fn.getWeights(dag, it_geo.currentItem())
            # Считаем веса выше порога погрешности
            inf_count = sum(1 for w in weights if w > 0.001)
            if inf_count > 4:
                self.errors.append(f"SKIN: {mesh_name} vertex[{it_geo.index()}] has {inf_count} influences (Max: 4).")
                break # Хватит одной ошибки на меш
            it_geo.next()

    def _check_materials(self):
        """Проверка названий материалов по манифесту (opaque/transparent)"""
        mats = cmds.ls(materials=True)
        valid_keywords = ['opaque', 'transparent']
        for m in mats:
            # Игнорируем стандартные ноды
            if m in ['lambert1', 'particleCloud1', 'standardSurface1']: continue
            if not any(kw in m.lower() for kw in valid_keywords):
                self.errors.append(f"MATERIAL: '{m}' name invalid. Must contain 'opaque' or 'transparent'.")