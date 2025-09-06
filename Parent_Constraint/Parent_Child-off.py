import bpy
from bpy.props import StringProperty


# =========================
# Helper Functions
# =========================

def get_childof_constraint_by_name(pbone_or_obj, name):
    """Cari constraint Child Of sesuai nama di PoseBone atau Object."""
    if not pbone_or_obj or not hasattr(pbone_or_obj, "constraints"):
        return None
    for c in pbone_or_obj.constraints:
        if c.type == 'CHILD_OF' and c.name == name:
            return c
    return None

def get_constraint(context, cname):
    """Cari constraint Child Of dari pose bone atau object aktif sesuai nama."""
    obj = context.object
    if context.mode == "POSE" and context.active_pose_bone:
        return get_childof_constraint_by_name(context.active_pose_bone, cname)
    elif obj and obj.type != "ARMATURE":
        return get_childof_constraint_by_name(obj, cname)
    return None

def get_constraint(context, constraint_name):
    obj = context.object
    if obj is None:
        return None
    
    # Kalau pose bone dipilih
    if context.mode == 'POSE':
        bone = context.active_pose_bone
        if bone:
            return bone.constraints.get(constraint_name)
    
    # Kalau object biasa
    return obj.constraints.get(constraint_name)


# ========================================= ENABLE =============================================================
def get_previous_keyframe(bone, current_frame):
    """
    Mencari keyframe sebelumnya dari tulang (bone) yang sedang dipilih.
    """
    if not bpy.context.object or not bpy.context.object.animation_data or not bpy.context.object.animation_data.action:
        return None
    keyframes = [int(kp.co.x) for fcurve in bpy.context.object.animation_data.action.fcurves 
                 if fcurve.data_path.startswith(f'pose.bones["{bone.name}"].')
                 for kp in fcurve.keyframe_points]
    keyframes = sorted(set(keyframes))
    prev_key = max([kf for kf in keyframes if kf < current_frame], default=None)
    return prev_key

def copy_paste_keyframes():
    """
    Menyalin keyframe dari frame sebelumnya dan menempelkannya ke frame berikutnya.
    Termasuk lokasi, rotasi (Euler dan Quaternion), serta nilai influence dari constraint "parent_child".
    """
    obj = bpy.context.object
    bone = bpy.context.active_pose_bone
    current_frame = int(bpy.context.scene.frame_current)
    
    if not obj or not bone:
        return
    
    # Periksa apakah objek memiliki data animasi
    anim_data = obj.animation_data
    if not anim_data or not anim_data.action:
        return
    
    # Cari keyframe sebelumnya
    prev_keyframe = get_previous_keyframe(bone, current_frame)
    if prev_keyframe is None:
        return
    
    prev_frame = int(prev_keyframe - 1)
    
    # Set keyframe di frame sekarang
    bpy.context.scene.frame_set(current_frame)
    bone.keyframe_insert(data_path="location")
    bone.keyframe_insert(data_path="rotation_quaternion")
    bone.keyframe_insert(data_path="rotation_euler")
    
    # Simpan nilai influence dari semua constraint yang sesuai
    influence_values = {constraint.name: constraint.influence for constraint in bone.constraints if constraint.name.startswith("parent_child")}
    for constraint in bone.constraints:
        if constraint.name.startswith("parent_child"):
            constraint.influence = 0
            constraint.keyframe_insert(data_path="influence")

    # Copy keyframe dari prev_frame
    bpy.context.scene.frame_set(prev_frame)
    loc = bone.location.copy()
    rot_euler = bone.rotation_euler.copy()
    rot_quat = bone.rotation_quaternion.copy()
    
    # Paste keyframe di frame +1
    bpy.context.scene.frame_set(current_frame + 1)
    bone.location = loc
    bone.rotation_euler = rot_euler
    bone.rotation_quaternion = rot_quat
    
    # Set influence menjadi 1 sebelum menyisipkan keyframe
    for constraint in bone.constraints:
        if constraint.name.startswith("parent_child"):
            constraint.influence = 1
            constraint.keyframe_insert(data_path="influence")
    
    # Masukkan keyframe untuk transformasi bone
    bone.keyframe_insert(data_path="location")
    bone.keyframe_insert(data_path="rotation_quaternion")
    bone.keyframe_insert(data_path="rotation_euler")


class OBJECT_OT_ENABLE(bpy.types.Operator):
    """
    Operator Blender untuk menyalin keyframe dari frame sebelumnya
    dan menempelkannya ke frame berikutnya.
    """
    bl_idname = "object.enable"
    bl_label = "enable-child-off"
    bl_description = "Copy keyframe from previous frame and paste it to the next frame"
    
    def execute(self, context):
        copy_paste_keyframes()
        return {'FINISHED'}

