# -*- coding: utf-8 -*-
# NEWTON_drag_install.py — Drag & Drop into Maya viewport to install / patch IsaacNewton

import os, sys, re, shutil, traceback
import maya.cmds as cmds
import maya.mel as mel

# ===== Config =====
PKG_NAME   = 'IsaacNewton'
BTN_LABEL  = 'Newton'   
BTN_ANNOT  = 'Launch SIR ISAAC NEWTON'
ICON_NAME  = 'AppleFall'   
ENTRY_CMD  = "import IsaacNewton as IN; IN.launch()"

_DROPPED_FILE = None  # set by onMayaDroppedPythonFile


# ===== Helpers =====
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

def _pick_pkg_src():
    base = _this_dir()
    cand = os.path.join(base, PKG_NAME)
    if os.path.isdir(cand):
        return cand
    sel = cmds.fileDialog2(ds=2, fileMode=3, caption="Select '{}' package folder'".format(PKG_NAME))
    if sel and os.path.isdir(sel[0]):
        return sel[0]
    return None

def _resolve_icon_path(icons_dir):
    # absolute
    if os.path.isabs(ICON_NAME) and os.path.exists(ICON_NAME):
        return ICON_NAME.replace('\\','/')
    # relative (no ext)
    cand = os.path.join(icons_dir, ICON_NAME).replace('\\','/')
    if os.path.exists(cand):
        return cand
    if '.' not in ICON_NAME:
        for ext in ('.png', '.xpm', '.bmp', '.ico'):
            p = os.path.join(icons_dir, ICON_NAME+ext).replace('\\','/')
            if os.path.exists(p):
                return p
    return 'pythonFamily.png'

def _current_shelf_layout():
    g = mel.eval('$gShelfTopLevel=$gShelfTopLevel')
    cur = cmds.shelfTabLayout(g, q=True, st=True)
    if cur and cmds.shelfLayout(cur, exists=True):
        return cur
    children = cmds.shelfTabLayout(g, q=True, ca=True) or []
    if children:
        return children[0]
    return cmds.shelfLayout('Custom', p=g)

def _remove_dup_button(shelf, label):
    for b in cmds.shelfLayout(shelf, q=True, ca=True) or []:
        if cmds.objectTypeUI(b) == 'shelfButton':
            try:
                if cmds.shelfButton(b, q=True, l=True) == label:
                    cmds.deleteUI(b)
            except Exception:
                pass

def _make_button_current_shelf(icons_dir):
    shelf = _current_shelf_layout()
    icon = _resolve_icon_path(icons_dir)
    _remove_dup_button(shelf, BTN_LABEL)
    cmds.shelfButton(
        p=shelf,
        l=BTN_LABEL,
        i=icon,
        ann=BTN_ANNOT,
        c=ENTRY_CMD,
        sourceType='python'    # <<< บังคับเป็น Python
    )
    try: cmds.saveAllShelves()
    except Exception: pass

def _patch_all_shelf_UI_buttons():
    """แพตช์ปุ่มที่มี IsaacNewton ทุกชั้นใน UI ให้เป็น Python + ENTRY_CMD"""
    g = mel.eval('$gShelfTopLevel=$gShelfTopLevel')
    for shelf in cmds.shelfTabLayout(g, q=True, ca=True) or []:
        for b in cmds.shelfLayout(shelf, q=True, ca=True) or []:
            if cmds.objectTypeUI(b) != 'shelfButton':
                continue
            lab = (cmds.shelfButton(b, q=True, l=True) or '').strip().lower()
            cmd = (cmds.shelfButton(b, q=True, c=True) or '')
            if ('IsaacNewton' in cmd) or (lab in {'newton','isaacnewton','sir isaac newton'}):
                cmds.shelfButton(b, e=True, c=ENTRY_CMD, sourceType='python', ann=BTN_ANNOT)
    try: cmds.saveAllShelves()
    except Exception: pass

