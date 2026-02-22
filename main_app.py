# -*- coding: utf-8 -*-
"""
FD_FishTool: Главная точка входа.
Отвечает за инициализацию приложения, проверку дубликатов интерфейса и запуск.
"""

import sys
import os
from PySide2 import QtWidgets
from maya import cmds

# Импорты компонентов нашего фреймворка
from FD_FishTool.core.config_manager import ConfigManager
from FD_FishTool.ui.main_window import FD_MainWindow

# Уникальный идентификатор окна для Maya UI
WINDOW_ID = "FD_FishTool_Unique_Window"

def get_maya_window():
    """
    Находит главное окно Maya в иерархии Qt объектов.
    Необходимо для того, чтобы окно инструмента всегда было поверх Maya.
    """
    maya_win = {obj.objectName(): obj for obj in QtWidgets.QApplication.topLevelWidgets()}.get("MayaWindow")
    return maya_win

def close_existing_window():
    """
    Проверяет, открыто ли уже окно или док-панель с нашим ID, и удаляет их.
    Это предотвращает дублирование интерфейсов при повторном запуске.
    """
    # Удаляем обычное окно
    if cmds.window(WINDOW_ID, exists=True):
        cmds.deleteUI(WINDOW_ID, window=True)
    
    # Удаляем dockControl, если он вдруг использовался
    if cmds.dockControl(WINDOW_ID + "_dock", exists=True):
        cmds.deleteUI(WINDOW_ID + "_dock", control=True)

def run():
    """
    Основная функция запуска инструмента.
    """
    # 1. Закрываем старые экземпляры тулзы
    close_existing_window()

    # 2. Инициализируем конфиг (он подгрузит data/paths.json и bone_map.json)
    try:
        cfg = ConfigManager()
    except Exception as e:
        cmds.error(f"FD_FishTool: Ошибка при загрузке конфигурации: {e}")
        return

    # 3. Создаем экземпляр окна
    # Мы объявляем переменную глобальной, чтобы Maya не очистила её из памяти
    global fd_fish_tool_window 
    
    parent_window = get_maya_window()
    fd_fish_tool_window = FD_MainWindow(config=cfg, parent=parent_window)
    fd_fish_tool_window.setObjectName(WINDOW_ID)

    # 4. Отображаем инструмент
    fd_fish_tool_window.show()
    
    print("FD_FishTool: Приложение успешно инициализировано и запущено.")

if __name__ == "__main__":
    # Этот блок сработает, если запустить файл напрямую из Maya Script Editor
    run()