# ===================================================== DISABLE =======================================================

def disable_constraint(obj, const, frame):
    if isinstance(obj, bpy.types.PoseBone):
        matrix_final = obj.matrix
    else:
        matrix_final = obj.matrix_world

    insert_keyframe(obj, frame=frame - 1)
    insert_keyframe_constraint(const, frame=frame - 1)

    const.influence = 0
    if isinstance(obj, bpy.types.PoseBone):
        obj.matrix = matrix_final
    else:
        obj.matrix_world = matrix_final

    insert_keyframe(obj, frame=frame)
    insert_keyframe_constraint(const, frame=frame)
    return

def get_rotation_mode(obj):
    if obj.rotation_mode in ("euler", "AXIS_ANGLE"):
        return obj.rotation_mode.lower()
    return "euler"

def get_selected_objects(context):
    if context.mode not in ("OBJECT", "POSE"):
        return

    if context.mode == "OBJECT":
        active = context.active_object
        selected = [obj for obj in context.selected_objects if obj != active]

    if context.mode == "POSE":
        active = context.active_pose_bone
        selected = [bone for bone in context.selected_pose_bones if bone != active]

    selected.append(active)
    return selected

def get_last_raha_parent_constraint(obj):
    if not obj.constraints:
        return
    const = obj.constraints[-1]
    if const.name.startswith("parent_child") and const.influence == 1:
        return const

def insert_keyframe(obj, frame):
    try:
        if isinstance(obj, bpy.types.PoseBone):
            arm = obj.id_data
            arm.keyframe_insert(data_path='pose.bones["' + obj.name + '"].location', frame=frame)
            if obj.rotation_mode == "QUATERNION":
                arm.keyframe_insert(data_path='pose.bones["' + obj.name + '"].rotation_quaternion', frame=frame)
            elif obj.rotation_mode == "AXIS_ANGLE":
                arm.keyframe_insert(data_path='pose.bones["' + obj.name + '"].rotation_axis_angle', frame=frame)
            else:
                arm.keyframe_insert(data_path='pose.bones["' + obj.name + '"].rotation_euler', frame=frame)
            arm.keyframe_insert(data_path='pose.bones["' + obj.name + '"].scale', frame=frame)
        else:
            obj.keyframe_insert(data_path="location", frame=frame)
            if obj.rotation_mode == "QUATERNION":
                obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            elif obj.rotation_mode == "AXIS_ANGLE":
                obj.keyframe_insert(data_path="rotation_axis_angle", frame=frame)
            else:
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            obj.keyframe_insert(data_path="scale", frame=frame)
    except Exception:
        try:
            obj.keyframe_insert(data_path="location", frame=frame)
        except Exception:
            pass

def insert_keyframe_constraint(constraint, frame):
    try:
        constraint.keyframe_insert(data_path="influence", frame=frame)
    except Exception:
        pass

def dp_keyframe_insert_obj(obj):
    obj.keyframe_insert(data_path="location")
    if obj.rotation_mode == "QUATERNION":
        obj.keyframe_insert(data_path="rotation_quaternion")
    elif obj.rotation_mode == "AXIS_ANGLE":
        obj.keyframe_insert(data_path="rotation_axis_angle")
    else:
        obj.keyframe_insert(data_path="rotation_euler")
    obj.keyframe_insert(data_path="scale")

def dp_keyframe_insert_pbone(arm, pbone):
    arm.keyframe_insert(data_path='pose.bones["' + pbone.name + '"].location')
    if pbone.rotation_mode == "QUATERNION":
        arm.keyframe_insert(data_path='pose.bones["' + pbone.name + '"].rotation_quaternion')
    elif pbone.rotation_mode == "AXIS_ANGLE":
        arm.keyframe_insert(data_path='pose.bones["' + pbone.name + '"].rotation_axis_angle')
    else:
        arm.keyframe_insert(data_path='pose.bones["' + pbone.name + '"].rotation_euler')
    arm.keyframe_insert(data_path='pose.bones["' + pbone.name + '"].scale')

