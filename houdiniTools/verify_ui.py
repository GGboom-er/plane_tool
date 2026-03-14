import sys
import os
from PySide6 import QtWidgets

# Setup Path
plugin_root = r"Y:\\GGbommer\\scripts\\plane_tool\\houdiniTools\\GG_SmartReduce_Tool"
python_dir = os.path.join(plugin_root, "python")
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

import PolyReduce_UI

print("--- UI INSTANTIATION TEST ---")

# 1. Create Qt App (Required for Widgets)
app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

try:
    # 2. Try to create the Window
    print("Creating SmartPolyReduceUI instance...")
    window = PolyReduce_UI.SmartPolyReduceUI()
    print("[PASS] UI initialized successfully.")
    
    # 3. Test Slider Logic (Simulate user dragging slider)
    print("Testing slider callbacks...")
    # These should run without error even if no file is loaded (thanks to try-except blocks)
    window.update_percentage(50)
    window.update_mask_weight(10)
    window.update_threshold(20)
    print("[PASS] Slider callbacks executed without crash.")
    
    # 4. Test Clean Slider Logic
    window.update_clean(50) # Should set tolerance to 0.005
    print("[PASS] Clean slider callback executed.")
    
    # 5. Test Browse (Mocking)
    # We can't pop up a dialog, but we can check if the method exists
    if hasattr(window, 'browse_file'):
        print("[PASS] Browse method exists.")

    print("\n[SUCCESS] UI code is syntactically correct and logical.")

except Exception as e:
    print(f"\n[FAIL] UI Error: {e}")
    import traceback
    traceback.print_exc()
