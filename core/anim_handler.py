import maya.cmds as cmds
import os
import re
import maya.mel as mel
import json
import traceback

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







class AnimationHandler:
    @staticmethod
    def load_etalon_animations():
        """
        Загружает список анимаций из data/animation.txt и использует MEL из data/AnimAssist.mel.
        """
        node_name = "AnimAssistant"
        window_name = "Aassist"
        
        # 1. ОПРЕДЕЛЕНИЕ ПУТЕЙ
        # Текущий файл: .../FD_FishTool/core/anim_handler.py
        current_dir = os.path.dirname(__file__)
        # Корень пакета: .../FD_FishTool/
        package_root = os.path.abspath(os.path.join(current_dir, ".."))
        
        # Файл данных: .../FD_FishTool/data/animation.txt
        txt_path = os.path.join(package_root, "data", "animation.txt")
        # НОВЫЙ ПУТЬ MEL: .../FD_FishTool/data/AnimAssist.mel
        mel_path = os.path.join(package_root, "data", "AnimAssist.mel").replace("\\", "/")

        # 2. ПРИНУДИТЕЛЬНЫЙ SOURCE MEL-ФАЙЛА
        if os.path.exists(mel_path):
            try:
                # Используем абсолютный путь для source
                mel.eval(f'source "{mel_path}";')
                print(f"FD_FishTool: MEL скрипт загружен из {mel_path}")
            except Exception as e:
                cmds.warning(f"FD_FishTool: Ошибка при выполнении source: {e}")
        else:
            cmds.error(f"FD_FishTool: Файл не найден по пути {mel_path}")
            return

        # 3. ИНИЦИАЛИЗАЦИЯ НОДЫ
        try:
            mel.eval("CreateIfNotExistNodeAttribute();")
        except Exception as e:
            cmds.error("FD_FishTool: Не удалось вызвать CreateIfNotExistNodeAttribute. Проверьте содержимое MEL.")
            return

        # 4. ПРОВЕРКА ДАННЫХ
        has_data = False
        if cmds.objExists(node_name):
            try:
                data = cmds.getAttr(f"{node_name}.AnimationClipName")
                if data and data.strip():
                    has_data = True
            except:
                pass

        if has_data:
            result = cmds.confirmDialog(
                title='FD_FishTool',
                message='Список в AnimAssist не пуст. Перезаписать его?',
                button=['Да', 'Нет'],
                defaultButton='Да',
                cancelButton='Нет',
                dismissString='Нет'
            )
            if result == 'Нет': return

        # 5. ЧТЕНИЕ И ЗАПИСЬ
        if not os.path.exists(txt_path):
            cmds.error(f"FD_FishTool: Файл данных не найден: {txt_path}")
            return

        try:
            with open(txt_path, 'r') as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            names, starts, ends = [], [], []
            for i, line in enumerate(lines):
                parts = line.split()
                if len(parts) < 3: continue
                
                s, e = parts[0], parts[1]
                n_raw = "_".join(parts[2:])
                
                idx = str(i + 1).zfill(2)
                names.append(f"{idx}|{n_raw}_{s}-{e}")
                starts.append(s)
                ends.append(e)

            # Записываем в атрибуты ноды
            cmds.setAttr(f"{node_name}.AnimationClipName", " ".join(names), type="string")
            cmds.setAttr(f"{node_name}.StartFrame", " ".join(starts), type="string")
            cmds.setAttr(f"{node_name}.EndFrame", " ".join(ends), type="string")

            # 6. ЗАПУСК И ОБНОВЛЕНИЕ
            # Запускаем окно
            mel.eval("AnimAssist;")
            
            # Проверяем наличие процедуры обновления
            if mel.eval('exists "updateAnims"'):
                mel.eval("updateAnims();")
            else:
                cmds.warning("FD_FishTool: Процедура updateAnims всё еще не найдена в MEL.")

            # Исправленный вывод уведомления (замена displayInfo)
            print(f"FD_FishTool: Успешно загружено {len(names)} анимаций.")
            cmds.inViewMessage(amg=f"Загружено {len(names)} клипов из эталона", pos="midCenter", fade=True)

        except Exception as e:
            print(f"FD_FishTool Error: {e}")
            traceback.print_exc()