import bpy
import math
import os

#====================== PROPERTIES ======================
bpy.types.Scene.use_custom_frame_range = bpy.props.BoolProperty(
    name="Gunakan Rentang Bingkai Kustom",
    description="Start - end frame export",
    default=False
)

bpy.types.Scene.custom_start_frame = bpy.props.IntProperty(
    name="Bingkai Mulai",
    description="Bingkai awal untuk ekspor",
    default=1
)

bpy.types.Scene.custom_end_frame = bpy.props.IntProperty(
    name="Bingkai Selesai",
    description="Bingkai akhir untuk ekspor",
    default=250
)

bpy.types.Scene.insert_missing_keyframes = bpy.props.BoolProperty(
    name="Perbaiki Keyframe",
    description="Scan and fix your keyframe",
    default=False
)

#================================= GET VALUE TYPE =================================
def get_value_type(bone, prop_name, value):
    if prop_name in bone and isinstance(bone[prop_name], bool):
        return "bool"
    elif prop_name in bone and isinstance(bone[prop_name], int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "str"
    elif isinstance(value, (list, tuple)):
        return "list"
    else:
        return "unknown"

#============================ INSERT MISSING KEYFRAMES ============================
def insert_missing_keyframes():
    obj = bpy.context.active_object
    if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
        print("Pilih objek Armature dalam Pose Mode.")
        return
    
    action = obj.animation_data.action if obj.animation_data else None
    if action is None:
        print("Objek tidak memiliki action (data animasi).")
        return
    
    scene = bpy.context.scene
    original_start_frame = scene.frame_start
    original_end_frame = scene.frame_end

    try:
        if scene.use_custom_frame_range:
            scene.frame_start = scene.custom_start_frame
            scene.frame_end = scene.custom_end_frame

        keyframes = set()
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframes.add(int(keyframe.co.x))

        for current_frame in sorted(keyframes):
            bpy.context.scene.frame_set(current_frame)
            for bone in obj.pose.bones:
                keyframe_status_euler = [False, False, False]
                keyframe_status_quat = [False, False, False, False]
                keyframe_status_loc = [False, False, False]
                keyframe_status_scale = [False, False, False]

                for fcurve in action.fcurves:
                    if fcurve.data_path == f'pose.bones["{bone.name}"].rotation_euler':
                        for keyframe in fcurve.keyframe_points:
                            if int(keyframe.co.x) == current_frame:
                                keyframe_status_euler[fcurve.array_index] = True
                    elif fcurve.data_path == f'pose.bones["{bone.name}"].rotation_quaternion':
                        for keyframe in fcurve.keyframe_points:
                            if int(keyframe.co.x) == current_frame:
                                keyframe_status_quat[fcurve.array_index] = True
                    elif fcurve.data_path == f'pose.bones["{bone.name}"].location':
                        for keyframe in fcurve.keyframe_points:
                            if int(keyframe.co.x) == current_frame:
                                keyframe_status_loc[fcurve.array_index] = True
                    elif fcurve.data_path == f'pose.bones["{bone.name}"].scale':
                        for keyframe in fcurve.keyframe_points:
                            if int(keyframe.co.x) == current_frame:
                                keyframe_status_scale[fcurve.array_index] = True

                if 0 < sum(keyframe_status_euler) < 3:
                    for i in range(3):
                        if not keyframe_status_euler[i]:
                            bone.keyframe_insert(data_path="rotation_euler", index=i)
                if 0 < sum(keyframe_status_loc) < 3:
                    for i in range(3):
                        if not keyframe_status_loc[i]:
                            bone.keyframe_insert(data_path="location", index=i)
                if 0 < sum(keyframe_status_scale) < 3:
                    for i in range(3):
                        if not keyframe_status_scale[i]:
                            bone.keyframe_insert(data_path="scale", index=i)
    finally:
        scene.frame_start = original_start_frame
        scene.frame_end = original_end_frame

#============================== EXPORT KEYFRAME DATA ===============================
def export_bone_keyframe_data(context, filepath):
    armature_obj = context.object
    if not armature_obj or armature_obj.type != 'ARMATURE':
        return {'CANCELLED'}

    scene = context.scene
    original_start_frame = scene.frame_start
    original_end_frame = scene.frame_end

    try:
        if scene.use_custom_frame_range:
            scene.frame_start = scene.custom_start_frame
            scene.frame_end = scene.custom_end_frame

        selected_bones = [b.name for b in bpy.context.selected_pose_bones]
        bone_data = {}

        base_folder = os.path.dirname(filepath)
        anim_data_folder = os.path.join(base_folder, "ANIM_DATA")
        preview_folder = os.path.join(base_folder, "Preview")

        os.makedirs(anim_data_folder, exist_ok=True)
        os.makedirs(preview_folder, exist_ok=True)

        file_name = os.path.splitext(os.path.basename(filepath))[0]
        script_path = os.path.join(anim_data_folder, f"{file_name}.py")
        playblast_path = os.path.join(preview_folder, f"{file_name}.mp4")
        screenshot_path = os.path.join(base_folder, f"{file_name}.png")

        for bone in armature_obj.pose.bones:
            if bone.bone.select:
                bone_data[bone.name] = {}

                if armature_obj.animation_data and armature_obj.animation_data.action:
                    action = armature_obj.animation_data.action
                    for fcurve in action.fcurves:
                        if fcurve.data_path.startswith(f'pose.bones["{bone.name}"]'):
                            for keyframe in fcurve.keyframe_points:
                                frame = int(keyframe.co[0])
                                if scene.use_custom_frame_range and (frame < scene.custom_start_frame or frame > scene.custom_end_frame):
                                    continue
                                if frame not in bone_data[bone.name]:
                                    bone_data[bone.name][frame] = {}
                                data_path = fcurve.data_path.split('"]')[-1][1:]
                                bone_data[bone.name][frame].setdefault(data_path, {})[fcurve.array_index] = keyframe.co[1]

                if bone.keys():
                    for frame in bone_data[bone.name]:
                        bone_data[bone.name][frame]["custom_props"] = {}
                    for prop_name in bone.keys():
                        if prop_name != "_RNA_UI":
                            action = armature_obj.animation_data.action
                            if action:
                                for fcurve in action.fcurves:
                                    if fcurve.data_path == f'pose.bones["{bone.name}"]["{prop_name}"]':
                                        for keyframe in fcurve.keyframe_points:
                                            frame = int(keyframe.co[0])
                                            if scene.use_custom_frame_range and (frame < scene.custom_start_frame or frame > scene.custom_end_frame):
                                                continue
                                            value = keyframe.co[1]
                                            bone_data[bone.name][frame]["custom_props"][prop_name] = {
                                                "value": value,
                                                "type": get_value_type(bone, prop_name, value)
                                            }

        if not bone_data:
            return {'CANCELLED'}

        with open(script_path, 'w') as file:
            file.write("import bpy\nimport math\n\nscene = bpy.context.scene\n")
            file.write("selected_pose_bones = bpy.context.selected_pose_bones\n")
            file.write("if selected_pose_bones:\n")
            file.write("    armature_obj = selected_pose_bones[0].id_data\n")
            file.write("    selected_bones = [bone.name for bone in selected_pose_bones]\n")
            file.write("    matched_bones = {}\n\n")

            all_frames = sorted({frame for bone_frames in bone_data.values() for frame in bone_frames})
            prev_frame = None
            for frame in all_frames:
                file.write(f"# Frame {frame}\n")
                if prev_frame is None:
                    file.write("frame_current = scene.frame_current\nscene.frame_set(frame_current)\nbpy.ops.anim.keyframe_insert()\n")
                else:
                    file.write(f"frame_target = frame_current + {frame - prev_frame}\n")
                    file.write("scene.frame_set(frame_target)\nframe_current = frame_target\n")

                for bone_name, frames in bone_data.items():
                    if frame in frames:
                        file.write(f"if '{bone_name}' in selected_bones:\n")
                        file.write(f"    bone = armature_obj.pose.bones['{bone_name}']\n")
                        for data_path, value in frames[frame].items():
                            if data_path == "location":
                                x, y, z = value.get(0, 0), value.get(1, 0), value.get(2, 0)
                                file.write(f"    bone.location = ({x}, {y}, {z})\n")
                                file.write("    bone.keyframe_insert(data_path='location')\n")
                            elif data_path == "rotation_quaternion":
                                w, x, y, z = [value.get(i, 0) for i in range(4)]
                                file.write(f"    bone.rotation_quaternion = ({w}, {x}, {y}, {z})\n")
                                file.write("    bone.keyframe_insert(data_path='rotation_quaternion')\n")
                            elif data_path == "rotation_euler":
                                x, y, z = value.get(0, 0), value.get(1, 0), value.get(2, 0)
                                file.write(f"    bone.rotation_euler = ({x}, {y}, {z})\n")
                                file.write("    bone.keyframe_insert(data_path='rotation_euler')\n")
                            elif data_path == "scale":
                                x, y, z = value.get(0, 1), value.get(1, 1), value.get(2, 1)
                                file.write(f"    bone.scale = ({x}, {y}, {z})\n")
                                file.write("    bone.keyframe_insert(data_path='scale')\n")
                            elif data_path == "custom_props":
                                for prop_name, prop_data in value.items():
                                    val = prop_data["value"]
                                    typ = prop_data["type"]
                                    if typ == "bool":
                                        file.write(f'    bone["{prop_name}"] = {str(bool(val))}\n')
                                    elif typ == "int":
                                        file.write(f'    bone["{prop_name}"] = int({val})\n')
                                    elif typ == "float":
                                        file.write(f'    bone["{prop_name}"] = float({val})\n')
                                    elif typ == "str":
                                        file.write(f'    bone["{prop_name}"] = "{val}"\n')
                                    elif typ == "list":
                                        file.write(f'    bone["{prop_name}"] = {list(val)}\n')
                                    else:
                                        file.write(f'    bone["{prop_name}"] = {val}\n')
                                    file.write(f'    bone.keyframe_insert(data_path=\'["{prop_name}"]\')\n')
                prev_frame = frame
                file.write("\n")

        # Playblast MP4
        scene.render.filepath = playblast_path
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.audio_codec = 'AAC'
        bpy.ops.render.opengl(animation=True)

        # Screenshot
        scene.frame_set(scene.frame_start)
        original_format = scene.render.image_settings.file_format
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = screenshot_path
        bpy.ops.render.opengl(write_still=True)
        scene.render.image_settings.file_format = original_format

    finally:
        scene.frame_start = original_start_frame
        scene.frame_end = original_end_frame

    return {'FINISHED'}

#=============================== REGISTER / UI SKIP =================================
# Anda bisa lanjutkan bagian `import`, `panel`, `operator` seperti sebelumnya
#================================= DEF import_bone_keyframe_data ========================
def import_bone_keyframe_data(context, filepath):
    directory, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)

    anim_data_dir = os.path.join(directory, "ANIM_DATA")

    if not os.path.exists(anim_data_dir):
        print(f"Folder ANIM_DATA tidak ditemukan di: {directory}")
        return {'CANCELLED'}

    script_filepath = os.path.join(anim_data_dir, f"{name}.py")  # Asumsi file script berekstensi .py

    if not os.path.exists(script_filepath):
        print(f"File script {name}.py tidak ditemukan di: {anim_data_dir}")
        return {'CANCELLED'}
    
    try:
        with open(script_filepath, 'r') as file:
            exec(file.read())
        print(f"Data keyframe dari {script_filepath} berhasil diimpor.")
        return {'FINISHED'}
    except Exception as e:  # Tangani potensi error saat membaca atau mengeksekusi script
        print(f"Terjadi error saat mengimpor script: {e}")
        return {'CANCELLED'}
    
