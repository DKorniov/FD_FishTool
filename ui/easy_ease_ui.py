# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds
from FD_FishTool.core.easy_ease import EasyEaseEngine

class EasyEaseWidget(QtWidgets.QWidget):
    def __init__(self, rig_manager, mesh_getter, parent=None):
        super(EasyEaseWidget, self).__init__(parent)
        self.engine = EasyEaseEngine(rig_manager)
        self.get_mesh = mesh_getter
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(8)

        # Верхняя панель управления (Глубина + Инфо)
        top_lay = QtWidgets.QHBoxLayout()
        top_lay.addWidget(QtWidgets.QLabel("🔍 Decay Depth (Loops):"))
        self.depth_spin = QtWidgets.QSpinBox()
        self.depth_spin.setRange(1, 10); self.depth_spin.setValue(4)
        top_lay.addWidget(self.depth_spin)
        
        top_lay.addStretch()
        
        # Кнопка описания инструмента
        self.help_btn = QtWidgets.QPushButton("?")
        self.help_btn.setFixedSize(20, 20)
        self.help_btn.setStyleSheet("border-radius: 10px; background: #555; font-weight: bold;")
        self.help_btn.clicked.connect(self._show_help_dialog)
        top_lay.addWidget(self.help_btn)
        
        layout.addLayout(top_lay)

        # Метки костей (Динамические)
        hl = QtWidgets.QHBoxLayout()
        self.bn1_lbl = QtWidgets.QLabel("🔴 <b>BN1</b>")
        self.ea_lbl = QtWidgets.QLabel("<b>EASE (0.0)</b>")
        self.bn2_lbl = QtWidgets.QLabel("<b>BN2</b> 🔵")
        hl.addWidget(self.bn1_lbl); hl.addStretch(); hl.addWidget(self.ea_lbl); hl.addStretch(); hl.addWidget(self.bn2_lbl)
        layout.addLayout(hl)

        self.ease_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ease_slider.setRange(-20, 20); self.ease_slider.setValue(0)
        self.ease_slider.setFixedHeight(30)
        
        self.ease_slider.sliderPressed.connect(self._on_press)
        self.ease_slider.sliderMoved.connect(self._on_move)
        self.ease_slider.sliderReleased.connect(self._on_release)
        layout.addWidget(self.ease_slider)

    def _show_help_dialog(self):
        """Окно с описанием инструмента."""
        text = (
            "<b>Принцип действия Easy In/Out (Easy Ease):</b><br><br>"
            "Инструмент работает как эффект «кругов на воде» или топологическое затухание.<br><br>"
            "<b>1. Принцип действия:</b><br>"
            "• Скрипт находит границу (шов) между двумя выбранными костями.<br>"
            "• От шва строятся слои (лупы) вертексов вглубь зоны влияния второй кости.<br>"
            "• Сила влияния падает с каждым слоем (100% → 50% → 25% → ...). Это создает мягкий переход веса.<br><br>"
            "<b>2. Порядок выбора:</b><br>"
            "• ПОРЯДОК ВАЖЕН!<br>"
            "• 1-я кость (BN1): Источник (Красный).<br>"
            "• 2-я кость (BN2): Цель (Синий).<br>"
            "• Градиент 'растет' от первой кости во вторую.<br><br>"
            "<b>3. Веса:</b><br>"
            "• Забор веса не привязан к 1.0. Скрипт меняет текущее состояние скиннинга.<br>"
            "• Благодаря нормализации (nrm=True), добавление веса одной кости пропорционально забирает его у других.<br><br>"
            "<b>Итог:</b> Позволяет растягивать или сжимать границы скиннинга, не ломая существующую работу."
        )
        QtWidgets.QMessageBox.information(self, "Easy Ease Info", text)

    def _on_press(self):
        joints = cmds.ls(os=True, type='joint')
        if len(joints) >= 2:
            n1, n2 = joints[0].split('|')[-1], joints[1].split('|')[-1]
            self.bn1_lbl.setText(f"🔴 <b>{n1}</b>")
            self.bn2_lbl.setText(f"<b>{n2}</b> 🔵")
            self.engine.start_ease_blend(self.get_mesh(), self.depth_spin.value())

    def _on_move(self, val):
        f_val = val * 0.05
        self.ea_lbl.setText(f"<b>EASE ({f_val:.2f})</b>")
        self.engine.update_ease_live(f_val)
        cmds.refresh(force=True)

    def _on_release(self):
        self.engine.stop_ease_blend()
        self.ease_slider.setValue(0)
        self.ea_lbl.setText("<b>EASE (0.0)</b>")
        self.bn1_lbl.setText("🔴 <b>BN1</b>")
        self.bn2_lbl.setText("<b>BN2</b> 🔵")
        QtWidgets.QApplication.processEvents()
        cmds.refresh(force=True)