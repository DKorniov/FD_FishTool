import maya.cmds as cmds
import os
import re

class AnimSyncManager:
    def __init__(self, ref_file_path):
        self.ref_file = ref_file_path
        self.node = "AnimAssistant"

    def get_canonical_name(self, name):
        """
        Нормализация: '001|normal_move_10-38' -> 'normal_move'
        """
        if not name: return ""
        # Убираем префикс (001|)
        clean = name.split('|')[-1]
        # Убираем суффикс тайминга (_10-38) в конце
        clean = re.sub(r'_\d+-\d+$', '', clean)
        return clean.strip().lower()

    def get_scene_data(self):
        """Сбор имен из сцены."""
        if not cmds.objExists(self.node): return {}
        
        names = (cmds.getAttr(f"{self.node}.AnimationClipName") or "").split()
        starts = (cmds.getAttr(f"{self.node}.StartFrame") or "").split()
        ends = (cmds.getAttr(f"{self.node}.EndFrame") or "").split()

        scene_map = {}
        for i in range(len(names)):
            raw_name = names[i]
            canon = self.get_canonical_name(raw_name)
            if not canon: continue
            
            scene_map[canon] = {
                "raw_name": raw_name,
                "start": starts[i] if i < len(starts) else "0",
                "end": ends[i] if i < len(ends) else "0"
            }
        return scene_map

    def get_reference_data(self):
        """Сбор имен из эталона."""
        ref_map = {}
        if self.ref_file and os.path.exists(self.ref_file):
            with open(self.ref_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        name = " ".join(parts[2:]).strip()
                        canon = self.get_canonical_name(name)
                        ref_map[canon] = {
                            "name": name,
                            "start": parts[0],
                            "end": parts[1]
                        }
        return ref_map

    def compare(self):
        """Сравнение только на наличие."""
        scene = self.get_scene_data()
        ref = self.get_reference_data()
        
        report = []
        # Собираем все уникальные каноничные имена
        all_canons = sorted(list(set(list(scene.keys()) + list(ref.keys()))))

        for canon in all_canons:
            s = scene.get(canon)
            r = ref.get(canon)

            if s and r:
                # Найдено совпадение по имени - СТАТУС OK (тайминг игнорируем)
                report.append({
                    "name": s["raw_name"], 
                    "status": "OK", 
                    "ref_time": f"{r['start']}-{r['end']}", 
                    "scene_time": f"{s['start']}-{s['end']}"
                })
            elif r:
                # Есть в файле, нет в сцене
                report.append({
                    "name": r["name"], 
                    "status": "MISSING", 
                    "ref_time": f"{r['start']}-{r['end']}", 
                    "scene_time": "MISSING"
                })
            elif s:
                # Есть в сцене, нет в файле
                report.append({
                    "name": s["raw_name"], 
                    "status": "EXTRA", 
                    "ref_time": "---", 
                    "scene_time": f"{s['start']}-{s['end']}"
                })
        
        return report