#==================================== ANIMImportBoneKeyframeData ==========================
class ANIMImportBoneKeyframeData(bpy.types.Operator):
    bl_idname = "object.import_bone_keyframe_data"
    bl_label = "Import Data"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        return import_bone_keyframe_data(context, self.filepath)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# #========================================= OPERATOR ANIMExportBoneKeyframeData ===================
class ANIMExportBoneKeyframeData(bpy.types.Operator):
    bl_idname = "object.export_bone_keyframe_data"
    bl_label = "Export Bone Keyframe Data"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    insert_missing_keyframes: bpy.props.BoolProperty(
        name="Insert Missing Keyframes",
        description="Insert missing keyframes before exporting",
        default=False
    )

    def execute(self, context):
        if self.insert_missing_keyframes:
            insert_missing_keyframes()
        return export_bone_keyframe_data(context, self.filepath)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

#=============================================  Panel UI ====================================
    
class ANIMBoneKeyframePanel(bpy.types.Panel):
    bl_label = "SAVE ANIMATION"
    bl_idname = "OBJECT_PT_bone_keyframe"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_ui_units_x = 10
    

    def draw(self, context):
        layout = self.layout
        scene = context.scene                
                
        layout = self.layout     
        layout.prop(scene, "use_custom_frame_range", text="Use Custom Frame Range")
        if scene.use_custom_frame_range:
            layout.prop(scene, "custom_start_frame", text="Start Frame")
            layout.prop(scene, "custom_end_frame", text="End Frame")        
           
        layout.prop(context.scene, "insert_missing_keyframes", text="let's fix your keyframe")
        export_op = layout.operator("object.export_bone_keyframe_data", text="Export Animation")
        export_op.insert_missing_keyframes = context.scene.insert_missing_keyframes      
        layout.operator("object.export_bone_keyframe_data_pose", text="Export Pose") 
        
        layout.separator()        
                                             
