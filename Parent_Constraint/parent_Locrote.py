import bpy
from bpy.props import FloatProperty, StringProperty, IntProperty

# --------------------------- Config ---------------------------
MAX_SETS = 10  # jumlah maksimal set CopasPos/CopasRot yang didukung (01..MAX_SETS)

# --------------------------- Utilities ---------------------------
def get_active_target(context):
    """Return (target, is_bone). target = PoseBone atau Object."""
    if context.mode == 'POSE' and context.active_pose_bone:
        return context.active_pose_bone, True
    elif context.mode == 'OBJECT' and context.active_object:
        return context.active_object, False
    return None, False

def get_constraint_by_base_and_suffix(target, base_name, suffix):
    """Return constraint object by base ('CopasRot'/'CopasPos') dan suffix ('', '02', '03', ...)."""
    name = base_name if suffix == "" else f"{base_name}{suffix}"
    for c in target.constraints:
        if c.name == name:
            return c
    return None

def get_copas_pairs(target):
    """
    Return list of tuples [(rot_constraint, loc_constraint, suffix_str), ...]
    suffix_str adalah '' untuk original (CopasRot / CopasPos), atau '02','03',...
    """
    rot_dict = {}
    loc_dict = {}
    for c in target.constraints:
        if c.type == 'COPY_ROTATION' and c.name.lower().startswith("copasrot"):
            suf = c.name[8:]  # setelah 'CopasRot'
            rot_dict[suf] = c
        elif c.type == 'COPY_LOCATION' and c.name.lower().startswith("copaspos"):
            suf = c.name[8:]  # setelah 'CopasPos'
            loc_dict[suf] = c

    pairs = []
    # hanya suffix yang punya rot & loc
    for suf, r in rot_dict.items():
        if suf in loc_dict:
            pairs.append((r, loc_dict[suf], suf))

    def sort_key(t):
        s = t[2]
        if s == "":
            return 0
        try:
            return int(s)
        except:
            return 9999
    pairs.sort(key=sort_key)
    return pairs

def unique_constraint_name(target, base_name):
    """Cari nama constraint unik berdasarkan base_name (CopasRot / CopasPos)."""
    existing_names = {c.name for c in target.constraints}
    if base_name not in existing_names:
        return base_name
    idx = 2
    while True:
        new_name = f"{base_name}{str(idx).zfill(2)}"
        if new_name not in existing_names:
            return new_name
        idx += 1

# --------------------------- Keyframe helpers ---------------------------
def insert_keyframes_for_constraints(target, suffix="", frame=None):
    """Insert keyframes untuk CopasRot, CopasPos, dan properti combined_influence_xx pada target+suffix."""
    if frame is None:
        frame = bpy.context.scene.frame_current
    idx = 1 if suffix == "" else int(suffix)
    prop_name = f"combined_influence_{str(idx).zfill(2)}"

    # key pada property slider (baik PoseBone maupun Object)
    try:
        target.keyframe_insert(data_path=prop_name, frame=frame)
    except Exception:
        pass

    # key pada influence constraints (jika ada)
    rot = get_constraint_by_base_and_suffix(target, "CopasRot", suffix)
    loc = get_constraint_by_base_and_suffix(target, "CopasPos", suffix)
    if rot:
        try:
            rot.keyframe_insert(data_path="influence", frame=frame)
        except Exception:
            pass
    if loc:
        try:
            loc.keyframe_insert(data_path="influence", frame=frame)
        except Exception:
            pass

