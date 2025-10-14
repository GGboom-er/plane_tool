import maya.cmds as cmds
import random

BASE_PATTERN_ROTATE = {
    "rotateX": {0: 0, 1: -3.281, 3: 2.988, 6: -1.475, 10: 1.008, 15: -0.883, 21: 0.566, 28: -0.216, 36: 0},
    "rotateY": {0: 0, 2: 1.082, 5: -0.318, 11: 0.914, 16: -0.242, 22: 0.319, 28: -0.151, 36: 0},
    "rotateZ": {0: 0, 4: -2.543, 7: 1.582, 11: -1.542, 17: 0.142, 23: -0.673, 28: -0.249, 36: 0},
}

BASE_PATTERN_TRANSLATE = {
    "translateX": {0: 0, 2: 1.082, 5: -0.318, 11: 0.914, 16: -0.242, 22: 0.319, 28: -0.151, 36: 0},
    "translateY": {0: 0, 1: -3.281, 3: 2.988, 6: -1.475, 10: 1.008, 15: -0.883, 21: 0.566, 28: -0.216, 36: 0},
    "translateZ": {0: 0, 4: -2.543, 7: 1.582, 11: -1.542, 17: 0.142, 23: -0.673, 28: -0.249, 36: 0},
}

def generate_scaled_pattern(base_pattern, start_frame, end_frame, strength, invert=False, selected_attrs=None, frame_offset_range=1):
    scaled_pattern = {}
    frame_range = end_frame - start_frame
    base_start = min(min(frames) for frames in base_pattern.values())
    base_end = max(max(frames) for frames in base_pattern.values())
    base_length = base_end - base_start if base_end > base_start else 1

    for attr, frames in base_pattern.items():
        if selected_attrs and attr not in selected_attrs:
            continue

        new_frames = {}
        for f, val in frames.items():
            
            v = -val if invert else val
            scaled_val = v * strength

            norm = (f - base_start) / float(base_length)
            remapped = int(start_frame + norm * frame_range)

            offset = random.randint(-frame_offset_range, frame_offset_range)
            offs_frame = remapped + offset
            offs_frame = max(start_frame, min(offs_frame, end_frame))

            new_frames[offs_frame] = scaled_val

        new_frames[start_frame] = 0.0
        new_frames[end_frame] = 0.0

        scaled_pattern[attr] = new_frames

    return scaled_pattern

def clear_keyframes(*args):
    selected_objects = cmds.ls(selection=True)
    if not selected_objects:
        cmds.warning("No objects selected!")
        return

    start_frame = cmds.playbackOptions(query=True, minTime=True)
    end_frame = cmds.playbackOptions(query=True, maxTime=True)
    for obj in selected_objects:
        cmds.cutKey(obj, clear=True, time=(start_frame, end_frame))

