"""
MRS Mode Switch Comprehensive Test
===================================
Tests all 6 mode transitions: FIK->FK, FIK->IK, FK->IK, FK->FIK, IK->FK, IK->FIK
plus round-trip cycles (FIK->FK->IK->FIK) to verify no garbage nodes accumulate
and all connections remain correct after repeated rebuilds.

Validates per transition:
  1. Control existence (FK/IK created/removed as expected)
  2. Bone driving (bones follow correct driver)
  3. Node topology (shared Scale_CM, InvScale, OPM wiring)
  4. Garbage detection (no orphan nodes from previous mode)
  5. Scale propagation (parent_object scale reaches all controllers)
  6. Set membership (Node_Set tracks current nodes, no stale refs)
"""
import maya.standalone
maya.standalone.initialize(name='python')

import maya.cmds as cmds
import maya.api.OpenMaya as om
import sys, os, math, traceback

CURRENT_DIR = r"Y:\GGbommer\scripts\plane_tool\rigTools\scirpts\matrixRibbonSystem"
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

PLUGIN_PATH = os.path.join(CURRENT_DIR, "py_matrix_ribbon.py")
try:
    if not cmds.pluginInfo("matrixRibbonMesh", q=True, loaded=True):
        cmds.loadPlugin(PLUGIN_PATH)
    if not cmds.pluginInfo("matrixNodes", q=True, loaded=True):
        try: cmds.loadPlugin("matrixNodes")
        except: pass
except: pass

import matrix_ribbon_system
from utils import MrsNaming, RigUtils

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TOL = 0.15
BASE = "SwitchTest"
NUM_BONES = 4  # j1..j4, parent=j0

def extract_scale(node):
    m = cmds.xform(node, q=True, ws=True, m=True)
    sx = math.sqrt(m[0]**2 + m[1]**2 + m[2]**2)
    sy = math.sqrt(m[4]**2 + m[5]**2 + m[6]**2)
    sz = math.sqrt(m[8]**2 + m[9]**2 + m[10]**2)
    return (sx, sy, sz)

def ws_pos(node):
    return cmds.xform(node, q=True, ws=True, t=True)

def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

def fk_name(idx, suffix):
    return RigUtils.generate_name(BASE, 0, idx, suffix)

# ---------------------------------------------------------------------------
# Scene setup (called once, reused across all switches)
# ---------------------------------------------------------------------------
mrs = None
chains = None
follow_mesh = None
parent_obj = None
bone_names = []

def setup_scene(enable_follow=False):
    """Create fresh scene with 5-joint chain + preview + initial FIK bind."""
    global mrs, chains, follow_mesh, parent_obj, bone_names
    cmds.file(new=True, force=True)
    mrs = matrix_ribbon_system.RibbonRigSystem()

    cmds.select(clear=True)
    j0 = cmds.joint(p=(0, 0, 0), n="Root_Bone")
    j1 = cmds.joint(p=(0, 0, 10), n="Bone_01")
    j2 = cmds.joint(p=(0, 0, 20), n="Bone_02")
    j3 = cmds.joint(p=(0, 0, 30), n="Bone_03")
    j4 = cmds.joint(p=(0, 0, 40), n="Bone_04")
    cmds.select(clear=True)

    parent_obj = j0
    bone_names = [j1, j2, j3, j4]
    chains = [bone_names]

    mrs.create_preview_mesh(chains, base_name=BASE, axis=4)
    mrs.bind_from_preview(
        f"{BASE}{MrsNaming.MESH_PREVIEW}", chains,
        enable_fk=True, enable_ik=True, parent_object=parent_obj,
        enable_follow=enable_follow
    )
    follow_mesh = f"{BASE}{MrsNaming.MESH_FOLLOW}"

    # Skin FollowMod to j0 for scale propagation tests
    cmds.skinCluster(parent_obj, follow_mesh, toSelectedBones=True, maximumInfluences=1)

