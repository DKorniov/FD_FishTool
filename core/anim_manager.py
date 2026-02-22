# -*- coding: utf-8 -*-
import maya.cmds as cmds
import os
import json

class AnimManager:
    def __init__(self, config_manager):
        self.cfg = config_manager
        paths = self.cfg.load_json("paths.json")
        self.etalon_path = paths.get("animation_data", "")
        # Путь к библиотеке пресетов относительно файла менеджера
        self.lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "studio_lib")
        self.anim_ranges = self._parse_etalon()

    def _parse_etalon(self):
        """Парсинг таймингов из текстового файла."""
        ranges = {}
        if not self.etalon_path or not os.path.exists(self.etalon_path): 
            return ranges
        try:
            with open(self.etalon_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        ranges[parts[2]] = (float(parts[0]), float(parts[1]))
        except Exception as e:
            print(f"FD_FishTool: Error parsing etalon: {e}")
        return ranges

    def apply_studio_anim(self, anim_folder_name):
        """
        Автономная вставка анимации без mutils:
        1. Читает set.json и выбирает контролы.
        2. Импортирует ключи из animation.ma (если есть).
        3. Накладывает статичную позу из pose.json на недостающие атрибуты.
        """
        is_body = "body" in anim_folder_name.lower()
        set_folder = "AS_body_set.set" if is_body else "AS_face_set.set"
        
        lib_dir = os.path.join(self.lib_path, anim_folder_name)
        set_path = os.path.join(self.lib_path, set_folder, "set.json")
        pose_path = os.path.join(lib_dir, "pose.json")
        ma_path = os.path.join(lib_dir, "animation.ma")

        # --- 1. ШАГ: СЕЛЕКЦИЯ ПО СЕТУ ---
        if not os.path.exists(set_path):
            cmds.error(f"Set file not found: {set_path}")
            return

        with open(set_path, 'r') as f:
            set_data = json.load(f)
        
        objects_in_set = set_data.get("objects", {}).keys()
        existing_objs = [obj for obj in objects_in_set if cmds.objExists(obj)]
        
        if existing_objs:
            cmds.select(existing_objs)
            print(f"FD_FishTool: Selected {len(existing_objs)} controls.")
        else:
            cmds.warning("FD_FishTool: No controls from set found in scene!")
            return

        # --- 2. ШАГ: ЗАГРУЗКА АНИМАЦИИ (.ma) ИЛИ ПОЗЫ (.json) ---
        cmds.undoInfo(openChunk=True)
        try:
            # А) Если есть файл .ma, импортируем его напрямую (это даст ключи)
            if os.path.exists(ma_path):
                print(f"FD_FishTool: Importing animation curves from {ma_path}...")
                # Используем временный namespace, чтобы не было конфликтов имен
                imported_nodes = cmds.file(ma_path, i=True, type="mayaAscii", rnn=True, namespace="temp_anim")
                
                # Сопоставляем кривые с объектами по именам из pose.json
                if os.path.exists(pose_path):
                    with open(pose_path, 'r') as f:
                        pose_data = json.load(f)
                    
                    for obj_name, data in pose_data.get("objects", {}).items():
                        if not cmds.objExists(obj_name): continue
                        
                        for attr_name, attr_info in data.get("attrs", {}).items():
                            curve_name = attr_info.get("curve")
                            if curve_name:
                                full_curve = f"temp_anim:{curve_name}"
                                if cmds.objExists(full_curve):
                                    try:
                                        cmds.connectAttr(f"{full_curve}.output", f"{obj_name}.{attr_name}", f=True)
                                    except: pass
                
                # Удаляем временный namespace (Maya сама удалит пустой после переподключения)
                cmds.namespace(removeNamespace="temp_anim", mergeNamespaceWithParent=True)

            # Б) Накладываем статичные значения из pose.json (для атрибутов без кривых)
            if os.path.exists(pose_path):
                with open(pose_path, 'r') as f:
                    pose_data = json.load(f)

                for obj_name, data in pose_data.get("objects", {}).items():
                    if not cmds.objExists(obj_name): continue
                    
                    for attr_name, attr_info in data.get("attrs", {}).items():
                        full_attr = f"{obj_name}.{attr_name}"
                        
                        # ФИКС ОШИБКИ: Проверяем существование атрибута перед getAttr/setAttr
                        if not cmds.objExists(full_attr): continue
                        if cmds.getAttr(full_attr, lock=True): continue
                            
                        val = attr_info.get("value")
                        try:
                            # Если на атрибуте нет входящих соединений (кривых), ставим значение
                            if not cmds.listConnections(full_attr, destination=False, source=True):
                                cmds.setAttr(full_attr, val)
                                cmds.setKeyframe(full_attr)
                        except: pass
            
            # Установка таймлайна
            clip_name = "normal_move" if is_body else "smile"
            self.set_timeline(clip_name)
            print(f"FD_FishTool: Animation successfully applied for {anim_folder_name}")
            
        finally:
            cmds.undoInfo(closeChunk=True)

    def set_timeline(self, anim_name):
        if anim_name in self.anim_ranges:
            start, end = self.anim_ranges[anim_name]
            cmds.playbackOptions(min=start, max=end, ast=start, aet=end)
            cmds.currentTime(start)
            return True
        return False

    def get_symmetric_control(self, ctrl):
        if "_R" in ctrl: return ctrl.replace("_R", "_L")
        if "_L" in ctrl: return ctrl.replace("_L", "_R")
        return None