def dp_create_raha_parent_obj(op):
    obj = bpy.context.active_object
    scn = bpy.context.scene
    list_selected_obj = bpy.context.selected_objects

    if len(list_selected_obj) == 2:
        i = list_selected_obj.index(obj)
        list_selected_obj.pop(i)
        parent_obj = list_selected_obj[0]

        dp_keyframe_insert_obj(obj)
        bpy.ops.object.constraint_add_with_targets(type="CHILD_OF")
        last_constraint = obj.constraints[-1]

        if parent_obj.type == "ARMATURE":
            last_constraint.subtarget = parent_obj.data.bones.active.name
            last_constraint.name = "parent_child" + last_constraint.target.name + "." + last_constraint.subtarget
        else:
            last_constraint.name = "parent_child" + last_constraint.target.name

        C = bpy.context.copy()
        C["constraint"] = last_constraint
        bpy.ops.constraint.childof_set_inverse(constraint=last_constraint.name, owner="OBJECT")

        current_frame = scn.frame_current
        scn.frame_current = current_frame - 1
        obj.constraints[last_constraint.name].influence = 0
        obj.keyframe_insert(data_path='constraints["' + last_constraint.name + '"].influence')

        scn.frame_current = current_frame
        obj.constraints[last_constraint.name].influence = 1
        obj.keyframe_insert(data_path='constraints["' + last_constraint.name + '"].influence')

        for ob in list_selected_obj:
            ob.select_set(False)
        obj.select_set(True)
        
        op.report({'INFO'}, 
                  f"Parent successfully created")        
        
    else:
        op.report({"ERROR"}, "Two objects must be selected")


def dp_create_raha_parent_pbone(op):
    """
    Buat Child Of constraint antara bone aktif (parent) dan bone terpilih lain (child).
    Harus bekerja benar untuk:
    1. Jika hanya 1 armature yang dipose mode → subtarget benar.
    2. Jika beberapa armature dipose mode → tetap subtarget benar sesuai bone aktif.
    """

    # pastikan ada context aktif
    obj = bpy.context.active_object
    if not obj or obj.type != 'ARMATURE' or bpy.context.mode != 'POSE':
        op.report({'WARNING'}, "Aktifkan armature dalam Pose Mode.")
        return {'CANCELLED'}

    active_pbone = bpy.context.active_pose_bone
    if not active_pbone:
        op.report({'WARNING'}, "Tidak ada bone aktif.")
        return {'CANCELLED'}

    selected_pbones = [pb for pb in bpy.context.selected_pose_bones if pb != active_pbone]
    if not selected_pbones:
        op.report({'WARNING'}, "Pilih minimal 1 bone lain selain active bone.")
        return {'CANCELLED'}

    # parent = bone aktif
    parent_obj = obj
    parent_bone = active_pbone.name

    for child_pbone in selected_pbones:
        child_obj = child_pbone.id_data  # armature object si child
        child_name = child_pbone.name

        # cek apakah constraint sudah ada
        cname = f"RAHAparent_{parent_obj.name}_{parent_bone}"
        cons = child_pbone.constraints.get(cname)
        if not cons:
            cons = child_pbone.constraints.new('CHILD_OF')
            cons.name = cname

        # set target dengan benar
        cons.target = parent_obj
        cons.subtarget = parent_bone

        # refresh matrix agar konsisten
        bpy.context.view_layer.update()

    # info print
    op.report({'INFO'}, 
              f"Parent successfully created")


    return {'FINISHED'}




def dp_clear(obj, pbone):
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return
    dp_curves = []
    dp_keys = []
    for fcurve in obj.animation_data.action.fcurves:
        if "constraints" in fcurve.data_path and "parent_child" in fcurve.data_path:
            dp_curves.append(fcurve)

    for f in dp_curves:
        for key in f.keyframe_points:
            dp_keys.append(key.co[0])

    dp_keys = list(set(dp_keys))
    dp_keys.sort()

    for fcurve in obj.animation_data.action.fcurves[:]:
        if fcurve.data_path.startswith("constraints") and "parent_child" in fcurve.data_path:
            try:
                obj.animation_data.action.fcurves.remove(fcurve)
            except Exception:
                pass
        else:
            for frame in dp_keys:
                for key in fcurve.keyframe_points[:]:
                    if key.co[0] == frame:
                        fcurve.keyframe_points.remove(key)
            if not fcurve.keyframe_points:
                try:
                    obj.animation_data.action.fcurves.remove(fcurve)
                except Exception:
                    pass

# ============================================================== CREATE ===============================================

class raha_parent_OT_create(bpy.types.Operator):
    """Create a new animated Child Of constraint"""
    bl_idname = "raha_parent.create"
    bl_label = "Create Constraint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        frame = context.scene.frame_current

        if obj.type == "ARMATURE":
            if obj.mode != "POSE":
                self.report({"ERROR"}, "Armature objects must be in Pose mode.")
                return {"CANCELLED"}
            obj = bpy.context.active_pose_bone
            const = get_last_raha_parent_constraint(obj)
            if const:
                disable_constraint(obj, const, frame)
            dp_create_raha_parent_pbone(self)
        else:
            const = get_last_raha_parent_constraint(obj)
            if const:
                disable_constraint(obj, const, frame)
            dp_create_raha_parent_obj(self)

        return {"FINISHED"}