def generate_custom_keyframe_ui():
    if cmds.window("customKeyframeUI", exists=True):
        cmds.deleteUI("customKeyframeUI")

    window = cmds.window("customKeyframeUI", title="Dynamic Camera Shaker v3", widthHeight=(350, 600))
    form = cmds.formLayout(nd=50)

    # Header + Separator
    header = cmds.text(label="Dynamic Camera Shaker", height=20, font="boldLabelFont", align="center")
    sep1 = cmds.separator(style="in")

    # Start Frame
    start_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(80, 50),
                               columnAttach=[(1, 'right', 5), (2, 'left', 5)])
    cmds.text(label="Start Frame:")
    start_frame_field = cmds.intField(value=0)
    cmds.setParent('..')

    # End Frame
    end_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(80, 50),
                             columnAttach=[(1, 'right', 5), (2, 'left', 5)])
    cmds.text(label="End Frame:")
    end_frame_field = cmds.intField(value=36)
    cmds.setParent('..')

    # Strength Translate
    trans_strength_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(110, 120),
                                        columnAttach=[(1, 'right', 5), (2, 'left', 5)])
    cmds.text(label="Strength Translate:")
    translate_strength_slider = cmds.floatSlider(min=0.1, max=3.0, value=0.1, step=0.01, width=80)
    cmds.setParent('..')

    # Strength Rotate
    rot_strength_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(100, 120),
                                      columnAttach=[(1, 'right', 5), (2, 'left', 5)])
    cmds.text(label="Strength Rotate:")
    rotate_strength_slider = cmds.floatSlider(min=0.1, max=3.0, value=1.0, step=0.01, width=80)
    cmds.setParent('..')

    # Random Key Offset
    frame_offset_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(95, 180),
                                      columnAttach=[(1, 'right', 5), (2, 'left', 5)])
    cmds.text(label="Random Key:")
    frame_offset_slider = cmds.intSlider(min=0, max=10, value=1, step=1, width=120)
    cmds.setParent('..')

    # Invert Overshoot Direction
    invert_cb = cmds.checkBox(label="Invert Overshoot", value=False)

    # Group Checkboxes (All Translate / All Rotate)
    group_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(110, 110),
                               columnAttach=[(1, 'left', 10), (2, 'left', 10)])
    translate_all_cb = cmds.checkBox(label="All Translate", value=False)
    rotate_all_cb = cmds.checkBox(label="All Rotate", value=False)
    cmds.setParent('..')

    # Attribute Checkboxes (ทีละแกน)
    checkbox_row = cmds.columnLayout(adjustableColumn=True)
    attr_layout = cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 80), (2, 80), (3, 80)])
    attr_checks = {}
    for attr in ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ']:
        attr_checks[attr] = cmds.checkBox(label=attr, value=True)
    cmds.setParent('..')
    cmds.setParent('..')

    sep2 = cmds.separator(style="in")

    type_row = cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(100, 200),
                              columnAttach=[(1, 'right', 5), (2, 'left', 5)])
    cmds.text(label="Generate Type:")
    type_option = cmds.optionMenu(width=80)
    cmds.menuItem(label="Base Pattern")
    cmds.menuItem(label="Staggered Pattern")
    cmds.setParent('..')

    sep3 = cmds.separator(style="in")

    generate_btn = cmds.button(label="SHAKE IT!", height=20, backgroundColor=[0.2, 0.6, 0.8])
    clear_btn = cmds.button(label="CLEAR KEYS", height=20, backgroundColor=[0.8, 0.2, 0.2])
    credit_text = cmds.text(label="By N3ÜRØ", align="center", font="smallPlainLabelFont",
                            backgroundColor=(0.2, 0.2, 0.2))

    cmds.formLayout(form, edit=True,
        attachForm=[
            (header, 'top', 10), (header, 'left', 10), (header, 'right', 10),
            (sep1, 'left', 10), (sep1, 'right', 10),
            (start_row, 'left', 10), (start_row, 'right', 10),
            (end_row, 'left', 10), (end_row, 'right', 10),
            (trans_strength_row, 'left', 10), (trans_strength_row, 'right', 10),
            (rot_strength_row, 'left', 10), (rot_strength_row, 'right', 10),
            (frame_offset_row, 'left', 10), (frame_offset_row, 'right', 10),
            (invert_cb, 'left', 10), (invert_cb, 'right', 10),
            (group_row, 'left', 10), (group_row, 'right', 10),
            (checkbox_row, 'left', 10), (checkbox_row, 'right', 10),
            (sep2, 'left', 10), (sep2, 'right', 10),
            (type_row, 'left', 10), (type_row, 'right', 10),
            (sep3, 'left', 10), (sep3, 'right', 10),
            (generate_btn, 'left', 10), (generate_btn, 'right', 10),
            (clear_btn, 'left', 10), (clear_btn, 'right', 10),
            (credit_text, 'left', 10), (credit_text, 'right', 10),
        ],
        attachControl=[
            (sep1, 'top', 10, header),
            (start_row, 'top', 10, sep1),
            (end_row, 'top', 8, start_row),
            (trans_strength_row, 'top', 8, end_row),
            (rot_strength_row, 'top', 8, trans_strength_row),
            (frame_offset_row, 'top', 8, rot_strength_row),
            (invert_cb, 'top', 8, frame_offset_row),
            (group_row, 'top', 8, invert_cb),
            (checkbox_row, 'top', 8, group_row),
            (sep2, 'top', 10, checkbox_row),
            (type_row, 'top', 10, sep2),
            (sep3, 'top', 8, type_row),
            (generate_btn, 'top', 12, sep3),
            (clear_btn, 'top', 8, generate_btn),
            (credit_text, 'top', 6, clear_btn)
        ]
    )

    def sync_group_checkboxes(*args):
        t_all = cmds.checkBox(translate_all_cb, query=True, value=True)
        for axis in ['translateX', 'translateY', 'translateZ']:
            cmds.checkBox(attr_checks[axis], edit=True, value=t_all)
        r_all = cmds.checkBox(rotate_all_cb, query=True, value=True)
        for axis in ['rotateX', 'rotateY', 'rotateZ']:
            cmds.checkBox(attr_checks[axis], edit=True, value=r_all)

    def sync_individual_checkboxes(*args):
        t_vals = [cmds.checkBox(attr_checks[axis], query=True, value=True) for axis in ['translateX', 'translateY', 'translateZ']]
        cmds.checkBox(translate_all_cb, edit=True, value=all(t_vals))
        r_vals = [cmds.checkBox(attr_checks[axis], query=True, value=True) for axis in ['rotateX', 'rotateY', 'rotateZ']]
        cmds.checkBox(rotate_all_cb, edit=True, value=all(r_vals))

    cmds.checkBox(translate_all_cb, edit=True, changeCommand=sync_group_checkboxes)
    cmds.checkBox(rotate_all_cb, edit=True, changeCommand=sync_group_checkboxes)
    for axis in attr_checks:
        cmds.checkBox(attr_checks[axis], edit=True, changeCommand=sync_individual_checkboxes)

    def generate_callback(*args):
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("Select at least one object.")
            return

        start_f = cmds.intField(start_frame_field, query=True, value=True)
        end_f   = cmds.intField(end_frame_field, query=True, value=True)
        translate_strength = cmds.floatSlider(translate_strength_slider, query=True, value=True)
        rotate_strength    = cmds.floatSlider(rotate_strength_slider, query=True, value=True)
        invert    = cmds.checkBox(invert_cb, query=True, value=True)
        offset_r  = cmds.intSlider(frame_offset_slider, query=True, value=True)
        selected_attrs_list = [a for a, cb in attr_checks.items() if cmds.checkBox(cb, query=True, value=True)]
        if not selected_attrs_list:
            cmds.warning("No attribute checked!")
            return

        gen_type = cmds.optionMenu(type_option, query=True, value=True)

        for obj in sel:
            for attr in selected_attrs_list:
                try:
                    cmds.cutKey(obj, attribute=attr, time=(start_f, end_f))
                except:
                    pass
            try:
                cmds.mute(obj, force=True)
            except:
                pass

        keyframe_data = {}

        if gen_type == "Base Pattern":
            if any(a.startswith("translate") for a in selected_attrs_list):
                tdata = generate_scaled_pattern(
                    BASE_PATTERN_TRANSLATE, start_f, end_f,
                    translate_strength, invert, selected_attrs_list, offset_r
                )
                if "translateZ" in tdata:
                    for f, v in tdata["translateZ"].items():
                        tdata["translateZ"][f] = v * 0.25
                keyframe_data.update(tdata)

            if any(a.startswith("rotate") for a in selected_attrs_list):
                rdata = generate_scaled_pattern(
                    BASE_PATTERN_ROTATE, start_f, end_f,
                    rotate_strength, invert, selected_attrs_list, offset_r
                )
                keyframe_data.update(rdata)

        elif gen_type == "Staggered Pattern":
            temp_data = {}
            if any(a.startswith("translate") for a in selected_attrs_list):
                temp_data.update(generate_scaled_pattern(
                    BASE_PATTERN_TRANSLATE, start_f, end_f,
                    translate_strength, invert, selected_attrs_list, offset_r
                ))
            if any(a.startswith("rotate") for a in selected_attrs_list):
                temp_data.update(generate_scaled_pattern(
                    BASE_PATTERN_ROTATE, start_f, end_f,
                    rotate_strength, invert, selected_attrs_list, offset_r
                ))

            for attr, frames_dict in temp_data.items():
                staggered_frames = {}
                if "X" in attr:
                    axis_off = offset_r
                elif "Y" in attr:
                    axis_off = offset_r * 2
                else:  # Z
                    axis_off = offset_r * 3
                for f, val in frames_dict.items():
                    new_f = f + axis_off
                    new_f = max(start_f, min(new_f, end_f))
                    staggered_frames[new_f] = val

                if attr == "translateZ":
                    for f in list(staggered_frames.keys()):
                        staggered_frames[f] = staggered_frames[f] * 0.25

                staggered_frames[start_f] = 0.0
                staggered_frames[end_f]   = 0.0
                keyframe_data[attr] = staggered_frames

        for obj in sel:
            for attr, frames_dict in keyframe_data.items():
                for f, val in frames_dict.items():
                    cmds.setKeyframe(obj, attribute=attr, value=val, time=f)

        for obj in sel:
            try:
                cmds.mute(obj, disable=True)
            except:
                pass

        cmds.select(sel)
        cmds.currentTime(start_f)
        cmds.inViewMessage(amg=f"Generated overshoot ({gen_type}) with Z × 0.25", pos='topCenter', fade=True)

    def clear_callback(*args):
        clear_keyframes()

    cmds.button(generate_btn, edit=True, command=generate_callback)
    cmds.button(clear_btn, edit=True, command=clear_callback)

    cmds.showWindow(window)

generate_custom_keyframe_ui()
