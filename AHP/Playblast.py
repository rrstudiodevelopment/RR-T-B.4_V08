import bpy
import os
import subprocess



# =================================== UPDATE RESOLUSI & WARNING ===================================

def get_next_version_file(base_name, folder, extension):
    # Hapus ekstensi
    name = os.path.splitext(base_name)[0]
    version = 1
    while True:
        versioned_name = f"{name}_v{version:02d}{extension}"
        full_path = os.path.join(folder, versioned_name)
        if not os.path.exists(full_path):
            return full_path
        version += 1


def update_temp_resolution(self, context):
    scene = context.scene
    percentage = scene.RAHA_temporary_resolution_percentage / 100

    if scene.RAHA_temporary_resolution_percentage < 50:
        scene["RAHA_resolution_warning"] = "Resolusi sangat burik."
    else:
        scene["RAHA_resolution_warning"] = ""

    scene.RAHA_temp_res_x = int(scene.render.resolution_x * percentage)
    scene.RAHA_temp_res_y = int(scene.render.resolution_y * percentage)

def is_resolution_too_low(scene):
    return scene.RAHA_use_temporary_resolution and scene.RAHA_temporary_resolution_percentage < 50

# ======================================== OPERATOR =============================================
class RAHA_OT_Playblast(bpy.types.Operator):
    bl_idname = "raha.playblast"
    bl_label = "Viewport Playblast"

    def switch_workspace(self, workspace_name):
        if workspace_name in bpy.data.workspaces:
            bpy.context.window.workspace = bpy.data.workspaces[workspace_name]
        else:
            self.report({'WARNING'}, f"Workspace '{workspace_name}' tidak ditemukan!")

    def execute(self, context):
        scene = context.scene

        if is_resolution_too_low(scene):
            self.report({'ERROR'}, "Resolusi terlalu rendah. Naikkan ke minimal 50% untuk melanjutkan.")
            return {'CANCELLED'}

        original_start_frame = scene.frame_start
        original_end_frame = scene.frame_end
        original_resolution_x = scene.render.resolution_x
        original_resolution_y = scene.render.resolution_y
        original_resolution_percentage = scene.render.resolution_percentage

        # Gunakan frame range custom jika diaktifkan
        if scene.RAHA_use_custom_frame_range:
            temp_start = scene.RAHA_custom_start_frame
            temp_end = scene.RAHA_custom_end_frame
        else:
            temp_start = original_start_frame
            temp_end = original_end_frame

        scene.frame_start = temp_start
        scene.frame_end = temp_end


        self.switch_workspace("Animation")

        output_path = bpy.path.abspath(scene.RAHA_playblast_output_path)
        file_name = scene.RAHA_playblast_file_name
        file_format = scene.RAHA_playblast_output_format

        if not output_path or not file_name:
            self.report({'ERROR'}, "Output path atau file name belum diisi.")
            return {'CANCELLED'}

        resolution_percentage = (
            scene.RAHA_temporary_resolution_percentage
            if scene.RAHA_use_temporary_resolution
            else original_resolution_percentage
        )

        resolution_x = int(original_resolution_x * (resolution_percentage / 100))
        resolution_y = int(original_resolution_y * (resolution_percentage / 100))

        if resolution_x <= 0 or resolution_y <= 0:
            self.report({'ERROR'}, "Resolution must be greater than 0.")
            return {'CANCELLED'}

        if file_format == 'FFMPEG':
            if resolution_y % 2 != 0:
                resolution_y += 1
            if resolution_x % 2 != 0:
                resolution_x += 1

        render = scene.render
        render.resolution_x = resolution_x
        render.resolution_y = resolution_y
        render.resolution_percentage = resolution_percentage
        render.image_settings.file_format = file_format

        if file_format == 'FFMPEG':
            render.ffmpeg.format = scene.RAHA_playblast_video_container
            render.ffmpeg.codec = scene.RAHA_playblast_video_codec
            render.ffmpeg.audio_codec = 'AAC'

        extension = {
            'FFMPEG': {
                'QUICKTIME': ".mov",
                'MPEG4': ".mp4",
                'MATROSKA': ".mkv"
            }.get(scene.RAHA_playblast_video_container, ".mp4"),
            'PNG': "_####.png",
            'JPEG': "_####.jpg"
        }.get(file_format, ".mp4")

        full_output_path = os.path.join(output_path, f"{file_name}{extension}")
        render.filepath = full_output_path
        render.use_file_extension = file_format in {'PNG', 'JPEG'}

        # Render selesai
        bpy.ops.render.opengl(animation=True)

        # --- Archive ---
        if scene.RAHA_use_archive:
            # Tentukan folder Archive di dalam folder output
            archive_folder = os.path.join(output_path, "Archive")
            os.makedirs(archive_folder, exist_ok=True)

            # Tentukan nama file versi berikutnya
            backup_path = get_next_version_file(
                os.path.basename(full_output_path),
                archive_folder,
                os.path.splitext(full_output_path)[1]
            )

            import shutil
            try:
                if os.path.exists(full_output_path):
                    shutil.copy2(full_output_path, backup_path)
                    self.report({'INFO'}, f"Backup disimpan di {backup_path}")
            except Exception as e:
                self.report({'ERROR'}, f"Gagal backup: {str(e)}")
                

        scene.frame_start = original_start_frame
        scene.frame_end = original_end_frame
        render.resolution_x = original_resolution_x
        render.resolution_y = original_resolution_y
        render.resolution_percentage = original_resolution_percentage

        try:
            if os.path.exists(full_output_path):
                if file_format in {'PNG', 'JPEG'}:
                    # Jika format image, buka folder
                    folder_path = os.path.dirname(full_output_path)
                    if os.name == 'nt':
                        os.startfile(folder_path)
                    elif os.name == 'posix':
                        subprocess.call(['xdg-open', folder_path])
                else:
                    if os.name == 'nt':
                        os.startfile(full_output_path)
                    elif os.name == 'posix':
                        subprocess.call(['xdg-open', full_output_path])
            else:
                self.report({'ERROR'}, f"File tidak ditemukan: {full_output_path}")
        except Exception as e:
            self.report({'ERROR'}, str(e))

        self.report({'INFO'}, f"Playblast disimpan di {full_output_path}")
        return {'FINISHED'}
    


    

