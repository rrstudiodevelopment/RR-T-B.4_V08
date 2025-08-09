import bpy
import os
from bpy.types import Operator, Panel
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper

# =========================== Import Audio ====================================
class RAHA_OT_import_audio(Operator, ImportHelper):
    """Import an audio file and set its start position"""
    bl_idname = "raha.import_audio"
    bl_label = "Add Audio"

    filter_glob: StringProperty(default="*.wav;*.mp3;*.ogg", options={'HIDDEN'})

    def execute(self, context):
        scene = context.scene
        audio_path = self.filepath

        if not scene.sequence_editor:
            scene.sequence_editor_create()

        frame_start = scene.frame_start
        max_channel = 32
        used_channels = set()

        for s in scene.sequence_editor.sequences_all:
            if s.type == 'SOUND':
                if s.frame_final_start <= frame_start <= s.frame_final_end:
                    used_channels.add(s.channel)
                else:
                    used_channels.add(s.channel)

        for channel in range(1, max_channel):
            if channel not in used_channels:
                break
        else:
            self.report({'ERROR'}, "No available channel found for audio.")
            return {'CANCELLED'}

        sound_strip = scene.sequence_editor.sequences.new_sound(
            name=os.path.basename(audio_path),
            filepath=audio_path,
            channel=channel,
            frame_start=frame_start
        )

        sound_strip.show_waveform = True
        scene.sync_mode = scene.raha_sync_mode

        return {'FINISHED'}

# =========================== Delete Audio ====================================
class RAHA_OT_delete_audio(Operator):
    """Delete audio strip by name"""
    bl_idname = "raha.delete_audio"
    bl_label = "Delete Audio"

    strip_name: StringProperty()

    def execute(self, context):
        scene = context.scene
        if scene.sequence_editor:
            strip = scene.sequence_editor.sequences.get(self.strip_name)
            if strip and strip.type == 'SOUND':
                scene.sequence_editor.sequences.remove(strip)
                self.report({'INFO'}, f"Audio '{self.strip_name}' deleted.")
            else:
                self.report({'WARNING'}, f"Audio strip '{self.strip_name}' not found.")
        return {'FINISHED'}

# =========================== Goto VSE (Manual Edit) ==========================
class RAHA_OT_goto_vse(Operator):
    """Go to Video Editing workspace (create if missing)"""
    bl_idname = "raha.goto_vse"
    bl_label = "Edit in Video Editor"

    def execute(self, context):
        current_windows = set(bpy.context.window_manager.windows)

        # Duplikat window (akan buka window baru)
        bpy.ops.screen.area_dupli('INVOKE_DEFAULT')

        def set_vse_in_new_window():
            # Cari window baru
            new_windows = [w for w in bpy.context.window_manager.windows if w not in current_windows]
            if not new_windows:
                return 0.1  # coba lagi

            new_window = new_windows[0]  # ambil yang baru
            for area in new_window.screen.areas:
                if area.type != 'SEQUENCE_EDITOR':
                    area.type = 'SEQUENCE_EDITOR'
                    break
            return None  # selesai

        bpy.app.timers.register(set_vse_in_new_window, first_interval=0.2)

        self.report({'INFO'}, "Opened Video Sequence Editor in new window.")
        return {'FINISHED'}

# =========================== Panel UI ========================================
class RAHA_PT_audio_panel(Panel):
    bl_label = "Audio Management Tool"
    bl_idname = "RAHA_PT_audio_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Audio Management Tools ")        
        box.label(text="Playback Settings", icon='PREFERENCES')
        box.prop(scene, "raha_sync_mode", text="Sync Mode")

        row = box.row()
        row.prop(scene, "use_audio_scrub", text="Audio Scrub")
        row.prop(scene, "use_audio", text="Use Audio")

        layout.separator()
        row = layout.row()
        row.operator("raha.import_audio", text="Add Audio", icon='SOUND')
        row.operator("raha.goto_vse", text="Edit", icon='SEQUENCE')
     


        layout.label(text="Audio Tracks:")
        audio_found = False

        if scene.sequence_editor and scene.sequence_editor.sequences_all:
            for strip in scene.sequence_editor.sequences_all:
                if strip.type == 'SOUND':
                    audio_found = True
                    box = layout.box()
                    row = box.row(align=True)
                    row.label(text=strip.name, icon='SOUND')
                    op = row.operator("raha.delete_audio", text="", icon='TRASH')
                    op.strip_name = strip.name

        if not audio_found:
            layout.box().label(text="No audio found.", icon='INFO')


        
# =========================== Register & Unregister ===========================
classes = [
    RAHA_OT_import_audio,
    RAHA_OT_delete_audio,
    RAHA_OT_goto_vse,
    RAHA_PT_audio_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.raha_sync_mode = EnumProperty(
        name="Sync Mode",
        description="Choose audio sync playback mode",
        items=[
            ('AUDIO_SYNC', "Audio Sync", "Sync playback to audio"),
            ('FRAME_DROP', "Frame Drop", "Drop frames to maintain framerate"),
            ('NONE', "Play Every Frame", "No sync")
        ],
        default='AUDIO_SYNC',
        update=lambda self, ctx: setattr(ctx.scene, 'sync_mode', ctx.scene.raha_sync_mode)
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.raha_sync_mode

if __name__ == "__main__":
    register()
