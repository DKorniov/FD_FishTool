# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel

class WeightBlender:
    def __init__(self, rig_manager):
        self.mgr = rig_manager
        self.active_data = None
        self.vtx_limit = 1000

    def start_live_blend(self, mesh_name):
        """Подготовка: Безопасный сбор данных и инвертированная логика."""
        joints = cmds.ls(os=True, type='joint')
        if len(joints) < 2:
            cmds.warning("FD_FishTool: Выделите 2 кости.")
            return False
        
        sc_nodes = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')
        if not sc_nodes: return False
        sc = sc_nodes[0]
        
        # Безопасная проверка инфлюенсов
        all_inf = cmds.skinCluster(sc, q=True, inf=True)
        for j in [joints[0], joints[1]]:
            if j not in all_inf:
                cmds.warning(f"FD_FishTool: Кость '{j}' не влияет на этот скин. Операция отменена.")
                return False

        bn1, bn2 = joints[0], joints[1] # bn1 - Слева (Red), bn2 - Справа (Blue)
        
        # Получаем облако вертексов
        vtxs1 = self.mgr.get_bone_island(sc, bn1)
        vtxs2 = self.mgr.get_bone_island(sc, bn2)
        combined = list(vtxs1 | vtxs2)
        
        if not combined:
            cmds.warning("FD_FishTool: Облако вертексов пусто.")
            return False

        if len(combined) > self.vtx_limit:
            combined = combined[:self.vtx_limit]
        
        # Делаем слепок веса ВТОРОЙ кости (Blue/Right), чтобы движение вправо было положительным
        snapshot = {v: cmds.skinPercent(sc, v, q=True, v=True, transform=bn2) for v in combined}
        
        # Изоляция
        active_panel = cmds.getPanel(withFocus=True)
        if "modelPanel" in active_panel:
            cmds.isolateSelect(active_panel, state=True)
            cmds.select(combined, r=True)
            cmds.isolateSelect(active_panel, addSelected=True)
        
        # Настройка цвета
        shape = cmds.listRelatives(mesh_name, s=True)[0]
        cmds.setAttr(f"{shape}.displayColors", 1)
        cmds.polyOptions(colorShadedDisplay=True)
        mel.eval('polyOptions -sizeVertex 10')
        cmds.select(cl=True)
        
        print("\n" + "="*50)
        print(f"FD_FishTool: TWIN MACHINE ACTIVATED")
        print(f"  > Target: {bn1} (Left) <-> {bn2} (Right)")
        
        self.active_data = {
            "sc": sc, "bn1": bn1, "bn2": bn2, 
            "vtxs": combined, "snapshot": snapshot,
            "panel": active_panel
        }
        return True

    def update_live_blend(self, offset):
        """Обновление: Прямая зависимость - тянешь вправо, BN2 растет."""
        if not self.active_data: return
        d = self.active_data
        
        changed_count = 0
        for v in d["vtxs"]:
            # Берем сохраненный вес BN2
            orig_w2 = d["snapshot"][v]
            # Новое значение BN2: тянем слайдер вправо (offset > 0) -> BN2 увеличивается
            new_w2 = max(0.0, min(1.0, orig_w2 + offset))
            
            # Проверка на изменения
            if abs(new_w2 - orig_w2) < 0.001 and (new_w2 == 1.0 or new_w2 == 0.0):
                continue
                
            # Применяем вес к BN2. Maya сама вычтет его у BN1 при нормализации
            cmds.skinPercent(d["sc"], v, tv=[(d["bn2"], new_w2)], nrm=True)
            self._apply_smart_color(v, new_w2, offset)
            changed_count += 1

        print(f"  [Twin] Target: {d['bn2']} | Offset: {offset:+.2f} | Vtx: {changed_count}")

    def _apply_smart_color(self, vtx, w2, offset):
        """Интуитивная раскраска: Яркость кости, к которой тянем."""
        if offset >= 0: # Тянем к BN2 (Синий)
            # w2 - текущий вес синей кости. Темнее при 1.0
            brightness = 1.0 - (w2 * 0.7)
            cmds.polyColorPerVertex(vtx, rgb=(0.05, 0.05, w2 * brightness))
        else: # Тянем к BN1 (Красный)
            w1 = 1.0 - w2 # Вес красной кости
            brightness = 1.0 - (w1 * 0.7)
            cmds.polyColorPerVertex(vtx, rgb=(w1 * brightness, 0.05, 0.05))

    def stop_live_blend(self):
        if not self.active_data: return
        if "modelPanel" in self.active_data["panel"]:
            cmds.isolateSelect(self.active_data["panel"], state=False)
        mel.eval('polyOptions -sizeVertex 3')
        cmds.polyColorPerVertex(self.active_data["vtxs"], remove=True)
        print("FD_FishTool: TWIN COMPLETE.\n" + "="*50)
        self.active_data = None