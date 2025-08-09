import bpy
import os
import subprocess



# =================================== UPDATE RESOLUSI & WARNING ===================================

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

        bpy.ops.render.opengl(animation=True)

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
        layout.prop(scene, "RAHA_playblast_output_path", text="Output Path")
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
        row = layout.row()
        row.enabled = not is_resolution_too_low(scene)
        row.operator("raha.playblast", text="PLAYBLAST")

# ======================================== REGISTER =============================================
classes = (
    RAHA_OT_Playblast,
    RAHA_PT_PlayblastPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

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

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    props = [p for p in dir(bpy.types.Scene) if p.startswith("RAHA_")]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)

if __name__ == "__main__":
    register()
