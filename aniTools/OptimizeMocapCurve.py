#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: test.py
@date: 2025/8/4 11:25
@desc: 
"""
import maya.cmds as cmds
import maya.mel as mel
import math

class AnimCurveOptimizerPro:
    def __init__( self ):
        self.window_name = "curveOptimizerPro"
        self.original_state = {}
        self.analysis_data = {}

    def create_ui( self ):
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        cmds.window(self.window_name, title="Curve Optimizer Pro", width=350, height=220)
        main_layout = cmds.columnLayout(adjustableColumn=True)

        # 力度控制
        cmds.frameLayout(label="Optimization Control", marginWidth=5)
        cmds.gridLayout(numberOfColumns=2, cellWidth=150)

        self.strength_slider = cmds.floatSliderGrp(
            label="Strength",
            field=True,
            minValue=0.0,
            maxValue=1.0,
            value=0.5,
            step=0.01,
            columnWidth3=[60, 40, 100],
            annotation="Control optimization intensity"
        )

        self.tolerance_slider = cmds.floatSliderGrp(
            label="Tolerance",
            field=True,
            minValue=0.001,
            maxValue=0.1,
            value=0.01,
            step=0.001,
            columnWidth3=[60, 40, 100],
            annotation="Maximum allowed deviation"
        )

        cmds.setParent('..')
        cmds.setParent('..')

        # 智能选项
        cmds.frameLayout(label="Smart Options", collapsable=True)
        cmds.gridLayout(numberOfColumns=2, cellWidth=150)

        self.keep_extremes = cmds.checkBoxGrp(
            numberOfCheckBoxes=1,
            label="Keep Extremes",
            value1=True
        )

        self.auto_tangents = cmds.checkBoxGrp(
            numberOfCheckBoxes=1,
            label="Auto Tangents",
            value1=True
        )

        self.curve_analysis = cmds.checkBoxGrp(
            numberOfCheckBoxes=1,
            label="Curvature Analysis",
            value1=True
        )

        self.time_analysis = cmds.checkBoxGrp(
            numberOfCheckBoxes=1,
            label="Time Analysis",
            value1=True
        )

        cmds.setParent('..')
        cmds.setParent('..')

        # 操作按钮
        cmds.frameLayout(label="Actions", marginWidth=5)
        cmds.rowLayout(numberOfColumns=4, columnWidth4=[80, 80, 80, 80])
        cmds.button(label="Optimize", command=self.optimize, backgroundColor=[0.3, 0.6, 0.3])
        cmds.button(label="Analyze", command=self.analyze)
        cmds.button(label="Preview", command=self.preview, backgroundColor=[0.4, 0.4, 0.8])
        cmds.button(label="Restore", command=self.restore)
        cmds.setParent('..')

        cmds.showWindow()

    def store_current_state( self ):
        """存储当前动画状态"""
        self.original_state = {}
        selection = cmds.ls(selection=True)
        for obj in selection:
            self.original_state[obj] = {}
            curves = cmds.listConnections(obj, type="animCurve") or []
            for curve in curves:
                self.original_state[obj][curve] = {
                    'times'   : cmds.keyframe(curve, query=True, timeChange=True),
                    'values'  : cmds.keyframe(curve, query=True, valueChange=True),
                    'tangents': cmds.keyTangent(curve, query=True, inAngle=True, outAngle=True)
                }

    def restore( self, *_ ):
        """还原动画状态"""
        for obj in self.original_state:
            if not cmds.objExists(obj):
                continue
            for curve in self.original_state[obj]:
                if cmds.objExists(curve):
                    cmds.cutKey(curve)
                    data = self.original_state[obj][curve]
                    for t, v in zip(data['times'], data['values']):
                        cmds.setKeyframe(curve, time=t, value=v)
                    tangents = data['tangents']
                    for i in range(0, len(tangents), 2):
                        cmds.keyTangent(
                            curve,
                            time=(data['times'][i // 2],),
                            inAngle=tangents[i],
                            outAngle=tangents[i + 1]
                        )
        cmds.inViewMessage(ams="Restore completed", pos='midCenter', fade=True)

    def rdp_simplification( self, points, epsilon, keep_indices ):
        """改进的Ramer-Douglas-Peucker曲线简化算法"""
        if len(points) < 3:
            return points

        # 找到离首尾连线最远的点
        dmax = 0
        index = 0
        start, end = points[0], points[-1]

        for i in range(1, len(points) - 1):
            if i in keep_indices:
                continue

            d = self.perpendicular_distance(points[i], start, end)
            if d > dmax:
                index = i
                dmax = d

        # 递归处理
        result = []
        if dmax > epsilon:
            rec_results1 = self.rdp_simplification(points[:index + 1], epsilon, keep_indices)
            rec_results2 = self.rdp_simplification(points[index:], epsilon, keep_indices)
            result = rec_results1[:-1] + rec_results2
        else:
            result = [start, end]

        return result

    def perpendicular_distance( self, point, line_start, line_end ):
        """计算点到直线的垂直距离"""
        if line_start[0] == line_end[0] and line_start[1] == line_end[1]:
            return math.sqrt((point[0] - line_start[0]) ** 2 + (point[1] - line_start[1]) ** 2)

        # 计算线段长度
        length_squared = (line_end[0] - line_start[0]) ** 2 + (line_end[1] - line_start[1]) ** 2

        # 计算投影比例
        t = max(0, min(1, ((point[0] - line_start[0]) * (line_end[0] - line_start[0]) +
                           (point[1] - line_start[1]) * (line_end[1] - line_start[1])) / length_squared))

        # 计算投影点
        projection = (
            line_start[0] + t * (line_end[0] - line_start[0]),
            line_start[1] + t * (line_end[1] - line_start[1])
        )

        # 计算距离
        return math.sqrt((point[0] - projection[0]) ** 2 + (point[1] - projection[1]) ** 2)

    def calculate_curvature( self, points, index ):
        """计算曲线在特定点的曲率"""
        if index <= 0 or index >= len(points) - 1:
            return 0

        p0 = points[index - 1]
        p1 = points[index]
        p2 = points[index + 1]

        # 计算向量
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])

        # 计算角度变化
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

        if mag1 == 0 or mag2 == 0:
            return 0

        cos_angle = dot_product / (mag1 * mag2)
        angle = math.acos(max(-1, min(1, cos_angle)))

        # 曲率是角度变化除以平均距离
        avg_distance = (mag1 + mag2) / 2
        if avg_distance == 0:
            return 0

        return angle / avg_distance

    def optimize_curve( self, curve, strength, tolerance ):
        """智能优化曲线算法"""
        times = cmds.keyframe(curve, query=True, timeChange=True)
        values = cmds.keyframe(curve, query=True, valueChange=True)
        if len(times) < 3:
            return 0, 0.0

        # 创建点列表 (时间, 值)
        points = list(zip(times, values))
        keep_indices = set([0, len(times) - 1])

        # 保留极值点
        if cmds.checkBoxGrp(self.keep_extremes, q=True, value1=True):
            max_val = max(values)
            min_val = min(values)
            for i, v in enumerate(values):
                if math.isclose(v, max_val, abs_tol=0.001) or math.isclose(v, min_val, abs_tol=0.001):
                    keep_indices.add(i)

        # 动态计算阈值
        time_range = max(times) - min(times)
        value_range = max(values) - min(values)

        # 组合阈值 - 基于用户设置和曲线特征
        epsilon = tolerance * (1.0 + strength * 2.0)

        # 曲率分析 - 保留高曲率点
        if cmds.checkBoxGrp(self.curve_analysis, q=True, value1=True):
            curvature_threshold = 0.05 + strength * 0.1
            for i in range(1, len(points) - 1):
                curvature = self.calculate_curvature(points, i)
                if curvature > curvature_threshold:
                    keep_indices.add(i)

        # 时间分析 - 保留时间间隔过大的点
        if cmds.checkBoxGrp(self.time_analysis, q=True, value1=True):
            avg_interval = time_range / (len(times) - 1)
            for i in range(1, len(times)):
                interval = times[i] - times[i - 1]
                if interval > avg_interval * 3.0:  # 超过平均间隔3倍
                    keep_indices.add(i - 1)
                    keep_indices.add(i)

        # 使用RDP算法简化曲线
        simplified_points = self.rdp_simplification(points, epsilon, keep_indices)

        # 确定要删除的关键帧
        simplified_times = {p[0] for p in simplified_points}
        to_delete = [t for t in times if t not in simplified_times]

        # 执行删除操作
        if to_delete:
            # 使用正确的时间参数格式
            time_ranges = [(t, t) for t in to_delete]
            cmds.cutKey(curve, time=time_ranges)

            if cmds.checkBoxGrp(self.auto_tangents, q=True, value1=True):
                cmds.keyTangent(curve, itt="auto", ott="auto")

        # 计算优化率
        reduction_rate = len(to_delete) / len(times) if times else 0.0

        return len(to_delete), reduction_rate

    def analyze( self, *_ ):
        """智能分析场景曲线"""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Select objects to analyze")
            return

        self.analysis_data = {}
        total_keys = 0
        potential_saving = 0
        high_curvature_points = 0

        for obj in selection:
            curves = cmds.listConnections(obj, type="animCurve") or []
            for curve in curves:
                times = cmds.keyframe(curve, query=True, timeChange=True) or []
                values = cmds.keyframe(curve, query=True, valueChange=True) or []

                if not times:
                    continue

                total_keys += len(times)
                self.analysis_data[curve] = {
                    'key_count'  : len(times),
                    'time_range' : max(times) - min(times) if times else 0,
                    'value_range': max(values) - min(values) if values else 0
                }

                # 估算可优化关键帧数量
                potential_saving += max(0, len(times) - math.ceil(len(times) ** 0.7))

                # 计算高曲率点
                points = list(zip(times, values))
                for i in range(1, len(points) - 1):
                    curvature = self.calculate_curvature(points, i)
                    if curvature > 0.1:
                        high_curvature_points += 1

        # 显示分析报告
        report = (f"<b>Analysis Report:</b>"
                  f"<br>Objects: {len(selection)}"
                  f"<br>Curves: {len(self.analysis_data)}"
                  f"<br>Total Keys: {total_keys}"
                  f"<br>High Curvature Points: {high_curvature_points}"
                  f"<br>Potential Reduction: ~{potential_saving} keys ({potential_saving / total_keys * 100:.1f}%)")

        cmds.inViewMessage(am=report, pos='midCenter', fade=True)

    def preview( self, *_ ):
        """优化预览功能"""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Select objects to preview")
            return

        strength = cmds.floatSliderGrp(self.strength_slider, query=True, value=True)
        tolerance = cmds.floatSliderGrp(self.tolerance_slider, query=True, value=True)

        # 存储原始状态
        self.store_current_state()

        # 创建预览组
        preview_group = "optimizer_preview_group"
        if cmds.objExists(preview_group):
            cmds.delete(preview_group)
        preview_group = cmds.group(empty=True, name=preview_group)

        # 为每个对象创建预览曲线
        for obj in selection:
            if not cmds.objExists(obj):
                continue

            curves = cmds.listConnections(obj, type="animCurve") or []
            for curve in curves:
                # 复制原始曲线
                preview_curve = cmds.duplicate(curve, name=f"{curve}_preview")[0]
                cmds.parent(preview_curve, preview_group)

                # 应用优化
                self.optimize_curve(preview_curve, strength, tolerance)

                # 设置预览颜色
                cmds.setAttr(f"{preview_curve}.useCurveColor", 1)
                cmds.setAttr(f"{preview_curve}.curveColor", 0, 1, 0)  # 绿色

        cmds.inViewMessage(ams="Preview created. Original curves in red, optimized in green.", pos='midCenter',
                           fade=True)

    def optimize( self, *_ ):
        """执行优化操作"""
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Select objects to optimize")
            return

        self.store_current_state()
        strength = cmds.floatSliderGrp(self.strength_slider, query=True, value=True)
        tolerance = cmds.floatSliderGrp(self.tolerance_slider, query=True, value=True)
        total_removed = 0
        total_original = 0
        max_reduction = 0.0

        gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
        cmds.progressBar(gMainProgressBar,
                         edit=True,
                         beginProgress=True,
                         status="Optimizing...",
                         maxValue=len(selection))

        try:
            cmds.undoInfo(openChunk=True)
            for idx, obj in enumerate(selection):
                cmds.progressBar(gMainProgressBar, edit=True, step=1)
                curves = cmds.listConnections(obj, type="animCurve") or []
                for curve in curves:
                    try:
                        times = cmds.keyframe(curve, query=True, timeChange=True) or []
                        total_original += len(times)
                        removed, reduction = self.optimize_curve(curve, strength, tolerance)
                        total_removed += removed
                        max_reduction = max(max_reduction, reduction)
                    except Exception as e:
                        print(f"Error processing {curve}: {str(e)}")

            reduction_percent = total_removed / total_original * 100 if total_original > 0 else 0
            report = (f"Removed {total_removed}/{total_original} keys ({reduction_percent:.1f}% reduction)\n"
                      f"Max curve reduction: {max_reduction * 100:.1f}%\n"
                      f"Strength: {strength * 100:.0f}%, Tolerance: {tolerance:.3f}")
            cmds.inViewMessage(ams=report, pos='midCenter', fade=True)

        except Exception as e:
            cmds.warning(f"Optimization failed: {str(e)}")
            self.restore()
        finally:
            cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
            cmds.undoInfo(closeChunk=True)

def show_tool():
    tool = AnimCurveOptimizerPro()
    tool.create_ui()

if __name__ == "__main__":
    show_tool()