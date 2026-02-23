# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os

class BodyRigManager:
    def __init__(self, config=None):
        self.cfg = config
        self.map_file = "bone_skin_map.json"

    # --- Вспомогательные методы ---
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
        try:
            cmds.select(cl=True)
            cmds.skinCluster(sc, edit=True, selectInfluenceVerts=bone)
            return set(cmds.ls(sl=True, fl=True))
        except: return set()

    def get_topology_distance(self, start_island, target_island):
        """Считает количество 'лупов' между двумя островами."""
        distance = 0
        current_area = set(start_island)
        edge_vtx = set(start_island)
        
        # Максимум 10 шагов для безопасности
        for i in range(1, 11):
            next_step = self.get_vtx_neighbors(list(edge_vtx)) - current_area
            if not next_step: break
            if next_step & target_island:
                return i
            current_area.update(next_step)
            edge_vtx = next_step
        return 10

    def apply_topological_gradient(self, mesh_name):
        """
        [STEP 3 - XL UPDATE] Адаптивная экспансия с поддержкой длинных градиентов.
        Выбирает схему весов на основе топологического расстояния.
        """
        joints = cmds.ls(os=True, type='joint')
        if len(joints) < 2:
            cmds.warning("Выделите цепочку костей по порядку."); return

        sc_list = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc_list: return
        sc = sc_list[0]

        # Конфигурация режимов
        MODES = {
            1: {"name": "DENSE", "steps": [0.25, 0.1]},
            2: {"name": "STANDARD", "steps": [0.5, 0.25, 0.1]},
            3: {"name": "STANDARD XL (Deep)", "steps": [0.75, 0.5, 0.25, 0.1]},
            4: {"name": "STANDARD XXL (Ultra)", "steps": [0.9, 0.75, 0.5, 0.25, 0.1]},
            5: {"name": "STANDARD XXXL (Infinite)", "steps": [1.0, 0.9, 0.75, 0.5, 0.25, 0.1]}
        }

        print("\n" + "="*70)
        print("FD_FishTool: SURGICAL ADAPTIVE EXPANSION (MULTI-MODE)")
        print("Chain: {}".format(" -> ".join(joints)))
        print("="*70)

        def expand_influence(source_bone, target_bone, label_direction):
            src_island = self.get_bone_island(sc, source_bone)
            tgt_island = self.get_bone_island(sc, target_bone)
            if not src_island or not tgt_island: return

            # Определяем расстояние и выбираем режим
            dist = self.get_topology_distance(src_island, tgt_island)
            mode_key = dist if dist in MODES else max(MODES.keys())
            mode = MODES[mode_key]
            
            print("\n  [{}] {} -> {} | Distance: {} | Mode: {}".format(
                label_direction, source_bone, target_bone, dist, mode["name"]))

            # Фронтир источника
            frontier = {v for v in src_island if self.get_vtx_neighbors([v]) - src_island}
            if not frontier: return

            current_source_area = set(src_island)
            previous_loop = set(frontier)
            
            for idx, weight in enumerate(mode["steps"]):
                next_loop = self.get_vtx_neighbors(list(previous_loop)) - current_source_area
                # Ограничиваем инвазию территорией цели
                next_loop = next_loop & tgt_island if tgt_island else next_loop
                
                if next_loop:
                    cmds.skinPercent(sc, list(next_loop), tv=[(source_bone, weight)], relative=True, nrm=True)
                    print("    > Row {}: {} vtx -> ADD {} weight for {}".format(idx+1, len(next_loop), weight, source_bone))
                    current_source_area.update(next_loop)
                    previous_loop = next_loop
                else: break

        for i in range(len(joints)):
            if i + 1 < len(joints): expand_influence(joints[i], joints[i+1], "FORWARD")
            if i - 1 >= 0: expand_influence(joints[i], joints[i-1], "BACKWARD")

        cmds.select(joints, r=True)
        print("\n" + "="*70 + "\nFD_FishTool: ALL TASKS COMPLETE.\n" + "="*70)

    # --- Стандартные методы скиннинга (без изменений) ---
    def get_full_bone_list(self, stage_key):
        data = self.cfg.load_json(self.map_file)
        if not data or stage_key not in data: return []
        s_data = data[stage_key]
        final = []
        if "chains" in s_data:
            for r in s_data["chains"]:
                if cmds.objExists(r):
                    chain = [r]; curr = r
                    while True:
                        child = cmds.listRelatives(curr, c=True, type='joint')
                        if not child: break
                        curr = child[0]; chain.append(curr)
                    final.extend(chain)
        if "roots" in s_data:
            for r in s_data["roots"]:
                if cmds.objExists(r):
                    final.append(r); final.extend(cmds.listRelatives(r, ad=True, type='joint') or [])
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
            cmds.select(mesh_name, r=True); mel.eval("removeUnusedInfluences;")
            cmds.skinCluster(sc[0], edit=True, rui=True)