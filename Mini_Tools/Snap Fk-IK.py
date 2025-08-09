bl_info = {
    "name": "Rigify Snap FK/IK (Default + Custom Set Bone)",
    "author": "Yanto Nugraha",
    "version": (1, 3),
    "blender": (4, 0, 0),
    "location": "View3D > Pose Mode > Rigify Snap",
    "description": "Snap FK ↔ IK on current frame for Rigify rigs or custom rigs (set bones from selection). Auto-detect L/R.",
    "category": "Animation",
}

import bpy
from mathutils import Matrix, Vector
import json

# ============================================================
#  Helper Functions
# ============================================================

def get_transform_matrix(obj, bone_name, *, space='POSE', with_constraints=True):
    bone = obj.pose.bones[bone_name]
    if with_constraints:
        return obj.convert_space(pose_bone=bone, matrix=bone.matrix,
                                 from_space='POSE', to_space=space)
    else:
        return obj.convert_space(pose_bone=bone, matrix=bone.matrix_basis,
                                 from_space='LOCAL', to_space=space)

def get_chain_transform_matrices(obj, bone_names, **options):
    return [get_transform_matrix(obj, name, **options) for name in bone_names]

def set_transform_from_matrix(obj, bone_name, matrix, *,
                              space='POSE',
                              ignore_locks=False, no_loc=False, no_rot=False, no_scale=False):
    bone = obj.pose.bones[bone_name]

    old_loc = Vector(bone.location)
    old_rot_euler = Vector(bone.rotation_euler)
    old_rot_quat = Vector(bone.rotation_quaternion)
    old_rot_axis = Vector(bone.rotation_axis_angle)
    old_scale = Vector(bone.scale)

    if space != 'LOCAL':
        matrix = obj.convert_space(pose_bone=bone, matrix=matrix,
                                   from_space=space, to_space='LOCAL')

    bone.matrix_basis = matrix

    def restore(prop, old_vec, locks, extra_lock):
        if extra_lock or (not ignore_locks and all(locks)):
            setattr(bone, prop, old_vec)
        else:
            if not ignore_locks and any(locks):
                new_vec = Vector(getattr(bone, prop))
                for i, lock in enumerate(locks):
                    if lock:
                        new_vec[i] = old_vec[i]
                setattr(bone, prop, new_vec)

    restore('location', old_loc, bone.lock_location, no_loc or bone.bone.use_connect)
    if bone.rotation_mode == 'QUATERNION':
        restore('rotation_quaternion', old_rot_quat, [False]*4, no_rot)
        bone.rotation_axis_angle = old_rot_axis
        bone.rotation_euler = old_rot_euler
    elif bone.rotation_mode == 'AXIS_ANGLE':
        bone.rotation_quaternion = old_rot_quat
        restore('rotation_axis_angle', old_rot_axis, [False]*4, no_rot)
        bone.rotation_euler = old_rot_euler
    else:
        bone.rotation_quaternion = old_rot_quat
        bone.rotation_axis_angle = old_rot_axis
        restore('rotation_euler', old_rot_euler, bone.lock_rotation, no_rot)

    restore('scale', old_scale, bone.lock_scale, no_scale)

def set_chain_transforms_from_matrices(context, obj, bone_names, matrices, **options):
    for bone, matrix in zip(bone_names, matrices):
        set_transform_from_matrix(obj, bone, matrix, **options)
        context.view_layer.update()

def check_rigify_bones_exist(obj, bone_names):
    """Check if all bones in the list exist in the armature"""
    missing_bones = [name for name in bone_names if name not in obj.pose.bones]
    return len(missing_bones) == 0, missing_bones

# ============================================================
#  Operators Snap
# ============================================================

