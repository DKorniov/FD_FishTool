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
    # Команда добавляет путь к инструменту в sys.path, чистит кэш и запускает main_app
    run_command = f'''\
import sys
import os

# Путь к родительской папке для импорта модуля
path = r"{os.path.dirname(tool_dir)}"
if path not in sys.path:
    sys.path.append(path)

# 1. Принудительно удаляем все модули инструмента из кэша Python в Maya
for mod in list(sys.modules.keys()):
    if mod.startswith("{tool_folder_name}"):
        del sys.modules[mod]

# 2. Теперь импортируем "с чистого листа"
try:
    import {tool_folder_name}.main_app as main_app
    main_app.run()
except ImportError as e:
    import maya.cmds as cmds
    cmds.warning("Убедитесь, что корневая папка инструмента называется '{tool_folder_name}'.")
    cmds.error(f"{tool_folder_name}: Ошибка импорта инструмента. {{e}}")
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
        overlayLabelColor=(1, 0.6, 0),
        overlayLabelBackColor=(0, 0, 0, 0.5)
    )

    cmds.inViewMessage(amg=f"Кнопка <hl>FD_FishTool</hl> успешно добавлена на полку <hl>{current_shelf}</hl>.", pos='midCenter', fade=True)