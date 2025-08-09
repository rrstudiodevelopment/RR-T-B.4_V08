import bpy
import mathutils

stored_matrix_world = None
stored_matrices = {}
original_keyframes = {}  # Untuk menyimpan keyframe asli

# Fungsi untuk mendapatkan semua keyframe dari sebuah bone
def get_bone_keyframes(bone):
    keyframes = set()
    
    # Cek location
    if bone.id_data.animation_data and bone.id_data.animation_data.action:
        for fcurve in bone.id_data.animation_data.action.fcurves:
            if fcurve.data_path.startswith(f'pose.bones["{bone.name}"]'):
                for point in fcurve.keyframe_points:
                    keyframes.add(int(point.co[0]))
    
    return sorted(keyframes)

# Fungsi untuk menghapus keyframe di frame yang tidak diinginkan
def clean_keyframes(bone, keep_frames):
    if not bone.id_data.animation_data or not bone.id_data.animation_data.action:
        return

    action = bone.id_data.animation_data.action

    # Dapatkan semua frame yang ada sekarang
    current_frames = get_bone_keyframes(bone)

    # Frame yang perlu dihapus = current_frames - keep_frames
    frames_to_delete = set(current_frames) - set(keep_frames)

    for frame in frames_to_delete:
        bone.keyframe_delete(data_path="location", frame=frame)
        bone.keyframe_delete(data_path="rotation_quaternion", frame=frame)
        bone.keyframe_delete(data_path="rotation_euler", frame=frame)
        bone.keyframe_delete(data_path="scale", frame=frame)

        # Custom properties → hapus hanya jika memang ada fcurve-nya
        for prop in bone.keys():
            if prop not in "_RNA_UI":
                path = f'pose.bones["{bone.name}"]["{prop}"]'
                if any(fc.data_path == path for fc in action.fcurves):
                    bone.keyframe_delete(data_path=f'["{prop}"]', frame=frame)