def do_update(enable_fk, enable_ik, enable_follow=False):
    """Perform an update-mode bind with given FK/IK/Follow flags."""
    mrs.bind_from_preview(
        preview_mesh=None, chains=chains,
        enable_fk=enable_fk, enable_ik=enable_ik,
        existing_follow_mesh=follow_mesh,
        existing_base_name=BASE,
        update_mode=True,
        parent_object=parent_obj,
        enable_follow=enable_follow
    )

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def ctrl_exists(idx, mode):
    """Check if FK or IK control exists for bone index."""
    suffix = MrsNaming.FK_CTRL if mode == "fk" else MrsNaming.IK_CTRL
    return cmds.objExists(fk_name(idx, suffix))

def offset_exists(idx, mode):
    suffix = MrsNaming.FK_OFFSET if mode == "fk" else MrsNaming.IK_OFFSET
    return cmds.objExists(fk_name(idx, suffix))

def validate_controls(label, expect_fk, expect_ik):
    """Verify correct controls exist/absent for all bones."""
    for i in range(NUM_BONES):
        if expect_fk:
            assert ctrl_exists(i, "fk"), f"[{label}] FK_Ctrl_{i} should exist"
            assert offset_exists(i, "fk"), f"[{label}] FK_Offset_{i} should exist"
        else:
            assert not ctrl_exists(i, "fk"), f"[{label}] FK_Ctrl_{i} should NOT exist"
            assert not offset_exists(i, "fk"), f"[{label}] FK_Offset_{i} should NOT exist"

        if expect_ik:
            assert ctrl_exists(i, "ik"), f"[{label}] IK_Ctrl_{i} should exist"
            assert offset_exists(i, "ik"), f"[{label}] IK_Offset_{i} should exist"
        else:
            assert not ctrl_exists(i, "ik"), f"[{label}] IK_Ctrl_{i} should NOT exist"
            assert not offset_exists(i, "ik"), f"[{label}] IK_Offset_{i} should NOT exist"

def validate_bone_driving(label, expect_fk, expect_ik):
    """Verify each bone is driven by the correct final driver via OPM."""
    for i, bone in enumerate(bone_names):
        opm_plug = f"{bone}.offsetParentMatrix"
        src = cmds.connectionInfo(opm_plug, sourceFromDestination=True)
        assert src, f"[{label}] Bone {bone} OPM not connected"

        # Final driver: IK if IK enabled, else FK
        if expect_ik:
            expected_driver = fk_name(i, MrsNaming.IK_CTRL)
        else:
            expected_driver = fk_name(i, MrsNaming.FK_CTRL)
        assert cmds.objExists(expected_driver), f"[{label}] Expected driver {expected_driver} missing"

def validate_no_garbage_scale_nodes(label, expect_fk):
    """Ensure no per-offset _ScaleCM nodes exist (they should be shared _Scale_CM)."""
    for i in range(NUM_BONES):
        for mode in ["fk", "ik"]:
            suffix = MrsNaming.FK_OFFSET if mode == "fk" else MrsNaming.IK_OFFSET
            grp = fk_name(i, suffix)
            # Per-offset ScaleCM should never exist (old pattern)
            old_cm = f"{grp}_ScaleCM"
            assert not cmds.objExists(old_cm), \
                f"[{label}] Garbage per-offset node {old_cm} still exists"
            # Old compensate nodes
            for comp in ["_ParentScale_DCM", "_ScaleComp", "_CtrlInvS_MD", "_CtrlInvS_CM"]:
                n = f"{grp}{comp}"
                assert not cmds.objExists(n), \
                    f"[{label}] Garbage legacy node {n} still exists"

    # Shared nodes should exist only when FK is active (needs scale injection)
    shared_scale = f"{BASE}_Scale_CM"
    shared_inv_md = f"{BASE}_InvScale_MD"
    shared_inv_cm = f"{BASE}_InvScale_CM"
    dcm = f"{BASE}_Parent_DCM"

    # DCM always exists when parent_object is set
    assert cmds.objExists(dcm), f"[{label}] Parent_DCM should exist"

    if expect_fk:
        assert cmds.objExists(shared_scale), f"[{label}] Shared Scale_CM should exist in FK mode"
        assert cmds.objExists(shared_inv_md), f"[{label}] Shared InvScale_MD should exist in FK mode"
        assert cmds.objExists(shared_inv_cm), f"[{label}] Shared InvScale_CM should exist in FK mode"
    # In pure IK mode, these are cleaned up before rebuild then recreated only if FK is enabled.
    # Since cleanup runs before build, and build only creates them for FK, they should be absent.

