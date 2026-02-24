# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os

class BodyRigManager:
    def __init__(self, config=None):
        self.cfg = config
        self.map_file = "bone_skin_map.json"

    # --- Вспомогательные методы (Рабочая версия) ---
    def get_all_meshes_in_scene(self):
        mesh_shapes = cmds.ls(type='mesh', ni=True) or []
        mesh_transforms = [cmds.listRelatives(s, p=True)[0] for s in mesh_shapes if cmds.listRelatives(s, p=True)]
        return sorted(list(set(mesh_transforms)))

    def find_default_mesh(self):
        scene_name = os.path.splitext(cmds.file(q=True, sn=True, shn=True))[0].lower()
        all_meshes = self.get_all_meshes_in_scene()
        if not all_meshes: return ""
        for m in all_meshes:
            if scene_name and scene_name in m.lower(): return m
            if any(s in m.lower() for s in ['_geo', '_mesh', '_msh']): return m
        return all_meshes[0]

    def get_vtx_neighbors(self, vtx_list):
        if not vtx_list: return set()
        edges = cmds.polyListComponentConversion(list(vtx_list), toEdge=True)
        neighbors = cmds.polyListComponentConversion(edges, toVertex=True)
        return set(cmds.ls(neighbors, fl=True))

    def get_bone_island(self, sc, bone):
        """Рабочий метод получения островов через выделение."""
        try:
            cmds.select(cl=True)
            cmds.skinCluster(sc, edit=True, selectInfluenceVerts=bone)
            return set(cmds.ls(sl=True, fl=True))
        except: return set()

    def get_topology_distance(self, start_island, target_island):
        """Считает количество 'лупов' между двумя островами (Рабочая версия)."""
        current_area = set(start_island)
        edge_vtx = set(start_island)
        for i in range(1, 11):
            next_step = self.get_vtx_neighbors(list(edge_vtx)) - current_area
            if not next_step: break
            if next_step & target_island:
                return i
            current_area.update(next_step)
            edge_vtx = next_step
        return 10

    def apply_topological_gradient(self, mesh_name):
        """Стабильный мульти-режимный градиент (Step 3 XL)."""
        joints = cmds.ls(os=True, type='joint')
        if len(joints) < 2: return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')[0]

        MODES = {
            1: {"name": "DENSE", "steps": [0.25, 0.1]},
            2: {"name": "STANDARD", "steps": [0.5, 0.25, 0.1]},
            3: {"name": "STANDARD XL", "steps": [0.75, 0.5, 0.25, 0.1]},
            4: {"name": "STANDARD XXL", "steps": [0.9, 0.75, 0.5, 0.25, 0.1]},
            5: {"name": "STANDARD XXXL", "steps": [1.0, 0.9, 0.75, 0.5, 0.25, 0.1]}
        }

        print("\n" + "="*70 + "\nFD_FishTool: ADAPTIVE XL GRADIENT (STABLE CHECKPOINT)\n" + "="*70)

        def expand(src_bone, tgt_bone, label):
            src_isl = self.get_bone_island(sc, src_bone); tgt_isl = self.get_bone_island(sc, tgt_bone)
            if not src_isl or not tgt_isl: return
            dist = self.get_topology_distance(src_isl, tgt_isl)
            mode = MODES[dist if dist in MODES else 5]
            print(f"  [{label}] {src_bone} -> {tgt_bone} | Dist: {dist} | Mode: {mode['name']}")

            frontier = {v for v in src_isl if self.get_vtx_neighbors([v]) - src_isl}
            curr_area = set(src_isl); prev_loop = set(frontier)
            for idx, weight in enumerate(mode["steps"]):
                next_loop = (self.get_vtx_neighbors(list(prev_loop)) - curr_area) & tgt_isl
                if next_loop:
                    cmds.skinPercent(sc, list(next_loop), tv=[(src_bone, weight)], relative=True, nrm=True)
                    print(f"    > Row {idx+1}: ADD {weight}")
                    curr_area.update(next_loop); prev_loop = next_loop
                else: break

        for i in range(len(joints)):
            if i + 1 < len(joints): expand(joints[i], joints[i+1], "FORWARD")
            if i - 1 >= 0: expand(joints[i], joints[i-1], "BACKWARD")
        cmds.select(joints, r=True)

    # --- Секция Скиннинга (Рабочая фильтрация плавников) ---
    def get_full_bone_list(self, stage_key):
        data = self.cfg.load_json(self.map_file)
        if not data or stage_key not in data: return []
        s_data = data[stage_key]; final = []
        if "chains" in s_data:
            for r in s_data["chains"]:
                if cmds.objExists(r):
                    final.append(r); curr = r
                    while True:
                        child = cmds.listRelatives(curr, c=True, type='joint')
                        if not child: break
                        curr = child[0]; final.append(curr)
        if "roots" in s_data:
            for r in s_data["roots"]:
                if cmds.objExists(r):
                    final.append(r); final.extend(cmds.listRelatives(r, ad=True, type='joint') or [])
        if "list" in s_data: final.extend(s_data["list"])
        return sorted(list(set([j for j in final if cmds.objExists(j)])))

    def select_stage_bones(self, idx):
        bones = self.get_full_bone_list(f"stage_{idx}")
        if bones: cmds.select(bones, r=True)

    def add_to_skin_logic(self, idx, mesh):
        bones = self.get_full_bone_list(f"stage_{idx}")
        if not bones or not cmds.objExists(mesh): return
        sc = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        if idx == 1 and not sc:
            cmds.select(bones, r=True); cmds.select(mesh, add=True)
            cmds.skinCluster(tsb=True, bm=0, nw=1, wd=0, mi=4, omi=True, dr=4, rui=False)
        elif sc:
            existing = cmds.skinCluster(sc[0], q=True, inf=True)
            for b in bones:
                if b not in existing: cmds.skinCluster(sc[0], edit=True, ai=b, lw=True, wt=0)

    def select_weighted_bones(self, mesh):
        sc = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        if sc: cmds.select(cmds.skinCluster(sc[0], q=True, inf=True), r=True)

    def clean_weightless_bones(self, mesh):
        sc = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        if sc:
            cmds.select(mesh, r=True); mel.eval("removeUnusedInfluences;")
            cmds.skinCluster(sc[0], edit=True, rui=True)