class RahaSmartBake(bpy.types.Operator):
    """Melakukan proses smart bake dari start frame hingga end frame untuk semua bone yang dipilih"""
    bl_idname = "object.smart_bake"
    bl_label = "Smart Bake"
    
    def execute(self, context):
        obj = context.object
        scene = context.scene
        start_frame = scene.start_frame
        end_frame = scene.end_frame
        
        # Ambil status checkbox
        bake_location = scene.bake_location
        bake_rotation = scene.bake_rotation
        bake_scale = scene.bake_scale
        bake_custom_props = scene.bake_custom_props
        delete_constraints = scene.delete_constraints
        auto_clean_keys = scene.auto_clean_keys  # Checkbox baru
        
        if obj and obj.type == 'ARMATURE' and obj.mode == 'POSE':
            selected_bones = context.selected_pose_bones
            if selected_bones:
                # Jika auto clean key diaktifkan, simpan keyframe asli
                if auto_clean_keys:
                    original_keyframes.clear()
                    for bone in selected_bones:
                        original_keyframes[bone.name] = get_bone_keyframes(bone)
                
                if not bake_scale:
                    for bone in selected_bones:
                        for constraint in bone.constraints:
                            if constraint.type == 'CHILD_OF':
                                constraint.use_scale_x = False
                                constraint.use_scale_y = False
                                constraint.use_scale_z = False
                                self.report({'INFO'}, f"Nonaktifkan scale pada constraint {constraint.name} di bone {bone.name}.")

                for bone in selected_bones:
                    for frame in range(start_frame, end_frame + 1):
                        scene.frame_set(frame)
                        
                        matrix = obj.matrix_world @ bone.matrix
                        location, rotation, scale = matrix.decompose()
                        stored_matrices[bone.name] = {
                            "matrix": [list(row) for row in matrix],
                            "location": list(location),
                            "rotation": list(rotation),
                            "scale": list(scale)
                        }
                        
                        scene.frame_set(frame + 1)
                        
                        if bake_location:
                            bone.keyframe_insert(data_path="location", index=-1)
                        if bake_rotation:
                            bone.keyframe_insert(data_path="rotation_quaternion", index=-1)
                            bone.keyframe_insert(data_path="rotation_euler", index=-1)
                        if bake_scale:
                            bone.keyframe_insert(data_path="scale", index=-1)
                        if bake_custom_props:
                            for prop in bone.keys():
                                if prop not in "_RNA_UI":
                                    try:
                                        bone.keyframe_insert(data_path=f'["{prop}"]')
                                    except TypeError:
                                        # Skip kalau properti ini tidak bisa dianimasikan
                                        pass

                        
                        scene.frame_set(frame)
                        
                        matrix_data = stored_matrices[bone.name]["matrix"]
                        location_data = stored_matrices[bone.name]["location"]
                        rotation_data = stored_matrices[bone.name]["rotation"]
                        scale_data = stored_matrices[bone.name]["scale"]
                        
                        new_matrix = mathutils.Matrix.Translation(location_data) @ rotation.to_matrix().to_4x4()
                        new_matrix = new_matrix @ mathutils.Matrix.Scale(scale_data[0], 4, (1, 0, 0))
                        new_matrix = new_matrix @ mathutils.Matrix.Scale(scale_data[1], 4, (0, 1, 0))
                        new_matrix = new_matrix @ mathutils.Matrix.Scale(scale_data[2], 4, (0, 0, 1))
                        
                        bone.matrix = obj.matrix_world.inverted() @ new_matrix
                        
                        if bake_location:
                            bone.keyframe_insert(data_path="location", index=-1)
                        if bake_rotation:
                            bone.keyframe_insert(data_path="rotation_quaternion", index=-1)
                            bone.keyframe_insert(data_path="rotation_euler", index=-1)
                        if bake_scale:
                            bone.keyframe_insert(data_path="scale", index=-1)
                        if bake_custom_props:
                            for prop in bone.keys():
                                if prop not in "_RNA_UI":
                                    try:
                                        bone.keyframe_insert(data_path=f'["{prop}"]')
                                    except TypeError:
                                        # Skip kalau properti ini tidak bisa dianimasikan
                                        pass

                                
                    scene.frame_set(end_frame + 1)
                    if bake_location:
                        bone.keyframe_delete(data_path="location")
                    if bake_rotation:
                        bone.keyframe_delete(data_path="rotation_quaternion")
                        bone.keyframe_delete(data_path="rotation_euler")
                    if bake_scale:
                        bone.keyframe_delete(data_path="scale")
                    if bake_custom_props:
                        for prop in bone.keys():
                            if prop not in "_RNA_UI":
                                try:
                                    bone.keyframe_insert(data_path=f'["{prop}"]')
                                except TypeError:
                                    # Skip kalau properti ini tidak bisa dianimasikan
                                    pass
                   
                    
                    # Auto clean keyframes jika diaktifkan
                    if auto_clean_keys and bone.name in original_keyframes:
                        clean_keyframes(bone, original_keyframes[bone.name])
                        self.report({'INFO'}, f"Keyframe pada bone {bone.name} telah dibersihkan")
                    
                    # Hapus constraint jika diaktifkan
                    if delete_constraints and bone.constraints:
                        for constraint in reversed(bone.constraints):
                            bone.constraints.remove(constraint)
                        self.report({'INFO'}, f"Semua constraint pada bone {bone.name} telah dihapus.")

                self.report({'INFO'}, f"Smart Bake selesai untuk {len(selected_bones)} bone.")
            else:
                self.report({'WARNING'}, "Tidak ada bone yang dipilih.")
        else:
            self.report({'WARNING'}, "Harap masuk ke Pose Mode dan pilih bone.")
        return {'FINISHED'}

class RahaSaveBoneMatrix(bpy.types.Operator):
    bl_idname = "pose.raha_save_bone_matrix"
    bl_label = "Save Fake Constraint (Universal)"
    bl_description = "Save active bone's world matrix to apply to other bones"

    def execute(self, context):
        global stored_matrix_world
        if context.mode != 'POSE' or not context.active_pose_bone:
            self.report({'ERROR'}, "Harus di Pose Mode dengan bone aktif")
            return {'CANCELLED'}

        obj = context.active_object
        bone = context.active_pose_bone
        stored_matrix_world = obj.matrix_world @ bone.matrix

        self.report({'INFO'}, f"Matrix world bone '{bone.name}' tersimpan!")
        return {'FINISHED'}

