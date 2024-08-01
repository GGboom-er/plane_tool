import maya.cmds as cmds

def update_reference_path(new_path):
    # 获取选中节点
    selected_nodes = cmds.ls(selection=True)
    
    if not selected_nodes:
        print("No node selected")
        return
    for i in selected_nodes:
    # 获取reference节点
        reference_node = cmds.referenceQuery(i, referenceNode=True)
        
        # 获取当前reference路径
        current_reference_path = cmds.referenceQuery(reference_node, filename=True)
        print("Current reference path:", current_reference_path)
        
        # 更新reference节点路径
        cmds.file(new_path, loadReference=reference_node)
        print("Reference path updated to:", new_path)


# 测试用例
new_reference_path = r"U:/ywm/tbx/slrobot/rig_slrobtlowb_low.ma"
update_reference_path(new_reference_path)