# ====================================================== CLEAR ========================================================

class raha_parent_OT_clear(bpy.types.Operator):
    """Clear Raha Parent constraints"""
    bl_idname = "raha_parent.clear"
    bl_label = "Clear Raha Parent"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        pbone = None

        # Kalau yang aktif armature + pose mode + ada bone aktif
        if obj and obj.type == "ARMATURE" and context.mode == 'POSE':
            pbone = context.active_pose_bone

        dp_clear(obj, pbone)
        return {"FINISHED"}

    
class CHILD_OT_insert_influence_keyframe(bpy.types.Operator):
    """Insert keyframe for influence of this constraint"""
    bl_idname = "childof.insert_influence_key"
    bl_label = "Insert Keyframe Influence"
    bl_options = {"REGISTER", "UNDO"}

    constraint_name: bpy.props.StringProperty()

    def execute(self, context):
        cname = (self.constraint_name or "").strip()
        if not cname:
            self.report({'ERROR'}, "Constraint name is empty.")
            return {'CANCELLED'}

        # ===== Pose Mode =====
        if context.mode == "POSE" and context.active_pose_bone:
            bone = context.active_pose_bone
            const = bone.constraints.get(cname)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on active bone.')
                return {'CANCELLED'}
            const.keyframe_insert(data_path="influence")
            self.report({'INFO'}, f"Keyframe inserted for {const.name} (Bone)")
            return {'FINISHED'}

        # ===== Object Mode =====
        elif context.mode == "OBJECT" and context.object:
            obj = context.object
            const = obj.constraints.get(cname)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on active object.')
                return {'CANCELLED'}
            const.keyframe_insert(data_path="influence")
            self.report({'INFO'}, f"Keyframe inserted for {const.name} (Object)")
            return {'FINISHED'}

        else:
            self.report({'ERROR'}, "No active bone or object selected.")
            return {'CANCELLED'}


# ========================================================================================================================
# ======================================== CHILD OFF ===========================================

def get_parent_child_constraints(bone):
    return [c for c in bone.constraints if c.type == 'CHILD_OF' and c.name.startswith("parent_child")]

def get_childof_constraint_by_name(bone, cname):
    for constraint in bone.constraints:
        if constraint.type == 'CHILD_OF' and constraint.name == cname and constraint.name.startswith("parent_child"):
            return constraint
    return None

class RAHA_OT_apply_constraint(bpy.types.Operator):
    bl_idname = "raha.apply_constraint_single"
    bl_label = "Apply Child-Of (single)"
    bl_options = {"REGISTER", "UNDO"}

    constraint_name: bpy.props.StringProperty()

    def _find_childof_constraint(self, owner, cname):
        """Cari CHILD_OF constraint yang namanya cocok atau diawali cname."""
        if not cname:
            return None
        for c in owner.constraints:
            if c.type == 'CHILD_OF' and (c.name == cname or c.name.startswith(cname)):
                return c
        return None

    def _insert_keys(self, target, frame):
        """Insert keyframe sesuai rotation_mode + loc/scale."""
        target.keyframe_insert(data_path="location", frame=frame)
        if target.rotation_mode == 'QUATERNION':
            target.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        elif target.rotation_mode == 'AXIS_ANGLE':
            target.keyframe_insert(data_path="rotation_axis_angle", frame=frame)
        else:  # Euler (XYZ, ZYX, dll)
            target.keyframe_insert(data_path="rotation_euler", frame=frame)
        target.keyframe_insert(data_path="scale", frame=frame)

    def execute(self, context):
        cname = (self.constraint_name or "").strip()
        if not cname:
            self.report({'ERROR'}, "Constraint name is empty.")
            return {'CANCELLED'}

        auto_key = context.scene.tool_settings.use_keyframe_insert_auto
        frame = context.scene.frame_current

        # POSE MODE
        if context.mode == "POSE" and context.active_pose_bone:
            bone = context.active_pose_bone
            const = self._find_childof_constraint(bone, cname)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on bone.')
                return {'CANCELLED'}

            arm = context.object
            mat = bone.matrix.copy()
            bone.constraints.remove(const)
            bone.matrix = mat
            arm.update_tag(refresh={'DATA'})
            context.view_layer.update()

            if auto_key:
                self._insert_keys(bone, frame)

            self.report({'INFO'}, f'Apply constraint succes".')
            print(f'[RahaTools] Apply constraint "{cname}" on bone "{bone.name}" at frame {frame}')

        # OBJECT MODE
        elif context.mode == "OBJECT" and context.object:
            obj = context.object
            const = self._find_childof_constraint(obj, cname)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on object.')
                return {'CANCELLED'}

            mat = obj.matrix_world.copy()
            obj.constraints.remove(const)
            obj.matrix_world = mat
            context.view_layer.update()

            if auto_key:
                self._insert_keys(obj, frame)

            self.report({'INFO'}, f'Apply constraint succes.')
            print(f'[RahaTools] Apply constraint "{cname}" on object "{obj.name}" at frame {frame}')

        else:
            self.report({'ERROR'}, "No active bone or object selected.")
            return {'CANCELLED'}

        return {'FINISHED'}