class POSE_OT_snap_fk_to_ik_custom(bpy.types.Operator):
    """Snap FK bones to match IK"""
    bl_idname = "pose.snap_fk_to_ik_custom"
    bl_label = "Snap FK → IK"
    bl_options = {'UNDO'}

    input_bones: bpy.props.StringProperty()
    output_bones: bpy.props.StringProperty()
    is_rigify_default: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}

        input_list = json.loads(self.input_bones)
        output_list = json.loads(self.output_bones)

        # Check if bones exist (only for Rigify default mode)
        if self.is_rigify_default:
            all_exist, missing_bones = check_rigify_bones_exist(obj, input_list + output_list)
            if not all_exist:
#                self.report({'ERROR'}, f"")
                
                # Show popup message
                def draw_popup(self, context):
                    layout = self.layout
                    layout.label(text="Your rig doesn't appear to be a Rigify rig")
                    layout.label(text="or uses different bone naming.")
                    layout.label(text="Try using Custom mode (Beta) instead.")
                    
                context.window_manager.popup_menu(draw_popup, title="Rigify Bones Not Found", icon='ERROR')
                return {'CANCELLED'}

        matrices = get_chain_transform_matrices(obj, input_list)
        set_chain_transforms_from_matrices(context, obj, output_list, matrices)
        return {'FINISHED'}


class POSE_OT_snap_ik_to_fk_custom(bpy.types.Operator):
    """Snap IK controls to match FK"""
    bl_idname = "pose.snap_ik_to_fk_custom"
    bl_label = "Snap IK → FK"
    bl_options = {'UNDO'}

    fk_bones: bpy.props.StringProperty()
    ctrl_bones: bpy.props.StringProperty()
    is_rigify_default: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}

        fk_list = json.loads(self.fk_bones)
        ctrl_list = json.loads(self.ctrl_bones)

        # Check if bones exist (only for Rigify default mode)
        if self.is_rigify_default:
            all_exist, missing_bones = check_rigify_bones_exist(obj, fk_list + ctrl_list)
            if not all_exist:
#                self.report({'ERROR'}, f"Missing Rigify bones")
                
                # Show popup message
                def draw_popup(self, context):
                    layout = self.layout
                    layout.label(text="Your rig doesn't appear to be a Rigify rig")
                    layout.label(text="or uses different bone naming.")
                    layout.label(text="Try using Custom mode (Beta) instead.")
                    
                context.window_manager.popup_menu(draw_popup, title="Rigify Bones Not Found", icon='ERROR')
                return {'CANCELLED'}

        matrices = get_chain_transform_matrices(obj, fk_list)
        set_chain_transforms_from_matrices(context, obj, ctrl_list, matrices)
        return {'FINISHED'}

# ============================================================
#  Operator Set From Selected
# ============================================================

class POSE_OT_set_custom_bone(bpy.types.Operator):
    """Set this bone slot from the active selected bone"""
    bl_idname = "pose.set_custom_bone"
    bl_label = "Set from Selected"

    slot_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Must select an armature")
            return {'CANCELLED'}

        bone = context.active_pose_bone
        if not bone:
            self.report({'ERROR'}, "No bone selected")
            return {'CANCELLED'}

        setattr(context.scene, self.slot_name, bone.name)
        self.report({'INFO'}, f"Set {self.slot_name} to '{bone.name}'")
        return {'FINISHED'}

# ============================================================
#  Panel
# ============================================================