class RahaApplyBoneMatrix(bpy.types.Operator):
    bl_idname = "pose.raha_apply_bone_matrix"
    bl_label = "Apply Fake Constraint (Universal)"
    bl_description = "Apply saved world matrix to active or selected bones"

    def execute(self, context):
        global stored_matrix_world
        if stored_matrix_world is None:
            self.report({'ERROR'}, "Tidak ada matrix yang disimpan")
            return {'CANCELLED'}

        if context.mode != 'POSE':
            self.report({'ERROR'}, "Harus di Pose Mode")
            return {'CANCELLED'}

        obj = context.active_object
        bones = context.selected_pose_bones or [context.active_pose_bone]

        for bone in bones:
            local_matrix = obj.matrix_world.inverted() @ stored_matrix_world
            bone.matrix = local_matrix
            bone.rotation_mode = 'XYZ'

        self.report({'INFO'}, f"Matrix diterapkan ke {len(bones)} bone")
        return {'FINISHED'}
    
class RahaApplyBoneMatrixMirror(bpy.types.Operator):
    bl_idname = "pose.raha_apply_bone_matrix_mirror"
    bl_label = "Apply Fake Constraint (Mirror)"
    bl_description = "Apply saved world matrix with mirror on selected axis"
    
    mirror_axis: bpy.props.EnumProperty(
        name="Mirror Axis",
        description="Axis to mirror the transformation on",
        items=[
            ('X', "X", "Mirror on X axis"),
            ('Y', "Y", "Mirror on Y axis"),
            ('Z', "Z", "Mirror on Z axis"),
        ],
        default='X'
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        global stored_matrix_world
        if stored_matrix_world is None:
            self.report({'ERROR'}, "No matrix saved")
            return {'CANCELLED'}

        if context.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode")
            return {'CANCELLED'}

        obj = context.active_object
        bones = context.selected_pose_bones or [context.active_pose_bone]

        # Create mirror matrix based on selected axis
        if self.mirror_axis == 'X':
            mirror_mat = mathutils.Matrix.Scale(-1, 4, (1, 0, 0))
        elif self.mirror_axis == 'Y':
            mirror_mat = mathutils.Matrix.Scale(-1, 4, (0, 1, 0))
        else:  # Z
            mirror_mat = mathutils.Matrix.Scale(-1, 4, (0, 0, 1))
        
        for bone in bones:
            mirrored_world = mirror_mat @ stored_matrix_world @ mirror_mat
            local_matrix = obj.matrix_world.inverted() @ mirrored_world
            bone.matrix = local_matrix
            bone.rotation_mode = 'XYZ'

        self.report({'INFO'}, f"Mirrored matrix applied to {len(bones)} bones (Axis: {self.mirror_axis})")
        return {'FINISHED'}    

class RahaForwardAnimation(bpy.types.Operator):
    """Save transformation at start frame then apply it forward to end frame with keyframes"""
    bl_idname = "object.forward_animation"
    bl_label = "Forward"
    
    def execute(self, context):
        obj = context.object
        scene = context.scene
        start_frame = scene.start_frame
        end_frame = scene.end_frame
        
        if obj and obj.type == 'ARMATURE' and obj.mode == 'POSE':
            bone = obj.pose.bones.get(context.active_pose_bone.name)
            if bone:
                stored_matrices[bone.name] = {
                    "matrix": [list(row) for row in (obj.matrix_world @ bone.matrix)]
                }
                for frame in range(start_frame, end_frame + 1):
                    scene.frame_set(frame)
                    matrix_data = stored_matrices[bone.name]["matrix"]
                    bone.matrix = obj.matrix_world.inverted() @ mathutils.Matrix(matrix_data)
                    bone.keyframe_insert(data_path="location", index=-1)
                    bone.keyframe_insert(data_path="rotation_quaternion", index=-1)
                    bone.keyframe_insert(data_path="rotation_euler", index=-1)
                self.report({'INFO'}, "Forward animation applied.")
        return {'FINISHED'}

class RahaBackwardAnimation(bpy.types.Operator):
    """Save transformation at end frame then apply it backward to start frame with keyframes"""    
    bl_idname = "object.backward_animation"
    bl_label = "Backward"
    
    def execute(self, context):
        obj = context.object
        scene = context.scene
        start_frame = scene.start_frame
        end_frame = scene.end_frame
        
        if obj and obj.type == 'ARMATURE' and obj.mode == 'POSE':
            bone = obj.pose.bones.get(context.active_pose_bone.name)
            if bone:
                scene.frame_set(end_frame)
                stored_matrices[bone.name] = {
                    "matrix": [list(row) for row in (obj.matrix_world @ bone.matrix)]
                }
                for frame in range(end_frame, start_frame - 1, -1):
                    scene.frame_set(frame)
                    matrix_data = stored_matrices[bone.name]["matrix"]
                    bone.matrix = obj.matrix_world.inverted() @ mathutils.Matrix(matrix_data)
                    bone.keyframe_insert(data_path="location", index=-1)
                    bone.keyframe_insert(data_path="rotation_quaternion", index=-1)
                    bone.keyframe_insert(data_path="rotation_euler", index=-1)
                self.report({'INFO'}, "Backward animation applied.")
        return {'FINISHED'}

class RahaBoneBakePanel(bpy.types.Panel):
    bl_label = "Smart Bake"
    bl_idname = "OBJECT_PT_bone_bake"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'    
    bl_ui_units_x = 10
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene       
        layout.label(text="Bake and delete Constraint")                      
        layout.prop(scene, "start_frame")
        layout.prop(scene, "end_frame")  
        row = layout.row()             
        
        # Section 3: Smart Bake
        box = layout.box()
        box.label(text="Smart Bake Options:")
        
        row = box.row()
        col = row.column()
        col.prop(scene, "bake_location", text="Location")
        col.prop(scene, "bake_rotation", text="Rotation")
        
        col = row.column()
        col.prop(scene, "bake_scale", text="Scale")
        col.prop(scene, "bake_custom_props", text="Custom Props")
        
        box.prop(scene, "delete_constraints", text="Delete Constraints After Bake")
        box.prop(scene, "auto_clean_keys", text="Auto Clean Keyframes")  # Checkbox baru
        box.operator("object.smart_bake", text="Bake Animation", icon='RENDER_ANIMATION')      

class RahaBoneMatrixPanel(bpy.types.Panel):
    bl_label = "Fake constraint N step snap : raha tools"
    bl_idname = "OBJECT_PT_bone_matrix"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'    
    bl_ui_units_x = 10
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Section 1: Fake Constraints
        box = layout.box()
        box.label(text="Fake Constraints:")
        row = box.row(align=True)
        row.operator("pose.raha_save_bone_matrix", text="Save", icon="COPYDOWN")
        row.operator("pose.raha_apply_bone_matrix", text="Paste", icon="PASTEDOWN")
        row.operator("pose.raha_apply_bone_matrix_mirror", text="Mirror", icon="PASTEFLIPDOWN")
        
        # Section 2: Animation Tools
        box = layout.box()
        box.label(text="Step Snap")
        
        col = box.column(align=True)
        col.label(text="Frame Range:")
        row = col.row(align=True)
        row.prop(scene, "start_frame", text="Start")
        row.prop(scene, "end_frame", text="End")
        
        row = box.row(align=True)
        row.operator("object.forward_animation", text="Forward", icon='TRIA_RIGHT')
        row.operator("object.backward_animation", text="Backward", icon='TRIA_LEFT')
     
        


classes = [
    RahaSaveBoneMatrix,
    RahaApplyBoneMatrix,
    RahaApplyBoneMatrixMirror,
    RahaForwardAnimation,
    RahaBackwardAnimation,
    RahaSmartBake,
    RahaBoneMatrixPanel,
    RahaBoneBakePanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.start_frame = bpy.props.IntProperty(name="Start Frame", default=1)
    bpy.types.Scene.end_frame = bpy.props.IntProperty(name="End Frame", default=250)
    bpy.types.Scene.bake_location = bpy.props.BoolProperty(name="Bake Location", default=True)
    bpy.types.Scene.bake_rotation = bpy.props.BoolProperty(name="Bake Rotation", default=True)
    bpy.types.Scene.bake_scale = bpy.props.BoolProperty(name="Bake Scale", default=True)
    bpy.types.Scene.bake_custom_props = bpy.props.BoolProperty(name="Bake Custom Properties", default=True)

    bpy.types.Scene.delete_constraints = bpy.props.BoolProperty(
        name="Delete Constraints After Bake",
        description="Remove all constraints after baking animation",
        default=True
    )
    bpy.types.Scene.auto_clean_keys = bpy.props.BoolProperty(
        name="Auto Clean Keyframes",
        description="Remember original keyframes and clean up after baking",
        default=False
    )   
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.start_frame
    del bpy.types.Scene.end_frame
    del bpy.types.Scene.bake_location
    del bpy.types.Scene.bake_rotation
    del bpy.types.Scene.bake_scale
    del bpy.types.Scene.bake_custom_props

if __name__ == "__main__":
    register()