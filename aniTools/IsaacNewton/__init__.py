# IsaacNewton/__init__.py
# -*- coding: utf-8 -*-
import os, sys, importlib

_pkg_dir = os.path.dirname(__file__)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

def launch():
    """Open the UI from the main module."""
    importlib.invalidate_caches()
    # รีโหลดตอน dev ให้ชัวร์ว่าเห็นไฟล์ล่าสุด
    sys.modules.pop(__name__ + '.isaac_newton', None)
    m = importlib.import_module('.isaac_newton', __name__)
    # เรียกจุดเข้า UI ที่มีอยู่
    for fn in ('SIR_ISAAC_NEWTON', 'rhs_ui', 'main', 'launch'):
        if hasattr(m, fn):
            try: getattr(m, fn)()
            except Exception: pass
            break
    return m
