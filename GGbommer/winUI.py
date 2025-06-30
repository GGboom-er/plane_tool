#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: winUI.py
@date: 2024/12/18 11:57
@desc: 
"""
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QPushButton
)
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Maya & Blender Interface")
        self.setGeometry(200, 200, 800, 600)

        # 创建 Tab Widget 作为中心窗口
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 添加 Maya 标签页
        self.maya_tab = self.create_maya_tab()
        self.tabs.addTab(self.maya_tab, "Maya")

        # 添加 Blender 标签页
        self.blender_tab = self.create_blender_tab()
        self.tabs.addTab(self.blender_tab, "Blender")

    def create_maya_tab(self):
        """创建 Maya 标签页"""
        tab = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Maya 界面内容")
        button = QPushButton("示例按钮")
        button.clicked.connect(lambda: print("Maya 按钮被点击"))

        layout.addWidget(label)
        layout.addWidget(button)

        tab.setLayout(layout)
        return tab

    def create_blender_tab(self):
        """创建 Blender 标签页"""
        tab = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Blender 界面内容")
        button = QPushButton("示例按钮")
        button.clicked.connect(lambda: print("Blender 按钮被点击"))

        layout.addWidget(label)
        layout.addWidget(button)

        tab.setLayout(layout)
        return tab


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    'test'