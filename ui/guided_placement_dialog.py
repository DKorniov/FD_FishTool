from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds

class GuidedPlacementDialog(QtWidgets.QDialog):
    def __init__(self, part_name, steps, image_path, callback):
        super().__init__()
        
        self.setWindowTitle(f"Placement Guide: {part_name}")
        self.steps = steps
        self.current_step = 0
        self.callback = callback
        self.results = []
        

        layout = QtWidgets.QVBoxLayout(self)
        self.instr = QtWidgets.QLabel(self.steps[0])
        layout.addWidget(self.instr)
        
        
        self.img = QtWidgets.QLabel()
        self.img.setPixmap(QtGui.QPixmap(image_path).scaled(700, 700))
        layout.addWidget(self.img)

        self.btn = QtWidgets.QPushButton("Confirm Vertex Selection")
        self.btn.clicked.connect(self.next_step)
        layout.addWidget(self.btn)

    def next_step(self):
        sel = cmds.ls(sl=True, fl=True)
        if not sel or ".vtx" not in sel[0]:
            QtWidgets.QMessageBox.warning(self, "Error", "Select a vertex on the mesh!")
            return
        
        self.results.append(sel[0])
        self.current_step += 1
        
        if self.current_step < len(self.steps):
            self.instr.setText(self.steps[self.current_step])
        else:
            self.callback(self.results)
            self.accept()