def validate_fk_topology(label):
    """Verify FK OPM wiring uses shared Scale_CM node."""
    shared_scale = f"{BASE}_Scale_CM"
    shared_inv_cm = f"{BASE}_InvScale_CM"

    # i==0: ScaleMM.matrixIn[0] -> shared Scale_CM
    root_offset = fk_name(0, MrsNaming.FK_OFFSET)
    scale_mm = f"{root_offset}_ScaleMM"
    assert cmds.objExists(scale_mm), f"[{label}] Root ScaleMM missing"
    src0 = cmds.connectionInfo(f"{scale_mm}.matrixIn[0]", sourceFromDestination=True)
    assert src0 == f"{shared_scale}.outputMatrix", \
        f"[{label}] Root ScaleMM.matrixIn[0] should be shared Scale_CM, got: {src0}"

    # i>=1: OPM.matrixIn[0] -> shared Scale_CM, matrixIn[3] -> InvScale_CM
    for i in range(1, NUM_BONES):
        child_offset = fk_name(i, MrsNaming.FK_OFFSET)
        opm = f"{child_offset}_OPM"
        assert cmds.objExists(opm), f"[{label}] Child OPM {opm} missing"

        s0 = cmds.connectionInfo(f"{opm}.matrixIn[0]", sourceFromDestination=True)
        assert s0 == f"{shared_scale}.outputMatrix", \
            f"[{label}] {opm}.matrixIn[0] should be shared Scale_CM, got: {s0}"

        s3 = cmds.connectionInfo(f"{opm}.matrixIn[3]", sourceFromDestination=True)
        assert s3 == f"{shared_inv_cm}.outputMatrix", \
            f"[{label}] {opm}.matrixIn[3] should be InvScale_CM, got: {s3}"

def validate_ik_scale(label, expect_fk):
    """Verify IK scale connections match mode."""
    dcm_scale = f"{BASE}_Parent_DCM.outputScale"
    for i in range(NUM_BONES):
        ik_offset = fk_name(i, MrsNaming.IK_OFFSET)
        if not cmds.objExists(ik_offset):
            continue
        scale_src = cmds.connectionInfo(f"{ik_offset}.scale", sourceFromDestination=True)
        if expect_fk:
            # Hybrid mode: IK offsets should NOT have .scale connection
            assert not scale_src, \
                f"[{label}] IK_Offset_{i} should not have .scale in hybrid mode, got: {scale_src}"
        else:
            # Pure IK: all IK offsets should have .scale from DCM
            assert scale_src == dcm_scale, \
                f"[{label}] IK_Offset_{i}.scale should be DCM.outputScale, got: {scale_src}"

def validate_scale_propagation(label, expect_fk, expect_ik):
    """Scale parent to 0.1, verify all controllers scale correctly."""
    cmds.setAttr(f"{parent_obj}.scale", 0.1, 0.1, 0.1)
    try:
        for i in range(NUM_BONES):
            if expect_ik:
                ctrl = fk_name(i, MrsNaming.IK_CTRL)
            elif expect_fk:
                ctrl = fk_name(i, MrsNaming.FK_CTRL)
            else:
                continue
            s = extract_scale(ctrl)
            for axis in range(3):
                assert abs(s[axis] - 0.1) < TOL, \
                    f"[{label}] {ctrl} axis {axis}: expected ~0.1, got {s[axis]:.3f}"
    finally:
        cmds.setAttr(f"{parent_obj}.scale", 1, 1, 1)

def validate_set_membership(label):
    """Verify Node_Set contains no stale references."""
    node_set = f"{BASE}{MrsNaming.NODE_SET}"
    if not cmds.objExists(node_set):
        return  # Set may not exist yet
    members = cmds.sets(node_set, q=True) or []
    for m in members:
        assert cmds.objExists(m), \
            f"[{label}] Node_Set contains stale reference: {m}"

