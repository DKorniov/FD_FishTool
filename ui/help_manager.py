# -*- coding: utf-8 -*-
import os
from PySide2 import QtWidgets, QtCore, QtGui

class HelpDialog(QtWidgets.QDialog):
    """Универсальное окно справки с поддержкой текста, изображений и GIF."""
    def __init__(self, title, html_text, image_filename=None, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)
        # Окно будет поверх Maya, но не заблокирует её работу (Modeless)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 1. БЛОК ИЗОБРАЖЕНИЯ ИЛИ GIF
        if image_filename:
            # Ищем файл в папке data/help относительно текущего файла
            current_dir = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.normpath(os.path.join(current_dir, "..", "data", "help", image_filename))

            if os.path.exists(img_path):
                img_label = QtWidgets.QLabel()
                img_label.setAlignment(QtCore.Qt.AlignCenter)
                
                # Если это GIF - запускаем через QMovie
                if img_path.lower().endswith('.gif'):
                    self.movie = QtGui.QMovie(img_path)
                    img_label.setMovie(self.movie)
                    self.movie.start()
                # Если статичная картинка - грузим через QPixmap
                else:
                    pixmap = QtGui.QPixmap(img_path)
                    pixmap = pixmap.scaled(600, 600, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    img_label.setPixmap(pixmap)
                    
                layout.addWidget(img_label)
            else:
                # Заглушка, если файл не найден
                err_lbl = QtWidgets.QLabel(f"<i>[Изображение не найдено: data/help/{image_filename}]</i>")
                err_lbl.setStyleSheet("color: red;")
                err_lbl.setAlignment(QtCore.Qt.AlignCenter)
                layout.addWidget(err_lbl)

        # 2. БЛОК ТЕКСТА
        text_label = QtWidgets.QLabel(html_text)
        text_label.setWordWrap(True)
        text_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        text_label.setStyleSheet("font-size: 10pt;")
        layout.addWidget(text_label)

        # 3. КНОПКА ЗАКРЫТИЯ
        btn_close = QtWidgets.QPushButton("Понятно")
        btn_close.setFixedHeight(35)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class HelpManager:
    """Централизованное хранилище справок для всего инструмента."""

    @staticmethod
    def show_stage_skin_help(parent=None):
        title = "Справка | Staged Skinning"
        text = """
        <b>Поэтапный скиннинг (Staged Skinning)</b><br><br>
        Инструмент позволяет разбить скиннинг рыбы на этапы:
        <ol>
            <li><b>Body</b> — основная масса.</li>
            <li><b>Side Fins</b> — боковые плавники.</li>
            <li><b>Vert Fins</b> — верхние/нижние плавники.</li>
        </ol>
        """
        HelpDialog(title, text, parent=parent).exec_()

    @staticmethod
    def show_skin_anim_help(parent=None):
        title = "Справка | Skin Animations"
        text = """
        <b>Тестовые анимации</b><br><br>
        Проверка деформаций меша в крайних позах через загрузку <i>body_test_anim.json</i>.
        """
        HelpDialog(title, text, parent=parent).exec_()
    
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
        HelpDialog(title, text, parent=parent).exec_()

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
        HelpDialog(title, text, parent=parent).exec_()
    
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
                    "1. <b> Переключает между режимами экспорта и рига.<br>"
                    "2. <b> Переносит кости и контролы в соответствующие папки.<br>"
                    "3. <b> Переименовывает кости для игрового движка.<br><br>"
                    )
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.exec_()

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
        HelpDialog(title, text, parent=parent).exec_()

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
        HelpDialog(title, text, parent=parent).exec_()

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
        HelpDialog(title, text, parent=parent).exec_()

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
        HelpDialog(title, text, parent=parent).exec_()