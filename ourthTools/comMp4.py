#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: comMp4.py
@date: 2025/2/27 20:28
@desc: 
"""

import subprocess
import os

def merge_mp4_weba_srt(mp4_path, weba_path, srt_path, output_path):
    """
    使用 FFmpeg 合并 MP4 视频、WEBA 音频和 SRT 字幕，输出 MP4 文件。

    :param mp4_path: MP4 视频文件路径
    :param weba_path: WEBA 音频文件路径
    :param srt_path: SRT 字幕文件路径
    :param output_path: 输出 MP4 文件路径
    """
    # 确保 FFmpeg 可用
    if subprocess.run([r'P:/pipeline/custom_plugin/ffmpeg/ffmpeg.exe', "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        print("错误: 未安装 FFmpeg，请先安装 FFmpeg")
        return

    # 确保输入文件存在
    if not os.path.exists(mp4_path):
        print(f"错误: 找不到 MP4 文件 {mp4_path}")
        return
    if not os.path.exists(weba_path):
        print(f"错误: 找不到 WEBA 音频文件 {weba_path}")
        return
    if not os.path.exists(srt_path):
        print(f"错误: 找不到 SRT 字幕文件 {srt_path}")
        return

    # FFmpeg 命令
    command = [
        r'P:/pipeline/custom_plugin/ffmpeg/ffmpeg.exe',
        "-i", mp4_path,  # 输入视频
        "-i", weba_path,  # 输入音频
        "-i", srt_path,   # 输入字幕
        "-c:v", "copy",   # 视频不重新编码
        "-c:a", "aac",    # 音频转换为 AAC
        "-c:s", "mov_text",  # 字幕转换为 MP4 兼容格式
        "-map", "0:v:0",  # 映射视频
        "-map", "1:a:0",  # 映射音频
        "-map", "2:s:0",  # 映射字幕
        "-metadata:s:s:0", "language=eng",  # 设置字幕语言
        output_path       # 输出文件
    ]

    # 执行 FFmpeg 命令
    try:
        subprocess.run(command, check=True)
        print(f"合成成功: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"合成失败: {e}")

# 示例调用
merge_mp4_weba_srt(r"C:\Users\yuweiming\Downloads\videoplayback.mp4", r"C:\Users\yuweiming\Downloads\videoplayback (1).weba", r"C:\Users\yuweiming\Downloads\FAQ part4_Simplified.srt", r"Y:\GGbommer\Rig\Learn_Rig\Vido\output.mp4")