def delete_keyframes_for_constraints(target, suffix=""):
    """Hapus keyframes terkait suffix (fcurve influence constraint & property)."""
    obj = bpy.context.object
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action

    idx = 1 if suffix == "" else int(suffix)
    prop_name = f"combined_influence_{str(idx).zfill(2)}"

    # Bangun data_path tanpa path_from_id (aman untuk PoseBone & Object)
    if isinstance(target, bpy.types.PoseBone):
        base = f'pose.bones["{target.name}"]'
        prop_path = f'{base}.{prop_name}'
        rot = get_constraint_by_base_and_suffix(target, "CopasRot", suffix)
        loc = get_constraint_by_base_and_suffix(target, "CopasPos", suffix)
        paths = [prop_path]
        if rot:
            paths.append(f'{base}.constraints["{rot.name}"].influence')
        if loc:
            paths.append(f'{base}.constraints["{loc.name}"].influence')
    else:
        # Object: data_path langsung di root object
        prop_path = f'{prop_name}'
        rot = get_constraint_by_base_and_suffix(target, "CopasRot", suffix)
        loc = get_constraint_by_base_and_suffix(target, "CopasPos", suffix)
        paths = [prop_path]
        if rot:
            paths.append(f'constraints["{rot.name}"].influence')
        if loc:
            paths.append(f'constraints["{loc.name}"].influence')

    # Remove fcurves yang data_path-nya cocok
    for fcurve in list(action.fcurves):
        if fcurve.data_path in paths:
            action.fcurves.remove(fcurve)

# --------------------------- Dynamic property update generator ---------------------------
def make_update_func_for_suffix(suffix):
    """Callback update untuk sinkronisasi slider -> influence constraints."""
    def update_fn(self, context):
        idx = 1 if suffix == "" else int(suffix)
        prop_name = f"combined_influence_{str(idx).zfill(2)}"
        value = getattr(self, prop_name, None)
        if value is None:
            return

        rot = get_constraint_by_base_and_suffix(self, "CopasRot", suffix)
        loc = get_constraint_by_base_and_suffix(self, "CopasPos", suffix)
        if rot:
            rot.influence = value
        if loc:
            loc.influence = value

        # Auto Key
        auto_key = context.scene.tool_settings.use_keyframe_insert_auto
        if auto_key:
            insert_keyframes_for_constraints(self, suffix, frame=context.scene.frame_current)
    return update_fn

# --------------------------- Register properties ---------------------------
def register_properties():
    # Buat property di PoseBone & Object (01..MAX_SETS)
    for i in range(1, MAX_SETS + 1):
        idx_s = str(i).zfill(2)
        suffix = "" if i == 1 else idx_s
        prop_name = f"combined_influence_{idx_s}"
        update_fn = make_update_func_for_suffix(suffix)

        if not hasattr(bpy.types.PoseBone, prop_name):
            setattr(
                bpy.types.PoseBone,
                prop_name,
                FloatProperty(
                    name=f"Influence {idx_s}",
                    description=f"Combined influence for Copas set {idx_s}",
                    default=1.0, min=0.0, max=1.0,
                    update=update_fn
                )
            )
        if not hasattr(bpy.types.Object, prop_name):
            setattr(
                bpy.types.Object,
                prop_name,
                FloatProperty(
                    name=f"Influence {idx_s}",
                    description=f"Combined influence for Copas set {idx_s}",
                    default=1.0, min=0.0, max=1.0,
                    update=update_fn
                )
            )

def unregister_properties():
    for i in range(1, MAX_SETS + 1):
        idx_s = str(i).zfill(2)
        prop_name = f"combined_influence_{idx_s}"
        for typ in (bpy.types.PoseBone, bpy.types.Object):
            if hasattr(typ, prop_name):
                try:
                    delattr(typ, prop_name)
                except Exception:
                    # fallback
                    try:
                        del typ.__dict__[prop_name]
                    except Exception:
                        pass

# --------------------------- Operators ---------------------------