class VIEW3D_PT_rigify_snap_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Raha_Tools'
    bl_label = 'Snap FK/IK'

    bpy.types.Scene.snap_mode = bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('DEFAULT', "Rigify Default", ""),
            ('CUSTOM', "Custom (Beta)", "")
        ],
        default='DEFAULT'
    )

    # Custom slots
    bpy.types.Scene.custom_fk_upper = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_fk_forearm = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_fk_hand = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_ik_upper = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_ik_pole = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_ik_hand = bpy.props.StringProperty(default="")

    @classmethod
    def poll(self, context):
        # Panel selalu muncul, tapi hanya aktif kalau ada armature
        return context.active_object is not None

    def draw_setter(self, layout, label, slot_name, value):
        row = layout.row(align=True)
        row.label(text=f"{label}: {value if value else '(Not set)'}")
        op = row.operator("pose.set_custom_bone", text="", icon="RESTRICT_SELECT_OFF")
        op.slot_name = slot_name

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object

        layout.prop(scene, "snap_mode", expand=True)

        if scene.snap_mode == 'DEFAULT':
            # Deteksi otomatis L/R dari bone aktif
            suffix = '.L'  # default
            active_bone = context.active_pose_bone
            if active_bone:
                if active_bone.name.endswith('.R'):
                    suffix = '.R'
                elif active_bone.name.endswith('.L'):
                    suffix = '.L'

            row = layout.row(align=True)
            op = row.operator("pose.snap_fk_to_ik_custom", text=f"FK→IK (Hand{suffix})")
            op.input_bones = json.dumps([
                f"upper_arm_ik{suffix}",
                f"MCH-forearm_ik{suffix}",
                f"MCH-upper_arm_ik_target{suffix}"
            ])
            op.output_bones = json.dumps([
                f"upper_arm_fk{suffix}",
                f"forearm_fk{suffix}",
                f"hand_fk{suffix}"
            ])
            op.is_rigify_default = True

            op2 = row.operator("pose.snap_ik_to_fk_custom", text=f"IK→FK (Hand{suffix})")
            op2.fk_bones = json.dumps([
                f"upper_arm_fk{suffix}",
                f"forearm_fk{suffix}",
                f"hand_fk{suffix}"
            ])
            op2.ctrl_bones = json.dumps([
                f"upper_arm_ik{suffix}",
                f"upper_arm_ik_target{suffix}",
                f"hand_ik{suffix}"
            ])
            op2.is_rigify_default = True

        else:
            box = layout.box()
            box.label(text="FK Bones:")
            self.draw_setter(box, "Upper Arm", "custom_fk_upper", scene.custom_fk_upper)
            self.draw_setter(box, "Forearm", "custom_fk_forearm", scene.custom_fk_forearm)
            self.draw_setter(box, "Hand", "custom_fk_hand", scene.custom_fk_hand)

            box.label(text="IK Bones:")
            self.draw_setter(box, "Upper Arm", "custom_ik_upper", scene.custom_ik_upper)
            self.draw_setter(box, "Pole", "custom_ik_pole", scene.custom_ik_pole)
            self.draw_setter(box, "Hand", "custom_ik_hand", scene.custom_ik_hand)

            row = layout.row(align=True)
            op = row.operator("pose.snap_fk_to_ik_custom", text="FK→IK (Custom)")
            op.input_bones = json.dumps([scene.custom_ik_upper, scene.custom_ik_pole, scene.custom_ik_hand])
            op.output_bones = json.dumps([scene.custom_fk_upper, scene.custom_fk_forearm, scene.custom_fk_hand])
            op.is_rigify_default = False

            op2 = row.operator("pose.snap_ik_to_fk_custom", text="IK→FK (Custom)")
            op2.fk_bones = json.dumps([scene.custom_fk_upper, scene.custom_fk_forearm, scene.custom_fk_hand])
            op2.ctrl_bones = json.dumps([scene.custom_ik_upper, scene.custom_ik_pole, scene.custom_ik_hand])
            op2.is_rigify_default = False

# ============================================================
#  Register
# ============================================================

classes = (
    POSE_OT_snap_fk_to_ik_custom,
    POSE_OT_snap_ik_to_fk_custom,
    POSE_OT_set_custom_bone,
#    VIEW3D_PT_rigify_snap_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.snap_mode
    del bpy.types.Scene.custom_fk_upper
    del bpy.types.Scene.custom_fk_forearm
    del bpy.types.Scene.custom_fk_hand
    del bpy.types.Scene.custom_ik_upper
    del bpy.types.Scene.custom_ik_pole
    del bpy.types.Scene.custom_ik_hand

if __name__ == "__main__":
    register()
