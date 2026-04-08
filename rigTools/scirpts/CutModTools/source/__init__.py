# -*- coding: utf-8 -*-
"""
CutMod 工具 — 基于骨骼权重的模型切分工具（Maya 2025）

功能：根据 skinCluster 权重自动切分模型为子网格，
     并用矩阵约束或 parentConstraint 绑定到对应骨骼，
     替代 skinCluster 模式以提高绑定运算效率。

使用方式：
    import CutModTools
    CutModTools.show()         # 启动 UI
    CutModTools.run()          # 脚本批量执行（选中多个网格）

完整调用命令：
    import sys
    sys.path.append(r"Y:\GGbommer\scripts\plane_tool\rigTools\scirpts")
    import CutModTools
    CutModTools.show()
"""

__version__ = "1.2.0"
__author__ = "CutModTools"


def show():
    """启动 CutMod 工具 UI 窗口"""
    from CutModTools.source.ui.main_window import CutModWindow
    return CutModWindow.display()


def run(meshes=None, mode="matrix", threshold=0.001,
        exclude_hierarchy=None, smooth_iterations=3,
        smooth_tolerance=0.15, enable_cap=True):
    """
    无 UI 批量执行切分（脚本调用入口）

    支持多网格：选中 N 个网格 → 全部切分 → 同一骨骼的子网格合并到同一组。

    Args:
        meshes: 要切分的网格列表，None 则使用当前选择
        mode: 绑定模式 "matrix" 或 "constraint"
        threshold: 权重忽略阈值
        exclude_hierarchy: 排除层级根骨骼名（如 "Head_M"）
        smooth_iterations: 边界平滑迭代次数
        smooth_tolerance: 平滑容差
        enable_cap: 是否封口

    Returns:
        dict: 执行结果
    """
    import maya.cmds as cmds
    from CutModTools.source.core.weight_analyzer import WeightAnalyzer
    from CutModTools.source.core.mesh_cutter import MeshCutter
    from CutModTools.source.core.binding import Binder
    from CutModTools.source.core.snapshot import SnapshotManager

    if meshes is None:
        meshes = cmds.ls(sl=True, type="transform") or []

    if not meshes:
        cmds.warning("CutMod: 未选择任何网格对象")
        return None

    # 在撤销块中执行全部操作
    cmds.undoInfo(openChunk=True, chunkName="CutMod_BatchExecute")

    try:
        # 1. 拍快照
        snapshot_mgr = SnapshotManager()
        snapshot_mgr.capture_scene_state()

        # 2. 逐网格分析 + 切分，收集所有 cut_results
        all_cut_results = []
        skincluster_joint = None
        if exclude_hierarchy:
            from CutModTools.source.utils.maya_helpers import short_joint_name
            skincluster_joint = short_joint_name(exclude_hierarchy)

        for mesh in meshes:
            analyzer = WeightAnalyzer(
                mesh, threshold=threshold,
                exclude_hierarchy=exclude_hierarchy,
                smooth_iterations=smooth_iterations,
                smooth_tolerance=smooth_tolerance)
            face_map = analyzer.analyze()

            cutter = MeshCutter(
                mesh, face_map,
                keep_original=True,
                enable_cap=enable_cap,
                skincluster_joint=skincluster_joint)
            cut_results = cutter.execute()
            all_cut_results.extend(cut_results)

        # 3. 统一绑定（所有网格的 cut_results 一起按骨骼分组）
        binder = Binder(
            all_cut_results, mode=mode,
            source_meshes=meshes)
        bind_results = binder.execute()

        # 4. 恢复快照
        change_log = snapshot_mgr.restore_protected_attrs()

        result = {
            "status": "success",
            "meshes_processed": len(meshes),
            "total_cuts": len(all_cut_results),
            "bone_groups": len(bind_results),
            "change_log": change_log
        }
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        cmds.warning("CutMod: 执行失败 — {}".format(e))
        return {"status": "error", "error": str(e)}

    finally:
        cmds.undoInfo(closeChunk=True)