class LOCROTE_OT_apply_both_constraints(bpy.types.Operator):
    """Apply CopasRot & CopasPos hanya untuk kombinasi slider ini"""
    bl_idname = "locrote.apply_both_constraints"
    bl_label = "Apply Both Constraints"
    suffix: StringProperty(default="")  # '', '02', '03', ...

    def execute(self, context):
        target, is_bone = get_active_target(context)
        if not target:
            self.report({'WARNING'}, "No active target")
            return {'CANCELLED'}

        applied_any = False
        # Ambil hanya pasangan dengan suffix yang cocok
        for r, l, suf in get_copas_pairs(target):
            if suf != self.suffix:
                continue

            if r:
                try:
                    bpy.ops.constraint.apply(constraint=r.name, owner='BONE' if is_bone else 'OBJECT')
                    applied_any = True
                except Exception:
                    pass

            if l:
                try:
                    bpy.ops.constraint.apply(constraint=l.name, owner='BONE' if is_bone else 'OBJECT')
                    applied_any = True
                except Exception:
                    pass

        if not applied_any:
            self.report({'WARNING'}, f"No CopasRot/CopasPos applied for suffix {self.suffix}")
            return {'CANCELLED'}

        return {'FINISHED'}

class LOCROTE_OT_create(bpy.types.Operator):
    """Create Loc+Rot constraints (CopasPos / CopasRot) pada target aktif.
    - Pose Mode: aktif = active_pose_bone, target = bone terpilih lintas armature (sesuai skrip asli).
    - Object Mode: aktif = active_object, target = objek terpilih (selain aktif).
    """
    bl_idname = "locrote.create"
    bl_label = "Create Parent LocRotate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target, is_bone = get_active_target(context)
        if not target:
            self.report({'WARNING'}, "Please select active bone/object first")
            return {'CANCELLED'}

        if is_bone:
            # ====== Jalur ASLI Pose Mode (dipertahankan) ======
            if context.mode != 'POSE':
                self.report({'WARNING'}, "Please switch to Pose Mode!")
                return {'CANCELLED'}

            # validasi: minimal 2 pose bones terpilih lintas armature
            if not context.active_pose_bone or len(context.selected_pose_bones) < 2:
                self.report({'WARNING'}, "Select at least 2 bones across armatures and set an active bone")
                return {'CANCELLED'}

            active = context.active_pose_bone

            # Loop semua pose bone terpilih (dari semua armature)
            for ob in context.selected_objects:
                if ob.type != 'ARMATURE':
                    continue
                for target_bone in ob.pose.bones:
                    if not target_bone.bone.select:
                        continue
                    if ob == context.object and target_bone == active:
                        continue  # skip active bone itself

                    # COPY_ROTATION
                    r_name = unique_constraint_name(active, "CopasRot")
                    r_new = active.constraints.new(type='COPY_ROTATION')
                    r_new.name = r_name
                    r_new.target = ob
                    r_new.subtarget = target_bone.name
                    r_new.influence = 1.0

                    # COPY_LOCATION
                    l_name = unique_constraint_name(active, "CopasPos")
                    l_new = active.constraints.new(type='COPY_LOCATION')
                    l_new.name = l_name
                    l_new.target = ob
                    l_new.subtarget = target_bone.name
                    l_new.influence = 1.0

                    # sinkronkan slider
                    suf = r_name[8:]
                    idx = 1 if suf == "" else int(suf)
                    prop_name = f"combined_influence_{str(idx).zfill(2)}"
                    try:
                        setattr(active, prop_name, 1.0)
                    except Exception:
                        pass

            self.report({'INFO'}, f"Created constraints on {active.name} targeting selected bones (multi-armature supported)")
            return {'FINISHED'}

        else:
            # ====== Jalur BARU Object Mode ======
            active_obj = context.active_object
            sel_objs = [o for o in context.selected_objects if o != active_obj]
            if not sel_objs:
                self.report({'WARNING'}, "Select at least 2 objects (active + target)")
                return {'CANCELLED'}

            for ob in sel_objs:
                # COPY_ROTATION
                r_name = unique_constraint_name(active_obj, "CopasRot")
                r_new = active_obj.constraints.new(type='COPY_ROTATION')
                r_new.name = r_name
                r_new.target = ob
                r_new.subtarget = ""  # object mode: tidak pakai subtarget
                r_new.influence = 1.0

                # COPY_LOCATION
                l_name = unique_constraint_name(active_obj, "CopasPos")
                l_new = active_obj.constraints.new(type='COPY_LOCATION')
                l_new.name = l_name
                l_new.target = ob
                l_new.subtarget = ""
                l_new.influence = 1.0

                # sinkronkan slider
                suf = r_name[8:]
                idx = 1 if suf == "" else int(suf)
                prop_name = f"combined_influence_{str(idx).zfill(2)}"
                try:
                    setattr(active_obj, prop_name, 1.0)
                except Exception:
                    pass

            self.report({'INFO'}, f"Created constraints on {active_obj.name} targeting selected objects")
            return {'FINISHED'}

