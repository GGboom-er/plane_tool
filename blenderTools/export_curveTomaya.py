#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: export_curveTomaya.py
@date: 2025/2/17 16:06
@desc: 
"""
import bpy
import mathutils
import re
import math

bl_info = {
    "name"       : "Autodesk Maya curves",
    "author"     : "Mario Baldi (updated for Blender 4.3 by Assistant)",
    "blender"    : (4, 3, 0),
    "location"   : "File > Import-Export",
    "description": "Export Blender curves to Autodesk Maya (.ma)",
    "warning"    : "",
    "wiki_url"   : "",
    "tracker_url": "",
    "support"    : 'OFFICIAL',
    "category"   : "Import-Export"
}


def build_maya_matrix():
    maya_mtrx = mathutils.Matrix()
    maya_mtrx[0].xyz = 1.0, 0.0, 0.0
    maya_mtrx[1].xyz = 0.0, 0.0, 1.0
    maya_mtrx[2].xyz = 0.0, -1.0, 0.0
    maya_mtrx[3].xyz = 0.0, 0.0, 0.0
    return maya_mtrx


def build_knots_array( nverts, degree ):
    knotLen = nverts + degree - 1
    lastKnotValue = max(0, nverts - degree)  # Ensure no negative value
    kn = []

    for i in range(knotLen):
        v = i - degree + 1
        if v < 0:
            v = 0
        elif v > lastKnotValue or i >= knotLen - degree:
            v = lastKnotValue
        kn.append(v)
    return kn


def sanitize_name( name ):
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)  # Replace non-alphanumeric characters with _
    if name[0].isdigit():  # If the name starts with a digit, prefix it with an underscore
        name = f"_{name}"
    return name


def write_curve_shape( spline, mtrx=None ):
    if spline.type == "POLY":
        points = spline.points
        degree = 1
    elif spline.type == "BEZIER":
        points = spline.bezier_points
        degree = 3
    elif spline.type == "NURBS":
        points = spline.points
        degree = spline.order_u

    nverts = spline.point_count_u
    nspans = nverts - degree
    knots = build_knots_array(nverts, degree)
    nknots = len(knots)
    knots_str = ' '.join(map(str, knots))
    openclosed = 2 if spline.use_cyclic_u else 0

    curve_attrs = []
    curve_attrs.append('    setAttr -k off ".v"; \n')
    curve_attrs.append('    setAttr ".cc" -type "nurbsCurve" \n')
    curve_attrs.append('        %s %s %s no 3 \n' % (degree, nspans, openclosed))
    curve_attrs.append('        %s %s   \n' % (nknots, knots_str))
    curve_attrs.append('        %s \n' % nverts)

    maya_mtrx = build_maya_matrix()

    for pt in points:
        local_pt = pt.co if hasattr(pt, 'co') else pt  # Handle different point types
        if local_pt.length == 0:  # Skip points with no length (potentially invalid data)
            continue
        if mtrx is not None:
            transformed_pt = (mtrx @ local_pt)  # Matrix-vector multiplication
            transformed_pt = maya_mtrx @ transformed_pt
        else:
            transformed_pt = maya_mtrx @ local_pt

        # Ensure all coordinate values are floats
        x, y, z = map(float, transformed_pt[:3])
        curve_attrs.append(f'        {x} {y} {z} \n')

    curve_attrs.append('        ; \n')

    return curve_attrs


def export_curves_to_maya( operator, context, filepath="", use_selection=True ):
    selection = bpy.context.selected_objects if use_selection else bpy.data.objects

    if len(selection) > 0:
        maya_file = [
            '//Maya ASCII 2024 scene \n',
            'requires maya "2024"; \n',
            'currentUnit -l centimeter -a degree -t film; \n',
            'fileInfo "application" "maya";\n',
        ]

        for sel in selection:
            if sel.type == "CURVE":
                bake_mw = sel.matrix_world
                # curves_grp = sanitize_name(sel.name)
                maya_file.append(f'createNode transform -n "{curves_grp}"; \n')

                for id, spl in enumerate(sel.data.splines):
                    curve_t_name = sanitize_name(f'{sel.name}')
                    curve_shape_name = sanitize_name(f'{sel.name}Shape{id + 1}')
                    # maya_file.append(f'createNode transform -n "{curve_t_name}" -p "{curves_grp}"; \n')
                    maya_file.append(f'createNode nurbsCurve -n "{curve_shape_name}" -p "{curve_t_name}"; \n')
                    maya_file.extend(write_curve_shape(spl, bake_mw))

        with open(filepath, "w") as f:
            f.writelines(maya_file)
    return {'FINISHED'}


from bpy.props import BoolProperty
from bpy_extras.io_utils import ExportHelper


class ExportCurvesToMaya(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.autodesk_maya_curves"
    bl_label = 'Export Curves to Maya'
    filename_ext = ".ma"

    use_selection: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=False,
    )

    def execute( self, context ):
        return export_curves_to_maya(self, context, filepath=self.filepath, use_selection=self.use_selection)


def menu_func_export( self, context ):
    self.layout.operator(ExportCurvesToMaya.bl_idname, text="Export Curves to Maya (.ma)")


def register():
    bpy.utils.register_class(ExportCurvesToMaya)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportCurvesToMaya)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
