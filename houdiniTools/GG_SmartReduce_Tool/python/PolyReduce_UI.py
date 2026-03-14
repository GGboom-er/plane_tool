import os
import hou
from PySide6 import QtWidgets, QtCore
import PolyReduce

class SmartPolyReduceUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart PolyReduce 2.4")
        self.current_file = ""
        self.ui_nodes = {} 
        self.init_ui()
        
    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 1. File Input
        grp_file = QtWidgets.QGroupBox("Source OBJ File")
        layout_file = QtWidgets.QHBoxLayout(grp_file)
        
        self.le_path = QtWidgets.QLineEdit()
        self.le_path.setPlaceholderText("Select an OBJ file...")
        self.le_path.setReadOnly(True)
        
        self.btn_browse = QtWidgets.QPushButton("Browse...")
        self.btn_browse.clicked.connect(self.browse_file)
        
        layout_file.addWidget(self.le_path)
        layout_file.addWidget(self.btn_browse)
        main_layout.addWidget(grp_file)
        
        # 2. Parameters
        grp_parms = QtWidgets.QGroupBox("Settings")
        self.layout_parms = QtWidgets.QVBoxLayout(grp_parms)
        
        self.slider_pct = self.create_slider("Reduction %", 1, 99, 15, self.update_percentage)
        self.slider_mask = self.create_slider("Mask Weight", 1, 100, 20, self.update_mask_weight)
        self.slider_thresh = self.create_slider("Hard Edge Threshold", 1, 30, 12, self.update_threshold)
        self.slider_clean = self.create_slider("Clean Tolerance (x10^-4)", 1, 100, 1, self.update_clean)
        self.slider_blur = self.create_slider("Blur Iterations", 0, 50, 5, self.update_blur)
        
        main_layout.addWidget(grp_parms)
        
        # 3. Actions
        grp_action = QtWidgets.QGroupBox("Actions")
        layout_action = QtWidgets.QVBoxLayout(grp_action)
        
        self.btn_export = QtWidgets.QPushButton("Process & Save")
        self.btn_export.setStyleSheet("background-color: #27ae60; font-weight: bold; padding: 12px; color: white;")
        self.btn_export.clicked.connect(self.run_process)
        
        layout_action.addWidget(self.btn_export)
        main_layout.addWidget(grp_action)
        main_layout.addStretch()

    def create_slider(self, label_text, min_val, max_val, default, callback):
        lbl = QtWidgets.QLabel(f"{label_text}: {default}")
        
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setSingleStep(1)
        slider.setPageStep(5) # [FIX] 点击滑道移动 5 而不是 10
        
        # 使用闭包捕获 label 和 name
        def on_change(val):
            self.update_label_and_parm(lbl, label_text, val, callback)
            
        slider.valueChanged.connect(on_change)
        
        self.layout_parms.addWidget(lbl)
        self.layout_parms.addWidget(slider)
        return slider

    def update_label_and_parm(self, label_widget, name, value, callback):
        disp_val = value
        
        # 特殊格式化
        if name == "Hard Edge Threshold": 
            disp_val = value / 10.0
            label_widget.setText(f"{name}: {disp_val}")
        elif "Clean Tolerance" in name:
            disp_val = value * 0.0001
            label_widget.setText(f"Clean Tolerance: {disp_val:.4f}")
        else:
            label_widget.setText(f"{name}: {disp_val}")
        
        try:
            callback(value)
        except hou.ObjectWasDeleted:
            self.ui_nodes = {}
        except Exception:
            pass

    def get_container(self):
        obj = hou.node("/obj")
        container = obj.node("Smart_PolyReduce_Processor")
        if not container:
            container = obj.createNode("geo", "Smart_PolyReduce_Processor")
            container.moveToGoodPosition()
        return container

    def browse_file(self):
        path = hou.ui.selectFile(title="Select Source OBJ", file_type=hou.fileType.Geometry, pattern="*.obj")
        if path:
            self.current_file = hou.expandString(path)
            self.le_path.setText(self.current_file)
            self.load_preview()

    def load_preview(self):
        if not self.current_file: return
        container = self.get_container()
        
        # 初始化预览 (静默构建)
        # 注意：这里我们重新调用构建逻辑来获取 ui_nodes，但不导出
        read_node = container.createNode("file", "temp_in") # 临时，会被 PolyReduce 清理
        
        # 参数字典
        parms = {
            'percentage': self.slider_pct.value(),
            'mask_weight': self.slider_mask.value(),
            'hard_threshold': self.slider_thresh.value() / 10.0,
            'tolerance': self.slider_clean.value() * 0.0001,
            'blur_iter': self.slider_blur.value()
        }
        
        # 复用 process_file 逻辑但只做预览部分太复杂，这里简化重用逻辑
        # 直接调用 process_file，但给一个假的 output_dir 不导出？不，process_file 会导出。
        # 最好是分离构建和导出，但在 PolyReduce.py 中它们是整合的。
        # 为了不破坏逻辑，我们手动触发一次 process 类似的行为，但不按导出按钮。
        
        # 更简单的方法：直接调用 process_file 但传入空 output_dir 或修改 PolyReduce。
        # 由于我们重构了 PolyReduce，process_file 负责了一切。
        # 现在的 load_preview 实际上就是为了获得 ui_nodes。
        
        # 临时方案：直接用 process_file 生成节点，但不关注导出结果
        # 因为 process_file 会清空子节点并重建
        try:
            # 伪造一个输出目录避免报错，或者我们在 browse 阶段不强制生成，只在 run_process 时生成？
            # 这是一个设计选择。为了响应性，Browse 后通常只加载。
            # 我们调用 process_file 的构建部分。
            
            # 由于 PolyReduce.py 现在比较干净，我们可以只调用 build_smart_reduce_chain
            container.deleteItems(container.children())
            read_node = container.createNode("file", "preview_in")
            read_node.parm("file").set(self.current_file)
            base_name = "preview"
            
            final_node = PolyReduce.build_smart_reduce_chain(container, read_node, base_name)
            self.ui_nodes = PolyReduce.get_ui_nodes(container)
            
            # 初始同步 UI 到节点
            self.update_percentage(self.slider_pct.value())
            self.update_mask_weight(self.slider_mask.value())
            self.update_threshold(self.slider_thresh.value())
            self.update_clean(self.slider_clean.value())
            self.update_blur(self.slider_blur.value())
            
            container.layoutChildren()
            final_node.setDisplayFlag(True)
            final_node.setRenderFlag(True)
            
        except Exception as e:
            print(f"Preview Error: {e}")

    # --- Callbacks ---
    def update_percentage(self, val):
        if n := self.ui_nodes.get('reduce'): n.parm('percentage').set(val)

    def update_mask_weight(self, val):
        if n := self.ui_nodes.get('reduce'): n.parm('retainattribweight').set(val)

    def update_threshold(self, val):
        if n := self.ui_nodes.get('wrangle'): n.parm('hard_threshold').set(val / 10.0)
            
    def update_clean(self, val):
        tol = val * 0.0001
        if n := self.ui_nodes.get('pre_clean'): PolyReduce.set_clean_tolerance(n, tol)
        if n := self.ui_nodes.get('final_clean'): PolyReduce.set_clean_tolerance(n, tol)
            
    def update_blur(self, val):
        if n := self.ui_nodes.get('blur'): n.parm('iterations').set(val)

    def run_process(self):
        if not self.current_file:
            hou.ui.displayMessage("Please select a file first!")
            return
            
        parms = {
            'percentage': self.slider_pct.value(),
            'mask_weight': self.slider_mask.value(),
            'hard_threshold': self.slider_thresh.value() / 10.0,
            'tolerance': self.slider_clean.value() * 0.0001,
            'blur_iter': self.slider_blur.value()
        }
        
        source_dir = os.path.dirname(self.current_file)
        out_dir = os.path.join(source_dir, "output_optimized")
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        container = self.get_container()
        
        try:
            with hou.InterruptableOperation("Processing...", open_interrupt_dialog=True):
                new_nodes = PolyReduce.process_file(self.current_file, out_dir, container, parms)
                if new_nodes: self.ui_nodes = new_nodes
            hou.ui.displayMessage(f"Success!\nSaved to: {out_dir}")
        except Exception as e:
            hou.ui.displayMessage(f"Error:\n{str(e)}", severity=hou.severityType.Error)