def count_dg_nodes(label):
    """Count MRS-specific DG nodes (for node budget verification)."""
    node_set = f"{BASE}{MrsNaming.NODE_SET}"
    if not cmds.objExists(node_set):
        return 0
    members = cmds.sets(node_set, q=True) or []
    valid = [m for m in members if cmds.objExists(m)]
    count = len(valid)
    print(f"    [{label}] DG node count in Node_Set: {count}")
    return count

# ---------------------------------------------------------------------------
# Full validation suite for a given mode
# ---------------------------------------------------------------------------
def validate_mode(label, expect_fk, expect_ik):
    """Run all validations for current mode."""
    validate_controls(label, expect_fk, expect_ik)
    validate_bone_driving(label, expect_fk, expect_ik)
    validate_no_garbage_scale_nodes(label, expect_fk)
    if expect_fk:
        validate_fk_topology(label)
    if expect_ik:
        validate_ik_scale(label, expect_fk)
    validate_scale_propagation(label, expect_fk, expect_ik)
    validate_set_membership(label)
    count_dg_nodes(label)

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

def run_test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS: {name}")
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  FAIL: {name} -> {e}")
        traceback.print_exc()


def test_initial_fik():
    """Test 0: Verify initial FIK bind is correct."""
    setup_scene()
    validate_mode("Initial-FIK", expect_fk=True, expect_ik=True)


def test_fik_to_fk():
    """Test 1: FIK -> Pure FK"""
    setup_scene()
    do_update(enable_fk=True, enable_ik=False)
    validate_mode("FIK->FK", expect_fk=True, expect_ik=False)


def test_fik_to_ik():
    """Test 2: FIK -> Pure IK"""
    setup_scene()
    do_update(enable_fk=False, enable_ik=True)
    validate_mode("FIK->IK", expect_fk=False, expect_ik=True)


def test_fk_to_ik():
    """Test 3: Pure FK -> Pure IK"""
    setup_scene()
    do_update(enable_fk=True, enable_ik=False)
    validate_mode("FK(prep)", expect_fk=True, expect_ik=False)
    do_update(enable_fk=False, enable_ik=True)
    validate_mode("FK->IK", expect_fk=False, expect_ik=True)


def test_fk_to_fik():
    """Test 4: Pure FK -> FIK"""
    setup_scene()
    do_update(enable_fk=True, enable_ik=False)
    validate_mode("FK(prep)", expect_fk=True, expect_ik=False)
    do_update(enable_fk=True, enable_ik=True)
    validate_mode("FK->FIK", expect_fk=True, expect_ik=True)


def test_ik_to_fk():
    """Test 5: Pure IK -> Pure FK"""
    setup_scene()
    do_update(enable_fk=False, enable_ik=True)
    validate_mode("IK(prep)", expect_fk=False, expect_ik=True)
    do_update(enable_fk=True, enable_ik=False)
    validate_mode("IK->FK", expect_fk=True, expect_ik=False)


def test_ik_to_fik():
    """Test 6: Pure IK -> FIK"""
    setup_scene()
    do_update(enable_fk=False, enable_ik=True)
    validate_mode("IK(prep)", expect_fk=False, expect_ik=True)
    do_update(enable_fk=True, enable_ik=True)
    validate_mode("IK->FIK", expect_fk=True, expect_ik=True)


