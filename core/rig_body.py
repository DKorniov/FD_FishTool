# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os
import math

class BodyRigManager:
    """Логика автоматизации скелета тела, поэтапного скиннинга и градиентов весов."""
    
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
                if mesh.lower() in scene_name or scene_name in mesh.lower():
                    return mesh
        for mesh in all_meshes:
            for sfx in priority_suffixes:
                if sfx in mesh.lower(): return mesh
        return all_meshes[0]

    def get_direct_chain(self, start_node):
        """Сбор костей строго по прямой цепочке (только первый ребенок)."""
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
            cmds.warning(f"{end_jnt} не потомок {start_jnt}. Выбирайте сверху вниз.")
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

    def get_full_bone_list(self, stage_key):
        """Сбор костей согласно правилам из JSON (roots, chains, list)."""
        data = self.cfg.load_json(self.map_file)
        if stage_key not in data: return []
        
        s_data = data[stage_key]
        final_list = []
        if "chains" in s_data:
            for root in s_data["chains"]:
                if cmds.objExists(root): final_list.extend(self.get_direct_chain(root))
        if "roots" in s_data:
            for root in s_data["roots"]:
                if cmds.objExists(root):
                    final_list.append(root)
                    final_list.extend(cmds.listRelatives(root, ad=True, type='joint') or [])
        if "list" in s_data:
            final_list.extend(s_data["list"])
        return sorted(list(set([j for j in final_list if cmds.objExists(j)])))

    def select_stage_bones(self, stage_index):
        """Выделяет кости этапа."""
        bones = self.get_full_bone_list(f"stage_{stage_index}")
        if bones: cmds.select(bones, r=True)

    def add_to_skin_logic(self, stage_index, mesh_name):
        """Поэтапное добавление в скин (Stage 1 - Bind, Stage 2+ - Add Influence)."""
        if not mesh_name or not cmds.objExists(mesh_name): return
        bones = self.get_full_bone_list(f"stage_{stage_index}")
        if not bones: return
        
        history = cmds.listHistory(mesh_name)
        sc = cmds.ls(history, type='skinCluster')
        
        if stage_index == 1:
            if not sc:
                cmds.select(bones, r=True); cmds.select(mesh_name, add=True)
                cmds.skinCluster(tsb=True, bm=0, nw=1, wd=0, mi=4, omi=True, dr=4, rui=False)
            else: cmds.warning("SkinCluster уже есть. Используйте Stage 2-4.")
        else:
            if not sc: return
            existing = cmds.skinCluster(sc[0], q=True, inf=True) or []
            for b in bones:
                if b not in existing:
                    # Добавляем в скин: Lock=On, Weight=0
                    cmds.skinCluster(sc[0], edit=True, ai=b, lw=True, wt=0)
            print(f"FD_FishTool: Stage {stage_index} added to {sc[0]}.")

    def apply_weight_gradient_logic(self, mesh_name):
        """
        Инструмент 'Hierarchical Blur': распределяет веса по твоей схеме:
        i-1 (0.25), i+1 (0.25), i+2 (0.1). Остаток на саму кость.
        """
        sel = cmds.ls(sl=True, type='joint')
        if len(sel) != 2:
            cmds.warning("Выделите Start Bone, затем End Bone цепочки."); return
        
        bone_chain = self.get_chain_between(sel[0], sel[1])
        if not bone_chain or not cmds.objExists(mesh_name): return
        
        sc_nodes = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc_nodes: return
        sc = sc_nodes[0]

        # 1. Группируем вертексы по доминантной кости (где вес максимальный)
        all_inf = cmds.skinCluster(sc, q=True, inf=True)
        vtx_count = cmds.polyEvaluate(mesh_name, v=True)
        buckets = {bone: [] for bone in bone_chain}

        print("--- [RigBody] Sorting vertices by dominance ---")
        for i in range(vtx_count):
            vtx = "{}.vtx[{}]".format(mesh_name, i)
            # Query всех весов разом (быстрее)
            all_weights = cmds.skinPercent(sc, vtx, q=True, v=True)
            
            # Находим макс. влияние среди костей нашей цепи
            chain_weights = []
            for b in bone_chain:
                try: chain_weights.append(all_weights[all_inf.index(b)])
                except: chain_weights.append(0.0)
            
            max_val = max(chain_weights)
            if max_val > 0.05:
                dom_idx = chain_weights.index(max_val)
                buckets[bone_chain[dom_idx]].append(vtx)

        # 2. Применяем распределение для каждого бакета
        for i, bone in enumerate(bone_chain):
            vtxs = buckets[bone]
            if not vtxs: continue
            
            tv = []
            assigned = 0.0
            if i-1 >= 0:
                tv.append((bone_chain[i-1], 0.25)); assigned += 0.25
            if i+1 < len(bone_chain):
                tv.append((bone_chain[i+1], 0.25)); assigned += 0.25
            if i+2 < len(bone_chain):
                tv.append((bone_chain[i+2], 0.1)); assigned += 0.1
            
            # Остаток веса на саму кость
            tv.append((bone, 1.0 - assigned))
            cmds.skinPercent(sc, vtxs, tv=tv)

        cmds.select(sel, r=True)
        print(f"FD_FishTool: Градиент применен для {len(bone_chain)} костей.")

    def select_weighted_bones(self, mesh_name):
        """Выделяет кости, влияющие на меш."""
        if not cmds.objExists(mesh_name): return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if sc:
            infl = cmds.skinCluster(sc[0], q=True, inf=True)
            if infl: cmds.select(infl, r=True)

    def clean_weightless_bones(self, mesh_name):
        """Принудительное удаление костей с 0 весом."""
        if not mesh_name or not cmds.objExists(mesh_name): return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc: return
        old_sel = cmds.ls(sl=True)
        cmds.select(mesh_name, r=True)
        try:
            mel.eval("removeUnusedInfluences;")
            cmds.skinCluster(sc[0], edit=True, rui=True)
        finally:
            if old_sel: cmds.select(old_sel, r=True)

    def center_and_find_seam(self):
        target = cmds.ls(sl=True, type='transform')
        if not target: target = ['fish']
        if not cmds.objExists(target[0]): return
        bbox = cmds.exactWorldBoundingBox(target[0])
        cmds.move(-(bbox[0]+bbox[3])/2, 0, 0, target[0], r=True, ws=True)

    def smart_hierarchy_fix(self):
        if cmds.objExists('Head1'): cmds.rename('Head1', 'Face')