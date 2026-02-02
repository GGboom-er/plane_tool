#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: cascadeur.py
@date: 2025/12/25 19:35
@desc:
"""

import csc
def set_global_time_range( start_frame, end_frame, sync_visible=True ):
    """
    [Write] 设置场景的全局物理时间范围 (Global Limits)。
    这是场景的硬边界，关键帧不能超出此范围。

    Args:
        start_frame (int): 全局起始帧
        end_frame (int): 全局结束帧
        sync_visible (bool): 是否将可视工作区 (UI范围) 重置为与全局范围一致 (默认 True)
    """
    # 1. 安全校验
    if start_frame >= end_frame:
        print(f"[Error] Invalid Global Range: Start ({start_frame}) >= End ({end_frame})")
        return

    app = csc.app.get_application()
    scene = app.get_scene_manager().current_scene()

    if not scene:
        print("[Error] No active scene.")
        return

    try:
        bounds = scene.animation_boundary()

        # 2. 核心操作：设置物理硬边界
        # 注意：操作顺序很重要。为了防止“可视范围”卡在“物理范围”之外报错，
        # 如果 sync_visible 为 True，我们直接覆盖两者。

        if sync_visible:
            # A. 先扩大/设置物理边界
            bounds.first_frame = start_frame
            bounds.last_frame = end_frame

            # B. 再对齐可视边界
            bounds.first_visible_frame = start_frame
            bounds.last_visible_frame = end_frame

            print(f"[Success] Global & Work Range set to: {start_frame} - {end_frame}")

        else:
            # 如果不强制同步，我们需要确保现有的可视范围不越界
            # 这里的逻辑是：物理范围必须 包含 可视范围

            # 先设置物理范围
            bounds.first_frame = start_frame
            bounds.last_frame = end_frame

            # 检查并修正可视范围 (Clamp)
            current_vis_start = bounds.first_visible_frame
            current_vis_end = bounds.last_visible_frame

            if current_vis_start < start_frame:
                bounds.first_visible_frame = start_frame

            if current_vis_end > end_frame:
                bounds.last_visible_frame = end_frame

            print(f"[Success] Global Range updated to: {start_frame} - {end_frame}")

    except Exception as e:
        print(f"[Error] Failed to set global limits: {e}")

# --- 测试调用 ---
if __name__ == '__main__':
    # 场景：将物理极限彻底改为 0-200，并让 UI 显示全范围
    set_global_time_range(0, 125, sync_visible=True)


def run_native_cleanup( scene ):
    print(">>> Running Native Cascadeur Cleanup...")
    domain = scene.domain_scene()

    def mod( model, update, scene_updater ):
        le = model.layers_editor()

        # 1. 调用内置的“清理空层”命令
        # 这通常比我们要自己写判定逻辑更准确
        try:
            le.delete_empty_layers()
            print("Executed: delete_empty_layers()")
        except Exception as e:
            print(f"Native empty layer cleanup failed: {e}")

        # 2. 调用内置的“清理空文件夹”命令
        try:
            le.delete_empty_folders()
            print("Executed: delete_empty_folders()")
        except Exception as e:
            print(f"Native empty folder cleanup failed: {e}")

    domain.modify_update('Native Cleanup', mod)


app = csc.app.get_application()
scene = app.get_scene_manager().current_scene()
run_native_cleanup(scene)
