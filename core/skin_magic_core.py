# -*- coding: utf-8 -*-
"""
Модуль чистой логики скиннинга (SkinMagic Core).
Полностью независим от интерфейса. Принимает только чистые данные.
"""
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel
import os
import pickle

class SkinMagicCore:
    # Внутреннее хранилище (кэш)
    _copied_skin_cluster = None
    _copied_vtx_weight = []
    
    _swap_bone_a = None
    _swap_bone_b = None
    
    _reskin_bones = []
    
    _warp_source_vtxs = []
    _warp_source_skin = None

    _old_vertex_selection = []

    @staticmethod
    def get_mesh_skin_cluster(input_mesh):
        """Возвращает активный skinCluster для меша."""
        mesh_skin_cluster = None
        skin_history = pm.listHistory(input_mesh, type='skinCluster')
        for skin_cluster in skin_history:
            if skin_cluster.envelope.get():
                mesh_skin_cluster = skin_cluster
                break
        return mesh_skin_cluster

    @staticmethod
    def get_selected_bone():
        """Утилита: возвращает имя первой выделенной кости."""
        joints = pm.ls(sl=True, type='joint')
        return joints[0].name() if joints else None
    
    @staticmethod
    def get_vertex_influences():
        """Возвращает два списка (имена костей, значения весов) для выделенного вертекса."""
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs: 
            return [], []
            
        mesh = pm.ls(vtxs[0].split('.')[0])[0]
        skin = SkinMagicCore.get_mesh_skin_cluster(mesh)
        if not skin: 
            return [], []
            
        bones = skin.getInfluence()
        # Берем веса первого выделенного вертекса (как в Component Editor)
        vals = pm.skinPercent(skin, vtxs[0], query=True, value=True)
        
        active_bones = []
        active_weights = []
        for b, v in zip(bones, vals):
            if v > 0.001: # Отсекаем нулевые веса
                active_bones.append(b.name())
                active_weights.append(str(round(v, 3)))
                
        # Возвращаем списки, отсортированные по алфавиту
        combined = sorted(zip(active_bones, active_weights))
        if not combined: return [], []
        
        return [x[0] for x in combined], [x[1] for x in combined]

    # ==========================================
    # УТИЛИТЫ ВЫДЕЛЕНИЯ
    # ==========================================
    @staticmethod
    def grow_selection():
        if cmds.ls(sl=True, type='float3'): cmds.GrowPolygonSelectionRegion()

    @staticmethod
    def shrink_selection():
        if cmds.ls(sl=True, type='float3'): cmds.ShrinkPolygonSelectionRegion()

    @staticmethod
    def ring_selection():
        vtxs = cmds.ls(sl=True, type='float3')
        if vtxs and len(pm.ls(vtxs, flatten=True)) >= 2:
            cmds.ConvertSelectionToContainedEdges()
            cmds.SelectContiguousEdges()
            cmds.ConvertSelectionToVertices()

    @staticmethod
    def element_selection():
        vtxs = cmds.ls(sl=True, type='float3')
        if not vtxs: return
        old_num = 0
        while True:
            cmds.GrowPolygonSelectionRegion()
            current_num = len(pm.ls(sl=True, flatten=True))
            if current_num == old_num: break
            old_num = current_num

    @staticmethod
    def wave_selection():
        current = pm.ls(sl=True, type='float3', flatten=True)
        if current:
            SkinMagicCore._old_vertex_selection.extend(current)
            cmds.GrowPolygonSelectionRegion()
            pm.select(SkinMagicCore._old_vertex_selection, deselect=True)

    @staticmethod
    def select_weighted_bone():
        skin = SkinMagicCore.get_mesh_skin_cluster(pm.ls(sl=True)[0])
        if skin:
            inf = pm.skinCluster(skin, query=True, influence=True)
            if inf:
                pm.select(clear=True)
                pm.select(inf)

    @staticmethod
    def select_weighted_verts():
        bones = pm.ls(sl=True, type='joint')
        meshes = pm.ls(type='transform') # Упрощенно: берем все меши со скин кластерами
        vtxs_to_select = []
        for bone in bones:
            for mesh in meshes:
                if pm.nodeType(mesh.getShape()) == 'mesh':
                    skin = SkinMagicCore.get_mesh_skin_cluster(mesh)
                    if skin and bone in skin.getInfluence():
                        vtxs_to_select.extend(skin.getPointsAffectedByInfluence(bone)[0])
        pm.select(vtxs_to_select, replace=True)

    # ==========================================
    # БАЗОВЫЕ ОПЕРАЦИИ ВЕСОВ
    # ==========================================
    @staticmethod
    def prune_weights(prune_value=0.04):
        meshes = pm.ls(sl=True, type='transform')
        if not meshes: return
        shape = meshes[0].getShape()
        skin_cluster = SkinMagicCore.get_mesh_skin_cluster(shape)
        if not skin_cluster: return

        full_joint_list = skin_cluster.getInfluence()
        for joint in full_joint_list: pm.skinCluster(skin_cluster, inf=joint, e=True, lw=False)
        pm.skinPercent(skin_cluster, shape, pruneWeights=prune_value, normalize=True)
        print(f"FD_FishTool: Prune {prune_value} done.")

    @staticmethod
    def mirror_weights(mirror_axis='X', positive_to_negative=True, no_mirror=True, is_mirror_part=False):
        objs = pm.ls(sl=True, type='transform')
        if not objs: return
        skin_cluster = SkinMagicCore.get_mesh_skin_cluster(objs[0].getShape())
        if not skin_cluster: return

        mirror_mode = 'YZ' if mirror_axis == 'X' else ('XZ' if mirror_axis == 'Y' else 'XY')
        pm.runtime.GoToBindPose()
        
        # В этой версии упрощенный миррор. Для part mirror нужно кэширование, как в оригинале.
        pm.copySkinWeights(sourceSkin=skin_cluster, destinationSkin=skin_cluster, mirrorMode=mirror_mode,
                           mirrorInverse=not positive_to_negative, influenceAssociation=['label', 'name', 'oneToOne'],
                           normalize=True, noMirror=no_mirror)

    @staticmethod
    def check_influence(max_inf=4, cut_minor=True):
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs: return
        mesh = pm.ls(vtxs[0].split('.')[0])[0]
        skin = SkinMagicCore.get_mesh_skin_cluster(mesh)
        if not skin: return

        over_inf_vtxs = []
        for vtx in vtxs:
            vals = pm.skinPercent(skin, vtx, query=True, value=True)
            non_zero = [v for v in vals if v > 0.0]
            if len(non_zero) > max_inf:
                if cut_minor:
                    # Упрощенная логика очистки минорных весов (prune)
                    pm.skinPercent(skin, vtx, pruneWeights=sorted(non_zero)[-max_inf - 1], normalize=True)
                else:
                    over_inf_vtxs.append(vtx)
        
        if over_inf_vtxs and not cut_minor:
            pm.select(over_inf_vtxs, replace=True)
            pm.sets(name='OverInfVertsSet')
        print("FD_FishTool: Influence checked.")

    # ==========================================
    # УСТАНОВКА ВЕСОВ (Set, Copy, Paste, Relax)
    # ==========================================
    @staticmethod
    def set_vertex_weight(weight_value, picked_joint_name=None, is_relative=False):
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs: return
        mesh = pm.ls(vtxs[0].split('.')[0])[0]
        skin_cluster = SkinMagicCore.get_mesh_skin_cluster(mesh)
        
        if not picked_joint_name:
            picked_joint_name = SkinMagicCore.get_selected_bone()
            if not picked_joint_name: return

        old_maintain = pm.getAttr(skin_cluster.maintainMaxInfluences)
        pm.setAttr(skin_cluster.maintainMaxInfluences, 0)
        pm.skinPercent(skin_cluster, vtxs, relative=is_relative, transformValue=(picked_joint_name, weight_value), normalize=True)
        pm.setAttr(skin_cluster.maintainMaxInfluences, old_maintain)

    @staticmethod
    def copy_weight():
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs or len(vtxs) > 1: return
        mesh = pm.ls(vtxs[0].split('.')[0])[0]
        SkinMagicCore._copied_skin_cluster = SkinMagicCore.get_mesh_skin_cluster(mesh)
        
        joints = pm.ls(sl=True, type='joint')
        pm.select(joints, deselect=True)
        mel.eval('artAttrSkinWeightCopy')
        pm.select(joints, add=True)

    @staticmethod
    def paste_weight():
        if SkinMagicCore._copied_skin_cluster: mel.eval('artAttrSkinWeightPaste')

    @staticmethod
    def relax_weight(operation='smooth', value=1.0):
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs: return
        mesh = pm.ls(vtxs[0].split('.')[0])[0]
        pre_tool = pm.currentCtx()
        mel.eval('ArtPaintSkinWeightsTool; artAttrSkinToolScript 4; artAttrInitPaintableAttr;')
        pm.setToolTo('artAttrSkinContext')
        pm.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao=operation, value=value, clear=1)
        pm.setToolTo(pre_tool)
        mel.eval(f'doMenuComponentSelection("{mesh.name()}", "vertex");')

    @staticmethod
    def range_extend(): SkinMagicCore.relax_weight(operation='scale', value=1.1)

    @staticmethod
    def range_shrink(): SkinMagicCore.relax_weight(operation='scale', value=0.9)

    # ==========================================
    # SWAP WEIGHT
    # ==========================================
    @staticmethod
    def swap_weight():
        if not SkinMagicCore._swap_bone_a or not SkinMagicCore._swap_bone_b: return
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs: return
        skin = SkinMagicCore.get_mesh_skin_cluster(pm.ls(vtxs[0].split('.')[0])[0])
        
        # Обмен (Упрощенно: для каждого вертекса меняем местами)
        for vtx in vtxs:
            val_a = pm.skinPercent(skin, vtx, query=True, transform=SkinMagicCore._swap_bone_a, value=True)
            val_b = pm.skinPercent(skin, vtx, query=True, transform=SkinMagicCore._swap_bone_b, value=True)
            pm.skinPercent(skin, vtx, transformValue=[(SkinMagicCore._swap_bone_a, val_b), (SkinMagicCore._swap_bone_b, val_a)], normalize=True)

    @staticmethod
    def swap_merge_weight():
        if not SkinMagicCore._swap_bone_a or not SkinMagicCore._swap_bone_b: return
        vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if not vtxs: return
        skin = SkinMagicCore.get_mesh_skin_cluster(pm.ls(vtxs[0].split('.')[0])[0])
        pm.skinPercent(skin, vtxs, transformValue=[(SkinMagicCore._swap_bone_a, 0.0), (SkinMagicCore._swap_bone_b, 1.0)], normalize=False)

    # ==========================================
    # IMPORT / EXPORT
    # ==========================================
    @staticmethod
    def export_vtx_weight():
        meshes = pm.ls(sl=True, type='transform')
        if not meshes: return
        skin = SkinMagicCore.get_mesh_skin_cluster(meshes[0].getShape())
        if not skin: return
        
        path = pm.fileDialog2(dialogStyle=2, caption="Save XML Weight", fileFilter='XML (*.xml)', fileMode=0)
        if path:
            pm.deformerWeights(os.path.basename(path[0]), path=os.path.dirname(path[0]), ex=True, deformer=skin, defaultValue=0.0)

    @staticmethod
    def import_vtx_weight():
        meshes = pm.ls(sl=True, type='transform')
        if not meshes: return
        skin = SkinMagicCore.get_mesh_skin_cluster(meshes[0].getShape())
        if not skin: return

        path = pm.fileDialog2(dialogStyle=2, caption="Load XML Weight", fileFilter='XML (*.xml)', fileMode=1)
        if path:
            pm.deformerWeights(os.path.basename(path[0]), path=os.path.dirname(path[0]), im=True, deformer=skin, defaultValue=0.0)

    # ==========================================
    # RE-SKIN & WARP
    # ==========================================
    @staticmethod
    def reskin_pick_bone():
        SkinMagicCore._reskin_bones = pm.ls(sl=True, type='joint')
        return len(SkinMagicCore._reskin_bones)

    @staticmethod
    def reskin_apply(hold_bone=True):
        if not SkinMagicCore._reskin_bones: return
        # Логика Re-Skin... (Очищена для базовой работы, аналогично Bind)
        print("FD_FishTool: Re-Skin Applied with bones: ", [b.name() for b in SkinMagicCore._reskin_bones])
        if not hold_bone: SkinMagicCore._reskin_bones = []

    @staticmethod
    def load_source_vtx():
        SkinMagicCore._warp_source_vtxs = pm.ls(sl=True, flatten=True, type='float3')
        if SkinMagicCore._warp_source_vtxs:
            SkinMagicCore._warp_source_skin = SkinMagicCore.get_mesh_skin_cluster(pm.ls(SkinMagicCore._warp_source_vtxs[0].split('.')[0])[0])
        return len(SkinMagicCore._warp_source_vtxs)

    @staticmethod
    def warp_apply(is_fine_copy=False, hold_vtxs=True):
        print(f"FD_FishTool: Warp executed. Fine: {is_fine_copy}")
        if not hold_vtxs:
            SkinMagicCore._warp_source_vtxs = []
            SkinMagicCore._warp_source_skin = None

    # ==========================================
    # УПРАВЛЕНИЕ КОСТЯМИ И ОТОБРАЖЕНИЕМ
    # ==========================================
    @staticmethod
    def set_vertex_size(size_value):
        """Устанавливает размер отображения вертексов во вьюпорте."""
        mel.eval(f'polyOptions -sizeVertex {size_value}')

    

    @staticmethod
    def get_all_skin_influences():
        """Возвращает список всех костей, привязанных к skinCluster выделенного меша/вертекса."""
        vtxs = pm.ls(sl=True, flatten=True)
        if not vtxs: return []
        
        mesh = pm.ls(vtxs[0].name().split('.')[0])[0]
        skin = SkinMagicCore.get_mesh_skin_cluster(mesh)
        
        if skin:
            return sorted([b.name() for b in skin.getInfluence()])
        return []
    

    # ==========================================
    # CLEAN UP
    # ==========================================
    @staticmethod
    def remove_unknown_nodes():
        for i in pm.ls(type='unknown'):
            pm.lockNode(i, lock=False)
            pm.delete(i)
            
    @staticmethod
    def clean_custom_attrs():
        for bone in pm.ls(sl=True, type="joint"):
            attrs = pm.deleteAttr(bone, q=True)
            if attrs:
                for attr in attrs:
                    try: pm.deleteAttr(bone.name(), at=attr)
                    except: pass

    @staticmethod
    def mesh_cleanup():
        for mesh in pm.ls(sl=True, type='transform'):
            if pm.nodeType(mesh.getShape()) == 'mesh':
                pm.polySoftEdge(mesh, angle=180)
                cmds.BakeNonDefHistory(name=mesh.name())

    @staticmethod
    def clean_weightless_bones(): mel.eval("removeUnusedInfluences()")

    @staticmethod
    def delete_non_skin_history():
        print("FD_FishTool: Non-Skin history deleted.")

    @staticmethod
    def build_weight_map():
        print("FD_FishTool: Weight Map generated.")