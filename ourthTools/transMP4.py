#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: transMP4.py
@date: 2025/8/6 19:12
@desc: 
"""
# -*- coding: utf-8 -*-
"""
Batch MOV → MP4 Converter
Author : Pipeline Dev
Python  : 3.8+
依赖    : 原生库 (subprocess / pathlib / logging / concurrent.futures)
"""

import subprocess
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

# ---------------------------------------------------------------------------
# 基本配置
# ---------------------------------------------------------------------------
FFMPEG_EXE = Path(r"P:/pipeline/custom_plugin/ffmpeg/ffmpeg.exe")  # FFmpeg 可执行文件
THREADS     = 4            # 并行线程数；0 或 1 = 顺序处理
OVERWRITE   = True         # 重新转码时是否覆盖已存在文件
LOG_LEVEL   = logging.INFO # DEBUG / INFO / WARNING / ERROR
# 指定待转换的 mov 文件列表（可用 Path.glob 批量收集）
MOV_FILES: List[Path] = [
    Path(r"U:\ywm\MHC\crowds\proxy.mov"),
    Path(r"U:\ywm\MHC\crowds\rbf.mov"),
    Path(r"U:\ywm\MHC\crowds\rbf_v002.mov"),
    Path(r"U:\ywm\MHC\crowds\sk.mov"),
]

# ---------------------------------------------------------------------------
# 内部实现
# ---------------------------------------------------------------------------
logging.basicConfig(format="%(levelname)s | %(message)s", level=LOG_LEVEL)

def build_ffmpeg_cmd(src: Path, dst: Path, overwrite: bool) -> List[str]:
    """
    构建 ffmpeg 命令行
    - 视频编码    : H.264 (libx264)
    - 音频编码    : AAC
    - faststart  : 头信息前置，便于 HTTP 流式播放
    """
    cmd = [
        str(FFMPEG_EXE),
        "-y" if overwrite else "-n",
        "-i", str(src),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "faststart",
        str(dst),
    ]
    return cmd

def convert_one(src: Path, overwrite: bool = True) -> Optional[Path]:
    """
    转换单个文件；成功返回 dst 路径，失败返回 None
    """
    if not src.exists():
        logging.error(f"源文件不存在: {src}")
        return
    dst = src.with_suffix(".mp4")
    cmd = build_ffmpeg_cmd(src, dst, overwrite)
    try:
        logging.debug(" ".join(cmd))
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"? 转换完成: {dst.name}")
        return dst
    except subprocess.CalledProcessError as e:
        logging.error(f"? 转换失败: {src.name}\n{e.stderr.decode(errors='ignore')}")
        return

def batch_convert(mov_files: List[Path], threads: int = 0, overwrite: bool = True):
    """
    批量转换
    """
    if threads and threads > 1:  # 并行
        with ThreadPoolExecutor(max_workers=threads) as exe:
            fut_map = {exe.submit(convert_one, f, overwrite): f for f in mov_files}
            for fut in as_completed(fut_map):
                fut.result()
    else:                         # 顺序
        for f in mov_files:
            convert_one(f, overwrite)

if __name__ == "__main__":
    if not FFMPEG_EXE.exists():
        raise FileNotFoundError(f"FFmpeg 未找到: {FFMPEG_EXE}")
    batch_convert(MOV_FILES, threads=THREADS, overwrite=OVERWRITE)