class RAHA_OT_set_inverse(bpy.types.Operator):
    bl_idname = "raha.set_inverse_single"
    bl_label = "Set Inverse (single)"
    constraint_name: StringProperty()

    def execute(self, context):
        cname = (self.constraint_name or "").strip()

        if context.mode == "POSE" and context.active_pose_bone:
            # Pose bone
            bone = context.active_pose_bone
            const = get_childof_constraint_by_name(bone, cname)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on bone.')
                return {'CANCELLED'}
            try:
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.constraint.childof_set_inverse(constraint=cname, owner='BONE')
            except Exception:
                self.report({'WARNING'}, "Set inverse failed for bone.")
                return {'CANCELLED'}

        elif context.mode == "OBJECT" and context.object:
            # Object
            obj = context.object
            const = next((c for c in obj.constraints if c.type=='CHILD_OF' and c.name==cname), None)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on object.')
                return {'CANCELLED'}
            try:
                bpy.ops.constraint.childof_set_inverse(constraint=cname, owner='OBJECT')
            except Exception:
                self.report({'WARNING'}, "Set inverse failed for object.")
                return {'CANCELLED'}

        else:
            self.report({'ERROR'}, "No active bone or object selected.")
            return {'CANCELLED'}

        return {'FINISHED'}


class RAHA_OT_clear_inverse(bpy.types.Operator):
    bl_idname = "raha.clear_inverse_single"
    bl_label = "Clear Inverse (single)"
    constraint_name: StringProperty()

    def execute(self, context):
        cname = (self.constraint_name or "").strip()

        if context.mode == "POSE" and context.active_pose_bone:
            # Pose bone
            bone = context.active_pose_bone
            const = get_childof_constraint_by_name(bone, cname)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on bone.')
                return {'CANCELLED'}
            try:
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.constraint.childof_clear_inverse(constraint=cname, owner='BONE')
            except Exception:
                self.report({'WARNING'}, "Clear inverse failed for bone.")
                return {'CANCELLED'}

        elif context.mode == "OBJECT" and context.object:
            # Object
            obj = context.object
            const = next((c for c in obj.constraints if c.type=='CHILD_OF' and c.name==cname), None)
            if not const:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on object.')
                return {'CANCELLED'}
            try:
                bpy.ops.constraint.childof_clear_inverse(constraint=cname, owner='OBJECT')
            except Exception:
                self.report({'WARNING'}, "Clear inverse failed for object.")
                return {'CANCELLED'}

        else:
            self.report({'ERROR'}, "No active bone or object selected.")
            return {'CANCELLED'}

        return {'FINISHED'}


class RAHA_OT_delete_constraint(bpy.types.Operator):
    """Delete Child-Of constraint (single)"""
    bl_idname = "raha.delete_constraint_single"
    bl_label = "Delete Child-Of (single)"
    bl_options = {"REGISTER", "UNDO"}

    constraint_name: bpy.props.StringProperty()

    def execute(self, context):
        cname = (self.constraint_name or "").strip()
        if not cname:
            self.report({'ERROR'}, "Constraint name is empty.")
            return {'CANCELLED'}

        # Pose Mode (bone)
        if context.mode == "POSE" and context.active_pose_bone:
            bone = context.active_pose_bone
            const = bone.constraints.get(cname)
            if const:
                bone.constraints.remove(const)
                self.report({'INFO'}, f'Deleted constraint "{cname}" from bone.')
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on active bone.')
                return {'CANCELLED'}

        # Object Mode
        elif context.mode == "OBJECT" and context.object:
            obj = context.object
            const = obj.constraints.get(cname)
            if const:
                obj.constraints.remove(const)
                self.report({'INFO'}, f'Deleted constraint "{cname}" from object.')
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, f'Constraint "{cname}" not found on active object.')
                return {'CANCELLED'}

        else:
            self.report({'ERROR'}, "No active bone or object selected.")
            return {'CANCELLED'}


