#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: rebuildConstraint.py
@date: 2024/10/11 15:11
@desc: 
"""
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance


def get_joint_constraints( joint ):
    constraints_data = []
    constraints = cmds.listConnections(joint, type='constraint', destination=True, source=False) or []

    for constraint in constraints:
        constraint_type = cmds.nodeType(constraint)
        targets = []
        target_count = cmds.getAttr(constraint + ".target", size=True)
        for i in range(target_count):
            target = cmds.listConnections(f"{constraint}.target[{i}].targetParentMatrix", source=True)
            if target:
                targets.append(target[0])
        maintain_offset = cmds.getAttr(constraint + ".maintainOffset") if cmds.attributeQuery('maintainOffset',
                                                                                              node=constraint,
                                                                                              exists=True) else False
        weight_attrs = cmds.listAttr(constraint, st='*W*', multi=True) or []
        weights = {attr: cmds.getAttr(constraint + '.' + attr) for attr in weight_attrs}

        constraints_data.append({
            'constraint'     : constraint,
            'constraint_type': constraint_type,
            'targets'        : targets,
            'maintain_offset': maintain_offset,
            'weights'        : weights
        })

    return constraints_data


def traverse_joints( root_joint ):
    joint_data = []

    def traverse( joint ):
        constraints = get_joint_constraints(joint)
        joint_data.append({
            'joint'      : joint,
            'constraints': constraints
        })
        children = cmds.listRelatives(joint, type='joint', children=True) or []
        for child in children:
            traverse(child)

    traverse(root_joint)
    return joint_data


def recreate_constraints( joint_data ):
    cmds.undoInfo(openChunk=True)
    try:
        for data in joint_data:
            joint = data['joint']
            constraints = data['constraints']

            for constraint_data in constraints:
                constraint_type = constraint_data['constraint_type']
                targets = [target for target in constraint_data['targets'] if target != joint]
                maintain_offset = bool(constraint_data['maintain_offset'])
                weights = constraint_data['weights']

                if targets:
                    new_constraint = None
                    if constraint_type == 'parentConstraint':
                        new_constraint = cmds.parentConstraint(targets, joint, maintainOffset=maintain_offset)
                    elif constraint_type == 'pointConstraint':
                        new_constraint = cmds.pointConstraint(targets, joint, maintainOffset=maintain_offset)
                    elif constraint_type == 'orientConstraint':
                        new_constraint = cmds.orientConstraint(targets, joint, maintainOffset=maintain_offset)
                    elif constraint_type == 'scaleConstraint':
                        new_constraint = cmds.scaleConstraint(targets, joint, maintainOffset=maintain_offset)

                    if new_constraint:
                        for attr, value in weights.items():
                            if cmds.objExists(new_constraint[0] + '.' + attr):
                                try:
                                    cmds.setAttr(new_constraint[0] + '.' + attr, value)
                                except RuntimeError:
                                    continue
    finally:
        cmds.undoInfo(closeChunk=True)


def delete_constraints( joint_data ):
    cmds.undoInfo(openChunk=True)
    try:
        for data in joint_data:
            constraints = data['constraints']

            for constraint_data in constraints:
                constraint = constraint_data['constraint']
                if cmds.objExists(constraint):
                    cmds.delete(constraint)
    finally:
        cmds.undoInfo(closeChunk=True)


def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class ConstraintToolUI(QtWidgets.QWidget):
    def __init__( self, parent=maya_main_window() ):
        super(ConstraintToolUI, self).__init__(parent)
        self.setWindowTitle("Constraint Tool UI")
        self.setGeometry(300, 300, 400, 150)
        self.setWindowFlags(QtCore.Qt.Window)
        self.build_ui()

    def build_ui( self ):
        layout = QtWidgets.QVBoxLayout(self)

        # Input Field and Button to Get Constraints
        self.root_joint_field = QtWidgets.QLineEdit()
        self.get_constraints_btn = QtWidgets.QPushButton("获取骨骼约束信息")
        self.get_constraints_btn.clicked.connect(self.get_constraints)

        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(self.root_joint_field)
        input_layout.addWidget(self.get_constraints_btn)

        layout.addLayout(input_layout)

        # Buttons to Delete and Recreate Constraints
        self.delete_constraints_btn = QtWidgets.QPushButton("删除约束")
        self.delete_constraints_btn.clicked.connect(self.delete_constraints)

        self.recreate_constraints_btn = QtWidgets.QPushButton("重建约束")
        self.recreate_constraints_btn.clicked.connect(self.recreate_constraints)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.delete_constraints_btn)
        buttons_layout.addWidget(self.recreate_constraints_btn)

        layout.addLayout(buttons_layout)

    def get_constraints( self ):
        selected_joints = cmds.ls(selection=True, type='joint')
        if not selected_joints:
            cmds.warning("请选择一个骨骼")
            return

        root_joint = selected_joints[0]
        self.root_joint_field.setText(root_joint)
        self.joint_info = traverse_joints(root_joint)
        cmds.confirmDialog(title="获取成功", message="已获取骨骼及其约束信息")

    def delete_constraints( self ):
        if hasattr(self, 'joint_info'):
            delete_constraints(self.joint_info)
            cmds.confirmDialog(title="删除成功", message="已成功删除所有约束")
        else:
            cmds.warning("请先获取骨骼的约束信息")

    def recreate_constraints( self ):
        if hasattr(self, 'joint_info'):
            recreate_constraints(self.joint_info)
            cmds.confirmDialog(title="重建成功", message="已成功重建所有约束")
        else:
            cmds.warning("请先获取骨骼的约束信息")


# Show UI
if __name__ == "__main__":
    try:
        constraint_tool_ui.close()  # pylint: disable=E0601
        constraint_tool_ui.deleteLater()
    except:
        pass

    constraint_tool_ui = ConstraintToolUI()
    constraint_tool_ui.show()