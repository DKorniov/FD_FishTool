# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore
import maya.cmds as cmds
from FD_FishTool.core.weight_blender import WeightBlender

class WeightBlenderWidget(QtWidgets.QWidget):
    def __init__(self, rig_manager, mesh_getter, parent=None):
        super(WeightBlenderWidget, self).__init__(parent)
        self.blender = WeightBlender(rig_manager)
        self.get_mesh = mesh_getter
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(10)

        # --- TWIN MACHINE UI ---
        tw_group = QtWidgets.QVBoxLayout()
        hl = QtWidgets.QHBoxLayout()
        self.bn1_label = QtWidgets.QLabel("🔴 <b>BN1</b>")
        self.bn1_label.setStyleSheet("color: #ffaaaa;")
        self.tw_lbl = QtWidgets.QLabel("<b>TWIN (0.0)</b>")
        self.bn2_label = QtWidgets.QLabel("<b>BN2</b> 🔵")
        self.bn2_label.setStyleSheet("color: #aaaaff;")
        
        hl.addWidget(self.bn1_label); hl.addStretch(); hl.addWidget(self.tw_lbl); hl.addStretch(); hl.addWidget(self.bn2_label)
        tw_group.addLayout(hl)

        self.tw_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tw_slider.setRange(-20, 20); self.tw_slider.setValue(0)
        self.tw_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        
        self.tw_slider.sliderPressed.connect(self._on_press)
        self.tw_slider.sliderMoved.connect(self._on_move)
        self.tw_slider.sliderReleased.connect(self._on_release)
        
        tw_group.addWidget(self.tw_slider); layout.addLayout(tw_group)

    def _on_press(self):
        """Информативное отображение имен костей."""
        joints = cmds.ls(os=True, type='joint')
        if len(joints) >= 2:
            n1, n2 = joints[0].split('|')[-1], joints[1].split('|')[-1]
            self.bn1_label.setText(f"🔴 <b>{n1}</b>")
            self.bn2_label.setText(f"<b>{n2}</b> 🔵")
            # Стартуем логику. Если кость не инфлюенс - вернет False.
            if not self.blender.start_live_blend(self.get_mesh()):
                # Сбрасываем метки, если старт не удался
                self.bn1_label.setText("🔴 <b>BN1</b>")
                self.bn2_label.setText("<b>BN2</b> 🔵")
        else:
            cmds.warning("FD_FishTool: Выделите две кости!")

    def _on_move(self, val):
        f_val = val * 0.05
        self.tw_lbl.setText(f"<b>TWIN ({f_val:.2f})</b>")
        self.blender.update_live_blend(f_val)
        cmds.refresh(force=True)

    def _on_release(self):
        self.blender.stop_live_blend()
        self.tw_slider.setValue(0)
        self.tw_lbl.setText("<b>TWIN (0.0)</b>")