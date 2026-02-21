# -*- coding: utf-8 -*-
import sys
import os
from PySide2 import QtWidgets
from maya import cmds

# Импорты компонентов нашего фреймворка
from FD_FishTool.core.config_manager import ConfigManager
from FD_FishTool.ui.main_window import FD_MainWindow

WINDOW_ID = "FD_FishTool_Unique_Window"

def get_maya_window():
    maya_win = {obj.objectName(): obj for obj in QtWidgets.QApplication.topLevelWidgets()}.get("MayaWindow")
    return maya_win

def close_existing_window():
    if cmds.window(WINDOW_ID, exists=True):
        cmds.deleteUI(WINDOW_ID, window=True)
    if cmds.dockControl(WINDOW_ID + "_dock", exists=True):
        cmds.deleteUI(WINDOW_ID + "_dock", control=True)

def run():
    close_existing_window()
    try:
        cfg = ConfigManager() #
    except Exception as e:
        cmds.error(f"FD_FishTool: Config Load Error: {e}")
        return

    global fd_fish_tool_window 
    parent_window = get_maya_window()
    
    # Здесь происходит вызов класса из main_window.py
    fd_fish_tool_window = FD_MainWindow(config=cfg, parent=parent_window)
    fd_fish_tool_window.setObjectName(WINDOW_ID)
    fd_fish_tool_window.show()
    print("FD_FishTool: Pipeline Master Started.")

if __name__ == "__main__":
    run()