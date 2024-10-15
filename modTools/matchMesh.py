#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: matchMesh.py
@date: 2024/9/11 14:47
@desc: 
"""
import maya.cmds as cmd
import maya.api.OpenMaya as om

class globalVar:
	def __init__(self):
		self.points = None

gv=globalVar()

def copy(_):
	# get the mesh vertex position
	sel = cmds.ls(sl=True)
	# get the dag path
	selection_list = om.MSelectionList ()
	selection_list.add(sel[0])
	dag_path = selection_list.getDagPath (0)
	# creating Mfn Mesh
	mfn_mesh = om.MFnMesh(dag_path)
	gv.points = mfn_mesh.getPoints()

def paste(_):
	# set the mesh vertex position
	sel = cmds.ls(sl=True)
	# get the dag path
	selection_list = om.MSelectionList ()
	selection_list.add(sel[0])
	dag_path = selection_list.getDagPath (0)
	# creating Mfn Mesh
	mfn_mesh = om.MFnMesh(dag_path)
	mfn_mesh.setPoints(gv.points)

def copyPasteVertUI():
	# Check if the window is already open
	if cmds.window("CopyPasteVert", q=1, exists=1) == True:
		cmds.deleteUI("CopyPasteVert")

	# Create a new window
	cmd.window("CopyPasteVert", title="Copy Paste Vert", width=300, height=200)
	layout = cmd.columnLayout(parent="CopyPasteVert")
	cmds.text(label="              ",  width=300, height=5, align="left")
	cmds.text(label="Copy and Paste Vertex in World space",  width=300, height=50, backgroundColor=[0.274, 0.619, 0.920], align="center")
	cmds.text(label="              ",  width=300, height=5, align="left")
	button1 = cmd.button(parent=layout, label='Copy',width=300, height=50, command=copy)
	cmds.text(label="              ",  width=300, height=5, align="left")
	button2 = cmd.button(parent=layout, label='Paste', width=300, height=50, command=paste)


	cmd.showWindow("CopyPasteVert")

copyPasteVertUI()