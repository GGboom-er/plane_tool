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

