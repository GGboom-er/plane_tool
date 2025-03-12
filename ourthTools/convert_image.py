#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: convert_image.py
@date: 2024/5/24 11:10
@desc:
"""
import os
import subprocess

def convert_image( input_image, output_image, scale='512:512' ):
    ffmpeg = r'P:/pipeline/custom_plugin/ffmpeg/ffmpeg.exe'
    run_cmd = '{ffmpeg} -y -i {input} -vf "scale={scale}" -vcodec tiff -compression_algo lzw {output}'.format(
        ffmpeg=ffmpeg, input=input_image, output=output_image, scale=scale)

    try:
        subprocess.Popen(run_cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(u"转换失败:", e)


outputPath = r'C:\Users\yuweiming\Desktop\qunji\sourceimages\prp'
inPath = r'X:\Project\tbx\sourceimages\prp\fansprp\tex\master'
info = os.walk(inPath)
for dirpath, dirnames, filenames in info:
    if dirpath.split('\\')[-1] == 'master':
        for tif in filenames:
            print tif
            if not os.path.exists(outputPath + '\\' + dirpath.split('\\')[-3] + r'\tex\master_1k'):
                os.makedirs(outputPath + '\\' + dirpath.split('\\')[-3] + r'\tex\master_1k')
            output_image = outputPath + '\\' + dirpath.split('\\')[-3] + r'\tex\master_1k' + '\\' + tif
            convert_image(dirpath + '\\' + tif, output_image, scale='512:512')

#\\\\\\\\\转换视频格式
def convert_video(input_video, output_video):
    ffmpeg = r'P:/pipeline/custom_plugin/ffmpeg/ffmpeg.exe'
    run_cmd = f'{ffmpeg} -y -i "{input_video}" -b:v 5000k -vf scale=3840:3840 -preset slow -vcodec libx264 -acodec aac -strict -2 "{output_video}"'

    try:
        subprocess.run(run_cmd, shell=True, check=True)
        print(f"转换成功: {input_video} -> {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"转换失败: {input_video}\n错误信息: {e}")

def batch_convert_videos(input_dir, output_dir):
    for dirpath, _, filenames in os.walk(input_dir):
        for filename in filenames:
            if filename.lower().endswith('.mov'):
                input_video = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(dirpath, input_dir)
                output_subdir = os.path.join(output_dir, relative_path)
                os.makedirs(output_subdir, exist_ok=True)
                output_video = os.path.join(output_subdir, f"{os.path.splitext(filename)[0]}.mp4")
                convert_video(input_video, output_video)
input_directory = r'U:\ywm\MHC\sxx\rig_v002\leg_v002.mov'
output_directory = r'U:\ywm\MHC\sxx\rig_v002\leg_v002.mp4'
convert_video(input_directory, output_directory)