class LOCROTE_OT_apply_key(bpy.types.Operator):
    """Apply & Keyframe untuk set Copas tertentu"""
    bl_idname = "locrote.apply_key"
    bl_label = "Apply & Keyframe"
    suffix: StringProperty(default="")  # '' untuk set 1, '02','03',...

    def execute(self, context):
        target, _ = get_active_target(context)
        if not target:
            return {'CANCELLED'}

        r = get_constraint_by_base_and_suffix(target, "CopasRot", self.suffix)
        l = get_constraint_by_base_and_suffix(target, "CopasPos", self.suffix)
        if not r and not l:
            return {'CANCELLED'}

        insert_keyframes_for_constraints(target, self.suffix, frame=context.scene.frame_current)
        return {'FINISHED'}

class LOCROTE_OT_clear_keys(bpy.types.Operator):
    """Clear keys untuk set Copas tertentu"""
    bl_idname = "locrote.clear_keys"
    bl_label = "Clear Keys"
    suffix: StringProperty(default="")

    def execute(self, context):
        target, _ = get_active_target(context)
        if not target:
            return {'CANCELLED'}
        delete_keyframes_for_constraints(target, self.suffix)
        return {'FINISHED'}

class LOCROTE_OT_enable(bpy.types.Operator):
    """Enable kedua constraint untuk suffix terpilih + sinkronkan slider"""
    bl_idname = "locrote.enable"
    bl_label = "Enable Both"
    suffix: StringProperty(default="")  # '' untuk set 1, '02', '03', ...

    def execute(self, context):
        target, _ = get_active_target(context)
        if not target:
            return {'CANCELLED'}

        r = get_constraint_by_base_and_suffix(target, "CopasRot", self.suffix)
        l = get_constraint_by_base_and_suffix(target, "CopasPos", self.suffix)

        if r:
            r.influence = 1.0
        if l:
            l.influence = 1.0

        # >>> penting: update slider supaya UI ikut berubah <<<
        idx = 1 if self.suffix == "" else int(self.suffix)
        prop_name = f"combined_influence_{str(idx).zfill(2)}"
        try:
            setattr(target, prop_name, 1.0)
        except Exception:
            pass

        insert_keyframes_for_constraints(target, self.suffix, frame=context.scene.frame_current)
        return {'FINISHED'}

class LOCROTE_OT_disable(bpy.types.Operator):
    """Disable kedua constraint untuk suffix terpilih + sinkronkan slider"""
    bl_idname = "locrote.disable"
    bl_label = "Disable Both"
    suffix: StringProperty(default="")  # '' untuk set 1, '02', '03', ...

    def execute(self, context):
        target, _ = get_active_target(context)
        if not target:
            return {'CANCELLED'}

        r = get_constraint_by_base_and_suffix(target, "CopasRot", self.suffix)
        l = get_constraint_by_base_and_suffix(target, "CopasPos", self.suffix)

        if r:
            r.influence = 0.0
        if l:
            l.influence = 0.0

        # >>> penting: update slider supaya UI ikut berubah <<<
        idx = 1 if self.suffix == "" else int(self.suffix)
        prop_name = f"combined_influence_{str(idx).zfill(2)}"
        try:
            setattr(target, prop_name, 0.0)
        except Exception:
            pass

        insert_keyframes_for_constraints(target, self.suffix, frame=context.scene.frame_current)
        return {'FINISHED'}

