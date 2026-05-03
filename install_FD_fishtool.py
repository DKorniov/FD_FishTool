# -*- coding: utf-8 -*-
"""
FD_FishTool: Скрипт автоматической установки.
Установка (Drag and Drop):
Перетащите этот файл (install_FD_fishtool.py) в окно Viewport Maya. 
Скрипт автоматически создаст кнопку на текущей открытой полке (Shelf).
"""

import os
import maya.cmds as cmds
import maya.mel as mel

def onMayaDroppedPythonFile(*args):
    """
    Магическая функция Maya. Вызывается автоматически при Drag-and-Drop
    файла во Viewport.
    """
    # 1. Получаем пути
    # Путь к папке скрипта (ожидается, что это папка FD_FishTool)
    tool_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Имя папки инструмента
    tool_folder_name = os.path.basename(tool_dir)

    # 2. Получаем текущую активную полку в Maya
    try:
        current_shelf = mel.eval('global string $gShelfTopLevel; $temp = `tabLayout -q -selectTab $gShelfTopLevel`;')
    except Exception as e:
        cmds.error(f"Не удалось определить текущую полку: {e}")
        return

    # 3. Формируем команду запуска
    # Команда добавляет путь к инструменту в sys.path и запускает main_app
    run_command = f'''
import sys
import os

# Путь к родительской папке для импорта модуля
path = r"{os.path.dirname(tool_dir)}"
if path not in sys.path:
    sys.path.append(path)

try:
    import FD_FishTool.main_app as main_app
    import importlib
    importlib.reload(main_app)
    main_app.run()
except ImportError as e:
    import maya.cmds as cmds
    cmds.warning("Убедитесь, что корневая папка инструмента называется 'FD_FishTool'.")
    cmds.error(f"FD_FishTool: Ошибка импорта инструмента. {{e}}")
'''

    # 4. Поиск иконки (согласно манифесту)
    # Ищем иконку в папке icons внутри FD_FishTool
    icon_path = os.path.normpath(os.path.join(tool_dir, "icons", "fd_fishtool_icon.png")).replace("\\", "/")
    
    # Проверка наличия файла, если нет — используем стандартную иконку Python
    if not os.path.exists(icon_path):
        cmds.warning(f"Иконка не найдена по пути: {icon_path}. Будет использована стандартная.")
        icon_path = 'pythonFamily.png'

    # 5. Создаем кнопку на полке
    cmds.shelfButton(
        parent=current_shelf,
        command=run_command,
        annotation='Запуск FD_FishTool (генерация и анимация рыбок)',
        sourceType='Python',
        image=icon_path,
        label='FishTool',
        imageOverlayLabel='', # Текст поверх иконки
        overlayLabelColor=(1, 0.6, 0), # Оранжевый текст (как в манифесте)
        overlayLabelBackColor=(0, 0, 0, 0.4)
    )

    # 6. Уведомление
    cmds.confirmDialog(
        title='Установка завершена',
        message=f'Кнопка FD_FishTool успешно добавлена на полку "{current_shelf}".',
        button=['OK']
    )
    print(f"FD_FishTool: Кнопка создана с иконкой: {icon_path}")