class RAHA_OT_enable_constraint(bpy.types.Operator):
    bl_idname = "raha.enable_constraint_single"
    bl_label = "Enable (single)"
    bl_description = "Enable Constraint: ON Parent"    
    bl_options = {"REGISTER", "UNDO"}

    constraint_name: StringProperty()

    def _find_constraint_global(self, cname, context):
        """Cari constraint bernama cname di:
           - active pose bone, semua pose bones di active armature, atau semua armature di scene (BONE)
           - active object, atau semua objects di scene (OBJECT)
           Kembalikan (constraint, owner, owner_type, armature_object_if_bone)
        """
        # POSE-first (search within active armature first)
        try:
            if context.mode == 'POSE':
                arm = context.object
                if arm and arm.type == 'ARMATURE':
                    # aktif bone
                    active_pb = context.active_pose_bone
                    if active_pb:
                        c = active_pb.constraints.get(cname)
                        if c:
                            return c, active_pb, 'BONE', arm
                    # search this armature's pose bones
                    for pb in arm.pose.bones:
                        c = pb.constraints.get(cname)
                        if c:
                            return c, pb, 'BONE', arm
                # fallback: search all armatures in scene
                for ob in bpy.data.objects:
                    if ob.type == 'ARMATURE':
                        for pb in ob.pose.bones:
                            c = pb.constraints.get(cname)
                            if c:
                                return c, pb, 'BONE', ob
        except Exception:
            pass

        # OBJECT mode / general object search
        try:
            obj = context.object
            if obj:
                c = obj.constraints.get(cname)
                if c:
                    return c, obj, 'OBJECT', obj
            # fallback: search all objects
            for ob in bpy.data.objects:
                c = ob.constraints.get(cname)
                if c:
                    return c, ob, 'OBJECT', ob
        except Exception:
            pass

        return None, None, None, None

    def execute(self, context):
        cname = (self.constraint_name or "").strip()
        if not cname:
            self.report({'ERROR'}, "Constraint name is empty.")
            return {'CANCELLED'}

        # simpan keadaan awal supaya bisa restore
        orig_active = context.object
        orig_mode = context.mode

        const, owner, otype, arm_obj = self._find_constraint_global(cname, context)
        if not const:
            self.report({'WARNING'}, f'Constraint \"{cname}\" not found.')
            return {'CANCELLED'}

        frame = context.scene.frame_current

        # POSE OWNER (PoseBone)
        if otype == 'BONE' and isinstance(owner, bpy.types.PoseBone):
            bone = owner
            arm = arm_obj  # armature object where bone lives
            # simpan world matrix bone sebelum perubahan
            try:
                prev_matrix_world = (arm.matrix_world @ bone.matrix).copy()
            except Exception:
                prev_matrix_world = None

            insert_keyframe(bone, frame=frame - 1)
            insert_keyframe_constraint(const, frame=frame - 1)

            const.influence = 1.0
            context.view_layer.update()

            # pastikan armature itu aktif & di Pose mode sebelum set inverse
            try:
                if context.object != arm:
                    bpy.context.view_layer.objects.active = arm
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.constraint.childof_set_inverse(constraint=const.name, owner='BONE')
            except Exception:
                # jangan crash kalau operator gagal
                pass

            # restore transform supaya tidak lompat
            try:
                if prev_matrix_world is not None:
                    bone.matrix = arm.matrix_world.inverted() @ prev_matrix_world
            except Exception:
                pass

            insert_keyframe(bone, frame=frame)
            insert_keyframe_constraint(const, frame=frame)

            # restore original active / mode
            try:
                if orig_active and orig_active != arm:
                    bpy.context.view_layer.objects.active = orig_active
                    bpy.ops.object.mode_set(mode=orig_mode)
            except Exception:
                pass

            return {'FINISHED'}

        # OBJECT OWNER
        elif otype == 'OBJECT' and isinstance(owner, bpy.types.Object):
            obj = owner
            try:
                prev_matrix = obj.matrix_world.copy()
            except Exception:
                prev_matrix = None

            insert_keyframe(obj, frame=frame - 1)
            insert_keyframe_constraint(const, frame=frame - 1)

            const.influence = 1.0
            context.view_layer.update()

            try:
                if context.object != obj:
                    bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.constraint.childof_set_inverse(constraint=const.name, owner='OBJECT')
            except Exception:
                pass

            try:
                if prev_matrix is not None:
                    obj.matrix_world = prev_matrix
            except Exception:
                pass

            insert_keyframe(obj, frame=frame)
            insert_keyframe_constraint(const, frame=frame)

            try:
                if orig_active and orig_active != obj:
                    bpy.context.view_layer.objects.active = orig_active
                    bpy.ops.object.mode_set(mode=orig_mode)
            except Exception:
                pass

            return {'FINISHED'}

        else:
            self.report({'ERROR'}, "Found constraint but owner type unknown.")
            return {'CANCELLED'}


