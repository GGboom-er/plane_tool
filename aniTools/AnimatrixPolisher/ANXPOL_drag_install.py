# -*- coding: utf-8 -*-
# Drag & Drop this file into Maya viewport to install AnimatrixPolisher

import os, sys, shutil, traceback
import maya.cmds as cmds
import maya.mel as mel

PKG_NAME  = 'AnimatrixPolisher'           # โฟลเดอร์แพ็กเกจ
BTN_LABEL = 'Polisher'                    # ชื่อที่โชว์บนปุ่ม
BTN_ANNOT = 'Launch Animatrix Polisher'   # tooltip
ICON_SHELF = 'sculpture'                  # ชื่อไฟล์ไอคอนบน shelf (ไม่ต้องใส่ .png)
BANNER    = 'Animatrix'                   # ชื่อแบนเนอร์ใน UI (ไฟล์อยู่ใน icons)

_DROPPED_FILE = None

def _this_dir():
    if _DROPPED_FILE and os.path.exists(_DROPPED_FILE):
        return os.path.dirname(_DROPPED_FILE)
    return os.path.dirname(__file__)

def _ensure_dir(p):
    if not os.path.exists(p):
        os.makedirs(p)

def _copytree_overwrite(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)

def _guess_pkg_src_from_neighbors():
    base = _this_dir()
    # 1) โฟลเดอร์ชื่อ PKG_NAME อยู่ข้าง ๆ ไฟล์ติดตั้ง
    cand = os.path.join(base, PKG_NAME)
    if os.path.isdir(cand):
        return cand
    # 2) โครง build แบบระบุเวอร์ชัน Python (ถ้าคุณจัดไว้)
    for sub in ('build_py39', 'build_py310', 'build_py311'):
        c2 = os.path.join(base, sub, PKG_NAME)
        if os.path.isdir(c2):
            return c2
    return None

def _pick_pkg_src():
    # เดาจากเพื่อนบ้านก่อน
    cand = _guess_pkg_src_from_neighbors()
    if cand:
        return cand
    # ให้เลือกโฟลเดอร์ด้วย dialog
    sel = cmds.fileDialog2(ds=2, fileMode=3, caption=f"Select '{PKG_NAME}' folder")
    if sel and os.path.isdir(sel[0]):
        # รองรับกรณีเลือกโฟลเดอร์ชั้นบน แล้วมี PKG_NAME ซ้อนอยู่ข้างใน
        p = sel[0]
        if os.path.basename(p).lower() != PKG_NAME.lower():
            q = os.path.join(p, PKG_NAME)
            if os.path.isdir(q):
                p = q
        return p
    return None

def _resolve_icon_path(icons_dir, name):
    # รับชื่อไฟล์โดยไม่ต้องใส่นามสกุล
    cand = os.path.join(icons_dir, name)
    if os.path.exists(cand):
        return cand.replace('\\','/')
    if '.' not in name:
        for ext in ('.png', '.xpm', '.bmp', '.ico'):
            p = os.path.join(icons_dir, name + ext)
            if os.path.exists(p):
                return p.replace('\\','/')
    # fallback
    return 'pythonFamily.png'

def _current_shelf_layout():
    gShelfTopLevel = mel.eval('$gShelfTopLevel=$gShelfTopLevel')
    cur = cmds.shelfTabLayout(gShelfTopLevel, q=True, st=True)
    if cur and cmds.shelfLayout(cur, exists=True):
        return cur
    kids = cmds.shelfTabLayout(gShelfTopLevel, q=True, ca=True) or []
    if kids:
        return kids[0]
    return cmds.shelfLayout('Custom', p=gShelfTopLevel)

def _make_shelf_button_on_current(icons_dir):
    shelf = _current_shelf_layout()
    icon_path = _resolve_icon_path(icons_dir, ICON_SHELF)

    # ลบปุ่มชื่อซ้ำบน shelf ปัจจุบัน
    for b in cmds.shelfLayout(shelf, q=True, ca=True) or []:
        if cmds.objectTypeUI(b) == 'shelfButton' and cmds.shelfButton(b, q=True, l=True) == BTN_LABEL:
            try: cmds.deleteUI(b)
            except: pass

    cmds.shelfButton(
        p=shelf, l=BTN_LABEL, i=icon_path, ann=BTN_ANNOT,
        c="import AnimatrixPolisher as ANP; ANP.launch()"
    )
    try: cmds.saveAllShelves()
    except: pass

def install():
    pkg_src = _pick_pkg_src()
    if not pkg_src:
        cmds.warning(f"Package '{PKG_NAME}' not found.")
        return

    scripts_dir = cmds.internalVar(userScriptDir=True)
    prefs_dir   = cmds.internalVar(userPrefDir=True)
    icons_dir   = os.path.join(prefs_dir, 'icons')
    pkg_dst     = os.path.join(scripts_dir, PKG_NAME)

    _ensure_dir(scripts_dir)
    _ensure_dir(icons_dir)

    # คัดลอกแพ็กเกจ (จะมีไฟล์ pyarmor_runtime_* ร่วมด้วยหลัง obfuscate)
    _copytree_overwrite(pkg_src, pkg_dst)

    # ก็อปไอคอนไป prefs/icons
    src_icons = os.path.join(pkg_src, 'icons')
    if os.path.isdir(src_icons):
        for fn in os.listdir(src_icons):
            sp = os.path.join(src_icons, fn)
            dp = os.path.join(icons_dir, fn)
            try: shutil.copy2(sp, dp)
            except Exception as e: print("Skip icon {}: {}".format(fn, e))

    # สร้างปุ่มบน shelf ปัจจุบัน
    _make_shelf_button_on_current(icons_dir)

    # smoke test import
    try:
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import importlib
        pkg = importlib.import_module(PKG_NAME)
        importlib.reload(pkg)
        print("Installed OK:", pkg.__file__)
    except Exception as e:
        traceback.print_exc()
        cmds.warning(f"Installed but import failed: {e}")

    try:
        cmds.confirmDialog(
            t="Install Complete",
            m=f"Installed {PKG_NAME}\nShelf button added on CURRENT shelf.\n",
            b=["OK"]
        )
    except:
        pass

def onMayaDroppedPythonFile(*args, **kwargs):
    global _DROPPED_FILE
    if args and isinstance(args[0], str):
        _DROPPED_FILE = args[0]
    try:
        install()
    except Exception as e:
        traceback.print_exc()
        cmds.warning(f"Install failed: {e}")

if __name__ == '__main__':
    onMayaDroppedPythonFile(__file__)
