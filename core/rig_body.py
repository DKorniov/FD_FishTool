# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os

class BodyRigManager:
    """Логика автоматизации скелета тела и поэтапного скиннинга."""
    
    def __init__(self, config=None):
        self.cfg = config
        self.map_file = "bone_skin_map.json"

    def find_default_mesh(self):
        """Интеллектуальный поиск меша по имени сцены и техническим суффиксам."""
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

    def get_all_meshes_in_scene(self):
        """Возвращает список трансформ-узлов всех мешей в сцене."""
        mesh_shapes = cmds.ls(type='mesh', ni=True) or []
        mesh_transforms = []
        for shape in mesh_shapes:
            parent = cmds.listRelatives(shape, p=True, f=False)
            if parent: mesh_transforms.append(parent[0])
        return sorted(list(set(mesh_transforms)))

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

    def get_full_bone_list(self, stage_key):
        """Сбор костей согласно правилам из JSON."""
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
        """Выделяет кости указанного этапа."""
        bones = self.get_full_bone_list(f"stage_{stage_index}")
        if bones: 
            cmds.select(bones, r=True)
            print(f"FD_FishTool: Выбрано {len(bones)} костей (Этап {stage_index}).")
        else:
            cmds.warning(f"FD_FishTool: Кости для этапа {stage_index} не найдены.")

    def add_to_skin_logic(self, stage_index, mesh_name):
        """Добавление костей в скин согласно правилам этапов."""
        if not mesh_name or not cmds.objExists(mesh_name): return

        bones = self.get_full_bone_list(f"stage_{stage_index}")
        if not bones: return

        history = cmds.listHistory(mesh_name)
        skin_clusters = cmds.ls(history, type='skinCluster')

        if stage_index == 1:
            if not skin_clusters:
                cmds.select(bones, r=True); cmds.select(mesh_name, add=True)
                cmds.skinCluster(tsb=True, bm=0, nw=1, wd=0, mi=4, omi=True, dr=4, rui=False)
                print(f"FD_FishTool: Stage 1 Bind complete for {mesh_name}.")
            else:
                cmds.warning(f"У меша '{mesh_name}' уже есть скин.")
        else:
            if not skin_clusters: return
            sc = skin_clusters[0]
            existing = cmds.skinCluster(sc, q=True, inf=True) or []
            for bone in bones:
                if bone not in existing:
                    cmds.skinCluster(sc, edit=True, ai=bone, lw=True, wt=0)
            print(f"FD_FishTool: Stage {stage_index} Influences added (Locked).")

    def select_weighted_bones(self, mesh_name):
        """Выделяет только те кости, которые имеют веса на меше."""
        if not cmds.objExists(mesh_name): return
        history = cmds.listHistory(mesh_name)
        sc = cmds.ls(history, type='skinCluster')
        if sc:
            infl = cmds.skinCluster(sc[0], q=True, inf=True)
            if infl: cmds.select(infl, r=True)

    def clean_weightless_bones(self, mesh_name):
        """
        Удаляет из скина кости с нулевым влиянием. 
        Логика полностью переписана по успешному логу.
        """
        if not mesh_name or not cmds.objExists(mesh_name): 
            cmds.warning("Выберите Target Mesh для очистки.")
            return
        
        # Находим скин-кластер
        history = cmds.listHistory(mesh_name)
        sc_nodes = cmds.ls(history, type='skinCluster')
        
        if not sc_nodes:
            cmds.warning(f"У объекта '{mesh_name}' не найден skinCluster.")
            return
            
        sc = sc_nodes[0]
        
        # Сохраняем текущее выделение
        old_sel = cmds.ls(sl=True)
        
        try:
            # 1. Выделяем меш
            cmds.select(mesh_name, r=True)
            # 2. Вызываем MEL очистку
            mel.eval("removeUnusedInfluences;")
            # 3. Принудительно чистим через узел кластера
            cmds.skinCluster(sc, edit=True, rui=True)
            
            print(f"--- [RigBody] Cleaned unused influences for {mesh_name} via {sc} ---")
            
        except Exception as e:
            cmds.error(f"Ошибка при очистке неиспользуемых костей: {e}")
        finally:
            # Возвращаем выделение
            if old_sel: cmds.select(old_sel, r=True)
            else: cmds.select(cl=True)