def _patch_all_shelf_files_to_disk():
    """แก้ไฟล์ .mel ของ shelf บนดิสก์ ให้กลายเป็น Python + ENTRY_CMD (กันมันย้อนกลับ)"""
    pref_dir = cmds.internalVar(userPrefDir=True)
    shelves_dir = os.path.join(pref_dir, 'shelves')
    if not os.path.isdir(shelves_dir):
        return
    for fn in os.listdir(shelves_dir):
        if not fn.lower().endswith('.mel'):
            continue
        path = os.path.join(shelves_dir, fn)
        try:
            try:
                with open(path, 'r', encoding='utf-8') as f: txt = f.read()
            except Exception:
                with open(path, 'r') as f: txt = f.read()
        except Exception:
            continue

        if 'IsaacNewton' not in txt:
            continue

        new = txt
        # เปลี่ยน command ที่มี IsaacNewton ทั้งหมดให้เป็น ENTRY_CMD
        new = re.sub(r'(-command\s+")([^"]*IsaacNewton[^"]*)(")', r'\1'+ENTRY_CMD+r'\3', new)
        # เปลี่ยน sourceType mel -> python เฉพาะบรรทัดที่มี IsaacNewton
        new = re.sub(r'(-sourceType\s+")mel(")(?=[^;]*IsaacNewton)', r'\1python\2', new)

        if new != txt:
            # backup ไฟล์ครั้งแรก
            bak = path + '.bak'
            if not os.path.exists(bak):
                try:
                    with open(bak, 'wb') as bf, open(path, 'rb') as rf:
                        bf.write(rf.read())
                except Exception:
                    pass
            try:
                with open(path, 'w', encoding='utf-8') as f: f.write(new)
            except Exception:
                with open(path, 'w') as f: f.write(new)

def _ensure_init_with_launch(pkg_dst):
    """บังคับให้ IsaacNewton/__init__.py มี launch() ที่เรียก UI"""
    init_path = os.path.join(pkg_dst, '__init__.py')
    content = r'''# -*- coding: utf-8 -*-
import os, sys, importlib
_pkg_dir = os.path.dirname(__file__)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)
def launch():
    importlib.invalidate_caches()
    sys.modules.pop(__name__ + '.isaac_newton', None)
    m = importlib.import_module('.isaac_newton', __name__)
    for fn in ('SIR_ISAAC_NEWTON','rhs_ui','main','launch'):
        if hasattr(m, fn):
            try: getattr(m, fn)()
            except Exception: pass
            break
    return m
'''
    # เขียนทับถ้าไม่มีหรือไม่มี launch()
    need = True
    if os.path.exists(init_path):
        try:
            with open(init_path, 'r', encoding='utf-8') as f:
                t = f.read()
            if 'def launch' in t and 'isaac_newton' in t:
                need = False
        except Exception:
            need = True
    if need:
        try:
            if os.path.exists(init_path):
                shutil.copy2(init_path, init_path + '.bak')
        except Exception:
            pass
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(content)

def _smoke_import(scripts_dir):
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import importlib
    sys.modules.pop(PKG_NAME, None)
    importlib.invalidate_caches()
    mod = importlib.import_module(PKG_NAME)
    try: importlib.reload(mod)
    except Exception: pass
    print("Installed OK:", mod.__file__)
    return mod


# ===== Main install =====
def install():
    pkg_src = _pick_pkg_src()
    if not pkg_src:
        cmds.warning("Package '{}' not found.".format(PKG_NAME))
        return

    scripts_dir = cmds.internalVar(userScriptDir=True)
    prefs_dir   = cmds.internalVar(userPrefDir=True)
    icons_dir   = os.path.join(prefs_dir, 'icons')
    pkg_dst     = os.path.join(scripts_dir, PKG_NAME)

    _ensure_dir(scripts_dir); _ensure_dir(icons_dir)

    # copy package
    _copytree_overwrite(pkg_src, pkg_dst)
    # make sure __init__.py has launch()
    _ensure_init_with_launch(pkg_dst)

    # copy icons
    src_icons = os.path.join(pkg_src, 'icons')
    if os.path.isdir(src_icons):
        for fn in os.listdir(src_icons):
            sp = os.path.join(src_icons, fn)
            dp = os.path.join(icons_dir, fn)
            try: shutil.copy2(sp, dp)
            except Exception as e: print("Skip icon {}: {}".format(fn, e))

    # create button on CURRENT shelf
    _make_button_current_shelf(icons_dir)
    # patch all existing shelf buttons in UI
    _patch_all_shelf_UI_buttons()
    # patch shelf .mel files on disk soมันไม่ย้อนกลับ
    _patch_all_shelf_files_to_disk()

    # smoke import
    try: _smoke_import(scripts_dir)
    except Exception as e:
        traceback.print_exc()
        cmds.warning("Installed but import failed: {}".format(e))

    try:
        cmds.confirmDialog(
            t="Install Complete",
            m="Installed {}\nShelf button fixed to Python.\nCommand:\n{}\n".format(PKG_NAME, ENTRY_CMD),
            b=["OK"]
        )
    except Exception:
        pass


# ===== Drag & drop entry =====
def onMayaDroppedPythonFile(*args, **kwargs):
    global _DROPPED_FILE
    if args and isinstance(args[0], str):
        _DROPPED_FILE = args[0]
    try:
        install()
    except Exception as e:
        traceback.print_exc()
        cmds.warning("Install failed: {}".format(e))

if __name__ == '__main__':
    onMayaDroppedPythonFile(__file__)