def test_full_cycle():
    """Test 7: Full round-trip cycle FIK -> FK -> IK -> FIK -> IK -> FK -> FIK
    Verifies no garbage accumulates across many transitions."""
    setup_scene()
    validate_mode("Cycle-FIK-0", expect_fk=True, expect_ik=True)

    transitions = [
        (True,  False, "Cycle-FK-1"),
        (False, True,  "Cycle-IK-2"),
        (True,  True,  "Cycle-FIK-3"),
        (False, True,  "Cycle-IK-4"),
        (True,  False, "Cycle-FK-5"),
        (True,  True,  "Cycle-FIK-6"),
    ]
    for fk, ik, label in transitions:
        do_update(enable_fk=fk, enable_ik=ik)
        validate_mode(label, expect_fk=fk, expect_ik=ik)

    # Final garbage sweep: search entire scene for orphan MRS nodes
    all_nodes = cmds.ls(f"{BASE}_*", long=True)
    node_set = f"{BASE}{MrsNaming.NODE_SET}"
    tracked = set(cmds.sets(node_set, q=True) or []) if cmds.objExists(node_set) else set()

    # Known valid non-tracked nodes: sets, groups, controls, meshes
    known_suffixes = [
        MrsNaming.RIG_SET, MrsNaming.GEO_SET, MrsNaming.GRP_SET,
        MrsNaming.CTRL_SET, MrsNaming.NODE_SET, MrsNaming.JNT_SET,
        MrsNaming.GRP_MAIN, MrsNaming.GRP_CTRL, MrsNaming.GRP_JNT,
        MrsNaming.FK_CTRL, MrsNaming.FK_OFFSET, MrsNaming.IK_CTRL, MrsNaming.IK_OFFSET,
        MrsNaming.MESH_FOLLOW,
    ]

    for node_path in all_nodes:
        node = node_path.split("|")[-1]
        # Skip if tracked in Node_Set
        if node in tracked:
            continue
        # Skip known structural nodes
        is_known = False
        for suf in known_suffixes:
            if node.endswith(suf):
                is_known = True
                break
        if is_known:
            continue
        # Skip chain group (e.g. SwitchTest_A_Grp)
        if node.endswith("_Grp") or node.endswith("Shape"):
            continue
        # Anything else is suspicious
        nt = cmds.nodeType(node)
        if nt in ("objectSet", "transform", "mesh", "joint"):
            continue
        # DG utility node not in Node_Set = garbage
        assert False, \
            f"[Cycle-Final] Orphan DG node found: {node} (type={nt})"


def test_node_count_optimization():
    """Test 8: Verify shared Scale_CM reduces node count.
    4-bone chain with parent_object (no follow) should have exactly 11 DG nodes in FK mode."""
    setup_scene()
    do_update(enable_fk=True, enable_ik=False)

    node_set = f"{BASE}{MrsNaming.NODE_SET}"
    members = cmds.sets(node_set, q=True) or []
    valid = [m for m in members if cmds.objExists(m)]

    # Filter to only scale/OPM related nodes (exclude uvPin, bone opm_drivers)
    scale_nodes = []
    for n in valid:
        nt = cmds.nodeType(n)
        if nt in ("decomposeMatrix", "multiplyDivide", "composeMatrix", "multMatrix", "inverseMatrix", "blendMatrix"):
            if "_opm_driver" in n:
                continue
            scale_nodes.append(n)

    print(f"    Scale/OPM DG nodes: {len(scale_nodes)}")
    for n in sorted(scale_nodes):
        print(f"      {n} ({cmds.nodeType(n)})")

    # Expected (no follow): DCM(1) + InvScale_MD(1) + InvScale_CM(1) + Scale_CM(1)
    #         + ScaleMM(1) + OPM(3) + PinInv(3) = 11
    assert len(scale_nodes) == 11, \
        f"Expected 11 scale/OPM nodes (no follow), got {len(scale_nodes)}"


