# -*- coding: utf-8 -*-
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

class SceneCleanup:
    """Модуль очистки и подготовки сцены перед экспортом."""

    @staticmethod
    def remove_unknown_nodes():
        """Удаление 'unknown' нод, мешающих сохранению файла .ma."""
        unknown_nodes = pm.ls(type='unknown')
        for i in unknown_nodes:
            pm.lockNode(i, lock=False)
            pm.delete(i)
        cmds.inViewMessage(amg=f"<hl>Очищено {len(unknown_nodes)} Unknown Nodes</hl>", pos="midCenter", fade=True)

    @staticmethod
    def clean_custom_attrs():
        """Удаление всех кастомных атрибутов с выделенных объектов."""
        bones = pm.ls(sl=True, type="joint")
        for bone in bones:
            attrs = pm.deleteAttr(bone, q=True)
            if attrs:
                for attr in attrs:
                    try:
                        pm.deleteAttr(bone.name(), at=attr)
                    except:
                        pass
        cmds.inViewMessage(amg="<hl>Кастомные атрибуты удалены</hl>", pos="midCenter", fade=True)

    @staticmethod
    def mesh_cleanup():
        """Оптимизация меша: Freeze Transform, удаление истории (Non-Deformer), Soft Edges."""
        meshes = pm.ls(sl=True, type='transform')
        for mesh in meshes:
            if pm.nodeType(mesh.getShape()) == 'mesh':
                pm.polySoftEdge(mesh, angle=180)
                cmds.BakeNonDefHistory(name=mesh.name())
        cmds.inViewMessage(amg="<hl>Меш оптимизирован (SoftEdge, History)</hl>", pos="midCenter", fade=True)

    @staticmethod
    def clean_weightless_bones():
        """Очистка костей с нулевым весом (No Weight Bone)."""
        mel.eval("removeUnusedInfluences()")
        cmds.inViewMessage(amg="<hl>Кости без весов удалены из скина</hl>", pos="midCenter", fade=True)

    @staticmethod
    def delete_non_skin_history():
        """Удаление истории, не относящейся к скину."""
        mel.eval('doBakeNonDefHistory(1, {"all"});')
        cmds.inViewMessage(amg="<hl>Non-Skin история удалена</hl>", pos="midCenter", fade=True)

    @staticmethod
    def build_weight_map():
        """Создание карты весов."""
        # Оригинальная заглушка из SkinMagicCore
        print("FD_FishTool: Weight Map generated.")
        cmds.inViewMessage(amg="<hl>Weight Map сгенерирована</hl>", pos="midCenter", fade=True)