# ======================================== PANEL UI =============================================
class RAHA_PT_PlayblastPanel(bpy.types.Panel):
    bl_label = "Playblast HUD"
    bl_idname = "RAHA_PT_Tools_playblast"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="Playblast Settings ")
        row = layout.row()
        row.prop(scene, "RAHA_playblast_output_path", text="Output Path")
                 
        layout.prop(scene, "RAHA_playblast_file_name", text="File Name")


        

        # Format Settings
        box = layout.box()
        row = box.row()
        row.prop(scene, "RAHA_pb_show_format", icon="TRIA_DOWN" if scene.RAHA_pb_show_format else "TRIA_RIGHT", emboss=False)
        row.label(text="Format Settings")
        if scene.RAHA_pb_show_format:
            box.label(text="Format")
            box.prop(scene, "RAHA_playblast_output_format", text="")
            if scene.RAHA_playblast_output_format == 'FFMPEG':
                box.label(text="Container")
                box.prop(scene, "RAHA_playblast_video_container", text="")
                box.prop(scene, "RAHA_playblast_video_codec", text="Codec")

            box.prop(scene, "RAHA_temporary_resolution_percentage", text="Resolution %", slider=True)
            box.label(text=f"Output Resolution: {scene.RAHA_temp_res_x} x {scene.RAHA_temp_res_y}")
            if "RAHA_resolution_warning" in scene and scene["RAHA_resolution_warning"]:
                warn = box.box()
                warn.alert = True
                warn.label(text=scene["RAHA_resolution_warning"], icon='ERROR')

        # Frame Range Settings
        box = layout.box()
        row = box.row()
        row.prop(scene, "RAHA_pb_show_frame_range", icon="TRIA_DOWN" if scene.RAHA_pb_show_frame_range else "TRIA_RIGHT", emboss=False)
        row.label(text="Frame Range Temporary")
        if scene.RAHA_pb_show_frame_range:
            box.prop(scene, "RAHA_use_custom_frame_range", text="Active")
            box.prop(scene, "RAHA_custom_start_frame", text="Start Frame")
            box.prop(scene, "RAHA_custom_end_frame", text="End Frame")


        layout.separator()
        row = layout.row(align=True)  # align=True membuat elemen menempel rapat
        row.enabled = not is_resolution_too_low(scene)

        # Checkbox Archive di kiri, tombol Playblast di kanan
        row.prop(scene, "RAHA_use_archive", text="Auto Archive")
        row = layout.row(align=True)        
        row.operator("raha.playblast", text="PLAYBLAST")
        
        
