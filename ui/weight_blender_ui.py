# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
from FD_FishTool.core.weight_blender import WeightBlender

class WeightBlenderWidget(QtWidgets.QWidget):
    def __init__(self, rig_manager, mesh_getter, parent=None):
        super(WeightBlenderWidget, self).__init__(parent)
        self.blender = WeightBlender(rig_manager)
        self.get_mesh = mesh_getter
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(5)

        # EA Color Bar
        self.ea_grad = QtWidgets.QLabel(); self.ea_grad.setFixedHeight(8)
        self.ea_grad.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5555, stop:0.5 #ffffff, stop:1 #55ff55); border-radius: 2px;")
        layout.addWidget(self.ea_grad)

        # Ease In/Out Slider
        hl1 = QtWidgets.QHBoxLayout(); hl1.addWidget(QtWidgets.QLabel("📉 In")); self.ea_lbl = QtWidgets.QLabel("<b>EA (0.0)</b>")
        hl1.addStretch(); hl1.addWidget(self.ea_lbl); hl1.addStretch(); hl1.addWidget(QtWidgets.QLabel("Out 📈"))
        layout.addLayout(hl1)
        self.ea_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ea_slider.setRange(-20, 20); self.ea_slider.setValue(0)
        self.ea_slider.valueChanged.connect(lambda v: self.ea_lbl.setText(f"<b>EA ({v*0.05:.2f})</b>"))
        layout.addWidget(self.ea_slider)

        # Twin Machine Slider
        hl2 = QtWidgets.QHBoxLayout(); hl2.addWidget(QtWidgets.QLabel("🔴 BN1")); self.tw_lbl = QtWidgets.QLabel("<b>TWIN (0.0)</b>")
        hl2.addStretch(); hl2.addWidget(self.tw_lbl); hl2.addStretch(); hl2.addWidget(QtWidgets.QLabel("BN2 🔵"))
        layout.addLayout(hl2)
        self.tw_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tw_slider.setRange(-20, 20); self.tw_slider.setValue(0)
        self.tw_slider.sliderPressed.connect(lambda: self.blender.start_live_blend(self.get_mesh()))
        self.tw_slider.sliderMoved.connect(lambda v: [self.tw_lbl.setText(f"<b>TWIN ({v*0.05:.2f})</b>"), self.blender.update_live_blend(v*0.05)])
        self.tw_slider.sliderReleased.connect(lambda: [self.blender.stop_live_blend(), self.tw_slider.setValue(0), self.tw_lbl.setText("<b>TWIN (0.0)</b>")])
        layout.addWidget(self.tw_slider)