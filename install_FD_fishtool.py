# -*- coding: utf-8 -*-
"""
FD_FishTool: Скрипт автоматической установки.
Установка (Drag and Drop):
Перетащите этот файл (install.py) в окно Viewport Maya. 
Скрипт автоматически создаст кнопку на текущей открытой полке (Shelf).
"""

import os
import sys
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
    
    # Путь к родительской папке (нужно для корректного 'import FD_FishTool...')
    parent_dir = os.path.dirname(tool_dir)
    
    # Имя папки инструмента (должно быть FD_FishTool для правильных импортов)
    tool_folder_name = os.path.basename(tool_dir)

    # 2. Получаем текущую активную полку в Maya
    try:
        current_shelf = mel.eval('global string $gShelfTopLevel; $temp = `tabLayout -q -selectTab $gShelfTopLevel`;')
    except Exception as e:
        cmds.error(f"Не удалось определить текущую полку: {e}")
        return False

    # 3. Формируем код, который будет исполняться при нажатии кнопки на полке
    # Мы добавляем путь динамически, чтобы не нужно было прописывать его в userSetup.py
    run_command = f'''import sys
import os

tool_path = r"{parent_dir}"
if tool_path not in sys.path:
    sys.path.insert(0, tool_path)

try:
    from {tool_folder_name} import main_app
    # Принудительная перезагрузка модуля удобна, если ты обновляешь код инструмента в процессе работы
    import importlib
    importlib.reload(main_app)
    
    main_app.run()
except ImportError as e:
    import maya.cmds as cmds
    cmds.warning("Убедитесь, что корневая папка инструмента называется 'FD_FishTool'.")
    cmds.error(f"FD_FishTool: Ошибка импорта инструмента. {{e}}")
except Exception as e:
    import maya.cmds as cmds
    cmds.error(f"FD_FishTool: Ошибка при запуске: {{e}}")
'''

    # 4. Проверяем, есть ли своя иконка (например в папке data), если нет - используем дефолтную Python иконку
    icon_path = 'pythonFamily.png'
    custom_icon = os.path.join(tool_dir, "data", "studio_lib", "AS_face_set.set", "thumbnail.jpg")
    if os.path.exists(custom_icon):
        icon_path = custom_icon

    # 5. Создаем кнопку на полке
    cmds.shelfButton(
        parent=current_shelf,
        command=run_command,
        annotation='Запуск FD_FishTool (генерация и анимация рыбок)',
        sourceType='Python',
        image=icon_path,
        label='FishTool',
        imageOverlayLabel='FISH' # Текст поверх иконки
    )

    # 6. Уведомляем пользователя об успешной установке
    cmds.confirmDialog(
        title='FD_FishTool Installer',
        message='Установка успешно завершена!\n\nКнопка "FishTool" была добавлена на вашу текущую полку.\nНажмите на нее для запуска.',
        button=['Отлично!']
    )
    
    print("FD_FishTool: Кнопка успешно добавлена на полку.")
    return True