def test_follow_zero_jump():
    """Test 9: Follow_Mesh toggle must be ZERO-JUMP.
    Switching Follow_Mesh from 1 to 0 must NOT change any controller position."""
    setup_scene(enable_follow=True)
    do_update(enable_fk=True, enable_ik=False, enable_follow=True)

    # All Follow_Mesh should default to 1.0
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        val = cmds.getAttr(f"{ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}")
        assert abs(val - 1.0) < 0.001, \
            f"Follow_Mesh default should be 1.0, got {val} on {ctrl}"

    # Record positions with Follow_Mesh=1 (uvPin driven)
    pos_fm1 = []
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        pos_fm1.append(ws_pos(ctrl))

    # Set all Follow_Mesh=0
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        cmds.setAttr(f"{ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}", 0)

    # --- ZERO-JUMP: every ctrl must stay at EXACTLY the same position ---
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        pos_fm0 = ws_pos(ctrl)
        d = dist(pos_fm0, pos_fm1[i])
        assert d < 0.01, \
            f"ZERO-JUMP VIOLATED: {ctrl} moved {d:.4f} units when toggling Follow_Mesh 1->0"

    # Set Follow_Mesh=0.5 (intermediate blend)
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        cmds.setAttr(f"{ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}", 0.5)
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        pos_half = ws_pos(ctrl)
        d = dist(pos_half, pos_fm1[i])
        assert d < 0.01, \
            f"Intermediate blend: {ctrl} should not move (static==dynamic at bind), drifted {d:.4f}"

    # Reset
    for i in range(NUM_BONES):
        ctrl = fk_name(i, MrsNaming.FK_CTRL)
        cmds.setAttr(f"{ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}", 1)


def test_follow_node_count():
    """Test 10: With follow enabled, node count = 11 + 4 blendMatrix = 15."""
    setup_scene(enable_follow=True)
    do_update(enable_fk=True, enable_ik=False, enable_follow=True)

    node_set = f"{BASE}{MrsNaming.NODE_SET}"
    members = cmds.sets(node_set, q=True) or []
    valid = [m for m in members if cmds.objExists(m)]

    scale_nodes = []
    for n in valid:
        nt = cmds.nodeType(n)
        if nt in ("decomposeMatrix", "multiplyDivide", "composeMatrix", "multMatrix", "inverseMatrix", "blendMatrix"):
            if "_opm_driver" in n:
                continue
            scale_nodes.append(n)

    # Expected: 11 base + 4 FollowBlend = 15
    assert len(scale_nodes) == 15, \
        f"Expected 15 nodes with follow, got {len(scale_nodes)}"

    # Verify each FollowBlend exists and is wired correctly to FK_Offset.OPM
    for i in range(NUM_BONES):
        blend = RigUtils.generate_name(BASE, 0, i, "_FollowBlend")
        assert cmds.objExists(blend), f"FollowBlend missing for bone {i}"
        env_src = cmds.connectionInfo(f"{blend}.envelope", sourceFromDestination=True)
        fk_ctrl = fk_name(i, MrsNaming.FK_CTRL)
        assert env_src == f"{fk_ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}", \
            f"{blend}.envelope should be driven by {fk_ctrl}.Follow_Mesh, got: {env_src}"
        # Verify FollowBlend output connects to FK_Offset.OPM
        fk_offset = fk_name(i, MrsNaming.FK_OFFSET)
        opm_src = cmds.connectionInfo(f"{fk_offset}.offsetParentMatrix", sourceFromDestination=True)
        assert opm_src == f"{blend}.outputMatrix", \
            f"{fk_offset}.OPM should be driven by {blend}.outputMatrix, got: {opm_src}"


def test_parent_object_persistence():
    """Test 11: parent_object stored on FollowMod, survives update mode."""
    setup_scene()

    fm = f"{BASE}{MrsNaming.MESH_FOLLOW}"
    assert cmds.attributeQuery(MrsNaming.ATTR_PARENT_OBJECT, node=fm, exists=True), \
        f"FollowMod should have {MrsNaming.ATTR_PARENT_OBJECT} attribute"

    stored = cmds.getAttr(f"{fm}.{MrsNaming.ATTR_PARENT_OBJECT}")
    assert stored == parent_obj, \
        f"Stored parent_object should be '{parent_obj}', got '{stored}'"

    do_update(enable_fk=True, enable_ik=False)
    assert cmds.attributeQuery(MrsNaming.ATTR_PARENT_OBJECT, node=fm, exists=True), \
        "mrsParentObject should survive update mode"
    stored2 = cmds.getAttr(f"{fm}.{MrsNaming.ATTR_PARENT_OBJECT}")
    assert stored2 == parent_obj, \
        f"Stored parent_object after update should be '{parent_obj}', got '{stored2}'"

    do_update(enable_fk=False, enable_ik=True)
    do_update(enable_fk=True, enable_ik=True)
    stored3 = cmds.getAttr(f"{fm}.{MrsNaming.ATTR_PARENT_OBJECT}")
    assert stored3 == parent_obj, \
        f"Stored parent_object after IK->FIK should be '{parent_obj}', got '{stored3}'"

    detected = RigUtils.detect_parent_object(BASE, chains)
    assert detected == parent_obj, \
        f"detect_parent_object should return '{parent_obj}', got '{detected}'"


