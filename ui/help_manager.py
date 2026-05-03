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
    
    @staticmethod
    def show_export_help(parent=None):
        """Окно справки для раздела экспорта и валидации."""
        msg = QtWidgets.QMessageBox(parent)
        msg.setWindowTitle("Справка: Валидация и Экспорт")
        msg.setText("<b>Техническая проверка сцены:</b><br><br>"
                    "1. <b>Naming:</b> Проверяет наличие всех костей из MetaLinks.xml.<br>"
                    "2. <b>Materials:</b> Ищет стандартные материалы проекта (mat_opaque и др.).<br>"
                    "3. <b>Limits:</b> Проверяет лимит костей в скине (&lt; 80) и влияние (&lt; 4).<br><br>"
                    "<b>Подготовка:</b><br>"
                    "Кнопка <i>Toggle</i> переименовывает и перепаренчивает кости для игрового движка. "
                    "Повторное нажатие возвращает риг в рабочее состояние.")
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.exec_()
    
    @staticmethod
    def show_export_preparation_help(parent=None):
        """Окно справки для раздела подготовки и экспорта."""
        msg = QtWidgets.QMessageBox(parent)
        msg.setWindowTitle("Справка: Подготовка и Экспорт")
        msg.setText("<b>Техническая проверка сцены:</b><br><br>"
                    "1. <b> Переключает между режимами экпорта и рига.<br>"
                    "2. <b> Переносит кости и контролы в соответсвующие папки.<br>"
                    "3. <b> Переименовывает кости для игрового движка.<br><br>"
                    )
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.exec_()
    
    # Добавьте эти методы в класс HelpManager в файле help_manager.py

    @staticmethod
    def show_driven_bones_help(parent=None):
        title = "Справка | Driven Bones"
        text = """
        <h3>Список ведомых костей</h3>
        В этом списке отображаются кости, которыми управляет выбранный контроллер.
        <ul>
            <li><b>Авто-заполнение:</b> Список обновляется автоматически при клике на кнопку в селекторе.</li>
            <li><b>Выделение:</b> Выбор элементов в списке дублирует выделение костей в сцене Maya.</li>
        </ul>
        """
        HelpDialog(title, text, parent).exec_()

    @staticmethod
    def show_face_anim_test_help(parent=None):
        title = "Справка | Face Test Tools"
        text = """
        <h3>Тестирование анимации лица</h3>
        Позволяет быстро проверить деформации меша.
        <ul>
            <li><b>Gen Test Anim:</b> Создает ключи на выбранных контроллерах на основе <i>face_test_anim.json</i>.</li>
            <li><b>Clean & Zero:</b> Удаляет все ключи с лицевых контроллеров и возвращает их в нулевое положение.</li>
        </ul>
        """
        HelpDialog(title, text, parent).exec_()

    @staticmethod
    def show_smart_key_help(parent=None):
        title = "Справка | SMART KEY"
        text = """
        <h3>Логика SMART KEY</h3>
        Эта кнопка автоматизирует создание <b>Set Driven Key</b> (SDK).
        <br><br>
        Она определяет тип контроллера (челюсть, веки, губы) и автоматически проставляет ключи 
        в нужных квадрантах (Pos Y, Neg Y и т.д.), включая зеркалирование на противоположную сторону.
        """
        HelpDialog(title, text, parent).exec_()

    @staticmethod
    def show_gradient_weight_help(parent=None):
        title = "Справка | Adaptive Gradient Weight"
        text = """
        <h3>Adaptive Gradient (Топологический градиент)</h3>
        Этот инструмент плавно и автоматически распределяет веса скиннинга, опираясь на <b>топологию (Edge Loops)</b> меша, а не просто на расстояние между точками.
        <br><br>
        <b>Как это работает:</b>
        <ul>
            <li>Берет меш, выбранный во вкладке <b>Body</b> (или выделенный в сцене).</li>
            <li>Анализирует сетку лица и создает идеальный градиент затухания весов для выделенных вертексов/костей.</li>
            <li>Отлично подходит для гладкого скиннинга губ, век и бровей.</li>
        </ul>
        """
        HelpDialog(title, text, parent).exec_()