class VIEW3D_HT_raha_playblast_header(bpy.types.Header):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOL_HEADER'   # atau 'HEADER'
    bl_label = "Raha Playblast Header"


    def draw(self, context):
        layout = self.layout
        layout.operator("raha.playblast", text="PLAYBLAST", icon='RENDER_ANIMATION')

           
# --- header append method (reliable) ---
def draw_raha_playblast_tool_header(self, context):
    layout = self.layout
    layout.separator()  # kasih jarak dari tombol lain

    row = layout.row(align=True)
    row.operator("raha.playblast", text="PLAYBLAST", icon='RENDER_ANIMATION')
    row.operator("floating.open_playblast", text="", icon='TOOL_SETTINGS')       

class FLOATING_OT_open_playblast(bpy.types.Operator):
    bl_idname = "floating.open_playblast"
    bl_label = "Playblast"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_Tools_playblast", keep_open=True)
        return {'FINISHED'}

# ======================================== REGISTER =============================================
classes = (
    RAHA_OT_Playblast,
    RAHA_PT_PlayblastPanel,
    VIEW3D_HT_raha_playblast_header,
    FLOATING_OT_open_playblast,       # <--- tambahkan ini
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.RAHA_use_archive = bpy.props.BoolProperty(
        name="Archive Backup",
        default=False,
        description="If checked, the playblast result will be copied to a backup folder"
    )


        

    bpy.types.Scene.RAHA_playblast_output_path = bpy.props.StringProperty(name="Output Path", subtype='DIR_PATH')
    bpy.types.Scene.RAHA_playblast_file_name = bpy.props.StringProperty(name="File Name", default="playblast")

    bpy.types.Scene.RAHA_use_temporary_resolution = bpy.props.BoolProperty(name="Use Temporary Resolution", default=False)
    bpy.types.Scene.RAHA_temporary_resolution_percentage = bpy.props.IntProperty(
        name="Resolution %", default=100, min=10, max=100,
        update=update_temp_resolution
    )
    bpy.types.Scene.RAHA_temp_res_x = bpy.props.IntProperty(name="Temp X", default=1920)
    bpy.types.Scene.RAHA_temp_res_y = bpy.props.IntProperty(name="Temp Y", default=1080)

    bpy.types.Scene.RAHA_use_custom_frame_range = bpy.props.BoolProperty(name="Use Custom Frame Range", default=False)
    bpy.types.Scene.RAHA_custom_start_frame = bpy.props.IntProperty(name="Start Frame", default=1)
    bpy.types.Scene.RAHA_custom_end_frame = bpy.props.IntProperty(name="End Frame", default=250)

    bpy.types.Scene.RAHA_playblast_output_format = bpy.props.EnumProperty(
        name="Output Format",
        description="Choose output format",
        items=[
            ('FFMPEG', "Video (FFMPEG)", ""),
            ('PNG', "Image Sequence (PNG)", ""),
            ('JPEG', "Image Sequence (JPEG)", "")
        ],
        default='FFMPEG'
    )

    bpy.types.Scene.RAHA_playblast_video_codec = bpy.props.EnumProperty(
        name="Video Codec",
        items=[
            ('H264', "H.264", ""),
            ('MPEG4', "MPEG-4", ""),
            ('DNXHD', "DNxHD", ""),
            ('PRORES', "ProRes", "")
        ],
        default='H264'
    )

    bpy.types.Scene.RAHA_playblast_video_container = bpy.props.EnumProperty(
        name="Container Format",
        items=[
            ('QUICKTIME', "QuickTime (.mov)", ""),
            ('MPEG4', "MPEG-4 (.mp4)", ""),
            ('MATROSKA', "Matroska (.mkv)", "")
        ],
        default='QUICKTIME'
    )

    bpy.types.Scene.RAHA_pb_show_format = bpy.props.BoolProperty(name="", default=True)
    bpy.types.Scene.RAHA_pb_show_frame_range = bpy.props.BoolProperty(name="", default=False)

    bpy.types.VIEW3D_HT_tool_header.append(draw_raha_playblast_tool_header)  

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    props = [p for p in dir(bpy.types.Scene) if p.startswith("RAHA_")]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)


    # hapus append dulu supaya bersih
    if draw_raha_playblast_header in bpy.types.VIEW3D_HT_header.__dict__.get("draw", ()):
        pass
    try:
        bpy.types.VIEW3D_HT_tool_header.remove(draw_raha_playblast_tool_header)
    except Exception:
        # safe ignore jika belum terpasang
        pass

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
        
if __name__ == "__main__":
    register()