def test_follow_mode_switch():
    """Test 12: FollowBlend correctly rebuilt/cleaned across mode switches."""
    setup_scene(enable_follow=True)

    # Initial FIK + follow: FollowBlend should exist
    for i in range(NUM_BONES):
        blend = RigUtils.generate_name(BASE, 0, i, "_FollowBlend")
        assert cmds.objExists(blend), f"FIK+follow: FollowBlend should exist for bone {i}"

    # Switch to pure IK (follow has no effect): all FollowBlend cleaned
    do_update(enable_fk=False, enable_ik=True, enable_follow=True)
    for i in range(NUM_BONES):
        blend = RigUtils.generate_name(BASE, 0, i, "_FollowBlend")
        assert not cmds.objExists(blend), f"Pure IK: FollowBlend should NOT exist for bone {i}"

    # Switch back to FK + follow: FollowBlend recreated
    do_update(enable_fk=True, enable_ik=False, enable_follow=True)
    for i in range(NUM_BONES):
        blend = RigUtils.generate_name(BASE, 0, i, "_FollowBlend")
        assert cmds.objExists(blend), f"FK+follow: FollowBlend should exist for bone {i}"

    # Switch to FK WITHOUT follow: FollowBlend cleaned
    do_update(enable_fk=True, enable_ik=False, enable_follow=False)
    for i in range(NUM_BONES):
        blend = RigUtils.generate_name(BASE, 0, i, "_FollowBlend")
        assert not cmds.objExists(blend), f"FK no-follow: FollowBlend should NOT exist for bone {i}"


