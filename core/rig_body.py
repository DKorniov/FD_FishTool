# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os

class BodyRigManager:
    def __init__(self, config=None):
        self.cfg = config
        self.map_file = "bone_skin_map.json"

    # --- Вспомогательные методы (Mesh & Lists) ---
    def get_all_meshes_in_scene(self):
        mesh_shapes = cmds.ls(type='mesh', ni=True) or []
        mesh_transforms = []
        for shape in mesh_shapes:
            parent = cmds.listRelatives(shape, p=True)
            if parent: mesh_transforms.append(parent[0])
        return sorted(list(set(mesh_transforms)))

    def find_default_mesh(self):
        scene_name = os.path.splitext(cmds.file(q=True, sn=True, shn=True))[0].lower()
        all_meshes = self.get_all_meshes_in_scene()
        if not all_meshes: return ""
        for m in all_meshes:
            if scene_name and scene_name in m.lower(): return m
            if any(s in m.lower() for s in ['_geo', '_mesh', '_msh']): return m
        return all_meshes[0]

    # --- Хирургическая Топологическая Логика ---
    def get_vtx_neighbors(self, vtx_list):
        """Находит соседей через эджи (топологический шаг)."""
        if not vtx_list: return set()
        edges = cmds.polyListComponentConversion(list(vtx_list), toEdge=True)
        neighbors = cmds.polyListComponentConversion(edges, toVertex=True)
        return set(cmds.ls(neighbors, fl=True))

    def get_bone_influence_island(self, sc, bone):
        """Получает массив вертексов, на которые влияет кость (из логики skinMagic)."""
        # Используем API-метод через cmds для получения точек влияния
        try:
            # Находим индекс кости в скинкластере
            all_inf = cmds.skinCluster(sc, q=True, inf=True)
            if bone not in all_inf: return set()
            
            # Получаем вертексы с весом > 0 для этой кости
            cmds.select(cl=True)
            cmds.skinCluster(sc, edit=True, selectInfluenceVerts=bone)
            island = set(cmds.ls(sl=True, fl=True))
            return island
        except:
            return set()

    def apply_topological_gradient(self, mesh_name):
        """Островной градиент: работает только с вертексами выделенных костей."""
        joints = cmds.ls(sl=True, type='joint')
        if len(joints) < 2:
            cmds.warning("Выделите хотя бы 2 кости (в порядке распределения).")
            return

        sc_list = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc_list: return
        sc = sc_list[0]

        print("--- [RigBody] Island-Based Gradient Logic Start ---")

        # Обрабатываем последовательно по парам из выделения (без иерархии)
        for i in range(len(joints) - 1):
            bnA, bnB = joints[i], joints[i+1]
            
            # 1. Получаем 'Острова' вертексов
            islandA = self.get_bone_influence_island(sc, bnA)
            islandB = self.get_bone_influence_island(sc, bnB)

            if not islandA or not islandB:
                print("  > Pair {}-{}: One island is empty. Skipping.".format(bnA, bnB))
                continue

            # 2. Находим ШОВ (вертексы A, касающиеся B, и наоборот)
            seamA = {v for v in islandA if self.get_vtx_neighbors([v]) & islandB}
            seamB = {v for v in islandB if self.get_vtx_neighbors([v]) & islandA}
            full_seam = list(seamA | seamB)

            if not full_seam:
                print("  > Pair {}-{}: No topological contact found.".format(bnA, bnB))
                continue

            print("  > Pair {}-{}: Seam found ({} vtx). Applying layers.".format(bnA, bnB, len(full_seam)))

            # 3. Слои BFS строго ВНУТРИ островов
            # Слои для А (вглубь острова А)
            l1A = (self.get_vtx_neighbors(seamA) & islandA) - seamA
            l2A = (self.get_vtx_neighbors(list(l1A)) & islandA) - seamA - l1A
            
            # Слои для B (вглубь острова B)
            l1B = (self.get_vtx_neighbors(seamB) & islandB) - seamB
            l2B = (self.get_vtx_neighbors(list(l1B)) & islandB) - seamB - l1B

            # 4. Хирургическое назначение весов (только для этой пары)
            # Шов: 0.5 / 0.5
            cmds.skinPercent(sc, full_seam, tv=[(bnA, 0.5), (bnB, 0.5)], nrm=True)
            # Шаг 1: 0.25 от соседа
            if l1A: cmds.skinPercent(sc, list(l1A), tv=[(bnA, 0.75), (bnB, 0.25)], nrm=True)
            if l1B: cmds.skinPercent(sc, list(l1B), tv=[(bnB, 0.75), (bnA, 0.25)], nrm=True)
            # Шаг 2: 0.1 от соседа
            if l2A: cmds.skinPercent(sc, list(l2A), tv=[(bnA, 0.9), (bnB, 0.1)], nrm=True)
            if l2B: cmds.skinPercent(sc, list(l2B), tv=[(bnB, 0.9), (bnA, 0.1)], nrm=True)

        cmds.select(joints, r=True)
        print("FD_FishTool: Островной топологический градиент завершен.")

    # --- Секция Скиннинга ---
    def get_full_bone_list(self, stage_key):
        data = self.cfg.load_json(self.map_file)
        if not data or stage_key not in data: return []
        s_data = data[stage_key]
        final = []
        # Собираем прямые цепи
        if "chains" in s_data:
            for r in s_data["chains"]:
                if cmds.objExists(r):
                    chain = [r]
                    curr = r
                    while True:
                        child = cmds.listRelatives(curr, c=True, type='joint')
                        if not child: break
                        curr = child[0]; chain.append(curr)
                    final.extend(chain)
        # Собираем корни
        if "roots" in s_data:
            for r in s_data["roots"]:
                if cmds.objExists(r):
                    final.append(r)
                    final.extend(cmds.listRelatives(r, ad=True, type='joint') or [])
        if "list" in s_data: final.extend(s_data["list"])
        return sorted(list(set([j for j in final if cmds.objExists(j)])))

    def select_stage_bones(self, stage_index):
        bones = self.get_full_bone_list("stage_{}".format(stage_index))
        if bones: cmds.select(bones, r=True)

    def add_to_skin_logic(self, stage_index, mesh_name):
        if not mesh_name or not cmds.objExists(mesh_name): return
        bones = self.get_full_bone_list("stage_{}".format(stage_index))
        if not bones: return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if stage_index == 1 and not sc:
            cmds.select(bones, r=True); cmds.select(mesh_name, add=True)
            cmds.skinCluster(tsb=True, bm=0, nw=1, wd=0, mi=4, omi=True, dr=4, rui=False)
        elif sc:
            existing = cmds.skinCluster(sc[0], q=True, inf=True)
            for b in bones:
                if b not in existing: cmds.skinCluster(sc[0], edit=True, ai=b, lw=True, wt=0)

    def select_weighted_bones(self, mesh_name):
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if sc: cmds.select(cmds.skinCluster(sc[0], q=True, inf=True), r=True)

    def clean_weightless_bones(self, mesh_name):
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if sc:
            cmds.select(mesh_name, r=True)
            mel.eval("removeUnusedInfluences;")
            cmds.skinCluster(sc[0], edit=True, rui=True)