class RAHA_OT_disable_constraint(bpy.types.Operator):
    bl_idname = "raha_parent.disable"
    bl_label = "Disable Constraint"
    bl_description = "Disable Constraint: Off Parent"    
    bl_options = {"REGISTER", "UNDO"}
    

    constraint_name: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return context.mode in ("OBJECT", "POSE")

    def _find_constraint_global(self, cname, context):
        # reuse same search logic sebagai enable
        try:
            if context.mode == 'POSE':
                arm = context.object
                if arm and arm.type == 'ARMATURE':
                    active_pb = context.active_pose_bone
                    if active_pb:
                        c = active_pb.constraints.get(cname)
                        if c:
                            return c, active_pb, 'BONE', arm
                    for pb in arm.pose.bones:
                        c = pb.constraints.get(cname)
                        if c:
                            return c, pb, 'BONE', arm
                for ob in bpy.data.objects:
                    if ob.type == 'ARMATURE':
                        for pb in ob.pose.bones:
                            c = pb.constraints.get(cname)
                            if c:
                                return c, pb, 'BONE', ob
        except Exception:
            pass

        try:
            obj = context.object
            if obj:
                c = obj.constraints.get(cname)
                if c:
                    return c, obj, 'OBJECT', obj
            for ob in bpy.data.objects:
                c = ob.constraints.get(cname)
                if c:
                    return c, ob, 'OBJECT', ob
        except Exception:
            pass

        return None, None, None, None

    def execute(self, context):
        frame = context.scene.frame_current
        cname = (self.constraint_name or "").strip()

        # SINGLE named constraint path
        if cname:
            const, owner, otype, arm_obj = self._find_constraint_global(cname, context)
            if not const:
                self.report({"WARNING"}, f'Constraint "{cname}" not found.')
                return {"CANCELLED"}
            disable_constraint(owner, const, frame)
            self.report({"INFO"}, f'Disabled \"{const.name}\".')
            return {"FINISHED"}

        # LEGACY/BATCH path (ketika tidak ada nama diberikan)
        objects = get_selected_objects(context)
        if not objects:
            self.report({"ERROR"}, "Nothing selected.")
            return {"CANCELLED"}

        counter = 0
        for obj in objects:
            # cari CHILD_OF terakhir pada owner (dukungan untuk PoseBone & Object)
            last = None
            try:
                for c in reversed(obj.constraints):
                    if c.type == 'CHILD_OF' and (c.name.startswith("parent_child") or c.name.startswith("RAHAparent_")):
                        last = c
                        break
            except Exception:
                last = None

            if last is None:
                continue
            disable_constraint(obj, last, frame)
            counter += 1

        self.report({"INFO"}, f"{counter} constraints were disabled.")
        return {"FINISHED"}


class RAHA_OT_clear_constraint_keys(bpy.types.Operator):
    bl_idname = "raha.clear_constraint_keys"
    bl_label = "Clear Keys (Parent)"
    bl_description = "Delet All keyframe Influence Only"    
    constraint_name: StringProperty()

    def execute(self, context):
        ob = context.object
        if not ob or not ob.animation_data or not ob.animation_data.action:
            return {'CANCELLED'}

        action = ob.animation_data.action

        # Tentukan path sesuai jenis target
        if ob.type == 'ARMATURE' and context.mode == 'POSE' and context.active_pose_bone:
            target_path = f'pose.bones["{context.active_pose_bone.name}"].constraints["{self.constraint_name}"]'
        else:
            target_path = f'constraints["{self.constraint_name}"]'

        # Hapus F-Curve yang cocok
        for fcurve in list(action.fcurves):
            if fcurve.data_path.startswith(target_path):
                action.fcurves.remove(fcurve)

        return {'FINISHED'}




