# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os
import math

class BodyRigManager:
    """Логика автоматизации скелета тела и поэтапного скиннинга."""
    
    def __init__(self, config=None):
        self.cfg = config
        self.map_file = "bone_skin_map.json"

    def get_all_meshes_in_scene(self):
        """Возвращает список трансформ-узлов всех мешей в сцене."""
        mesh_shapes = cmds.ls(type='mesh', ni=True) or []
        mesh_transforms = []
        for shape in mesh_shapes:
            parent = cmds.listRelatives(shape, p=True, f=False)
            if parent: mesh_transforms.append(parent[0])
        return sorted(list(set(mesh_transforms)))

    def find_default_mesh(self):
        """Интеллектуальный поиск меша по имени сцены и суффиксам."""
        scene_path = cmds.file(q=True, sn=True, shn=True)
        scene_name = os.path.splitext(scene_path)[0].lower() if scene_path else ""
        all_meshes = self.get_all_meshes_in_scene()
        if not all_meshes: return ""
        priority_suffixes = ['_geo', '_mesh', '_msh', '_low']
        if scene_name:
            for mesh in all_meshes:
                if mesh.lower() in scene_name or scene_name in mesh.lower(): return mesh
        for mesh in all_meshes:
            for sfx in priority_suffixes:
                if sfx in mesh.lower(): return mesh
        return all_meshes[0]

    def get_direct_chain(self, start_node):
        """Сбор костей строго по цепочке (только первый ребенок)."""
        chain = [start_node]
        current = start_node
        while True:
            children = cmds.listRelatives(current, children=True, type='joint') or []
            if not children: break
            current = children[0]
            chain.append(current)
        return chain

    def get_chain_between(self, start_jnt, end_jnt):
        """Находит все кости между двумя выбранными (Start -> End)."""
        if not cmds.objExists(start_jnt) or not cmds.objExists(end_jnt): return []
        descendants = cmds.listRelatives(start_jnt, ad=True, type='joint') or []
        if end_jnt not in descendants and start_jnt != end_jnt:
            cmds.warning(f"Кость {end_jnt} не является потомком {start_jnt}.")
            return []
        chain = [end_jnt]
        curr = end_jnt
        while curr != start_jnt:
            parent = cmds.listRelatives(curr, p=True, type='joint')
            if not parent: break
            curr = parent[0]
            chain.append(curr)
        chain.reverse()
        return chain

    def apply_weight_gradient_logic(self, mesh_name):
        """
        Инструмент 'Hierarchical Blur': распределяет веса между соседями по цепочке.
        Реализация твоей логики: i-1(0.25), i+1(0.25), i+2(0.1).
        """
        sel = cmds.ls(sl=True, type='joint')
        if len(sel) != 2:
            cmds.warning("Выделите Start Bone, затем End Bone цепочки.")
            return

        bone_chain = self.get_chain_between(sel[0], sel[1])
        if not bone_chain or not cmds.objExists(mesh_name): return

        sc_nodes = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc_nodes: return
        sc = sc_nodes[0]

        print(f"--- [RigBody] Applying Hierarchical Blur for {len(bone_chain)} bones ---")

        # 1. Группируем все вертексы меша по их 'владельцу' в нашей цепочке
        all_inf = cmds.skinCluster(sc, q=True, inf=True)
        vtx_count = cmds.polyEvaluate(mesh_name, v=True)
        groups = {bone: [] for bone in bone_chain}

        for i in range(vtx_count):
            vtx = f"{mesh_name}.vtx[{i}]"
            # Получаем веса только для нашей цепочки (быстрым способом через индекс)
            all_weights = cmds.skinPercent(sc, vtx, q=True, v=True)
            chain_weights = [all_weights[all_inf.index(b)] for b in bone_chain]
            
            max_val = max(chain_weights)
            if max_val < 0.05: continue # Пропускаем вертексы без влияния цепочки
            
            dominant_bone = bone_chain[chain_weights.index(max_val)]
            groups[dominant_bone].append(vtx)

        # 2. Перераспределяем веса для каждой группы согласно твоей схеме
        for i, current_bone in enumerate(bone_chain):
            vtx_list = groups[current_bone]
            if not vtx_list: continue

            tv_list = []
            assigned_sum = 0.0

            # 1 шаг ВВЕРХ (0.25)
            if i - 1 >= 0:
                tv_list.append((bone_chain[i-1], 0.25))
                assigned_sum += 0.25
            # 1 шаг ВНИЗ (0.25)
            if i + 1 < len(bone_chain):
                tv_list.append((bone_chain[i+1], 0.25))
                assigned_sum += 0.25
            # 2 шага ВНИЗ (0.1)
            if i + 2 < len(bone_chain):
                tv_list.append((bone_chain[i+2], 0.1))
                assigned_sum += 0.1

            # Текущая кость забирает остаток (например, 0.4)
            tv_list.append((current_bone, 1.0 - assigned_sum))

            # Применяем пачкой к вертексам этой кости
            cmds.skinPercent(sc, vtx_list, tv=tv_list)

        cmds.select(sel, r=True)
        print("FD_FishTool: Иерархический градиент успешно распределен.")

    def add_to_skin_logic(self, stage_index, mesh_name):
        """Поэтапный скиннинг."""
        if not mesh_name or not cmds.objExists(mesh_name): return
        bones = self.get_full_bone_list(f"stage_{stage_index}")
        if not bones: return
        history = cmds.listHistory(mesh_name)
        sc = cmds.ls(history, type='skinCluster')
        if stage_index == 1:
            if not sc:
                cmds.select(bones, r=True); cmds.select(mesh_name, add=True)
                cmds.skinCluster(tsb=True, bm=0, nw=1, wd=0, mi=4, omi=True, dr=4, rui=False)
            else: cmds.warning("SkinCluster уже существует.")
        else:
            if not sc: return
            existing = cmds.skinCluster(sc[0], q=True, inf=True) or []
            for b in bones:
                if b not in existing: cmds.skinCluster(sc[0], edit=True, ai=b, lw=True, wt=0)

    def select_stage_bones(self, stage_index):
        bones = self.get_full_bone_list(f"stage_{stage_index}")
        if bones: cmds.select(bones, r=True)

    def select_weighted_bones(self, mesh_name):
        if not mesh_name or not cmds.objExists(mesh_name): return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if sc:
            infl = cmds.skinCluster(sc[0], q=True, inf=True)
            if infl: cmds.select(infl, r=True)

    def clean_weightless_bones(self, mesh_name):
        if not mesh_name or not cmds.objExists(mesh_name): return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc: return
        cmds.select(mesh_name, r=True)
        try:
            mel.eval("removeUnusedInfluences;")
            cmds.skinCluster(sc[0], edit=True, rui=True)
        finally: cmds.select(cl=True)

    def center_and_find_seam(self):
        sel = cmds.ls(sl=True, type='transform')
        target = sel[0] if sel else 'fish'
        if not cmds.objExists(target): return
        bbox = cmds.exactWorldBoundingBox(target)
        cmds.move(-(bbox[0]+bbox[3])/2, 0, 0, target, r=True, ws=True)

    def smart_hierarchy_fix(self):
        if cmds.objExists('Head1'): cmds.rename('Head1', 'Face')