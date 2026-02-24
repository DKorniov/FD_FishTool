# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel

class WeightBlender:
    def __init__(self, rig_manager):
        self.mgr = rig_manager
        self.active_data = None

    def start_live_blend(self, mesh_name):
        joints = cmds.ls(os=True, type='joint')
        if len(joints) < 2: return False
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')[0]
        bn1, bn2 = joints[0], joints[1]
        vtxs = list(self.mgr.get_bone_island(sc, bn1) | self.mgr.get_bone_island(sc, bn2))
        snapshot = {v: {bn1: cmds.skinPercent(sc, v, q=True, v=True, transform=bn1)} for v in vtxs}
        self.active_data = {"sc": sc, "bn1": bn1, "bn2": bn2, "vtxs": vtxs, "snapshot": snapshot}
        
        # УБРАНО выделение вертексов, чтобы не мешать цветам
        cmds.select(cl=True) 
        mel.eval('polyOptions -sizeVertex 8')
        return True

    def update_live_blend(self, offset):
        if not self.active_data: return
        d = self.active_data
        for v in d["vtxs"]:
            new_w = max(0, min(1, d["snapshot"][v][d["bn1"]] + offset))
            cmds.skinPercent(d["sc"], v, tv=[(d["bn1"], new_w)], nrm=True)
            # Покраска: Red -> bn1, Blue -> bn2. Темнее при весе 1.0.
            r = 1.0 - (new_w * 0.8); b = 1.0 - ((1.0 - new_w) * 0.8)
            cmds.polyColorPerVertex(v, rgb=(new_w*r, 0.1, (1.0-new_w)*b))

    def stop_live_blend(self):
        if not self.active_data: return
        mel.eval('polyOptions -sizeVertex 3')
        cmds.polyColorPerVertex(self.active_data["vtxs"], remove=True)
        self.active_data = None