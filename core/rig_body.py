# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel
import os

class BodyRigManager:
    def __init__(self, config=None):
        self.cfg = config
        self.map_file = "bone_skin_map.json"

    # --- Вспомогательные методы (Рабочая версия) ---
    def launch_advanced_skeleton(self):
        """Запускает скрипт Advanced Skeleton по пути из настроек."""
        if not self.cfg:
            cmds.warning("FD_FishTool: Конфигуратор не загружен!")
            return

        data = self.cfg.load_json("paths.json")
        script_path = data.get("advanced_skeleton_path", "")

        # 1. ПРОВЕРКА НАЛИЧИЯ ФАЙЛА
        if not script_path or not os.path.exists(script_path):
            cmds.warning("FD_FishTool: Путь к Advanced Skeleton не настроен или файл не существует! Укажите его в 'Настройках пайплайна'.")
            return

        # 2. ЗАПУСК СКРИПТА
        # Приводим слеши к правильному формату для Maya MEL
        script_path = script_path.replace("\\", "/")
        
        try:
            if script_path.endswith(".mel"):
                # Для классического Advanced Skeleton 5 (MEL)
                mel.eval(f'source "{script_path}";')
                
                # В MEL-скриптах главная функция обычно совпадает с названием файла (например: AdvancedSkeleton5;)
                func_name = os.path.basename(script_path).replace(".mel", "")
                mel.eval(f'{func_name};')
                
            elif script_path.endswith(".py"):
                # Для Python скриптов (на случай кастомных врапперов)
                with open(script_path, 'r', encoding='utf-8') as f:
                    exec(f.read(), globals())
                    
            print(f"FD_FishTool: Скрипт {os.path.basename(script_path)} успешно запущен!")
        except Exception as e:
            cmds.warning(f"FD_FishTool: Ошибка при запуске скрипта Advanced Skeleton: {e}")
    
    def set_bones_color(self, color_rgb):
        """Изменяет цвет (Drawing Overrides) выделенных костей."""
        selection = cmds.ls(selection=True, type='joint')
        
        if not selection:
            cmds.warning("FD_FishTool: Выделите хотя бы одну кость для изменения цвета!")
            return
            
        r, g, b = color_rgb
        for bone in selection:
            # 1. Включаем переопределение отображения
            cmds.setAttr(f"{bone}.overrideEnabled", 1)
            # 2. Включаем режим цвета RGB (вместо стандартного индексного Maya)
            cmds.setAttr(f"{bone}.overrideRGBColors", 1)
            # 3. Применяем цвет
            cmds.setAttr(f"{bone}.overrideColorRGB", r, g, b)
            
        print(f"FD_FishTool: Цвет успешно изменен для {len(selection)} костей.")

    def colorize_meta_bones_in_outliner(self):
        """Подсвечивает META-кости (найденные в bone_map.json) в Outliner."""
        if not self.cfg:
            cmds.warning("FD_FishTool: Конфигуратор не загружен!")
            return

        # 1. Загружаем bone_map.json (используя ConfigManager)
        bone_map = self.cfg.load_json("bone_map.json")
        if not bone_map:
            cmds.warning("FD_FishTool: Файл bone_map.json не найден или пуст! Проверьте папку data.")
            return

        # 2. Собираем все уникальные имена костей из ключей и значений JSON
        target_names = set()
        for key, value in bone_map.items():
            target_names.add(key)
            # Значение может быть строкой или списком
            if isinstance(value, str):
                target_names.add(value)
            elif isinstance(value, list):
                target_names.update(value)

        # 3. Ищем эти кости в текущей сцене
        all_joints = cmds.ls(type='joint')
        matched_joints = []
        
        for jnt in all_joints:
            # Извлекаем чистое имя (без путей вроде |root|spine и без неймспейсов)
            short_name = jnt.split(':')[-1].split('|')[-1]
            if short_name in target_names or jnt in target_names:
                matched_joints.append(jnt)

        if not matched_joints:
            cmds.warning("FD_FishTool: Ни одна кость из bone_map.json не найдена в текущей сцене!")
            return

        # 4. Меняем цвет в Outliner (Выбран ярко-оранжевый цвет)
        r, g, b = (1.0, 0.65, 0.0) 
        
        for jnt in matched_joints:
            try:
                # Включаем кастомный цвет в Outliner
                cmds.setAttr(f"{jnt}.useOutlinerColor", True)
                # Применяем RGB
                cmds.setAttr(f"{jnt}.outlinerColor", r, g, b)
            except Exception as e:
                print(f"FD_FishTool: Ошибка при покраске кости {jnt}: {e}")
                
        print(f"FD_FishTool: Успешно изменен цвет в Outliner для {len(matched_joints)} META-костей.")
    
    def reset_bones_color(self, all_bones=False):
        """Сбрасывает цвет (Drawing Overrides) костей на дефолтный. 
        Если all_bones=True, сбрасывает все кости в сцене, иначе - только выделенные."""
        
        if all_bones:
            target_bones = cmds.ls(type='joint')
            if not target_bones:
                cmds.warning("FD_FishTool: В сцене нет костей!")
                return
        else:
            target_bones = cmds.ls(selection=True, type='joint')
            if not target_bones:
                cmds.warning("FD_FishTool: Выделите хотя бы одну кость для сброса цвета (или включите галочку 'for_all_bones')!")
                return
            
        for bone in target_bones:
            # 1. Отключаем переопределение цвета во вьюпорте (возвращает стандартный темно-фиолетовый)
            if cmds.attributeQuery("overrideEnabled", node=bone, exists=True):
                cmds.setAttr(f"{bone}.overrideEnabled", 0)
                
            # 2. Отключаем пользовательский цвет в Outliner (возвращает стандартный белый текст)
            if cmds.attributeQuery("useOutlinerColor", node=bone, exists=True):
                cmds.setAttr(f"{bone}.useOutlinerColor", 0)
        
        mode_text = "всех" if all_bones else "выделенных"
        print(f"FD_FishTool: Цвет успешно сброшен на дефолтный для {len(target_bones)} {mode_text} костей.")

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
    
    def snap_pivot_to_zero_and_freeze(self):
        """Переносит Pivot выделенных объектов в [0, 0, 0], делает Freeze Transformations и удаляет Non-Deformer историю."""
        selection = cmds.ls(selection=True, type='transform')
        
        if not selection:
            cmds.warning("FD_FishTool: Ничего не выбрано! Выберите объект.")
            return

        for obj in selection:
            # Перемещаем ПИВОТ к началу координат [0, 0, 0]
            cmds.xform(obj, piv=(0, 0, 0), worldSpace=True)
            
            # Freeze Transformations (Apply: Translate, Rotate, Scale)
            cmds.makeIdentity(obj, apply=True, translate=True, rotate=True, scale=True, normal=0)
            
        # Восстанавливаем выделение, так как doBakeNonDefHistory работает с активным селекшеном
        cmds.select(selection, replace=True)
        
        # Вызываем MEL-команду очистки Non-Deformer истории
        mel.eval('doBakeNonDefHistory( 1, {"prePost"} );')
            
        cmds.select(clear=True)
        print("FD_FishTool: Пивот перемещен в [0,0,0], трансформации заморожены, Non-Deformer история удалена.")
    
    def check_model_symmetry(self, mesh_name):
        """Проверяет меш только на симметрию (точная дистанция по локальному X)."""
        if not mesh_name or not cmds.objExists(mesh_name):
            cmds.warning("FD_FishTool: Меш не найден или не выбран в списке!")
            return

        problem_vtxs = set()

        # 1. ПРОВЕРКА НА СИММЕТРИЮ (Быстрая хэш-сетка + точная проверка)
        vtxs = cmds.ls(mesh_name + '.vtx[*]', flatten=True)
        if vtxs:
            coords = cmds.xform(vtxs, q=True, os=True, t=True)
            
            left_vtxs = []
            right_vtxs = []
            tol = 0.001 # Толерантность совпадения вершин (0.001 юнита)
            
            for i, vtx in enumerate(vtxs):
                x, y, z = coords[i*3], coords[i*3+1], coords[i*3+2]
                if x > tol:
                    right_vtxs.append((vtx, x, y, z))
                elif x < -tol:
                    left_vtxs.append((vtx, x, y, z))
            
            # Строим словарь для левой стороны (ключ - грубые координаты до сотых)
            left_dict = {}
            for vtx, x, y, z in left_vtxs:
                key = (round(abs(x), 2), round(y, 2), round(z, 2))
                if key not in left_dict:
                    left_dict[key] = []
                left_dict[key].append((vtx, x, y, z))
                
            matched_left = set()
            
            # Проверяем правую сторону
            for vtx_r, x_r, y_r, z_r in right_vtxs:
                key = (round(x_r, 2), round(y_r, 2), round(z_r, 2))
                candidates = left_dict.get(key, [])
                
                match_found = False
                for c_vtx, c_x, c_y, c_z in candidates:
                    if c_vtx in matched_left:
                        continue
                    
                    # Точная проверка дистанции
                    if (abs(abs(x_r) - abs(c_x)) < tol and 
                        abs(y_r - c_y) < tol and 
                        abs(z_r - c_z) < tol):
                        match_found = True
                        matched_left.add(c_vtx)
                        break
                
                if not match_found:
                    problem_vtxs.add(vtx_r)
                    
            # Все левые вершины без правой пары — асимметричны
            for vtx, _, _, _ in left_vtxs:
                if vtx not in matched_left:
                    problem_vtxs.add(vtx)

        # 2. ВЫВОД РЕЗУЛЬТАТОВ И ПОДСВЕТКА
        problem_list = list(problem_vtxs)

        if problem_list:
            cmds.selectMode(component=True)
            cmds.hilite(mesh_name, replace=True)
            cmds.selectType(vertex=True)
            cmds.select(problem_list, replace=True)
            
            msg = f"FD_FishTool: НАЙДЕНА АСИММЕТРИЯ ({len(problem_list)} вертексов)! Возможно, пивот меша не по центру (не в X=0)."
            cmds.warning(msg)
        else:
            cmds.selectMode(object=True)
            cmds.select(mesh_name, replace=True)
            print(f"FD_FishTool: Меш {mesh_name} идеален! Симметрия строго соблюдена.")
    
    def import_sizecheck_mesh(self):
        """Импортирует эталонный меш ClownFish.fbx из папки data для проверки размера."""
        # Вычисляем абсолютный путь: скрипт лежит в core/, значит папка data/ находится на уровень выше
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fbx_path = os.path.join(current_dir, "..", "data", "ClownFish.fbx")
        fbx_path = os.path.normpath(fbx_path)

        # Проверка существования файла
        if not os.path.exists(fbx_path):
            cmds.warning(f"FD_FishTool: Файл эталона не найден! Ожидаемый путь: {fbx_path}")
            return

        # Проверяем, загружен ли плагин FBX в Maya
        if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
            cmds.loadPlugin('fbxmaya')

        try:
            # Импортируем файл с уникальным namespace, чтобы избежать конфликтов имён в сцене
            imported_nodes = cmds.file(
                fbx_path, 
                i=True, 
                type="FBX", 
                returnNewNodes=True, 
                namespace="SizeCheckFish", 
                mergeNamespacesOnClash=False
            )
            
            # Находим корневые объекты (transform без родителей) среди импортированных
            transforms = cmds.ls(imported_nodes, type='transform')
            top_level = [t for t in transforms if not cmds.listRelatives(t, parent=True)]
            
            # Принудительно ставим их в [0, 0, 0] на случай, если FBX был сохранен криво
            for obj in top_level:
                cmds.xform(obj, translation=(0, 0, 0), worldSpace=True)
            
            cmds.select(clear=True)
            print(f"FD_FishTool: Эталон {os.path.basename(fbx_path)} успешно импортирован!")
            
        except Exception as e:
            cmds.warning(f"FD_FishTool: Ошибка при импорте FBX: {e}")

    def get_vtx_neighbors(self, vtx_list):
        if not vtx_list: return set()
        edges = cmds.polyListComponentConversion(list(vtx_list), toEdge=True)
        neighbors = cmds.polyListComponentConversion(edges, toVertex=True)
        return set(cmds.ls(neighbors, fl=True))

    def get_bone_island(self, sc, bone):
        """Рабочий метод получения островов через выделение."""
        try:
            cmds.select(cl=True)
            cmds.skinCluster(sc, edit=True, selectInfluenceVerts=bone)
            return set(cmds.ls(sl=True, fl=True))
        except: return set()

    def get_topology_distance(self, start_island, target_island):
        """Считает количество 'лупов' между двумя островами (Рабочая версия)."""
        current_area = set(start_island)
        edge_vtx = set(start_island)
        for i in range(1, 11):
            next_step = self.get_vtx_neighbors(list(edge_vtx)) - current_area
            if not next_step: break
            if next_step & target_island:
                return i
            current_area.update(next_step)
            edge_vtx = next_step
        return 10

    def apply_topological_gradient(self, mesh_name):
        """Стабильный мульти-режимный градиент (Step 3 XL)."""
        joints = cmds.ls(os=True, type='joint')
        if len(joints) < 2: return
        sc = cmds.ls(cmds.listHistory(mesh_name), type='skinCluster')[0]

        MODES = {
            1: {"name": "DENSE", "steps": [0.25, 0.1]},
            2: {"name": "STANDARD", "steps": [0.5, 0.25, 0.1]},
            3: {"name": "STANDARD XL", "steps": [0.75, 0.5, 0.25, 0.1]},
            4: {"name": "STANDARD XXL", "steps": [0.9, 0.75, 0.5, 0.25, 0.1]},
            5: {"name": "STANDARD XXXL", "steps": [1.0, 0.9, 0.75, 0.5, 0.25, 0.1]}
        }

        print("\n" + "="*70 + "\nFD_FishTool: ADAPTIVE XL GRADIENT (STABLE CHECKPOINT)\n" + "="*70)

        def expand(src_bone, tgt_bone, label):
            src_isl = self.get_bone_island(sc, src_bone); tgt_isl = self.get_bone_island(sc, tgt_bone)
            if not src_isl or not tgt_isl: return
            dist = self.get_topology_distance(src_isl, tgt_isl)
            mode = MODES[dist if dist in MODES else 5]
            print(f"  [{label}] {src_bone} -> {tgt_bone} | Dist: {dist} | Mode: {mode['name']}")

            frontier = {v for v in src_isl if self.get_vtx_neighbors([v]) - src_isl}
            curr_area = set(src_isl); prev_loop = set(frontier)
            for idx, weight in enumerate(mode["steps"]):
                next_loop = (self.get_vtx_neighbors(list(prev_loop)) - curr_area) & tgt_isl
                if next_loop:
                    cmds.skinPercent(sc, list(next_loop), tv=[(src_bone, weight)], relative=True, nrm=True)
                    print(f"    > Row {idx+1}: ADD {weight}")
                    curr_area.update(next_loop); prev_loop = next_loop
                else: break

        for i in range(len(joints)):
            if i + 1 < len(joints): expand(joints[i], joints[i+1], "FORWARD")
            if i - 1 >= 0: expand(joints[i], joints[i-1], "BACKWARD")
        cmds.select(joints, r=True)

    # --- Секция Скиннинга (Рабочая фильтрация плавников) ---
    def get_full_bone_list(self, stage_key):
        data = self.cfg.load_json(self.map_file)
        if not data or stage_key not in data: return []
        s_data = data[stage_key]; final = []
        if "chains" in s_data:
            for r in s_data["chains"]:
                if cmds.objExists(r):
                    final.append(r); curr = r
                    while True:
                        child = cmds.listRelatives(curr, c=True, type='joint')
                        if not child: break
                        curr = child[0]; final.append(curr)
        if "roots" in s_data:
            for r in s_data["roots"]:
                if cmds.objExists(r):
                    final.append(r); final.extend(cmds.listRelatives(r, ad=True, type='joint') or [])
        if "list" in s_data: final.extend(s_data["list"])
        return sorted(list(set([j for j in final if cmds.objExists(j)])))

    def select_stage_bones(self, idx):
        bones = self.get_full_bone_list(f"stage_{idx}")
        if bones: cmds.select(bones, r=True)

    def add_to_skin_logic(self, idx, mesh):
        bones = self.get_full_bone_list(f"stage_{idx}")
        if not bones or not cmds.objExists(mesh): return
        sc = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        if idx == 1 and not sc:
            cmds.select(bones, r=True); cmds.select(mesh, add=True)
            cmds.skinCluster(tsb=True, bm=0, nw=1, wd=0, mi=4, omi=True, dr=4, rui=False)
        elif sc:
            existing = cmds.skinCluster(sc[0], q=True, inf=True)
            for b in bones:
                if b not in existing: cmds.skinCluster(sc[0], edit=True, ai=b, lw=True, wt=0)

    def select_weighted_bones(self, mesh):
        sc = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        if sc: cmds.select(cmds.skinCluster(sc[0], q=True, inf=True), r=True)

    def clean_weightless_bones(self, mesh):
        sc = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
        if sc:
            cmds.select(mesh, r=True); mel.eval("removeUnusedInfluences;")
            cmds.skinCluster(sc[0], edit=True, rui=True)

    
    # --- Секция Материалов ---

    def find_textures_in_project(self):
        """Ищет текстуры в папке sourceimages, только если сцена сохранена и имеет проект."""
        # Проверяем, сохранена ли текущая сцена (если Untitled, вернет пустую строку)
        scene_name = cmds.file(q=True, sn=True)
        if not scene_name:
            return [] # Сцена не сохранена, точного проекта нет, форсируем ручной выбор
            
        workspace = cmds.workspace(q=True, rootDirectory=True)
        sourceimages = os.path.join(workspace, "sourceimages")
        textures = []
        
        if os.path.exists(sourceimages):
            valid_exts = ('.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff')
            for f in os.listdir(sourceimages):
                if f.lower().endswith(valid_exts):
                    textures.append(os.path.join(sourceimages, f))
        return textures


    def create_fish_materials(self, texture_path, overwrite=False):
        """Создает 4 эталонных phong материала и подключает к ним текстуру."""
        mat_names = ["mat_opaque", "mat_transparent", "mat_overlap_eyes", "mat_overlap_teeth"]
        
        # Проверка существующих материалов
        existing = [m for m in mat_names if cmds.objExists(m)]
        if existing and not overwrite:
            # Возвращаем Shading Groups существующих материалов
            return {m: cmds.listConnections(m + ".outColor", type="shadingEngine")[0] for m in existing}
        
        # Удаляем старые, если запрошена перезапись
        for m in mat_names:
            if cmds.objExists(m):
                sg = cmds.listConnections(m + ".outColor", type="shadingEngine")
                cmds.delete(m)
                if sg: cmds.delete(sg)
                
        # Создаем единую ноду файла (оптимизация для сцены)
        file_node = cmds.shadingNode('file', asTexture=True, isColorManaged=True)
        cmds.setAttr(file_node + ".fileTextureName", texture_path, type="string")
        p2d = cmds.shadingNode('place2dTexture', asUtility=True)
        
        # Подключаем place2dTexture к file
        attrs = ["coverage", "translateFrame", "rotateFrame", "mirrorU", "mirrorV", "stagger", 
                 "wrapU", "wrapV", "repeatUV", "offset", "rotateUV", "noiseUV", 
                 "vertexUvOne", "vertexUvTwo", "vertexUvThree", "vertexCameraOne"]
        for attr in attrs:
            cmds.connectAttr(p2d + "." + attr, file_node + "." + attr, f=True)
        cmds.connectAttr(p2d + ".outUV", file_node + ".uvCoord")
        cmds.connectAttr(p2d + ".outUvFilterSize", file_node + ".uvFilterSize")
        
        sgs = {}
        for m in mat_names:
            mat = cmds.shadingNode('phong', asShader=True, name=m)
            sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=m + "SG")
            cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader", f=True)
            
            # Применяем настройки из fish_materials.ma
            cmds.setAttr(mat + ".ambientColor", 1, 1, 1, type="double3")
            cmds.setAttr(mat + ".specularColor", 0, 0, 0, type="double3")
            cmds.setAttr(mat + ".reflectivity", 0)
            cmds.setAttr(mat + ".cosinePower", 2)
            
            # Подключаем текстуру к цвету (для всех материалов)
            cmds.connectAttr(file_node + ".outColor", mat + ".color", f=True)
            
            # РАЗДЕЛЕНИЕ ЛОГИКИ АЛЬФА-КАНАЛА:
            if m == "mat_transparent":
                # Только для плавников подключаем прозрачность из текстуры
                cmds.connectAttr(file_node + ".outTransparency", mat + ".transparency", f=True)
            else:
                # Для глаз, зубов и тела жестко задаем непрозрачность (черный цвет = 0, 0, 0)
                cmds.setAttr(mat + ".transparency", 0, 0, 0, type="double3")
            
            sgs[m] = sg
            
        return sgs

    def assign_material(self, targets, sg_name):
        """Назначает материал (Shading Group) на переданные объекты или полигоны."""
        if targets and cmds.objExists(sg_name):
            try:
                cmds.sets(targets, e=True, forceElement=sg_name)
            except Exception as e:
                cmds.warning(f"FD_FishTool: Ошибка назначения материала {sg_name}: {e}")
    
    # --- Секция анимаций ---

    def apply_test_animation(self, anim_key):
        """Загружает ключи из body_test_anim.json и применяет их к контролам, предварительно сбросив их в Bind Pose."""
        import json
        
        # Определяем путь к файлу в папке data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "..", "data", "body_test_anim.json")
        json_path = os.path.normpath(json_path)

        if not os.path.exists(json_path):
            cmds.warning(f"FD_FishTool: Файл анимации не найден: {json_path}")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            cmds.warning(f"FD_FishTool: Ошибка чтения JSON файла (проверьте синтаксис): {e}")
            return

        anim_data = data.get(anim_key, {})
        if not anim_data:
            cmds.warning(f"FD_FishTool: В JSON не найден ключ '{anim_key}'!")
            return

        # 1. Проверка наличия контролов в сцене
        controls_in_scene = [ctrl for ctrl in anim_data.keys() if cmds.objExists(ctrl)]
        if not controls_in_scene:
            cmds.warning(f"FD_FishTool: В сцене не найдено ни одного контрола для {anim_key}!")
            return

        keys_set = 0
        for ctrl in controls_in_scene:
            # 2. Удаляем старую анимацию
            if cmds.keyframe(ctrl, query=True, keyframeCount=True):
                # ИСПРАВЛЕНО: time=(":",) и clear=True
                cmds.cutKey(ctrl, clear=True, time=(":",))
                
            # 3. СБРОС В BIND POSE (0,0,0 для T/R и 1,1,1 для S)
            # Проверяем, существует ли атрибут и можно ли в него писать (не заблокирован ли он)
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                if cmds.attributeQuery(attr, node=ctrl, exists=True) and cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    cmds.setAttr(f"{ctrl}.{attr}", 0.0)
                    
            for attr in ['sx', 'sy', 'sz']:
                if cmds.attributeQuery(attr, node=ctrl, exists=True) and cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    cmds.setAttr(f"{ctrl}.{attr}", 1.0)
            
            # 4. Устанавливаем новые ключи
            ctrl_data = anim_data[ctrl]
            frames = ctrl_data.get("frames", [])
            for attr, values in ctrl_data.items():
                if attr == "frames":
                    continue
                
                # Проверяем, существует ли кастомный атрибут на контроле (например, FKIKBlend)
                if cmds.attributeQuery(attr, node=ctrl, exists=True):
                    for i, f in enumerate(frames):
                        if i < len(values):
                            cmds.setKeyframe(ctrl, attribute=attr, time=f, value=values[i])
                            keys_set += 1
                            
        print(f"FD_FishTool: Успешно установлено {keys_set} ключей для {anim_key}.")

    def delete_all_test_animation(self):
        """Удаляет всю анимацию с контролов (описанных в JSON файле) и сбрасывает их трансформации."""
        import json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "..", "data", "body_test_anim.json")
        json_path = os.path.normpath(json_path)

        controls_to_clean = set()
        
        # 1. Собираем все контролы из JSON файла
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, val in data.items():
                        if isinstance(val, dict):
                            for ctrl in val.keys():
                                controls_to_clean.add(ctrl)
            except Exception:
                pass

        # Если файл не прочитался или пуст, собираем вообще все контролы (кривые) в сцене
        if not controls_to_clean:
            curves = cmds.ls(type="nurbsCurve")
            if curves:
                for c in curves:
                    parent = cmds.listRelatives(c, parent=True)
                    if parent: controls_to_clean.add(parent[0])

        existing_ctrls = [c for c in controls_to_clean if cmds.objExists(c)]
        if not existing_ctrls:
            cmds.warning("FD_FishTool: Контролы для очистки не найдены в сцене.")
            return

        cleaned_count = 0
        for ctrl in existing_ctrls:
            # 2. Удаляем ключи
            keys_count = cmds.keyframe(ctrl, query=True, keyframeCount=True)
            if keys_count:
                # ИСПРАВЛЕНО: time=(":",) и clear=True
                cmds.cutKey(ctrl, clear=True, time=(":",))
                cleaned_count += 1
                
            # 3. СБРОС В BIND POSE (0,0,0, 0,0,0, 1,1,1)
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                if cmds.attributeQuery(attr, node=ctrl, exists=True) and cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    cmds.setAttr(f"{ctrl}.{attr}", 0.0)
                    
            for attr in ['sx', 'sy', 'sz']:
                if cmds.attributeQuery(attr, node=ctrl, exists=True) and cmds.getAttr(f"{ctrl}.{attr}", settable=True):
                    cmds.setAttr(f"{ctrl}.{attr}", 1.0)
                
        print(f"FD_FishTool: Анимация удалена с {cleaned_count} контролов. Все контролы сброшены в T-Pose.")