class LOCROTE_OT_delete(bpy.types.Operator):
    """Delete kedua constraint untuk target aktif (hanya suffix terpilih)"""
    bl_idname = "locrote.delete"
    bl_label = "Delete Both"
    suffix: StringProperty(default="")  # '' untuk set 1, '02', '03', ...

    def execute(self, context):
        target, _ = get_active_target(context)
        if not target:
            return {'CANCELLED'}

        r = get_constraint_by_base_and_suffix(target, "CopasRot", self.suffix)
        l = get_constraint_by_base_and_suffix(target, "CopasPos", self.suffix)

        if r:
            try:
                target.constraints.remove(r)
            except Exception:
                pass
        if l:
            try:
                target.constraints.remove(l)
            except Exception:
                pass

        # hapus keyframe terkait
        delete_keyframes_for_constraints(target, self.suffix)
        return {'FINISHED'}

# --------------------------- Panel ---------------------------
class VIEW3D_PT_Raha_LocRot(bpy.types.Panel):
    bl_label = "Raha Parent LocRotate"
    bl_idname = "VIEW3D_PT_Raha_LocRot"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Raha_Tools"

    @classmethod
    def poll(cls, context):
        # panel muncul di Pose Mode & Object Mode
        return context.mode in {'POSE', 'OBJECT'}

    def draw(self, context):
        layout = self.layout
        target, is_bone = get_active_target(context)

        # Tombol create selalu ada
        layout.operator("locrote.create", text="Create Parent LocRotate")

        # Slider per-pasangan (bone/object)
        if target:
            pairs = get_copas_pairs(target)
            if pairs:
                box = layout.box()
                box.label(text="Parent Locrote")
                for r, l, suf in pairs:
                    suf_for_prop = "" if suf == "" else suf  # '' atau '02'
                    idx = 1 if suf_for_prop == "" else int(suf_for_prop)
                    prop_name = f"combined_influence_{str(idx).zfill(2)}"

                    row = box.row(align=True)
                    # Slider
                    row.prop(target, prop_name, slider=True, text=f"influence {str(idx).zfill(2)}")
                    # Keyframe & Clear
                    op_apply = row.operator("locrote.apply_key", text="", icon="DECORATE_KEYFRAME")
                    op_apply.suffix = "" if suf_for_prop == "" else suf_for_prop
                    op_clear = row.operator("locrote.clear_keys", text="", icon="KEYTYPE_GENERATED_VEC")
                    op_clear.suffix = "" if suf_for_prop == "" else suf_for_prop

                    # Baris tombol aksi
                    row = box.row(align=True)
                    op_enable = row.operator("locrote.enable", text="Enable")
                    op_enable.suffix = "" if suf_for_prop == "" else suf_for_prop
                    op_disable = row.operator("locrote.disable", text="Disable")
                    op_disable.suffix = "" if suf_for_prop == "" else suf_for_prop
                    op_trash = row.operator("locrote.delete", text="", icon="TRASH")
                    op_trash.suffix = "" if suf_for_prop == "" else suf_for_prop
                    op_apply_constraints = row.operator("locrote.apply_both_constraints", text="", icon="CHECKMARK")
                    op_apply_constraints.suffix = "" if suf_for_prop == "" else suf_for_prop
#                    box = layout.box()

# --------------------------- Register ---------------------------
classes = (
    LOCROTE_OT_create,
    LOCROTE_OT_apply_key,
    LOCROTE_OT_enable,
    LOCROTE_OT_disable,
    LOCROTE_OT_clear_keys,
    LOCROTE_OT_delete,
    LOCROTE_OT_apply_both_constraints,
#    VIEW3D_PT_Raha_LocRot,
)

def register():
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    unregister_properties()

if __name__ == "__main__":
    register()
