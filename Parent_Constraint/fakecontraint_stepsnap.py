import bpy
import mathutils

stored_matrix_world = None
stored_matrices = {}

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
    bl_description = "Apply saved world matrix to active or selected bones (auto keyframe if Auto Key is on)"

    def execute(self, context):
        global stored_matrix_world
        scene = context.scene
        if stored_matrix_world is None:
            self.report({'ERROR'}, "Tidak ada matrix yang disimpan")
            return {'CANCELLED'}

        if context.mode != 'POSE':
            self.report({'ERROR'}, "Harus di Pose Mode")
            return {'CANCELLED'}

        obj = context.active_object
        bones = context.selected_pose_bones or [context.active_pose_bone]

        autokey = context.scene.tool_settings.use_keyframe_insert_auto
        frame = context.scene.frame_current

        for bone in bones:
            # Dapatkan transformasi saat ini dari bone
            current_matrix = obj.matrix_world @ bone.matrix
            current_location, current_rotation, current_scale = current_matrix.decompose()
            
            # Dapatkan transformasi yang disimpan
            saved_location, saved_rotation, saved_scale = stored_matrix_world.decompose()
            
            # Apply custom axis settings
            new_location = mathutils.Vector()
            new_rotation = mathutils.Quaternion()
            new_scale = mathutils.Vector()
            
            if scene.apply_custom_axis:
                # Apply location berdasarkan custom axis
                if scene.apply_location:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"location_axis_{axis}"):
                            new_location[i] = saved_location[i]
                        else:
                            new_location[i] = current_location[i]
                else:
                    new_location = current_location
                    
                # Apply rotation berdasarkan custom axis
                if scene.apply_rotation:
                    # Convert ke Euler untuk pemilihan axis yang lebih mudah
                    current_euler = current_rotation.to_euler()
                    saved_euler = saved_rotation.to_euler()
                    
                    new_euler = mathutils.Euler()
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"rotation_axis_{axis}"):
                            new_euler[i] = saved_euler[i]
                        else:
                            new_euler[i] = current_euler[i]
                    
                    new_rotation = new_euler.to_quaternion()
                else:
                    new_rotation = current_rotation
                    
                # Apply scale berdasarkan custom axis
                if scene.apply_scale:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"scale_axis_{axis}"):
                            new_scale[i] = saved_scale[i]
                        else:
                            new_scale[i] = current_scale[i]
                else:
                    new_scale = current_scale
            else:
                # Mode normal - apply semua
                new_location = saved_location
                new_rotation = saved_rotation
                new_scale = saved_scale
            
            # Bangun matrix baru
            new_matrix = mathutils.Matrix.Translation(new_location)
            new_matrix @= new_rotation.to_matrix().to_4x4()
            new_matrix @= mathutils.Matrix.Diagonal(new_scale).to_4x4()
            
            # Convert ke local space
            local_matrix = obj.matrix_world.inverted() @ new_matrix
            bone.matrix = local_matrix

            # Kalau autokey aktif → insert keyframe
            if autokey:
                bone.keyframe_insert(data_path="location", frame=frame)
                if bone.rotation_mode == 'QUATERNION':
                    bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                else:
                    bone.keyframe_insert(data_path="rotation_euler", frame=frame)
                bone.keyframe_insert(data_path="scale", frame=frame)

        msg = f"Matrix diterapkan ke {len(bones)} bone"
        if autokey:
            msg += " + keyframe dimasukkan"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class RahaApplyBoneMatrixMirror(bpy.types.Operator):
    bl_idname = "pose.raha_apply_bone_matrix_mirror"
    bl_label = "Apply Fake Constraint (Mirror)"
    bl_description = "Apply saved world matrix with mirror on selected axis (auto keyframe if Auto Key is on)"
    
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
        scene = context.scene
        if stored_matrix_world is None:
            self.report({'ERROR'}, "No matrix saved")
            return {'CANCELLED'}

        if context.mode != 'POSE':
            self.report({'ERROR'}, "Must be in Pose Mode")
            return {'CANCELLED'}

        obj = context.active_object
        bones = context.selected_pose_bones or [context.active_pose_bone]

        # Buat mirror matrix
        if self.mirror_axis == 'X':
            mirror_mat = mathutils.Matrix.Scale(-1, 4, (1, 0, 0))
        elif self.mirror_axis == 'Y':
            mirror_mat = mathutils.Matrix.Scale(-1, 4, (0, 1, 0))
        else:  # Z
            mirror_mat = mathutils.Matrix.Scale(-1, 4, (0, 0, 1))
        
        autokey = context.scene.tool_settings.use_keyframe_insert_auto
        frame = context.scene.frame_current

        for bone in bones:
            # Dapatkan transformasi saat ini
            current_matrix = obj.matrix_world @ bone.matrix
            current_location, current_rotation, current_scale = current_matrix.decompose()
            
            # Buat mirrored matrix
            mirrored_world = mirror_mat @ stored_matrix_world @ mirror_mat
            saved_location, saved_rotation, saved_scale = mirrored_world.decompose()
            
            # Apply custom axis settings
            new_location = mathutils.Vector()
            new_rotation = mathutils.Quaternion()
            new_scale = mathutils.Vector()
            
            if scene.apply_custom_axis:
                if scene.apply_location:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"location_axis_{axis}"):
                            new_location[i] = saved_location[i]
                        else:
                            new_location[i] = current_location[i]
                else:
                    new_location = current_location
                    
                if scene.apply_rotation:
                    # Convert ke Euler untuk pemilihan axis
                    current_euler = current_rotation.to_euler()
                    saved_euler = saved_rotation.to_euler()
                    
                    new_euler = mathutils.Euler()
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"rotation_axis_{axis}"):
                            new_euler[i] = saved_euler[i]
                        else:
                            new_euler[i] = current_euler[i]
                    
                    new_rotation = new_euler.to_quaternion()
                else:
                    new_rotation = current_rotation
                    
                if scene.apply_scale:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"scale_axis_{axis}"):
                            new_scale[i] = saved_scale[i]
                        else:
                            new_scale[i] = current_scale[i]
                else:
                    new_scale = current_scale
            else:
                new_location = saved_location
                new_rotation = saved_rotation
                new_scale = saved_scale
            
            # Bangun matrix baru
            new_matrix = mathutils.Matrix.Translation(new_location)
            new_matrix @= new_rotation.to_matrix().to_4x4()
            new_matrix @= mathutils.Matrix.Diagonal(new_scale).to_4x4()
            
            local_matrix = obj.matrix_world.inverted() @ new_matrix
            bone.matrix = local_matrix

            if autokey:
                bone.keyframe_insert(data_path="location", frame=frame)
                if bone.rotation_mode == 'QUATERNION':
                    bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                else:
                    bone.keyframe_insert(data_path="rotation_euler", frame=frame)
                bone.keyframe_insert(data_path="scale", frame=frame)

        msg = f"Mirrored matrix applied to {len(bones)} bones (Axis: {self.mirror_axis})"
        if autokey:
            msg += " + keyframe inserted"
        self.report({'INFO'}, msg)
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

        if not (obj and obj.type == 'ARMATURE' and obj.mode == 'POSE'):
            self.report({'WARNING'}, "Harap masuk ke Pose Mode dan pilih armature aktif.")
            return {'CANCELLED'}

        active_pb = context.active_pose_bone
        if not active_pb:
            self.report({'WARNING'}, "Tidak ada bone aktif.")
            return {'CANCELLED'}

        bone = obj.pose.bones.get(active_pb.name)
        if not bone:
            self.report({'WARNING'}, "Bone aktif tidak ditemukan.")
            return {'CANCELLED'}

        # simpan frame saat ini supaya bisa dikembalikan
        current_frame = scene.frame_current

        # pindah ke start_frame dan ambil transform yang dievaluasi di frame itu
        scene.frame_set(start_frame)
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        bone_eval = obj_eval.pose.bones.get(bone.name)
        if not bone_eval:
            scene.frame_set(current_frame)
            self.report({'ERROR'}, f"Gagal mengevaluasi bone '{bone.name}' pada frame {start_frame}.")
            return {'CANCELLED'}

        # Simpan transformasi awal
        start_matrix = obj_eval.matrix_world @ bone_eval.matrix
        start_location, start_rotation, start_scale = start_matrix.decompose()
        
        stored_matrices[bone.name] = {
            "location": list(start_location),
            "rotation": list(start_rotation),
            "scale": list(start_scale)
        }

        # Terapkan ke semua frame dalam rentang
        for f in range(start_frame, end_frame + 1):
            scene.frame_set(f)
            
            # Dapatkan transformasi saat ini
            current_matrix = obj.matrix_world @ bone.matrix
            current_location, current_rotation, current_scale = current_matrix.decompose()
            
            # Apply custom axis settings
            new_location = mathutils.Vector()
            new_rotation = mathutils.Quaternion()
            new_scale = mathutils.Vector()
            
            if scene.apply_custom_axis:
                # Location
                if scene.apply_location:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"location_axis_{axis}"):
                            new_location[i] = start_location[i]
                        else:
                            new_location[i] = current_location[i]
                else:
                    new_location = current_location
                
                # Rotation
                if scene.apply_rotation:
                    # Convert ke Euler untuk pemilihan axis
                    current_euler = current_rotation.to_euler()
                    start_euler = start_rotation.to_euler()
                    
                    new_euler = mathutils.Euler()
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"rotation_axis_{axis}"):
                            new_euler[i] = start_euler[i]
                        else:
                            new_euler[i] = current_euler[i]
                    
                    new_rotation = new_euler.to_quaternion()
                else:
                    new_rotation = current_rotation
                
                # Scale
                if scene.apply_scale:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"scale_axis_{axis}"):
                            new_scale[i] = start_scale[i]
                        else:
                            new_scale[i] = current_scale[i]
                else:
                    new_scale = current_scale
            else:
                # Mode normal
                new_location = start_location
                new_rotation = start_rotation
                new_scale = start_scale
            
            # Bangun matrix baru
            new_matrix = mathutils.Matrix.Translation(new_location)
            new_matrix @= new_rotation.to_matrix().to_4x4()
            new_matrix @= mathutils.Matrix.Diagonal(new_scale).to_4x4()
            
            bone.matrix = obj.matrix_world.inverted() @ new_matrix

            # Insert keyframes
            bone.keyframe_insert(data_path="location", frame=f)
            if bone.rotation_mode == 'QUATERNION':
                bone.keyframe_insert(data_path="rotation_quaternion", frame=f)
            else:
                bone.keyframe_insert(data_path="rotation_euler", frame=f)
            bone.keyframe_insert(data_path="scale", frame=f)

        # kembalikan ke frame semula
        scene.frame_set(current_frame)

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
        
        if not (obj and obj.type == 'ARMATURE' and obj.mode == 'POSE'):
            self.report({'WARNING'}, "Harap masuk ke Pose Mode dan pilih armature aktif.")
            return {'CANCELLED'}

        active_pb = context.active_pose_bone
        if not active_pb:
            self.report({'WARNING'}, "Tidak ada bone aktif.")
            return {'CANCELLED'}

        bone = obj.pose.bones.get(active_pb.name)
        if not bone:
            self.report({'WARNING'}, "Bone aktif tidak ditemukan.")
            return {'CANCELLED'}

        current_frame = scene.frame_current

        # Simpan transformasi akhir
        scene.frame_set(end_frame)
        end_matrix = obj.matrix_world @ bone.matrix
        end_location, end_rotation, end_scale = end_matrix.decompose()
        
        stored_matrices[bone.name] = {
            "location": list(end_location),
            "rotation": list(end_rotation),
            "scale": list(end_scale)
        }

        # Terapkan mundur ke semua frame
        for f in range(end_frame, start_frame - 1, -1):
            scene.frame_set(f)
            
            # Dapatkan transformasi saat ini
            current_matrix = obj.matrix_world @ bone.matrix
            current_location, current_rotation, current_scale = current_matrix.decompose()
            
            # Apply custom axis settings
            new_location = mathutils.Vector()
            new_rotation = mathutils.Quaternion()
            new_scale = mathutils.Vector()
            
            if scene.apply_custom_axis:
                if scene.apply_location:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"location_axis_{axis}"):
                            new_location[i] = end_location[i]
                        else:
                            new_location[i] = current_location[i]
                else:
                    new_location = current_location
                    
                if scene.apply_rotation:
                    # Convert ke Euler untuk pemilihan axis
                    current_euler = current_rotation.to_euler()
                    end_euler = end_rotation.to_euler()
                    
                    new_euler = mathutils.Euler()
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"rotation_axis_{axis}"):
                            new_euler[i] = end_euler[i]
                        else:
                            new_euler[i] = current_euler[i]
                    
                    new_rotation = new_euler.to_quaternion()
                else:
                    new_rotation = current_rotation
                    
                if scene.apply_scale:
                    for i, axis in enumerate(['x', 'y', 'z']):
                        if getattr(scene, f"scale_axis_{axis}"):
                            new_scale[i] = end_scale[i]
                        else:
                            new_scale[i] = current_scale[i]
                else:
                    new_scale = current_scale
            else:
                new_location = end_location
                new_rotation = end_rotation
                new_scale = end_scale
            
            # Bangun matrix baru
            new_matrix = mathutils.Matrix.Translation(new_location)
            new_matrix @= new_rotation.to_matrix().to_4x4()
            new_matrix @= mathutils.Matrix.Diagonal(new_scale).to_4x4()
            
            bone.matrix = obj.matrix_world.inverted() @ new_matrix

            # Insert keyframes
            bone.keyframe_insert(data_path="location", frame=f)
            if bone.rotation_mode == 'QUATERNION':
                bone.keyframe_insert(data_path="rotation_quaternion", frame=f)
            else:
                bone.keyframe_insert(data_path="rotation_euler", frame=f)
            bone.keyframe_insert(data_path="scale", frame=f)

        scene.frame_set(current_frame)
        self.report({'INFO'}, "Backward animation applied.")
        return {'FINISHED'}