class RAHA_OT_clear_constraint_key_current(bpy.types.Operator):
    bl_idname = "raha.clear_constraint_key_current"
    bl_label = "delete Key (Parent - Current Frame)"
    bl_description = "Delete influence keyframe at the current frame only"    
    constraint_name: StringProperty()

    def execute(self, context):
        ob = context.object
        if not ob or not ob.animation_data or not ob.animation_data.action:
            return {'CANCELLED'}

        action = ob.animation_data.action
        current_frame = context.scene.frame_current

        # Tentukan path sesuai jenis target
        if ob.type == 'ARMATURE' and context.mode == 'POSE' and context.active_pose_bone:
            target_path = f'pose.bones["{context.active_pose_bone.name}"].constraints["{self.constraint_name}"]'
        else:
            target_path = f'constraints["{self.constraint_name}"]'

        found = False
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith(target_path):
                key_indices = [i for i, kp in enumerate(fcurve.keyframe_points) if int(kp.co.x) == current_frame]
                for i in reversed(key_indices):
                    fcurve.keyframe_points.remove(fcurve.keyframe_points[i])
                    found = True
                fcurve.update()

        if not found:
            self.report({'INFO'}, f"No keyframe found at frame {current_frame}")

        return {'FINISHED'}



# ========================================================================================================================
#  ======================================================  TOMBOL PARENT (Panel) ==============================================  
    
class VIEW3D_PT_Raha_Parents(bpy.types.Panel):
    bl_label = "Raha Parent Tools"
    bl_idname = "VIEW3D_PT_Raha_Parents"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Raha_Tools"
    bl_ui_units_x = 10

    def get_parent_child_constraints(target):
        """Ambil constraint Child Of dari object atau pose bone"""
        if hasattr(target, "constraints"):
            return [c for c in target.constraints if c.type == 'CHILD_OF']
        return []


    def draw(self, context):
        layout = self.layout
        obj = context.object
        bone = context.active_pose_bone

        # Tombol Create Parent selalu muncul
        row = layout.row()
        row.operator("raha_parent.create", text="Parent Child-Of")

        # Tentukan sumber constraint
        constraints = []
        if obj:
            if bone:  # Pose bone aktif
                constraints = get_parent_child_constraints(bone)
            else:  # Object aktif
                constraints = get_parent_child_constraints(obj)

        # Tampilkan daftar constraint kalau ada
        if constraints:
            layout.separator()
            for c in constraints:
                box = layout.box()
                header = box.row(align=True)
                target_name = ""
                if c.target:
                    target_name = c.target.name
                    if getattr(c, "subtarget", ""):
                        target_name += "." + c.subtarget
                header.label(text=f"Parent Child-of: {target_name}")
                
                row = box.row(align=True)
                row.prop(c, "influence", text="Influence")
                op = row.operator("childof.insert_influence_key", text="", icon="KEYTYPE_KEYFRAME_VEC")
                op.constraint_name = c.name
                op = row.operator("raha.clear_constraint_key_current", text="", icon="KEYFRAME")
                op.constraint_name = c.name                              
                
                row = box.row(align=True)
                op = row.operator("raha.enable_constraint_single", text="Enable", icon="LINKED")
                op.constraint_name = c.name
                op = row.operator("raha_parent.disable", text="Disable", icon="UNLINKED")
                op.constraint_name = c.name
                row = box.row(align=False)                
                op = row.operator("raha.set_inverse_single", text="", icon="ARROW_LEFTRIGHT")
                op.constraint_name = c.name
                op = row.operator("raha.clear_inverse_single", text="", icon="TRACKING_CLEAR_BACKWARDS")
                op.constraint_name = c.name
                op = row.operator("raha.apply_constraint_single", text="", icon="CHECKMARK")
                op.constraint_name = c.name
                op = row.operator("raha.clear_constraint_keys", text="", icon="KEYTYPE_GENERATED_VEC")
                op.constraint_name = c.name

                op = row.operator("raha.delete_constraint_single", text="", icon="TRASH")
                op.constraint_name = c.name
        else:
            layout.label(text="No 'Child Of' constraint found", icon="INFO")


# ========================================================================================================================
#                                               REGISTER     
   
classes = (
    OBJECT_OT_ENABLE,
    raha_parent_OT_create,
    raha_parent_OT_clear,
    RAHA_OT_apply_constraint,
    RAHA_OT_set_inverse,
    RAHA_OT_clear_inverse,
    RAHA_OT_delete_constraint,
    RAHA_OT_enable_constraint,
    RAHA_OT_disable_constraint,
    RAHA_OT_clear_constraint_keys,
    RAHA_OT_clear_constraint_key_current,
    CHILD_OT_insert_influence_keyframe,   # <-- TAMBAHKAN INI
#    VIEW3D_PT_Raha_Parents,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

if __name__ == "__main__":
    register()
