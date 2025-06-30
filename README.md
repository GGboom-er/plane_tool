# Plane Tool Project

这是一个用于各种CG工作流程的工具集合，主要涵盖动画、批处理、Blender、缓存、模型、绑定和虚幻引擎等方面的工具。

## 目录结构

- `aniTools/`: 动画相关工具，可能包含参考管理、路径修改、动画曲线平滑等功能。
- `batchTools/`: 批处理工具，用于自动化执行一些重复性任务，例如批量处理参考文件或检查Maya文件。
- `blenderTools/`: Blender相关工具，用于Blender软件中的各种操作，如驱动、材质、修改器、文件导入导出等。
- `cacheTools/`: 缓存工具，用于处理模型序列缓存的构建和导出。
- `GGbommer/`: 可能包含一些通用工具或UI界面相关的代码。
- `modTools/`: 模型修改工具，可能包含UV修复、网格匹配、肌肉系统、纹理绑定等功能。
- `ourthTools/`: 其他通用工具，例如图像转换或视频压缩。
- `rigTools/`: 绑定工具，包含角色绑定、蒙皮、骨骼、DNA绑定等高级功能。
- `ueTools/`: 虚幻引擎相关工具，用于Maya和虚幻引擎之间的数据交互，例如FBX导入和导出。
- `__pycache__/`: Python编译缓存目录。
- `.git/`: Git版本控制相关文件。
- `.idea/`: IDE（如PyCharm）项目配置文件。
- `.ts/`: 可能是一些时间序列或特定工具的配置文件。
- `__init__.py`: Python包初始化文件。
- `test.py`, `test2.py`: 测试脚本。
- `.gitignore`: Git忽略文件配置。

## 主要模块功能概述

### `aniTools` (动画工具)
- `batchReference.py`: 批量处理参考文件。
- `changeRNPath.py`: 修改参考节点路径。
- `fixReferenceName.py`: 修复参考名称。
- `WretargetTool.py`: 重定向工具。
- `smoothAnimCurve/`: 动画曲线平滑工具。

### `batchTools` (批处理工具)
- `batch_RN.py`: 批量参考节点处理。
- `checkMA.py`: 检查Maya文件。
- `textCheckMa.py`: 文本检查Maya文件。

### `blenderTools` (Blender工具)
- `addDirve.py`: 添加驱动。
- `appendCache.py`: 追加缓存。
- `appendFile.py`: 追加文件。
- `copyMaterial.py`: 复制材质。
- `delDeform.py`: 删除形变。
- `Editmodifier.py`: 编辑修改器。
- `export_curveTomaya.py`: 导出曲线到Maya。
- `moveOutline.py`: 移动大纲。
- `optimizBlender.py`: 优化Blender文件。
- `renameShape.py`: 重命名形状。
- `setDrive.py`: 设置驱动。
- `setLightValueFn.py`: 设置灯光值函数。

### `cacheTools` (缓存工具)
- `buildSequenceMeshDFM.py`: 构建序列网格DFM。
- `buildSequenceMeshDFM2.py`: 构建序列网格DFM2。
- `exportCache.py`: 导出缓存。

### `modTools` (模型修改工具)
- `fixUVset.py`: 修复UV集。
- `matchMesh.py`: 网格匹配。
- `muscleTool_v1.0.py`: 肌肉工具。
- `quadPatcher_v1.0.py`: 四边面修补工具。
- `senceInfoFn.pyc`: 场景信息函数。
- `textureRig.py`: 纹理绑定。
- `transferUV.py`: 传输UV。
- `transSGInfo.py`: 传输SG信息。
- `AriStraightVertex/`: 顶点拉直工具。
- `MuscleJointSystem/`: 肌肉关节系统。

### `ourthTools` (其他工具)
- `comMp4.py`: MP4压缩。
- `convert_image.py`: 图像转换。

### `rigTools` (绑定工具)
- `MHC/`: 角色绑定、DNA绑定相关。
- `qc/skinning-tools/`: 蒙皮工具。
- `scirpts/`: 各种绑定脚本，例如：
    - `animToSDK.py`: 动画到SDK。
    - `atachCurveEPToMesh.py`: 曲线EP附加到网格。
    - `attrSetsFn.py`: 属性设置函数。
    - `buildBS.py`: 构建混合形状。
    - `channelBoxColor.py`: 通道盒颜色。
    - `compareInMaya.py`: Maya中比较。
    - `create_bs_connection_manager.py`: 创建混合形状连接管理器。
    - `exprotUSD.py`: 导出USD。
    - `getMax_inf.py`: 获取最大影响。
    - `getMeshCenterCurve.py`: 获取网格中心曲线。
    - `getWarpBS.py`: 获取扭曲混合形状。
    - `locToMeshNormal.py`: 定位器到网格法线。
    - `Quick_skin_2025.py`, `Quick_skin.py`: 快速蒙皮工具。
    - `rebuildBoneHierarchy.py`: 重建骨骼层级。
    - `rebuildConstraint.py`: 重建约束。
    - `reConnectBSDIrve.py`: 重新连接混合形状驱动。
    - `renameParent.py`: 重命名父级。
    - `replaceAsset.py`: 替换资产。
    - `replaceAttr.py`: 替换属性。
    - `setSDK.py`: 设置SDK。
    - `skinClusterFn.py`: 蒙皮簇函数。
    - `softSelToSoftmod.py`: 软选择到软修改。
    - `tools.py`, `util.py`: 通用工具函数。
    - `attrToolsPK/`: 属性工具包。
    - `copySkinWeight/`: 复制蒙皮权重。
    - `customADV/`: 自定义高级骨骼。
    - `CutTime/`: 时间切割工具。
    - `kz_secondaryCtrl/`: 次级控制器。
    - `ReBlendShapeTool/`: 重新混合形状工具。

### `ueTools` (虚幻引擎工具)
- `inputFBXToMat.py`: FBX输入到材质。
- `mayaToUeFbx.py`: Maya到UE的FBX导出。
- `utils.py`: 通用工具函数。

### `GGbommer/winUI.py` 端口映射说明
此界面需要通过 Socket 向 Maya 或 Blender 发送命令。由于官方并未为
Maya 2025 或 Blender 4.3 提供默认的远程执行端口，启动软件时需显式
打开 `commandPort` 并记录端口号。建议在启动脚本中将端口和对应进程
PID 写入根目录下的 `dcc_port_map.json`，格式示例：

```json
{
    "1234": 7002,
    "2345": 7003
}
```

界面启动后会读取该文件以确定每个进程的端口号。若未找到端口映射，则
按钮会提示"Port is unknown"并不会尝试发送命令。


