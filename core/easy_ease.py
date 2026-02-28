# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel

class EasyEaseEngine:
    def __init__(self, rig_manager):
        self.mgr = rig_manager
        self.active_data = None
        self.ease_depth = 4 

    def start_ease_blend(self, mesh_name, depth):
        """Восстановленная рабочая логика поиска слоев."""
        self.ease_depth = depth
        joints = cmds.ls(os=True, type='joint')
        if len(joints) < 2: return False
        
        sc_nodes = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc_nodes: return False
        sc = sc_nodes[0]
        bn1, bn2 = joints[0], joints[1]
        
        # 1. Используем острова (как в рабочем Step 3)
        isl1 = self.mgr.get_bone_island(sc, bn1)
        isl2 = self.mgr.get_bone_island(sc, bn2)
        
        if not isl1 or not isl2:
            cmds.warning("FD_FishTool: Одна из костей не имеет весов.")
            return False

        # 2. Построение слоев (топологические лупы)
        layers = []
        processed = set(isl1)
        # Находим стык
        current_frontier = {v for v in isl1 if self.mgr.get_vtx_neighbors([v]) & isl2}
        
        for i in range(self.ease_depth):
            next_layer = (self.mgr.get_vtx_neighbors(list(current_frontier)) - processed) & isl2
            if not next_layer: break
            layers.append(list(next_layer))
            processed.update(next_layer)
            current_frontier = next_layer

        all_vtxs = [v for layer in layers for v in layer]
        if not all_vtxs: return False

        # 3. Изоляция в стиле Twin Machine (с фиксом пропадания меша)
        active_panel = cmds.getPanel(withFocus=True)
        if "modelPanel" in active_panel:
            cmds.isolateSelect(active_panel, state=True)
            cmds.isolateSelect(active_panel, addSelectedObjects=mesh_name) 
            cmds.select(all_vtxs, r=True)
            cmds.isolateSelect(active_panel, addSelected=True)
        
        # 4. Визуализация и Snapshot
        snapshot = {v: cmds.skinPercent(sc, v, q=True, v=True, transform=bn2) for v in all_vtxs}
        shape = cmds.listRelatives(mesh_name, s=True)[0]
        cmds.setAttr(f"{shape}.displayColors", 1)
        cmds.polyOptions(colorShadedDisplay=True)
        mel.eval('polyOptions -sizeVertex 10')
        cmds.select(cl=True)
        
        print("\n" + "="*50)
        print(f"FD_FishTool: EASY EASE ACTIVATED")
        print(f"  > Target: {bn1} (Left) <-> {bn2} (Right)")
        print(f"  > Cloud: {len(all_vtxs)} vertices in {len(layers)} layers.")

        self.active_data = {
            "sc": sc, "bn1": bn1, "bn2": bn2, "layers": layers, 
            "snapshot": snapshot, "panel": active_panel, "vtxs": all_vtxs
        }
        return True

    def update_ease_live(self, offset):
        if not self.active_data: return
        d = self.active_data
        multipliers = [1.0, 0.5, 0.25, 0.1, 0.05, 0.02, 0.01]
        
        for i, layer in enumerate(d["layers"]):
            mult = multipliers[i] if i < len(multipliers) else 0.001
            for v in layer:
                orig_w2 = d["snapshot"][v]
                new_w2 = max(0.0, min(1.0, orig_w2 + (offset * mult)))
                cmds.skinPercent(d["sc"], v, tv=[(d["bn2"], new_w2)], nrm=True)
                
                if offset >= 0: # Blue shift
                    cmds.polyColorPerVertex(v, rgb=(0.0, 0.1, new_w2 * mult))
                else: # Red shift
                    w1 = 1.0 - new_w2
                    cmds.polyColorPerVertex(v, rgb=(w1 * mult, 0.1, 0.0))

    def stop_ease_blend(self):
        if not self.active_data: return
        d = self.active_data
        if "modelPanel" in d["panel"]:
            cmds.isolateSelect(d["panel"], state=False)
        mel.eval('polyOptions -sizeVertex 3')
        cmds.polyColorPerVertex(d["vtxs"], remove=True)
        print("FD_FishTool: EASY EASE COMPLETE.\n" + "="*50)
        self.active_data = None