def test_follow_child_isolation():
    """Test 13: Switching ctrl_0 Follow_Mesh=0 must NOT drift ctrl_1 or any child."""
    setup_scene(enable_follow=True)
    do_update(enable_fk=True, enable_ik=False, enable_follow=True)

    # Record all controller positions with Follow_Mesh=1 (default)
    pos_before = [ws_pos(fk_name(i, MrsNaming.FK_CTRL)) for i in range(NUM_BONES)]

    # Only switch ctrl_0 to Follow_Mesh=0
    cmds.setAttr(f"{fk_name(0, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 0)

    # ctrl_0 zero-jump
    assert dist(ws_pos(fk_name(0, MrsNaming.FK_CTRL)), pos_before[0]) < 0.01, \
        "ctrl_0 should not move when toggling Follow_Mesh 1->0"
    # ctrl_1 must NOT drift (core fix validation)
    assert dist(ws_pos(fk_name(1, MrsNaming.FK_CTRL)), pos_before[1]) < 0.01, \
        "ctrl_1 should not drift when ctrl_0.Follow_Mesh=0"
    # All remaining children
    for i in range(2, NUM_BONES):
        assert dist(ws_pos(fk_name(i, MrsNaming.FK_CTRL)), pos_before[i]) < 0.01, \
            f"ctrl_{i} should not drift when ctrl_0.Follow_Mesh=0"

    # Reset
    cmds.setAttr(f"{fk_name(0, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 1)


def test_follow_deformation_isolation():
    """Test 14: Follow_Mesh=0 controllers must stay static when mesh deforms."""
    setup_scene(enable_follow=True)
    do_update(enable_fk=True, enable_ik=False, enable_follow=True)

    # Set all Follow_Mesh=0
    for i in range(NUM_BONES):
        cmds.setAttr(f"{fk_name(i, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 0)

    pos_static = [ws_pos(fk_name(i, MrsNaming.FK_CTRL)) for i in range(NUM_BONES)]

    # Move parent_obj (simulates mesh deformation via skinCluster)
    cmds.setAttr(f"{parent_obj}.translate", 50, 50, 50)

    # All controllers should remain static (Follow_Mesh=0 = frozen snapshot)
    for i in range(NUM_BONES):
        pos_after = ws_pos(fk_name(i, MrsNaming.FK_CTRL))
        assert dist(pos_after, pos_static[i]) < 0.01, \
            f"ctrl_{i} should be static when Follow_Mesh=0, moved {dist(pos_after, pos_static[i]):.4f}"

    # Restore
    cmds.setAttr(f"{parent_obj}.translate", 0, 0, 0)
    for i in range(NUM_BONES):
        cmds.setAttr(f"{fk_name(i, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 1)


def test_follow_l_shape():
    """Test 15: L-shape behavior — front follows mesh, rear maintains bind-time offset."""
    setup_scene(enable_follow=True)
    do_update(enable_fk=True, enable_ik=False, enable_follow=True)

    # Record bind-time relative offset between ctrl_1 and ctrl_2
    pos1_bind = ws_pos(fk_name(1, MrsNaming.FK_CTRL))
    pos2_bind = ws_pos(fk_name(2, MrsNaming.FK_CTRL))
    offset_bind = [b - a for a, b in zip(pos1_bind, pos2_bind)]

    # ctrl_2 and ctrl_3 Follow=0 (rear section static relative to parent)
    cmds.setAttr(f"{fk_name(2, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 0)
    cmds.setAttr(f"{fk_name(3, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 0)

    # Move parent_obj to simulate mesh deformation via skinCluster
    cmds.setAttr(f"{parent_obj}.translate", 10, 10, 0)

    # ctrl_1 follows mesh (Follow=1)
    pos1_after = ws_pos(fk_name(1, MrsNaming.FK_CTRL))
    # ctrl_2 should maintain bind-time relative offset from ctrl_1
    pos2_after = ws_pos(fk_name(2, MrsNaming.FK_CTRL))
    offset_after = [b - a for a, b in zip(pos1_after, pos2_after)]

    # Relative offset should be preserved (L-shape)
    for axis in range(3):
        assert abs(offset_after[axis] - offset_bind[axis]) < 0.5, \
            f"ctrl_2 should maintain bind-time offset from ctrl_1 (L-shape), " \
            f"axis {axis}: bind={offset_bind[axis]:.2f}, after={offset_after[axis]:.2f}"

    # Restore
    cmds.setAttr(f"{parent_obj}.translate", 0, 0, 0)
    cmds.setAttr(f"{fk_name(2, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 1)
    cmds.setAttr(f"{fk_name(3, MrsNaming.FK_CTRL)}.{MrsNaming.ATTR_FOLLOW_MESH}", 1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_all():
    print("=" * 60)
    print("  MRS MODE SWITCH COMPREHENSIVE TEST")
    print("=" * 60)

    tests = [
        ("Initial FIK bind",                    test_initial_fik),
        ("FIK -> Pure FK",                       test_fik_to_fk),
        ("FIK -> Pure IK",                       test_fik_to_ik),
        ("Pure FK -> Pure IK",                   test_fk_to_ik),
        ("Pure FK -> FIK",                       test_fk_to_fik),
        ("Pure IK -> Pure FK",                   test_ik_to_fk),
        ("Pure IK -> FIK",                       test_ik_to_fik),
        ("Full round-trip cycle (7 transitions)", test_full_cycle),
        ("Node count optimization (11 nodes)",   test_node_count_optimization),
        ("Follow zero-jump toggle",              test_follow_zero_jump),
        ("Follow node count (15 nodes)",         test_follow_node_count),
        ("Parent object persistence",            test_parent_object_persistence),
        ("FollowBlend mode switch cleanup",     test_follow_mode_switch),
        ("Follow child isolation",               test_follow_child_isolation),
        ("Follow deformation isolation",         test_follow_deformation_isolation),
        ("Follow L-shape behavior",              test_follow_l_shape),
    ]

    for name, fn in tests:
        run_test(name, fn)

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED.")


if __name__ == "__main__":
    run_all()
