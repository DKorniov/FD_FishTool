# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui

class HelpDialog(QtWidgets.QDialog):
    """Универсальное окно справки."""
    def __init__(self, title, text, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)
        
        layout = QtWidgets.QVBoxLayout(self)
        browser = QtWidgets.QTextBrowser()
        browser.setHtml(text)
        layout.addWidget(browser)
        
        btn = QtWidgets.QPushButton("Понятно")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class HelpManager:
    """Централизованное хранилище справок для всего инструмента."""
    
    @staticmethod
    def show_studio_library_help(parent=None):
        title = "Справка | Studio Library Presets"
        text = """
        <h3>Работа с пресетами анимации</h3>
        Этот блок позволяет быстро накладывать эталонные анимации на рыбу.
        <ul>
            <li><b>Select BODY/FACE</b> — Выделяет контролы, для которых предназначена анимация.</li>
            <li><b>Apply BODY/FACE</b> — Накладывает анимацию.</li>
        </ul>
        <i>Примечание: Анимация берется из папки data/studio_lib.</i>
        """
        HelpDialog(title, text, parent).exec_()

    @staticmethod
    def show_physics_help(parent=None):
        title = "Справка | Physics Pipeline"
        text = """
        <h3>Автоматизация SpringMagic</h3>
        Инструмент позволяет просчитывать физику сразу для нескольких цепочек и во всех нужных анимациях.
        <ol>
            <li>Добавьте цепочку кнопкой <b>+</b>.</li>
            <li>Выберите контролы в сцене и нажмите <b>Выбрать</b>.</li>
            <li>Укажите тип (Fin — для плавников, Body — для хвоста).</li>
            <li>Нажмите <b>Просчитать</b>.</li>
        </ol>
        """
        HelpDialog(title, text, parent).exec_()
    
    @staticmethod
    def show_physics_help(parent=None):
        title = "Справка | Spring Selector"
        text = """
        <h3>Динамический просчет физики</h3>
        Этот инструмент автоматизирует работу со SpringMagic для множества цепей.
        <ul>
            <li><b>Добавить цепочку</b> — создает новую строку.</li>
            <li><b>Выбрать</b> — назначает выделенные контролы. Скрипт автоматически найдет симметричную сторону (L/R).</li>
            <li><b>Тип (Fin/Body)</b> — определяет, какие анимации из эталона будут просчитаны.</li>
            <li><b>Очистить выбранные</b> — удаляет анимацию только с тех костей, что вы добавили в список выше.</li>
        </ul>
        """
        HelpDialog(title, text, parent).exec_()