#       layout.operator("object.import_bone_keyframe_data", text="Import")

      
            
class ANIMExportBoneSettings(bpy.types.PropertyGroup):
    use_custom_frame_range: bpy.props.BoolProperty(
        name="Custom Frame Range",
        description="Enable custom frame range for playblast",
        default=False
    )
    custom_start_frame: bpy.props.IntProperty(  # Corrected property name
        name="Start Frame",
        default=1
    )
    custom_end_frame: bpy.props.IntProperty(  # Corrected property name
        name="End Frame",
        default=250
    )               
        

# Registrasi addon
def register():
    print("Anim Lib Registered")
    

    bpy.utils.register_class(ANIMExportBoneKeyframeData)
    bpy.utils.register_class(ANIMImportBoneKeyframeData)
    bpy.utils.register_class(ANIMExportBoneSettings) 
    bpy.utils.register_class(ANIMBoneKeyframePanel)

    # Definisi property dengan format yang benar
    use_custom_frame_range: bpy.props.BoolProperty(
        name="Custom Frame Range",
        description="Enable custom frame range for playblast",
        default=False
    )

    bpy.types.Scene.custom_start_frame = bpy.props.IntProperty(
        name="Custom Start Frame",
        default=1
    )

    bpy.types.Scene.custom_end_frame = bpy.props.IntProperty(
        name="Custom End Frame",
        default=250
    )

def unregister():
    print("Anim Lib Unregistered")
    
    
    bpy.utils.unregister_class(ANIMExportBoneKeyframeData)
    bpy.utils.unregister_class(ANIMImportBoneKeyframeData)
    bpy.utils.unregister_class(ANIMExportBoneSettings) 
    bpy.utils.unregister_class(ANIMBoneKeyframePanel)

    # Menghapus properti dari bpy.types.Scene dengan benar
    del bpy.types.Scene.insert_missing_keyframes
    del bpy.types.Scene.custom_start_frame
    del bpy.types.Scene.custom_end_frame
    

if __name__ == "__main__":
    register()