class RahaBoneMatrixPanel(bpy.types.Panel):
    bl_label = "Fake constraint N step snap : raha tools"
    bl_idname = "OBJECT_PT_bone_matrix"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'    
    bl_ui_units_x = 10
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Section 2: Custom Axis Settings
        box = layout.box()
        box.prop(scene, "apply_custom_axis", text="Enable Custom Axis")
        
        if scene.apply_custom_axis:
            row = box.row()
            
            # Location Column
            col = row.column()
            col.prop(scene, "apply_location", text="Location")
            if scene.apply_location:
                row_axis = col.row(align=True)
                row_axis.prop(scene, "location_axis_x", text="X", toggle=True)
                row_axis.prop(scene, "location_axis_y", text="Y", toggle=True)
                row_axis.prop(scene, "location_axis_z", text="Z", toggle=True)
            
            # Rotation Column
            col = row.column()
            col.prop(scene, "apply_rotation", text="Rotation")
            if scene.apply_rotation:
                row_axis = col.row(align=True)
                row_axis.prop(scene, "rotation_axis_x", text="X", toggle=True)
                row_axis.prop(scene, "rotation_axis_y", text="Y", toggle=True)
                row_axis.prop(scene, "rotation_axis_z", text="Z", toggle=True)
            
            # Scale Column
            col = row.column()
            col.prop(scene, "apply_scale", text="Scale")
            if scene.apply_scale:
                row_axis = col.row(align=True)
                row_axis.prop(scene, "scale_axis_x", text="X", toggle=True)
                row_axis.prop(scene, "scale_axis_y", text="Y", toggle=True)
                row_axis.prop(scene, "scale_axis_z", text="Z", toggle=True)        
        
        # Section 1: Fake Constraints

        box.label(text="Fake Constraints & StepSnap :")
        row = box.row(align=True)
        row.operator("pose.raha_save_bone_matrix", text="Save", icon="COPYDOWN")
        row.operator("pose.raha_apply_bone_matrix", text="Paste", icon="PASTEDOWN")
        row.operator("pose.raha_apply_bone_matrix_mirror", text="Mirror", icon="PASTEFLIPDOWN")
        

        
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
    RahaBoneMatrixPanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Frame range properties
    bpy.types.Scene.start_frame = bpy.props.IntProperty(name="Start Frame", default=1)
    bpy.types.Scene.end_frame = bpy.props.IntProperty(name="End Frame", default=250)
    
    # Custom axis properties
    bpy.types.Scene.apply_custom_axis = bpy.props.BoolProperty(
        name="Custom Axis",
        description="Enable custom axis selection for transformation",
        default=False
    )
    
    bpy.types.Scene.apply_location = bpy.props.BoolProperty(
        name="Apply Location",
        description="Apply location transformation",
        default=True
    )
    
    bpy.types.Scene.apply_rotation = bpy.props.BoolProperty(
        name="Apply Rotation",
        description="Apply rotation transformation",
        default=True
    )
    
    bpy.types.Scene.apply_scale = bpy.props.BoolProperty(
        name="Apply Scale",
        description="Apply scale transformation",
        default=True
    )
    
    # Axis toggle properties untuk semua sumbu
    for axis in ['x', 'y', 'z']:
        setattr(bpy.types.Scene, f"location_axis_{axis}", 
                bpy.props.BoolProperty(name=f"Location {axis.upper()}", default=True))
        setattr(bpy.types.Scene, f"rotation_axis_{axis}", 
                bpy.props.BoolProperty(name=f"Rotation {axis.upper()}", default=True))
        setattr(bpy.types.Scene, f"scale_axis_{axis}", 
                bpy.props.BoolProperty(name=f"Scale {axis.upper()}", default=True))
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    # Hapus properties
    del bpy.types.Scene.start_frame
    del bpy.types.Scene.end_frame
    del bpy.types.Scene.apply_custom_axis
    del bpy.types.Scene.apply_location
    del bpy.types.Scene.apply_rotation
    del bpy.types.Scene.apply_scale
    
    # Hapus axis properties
    for axis in ['x', 'y', 'z']:
        delattr(bpy.types.Scene, f"location_axis_{axis}")
        delattr(bpy.types.Scene, f"rotation_axis_{axis}")
        delattr(bpy.types.Scene, f"scale_axis_{axis}")

if __name__ == "__main__":
    register()