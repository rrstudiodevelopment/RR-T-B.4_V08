import bpy
import webbrowser

# ---------------------
# Dummy Operator untuk TOOLTIP
# ---------------------

class FLOATING_OT_open_audio(bpy.types.Operator):
    bl_idname = "floating.open_audio"
    bl_label = "Audio"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_audio_tools", keep_open=True)
        return {'FINISHED'}


class FLOATING_OT_open_hud(bpy.types.Operator):
    bl_idname = "floating.open_hud"
    bl_label = "HUD"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_HUD", keep_open=True)
        return {'FINISHED'}


class FLOATING_OT_open_playblast(bpy.types.Operator):
    bl_idname = "floating.open_playblast"
    bl_label = "Playblast"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_Tools_playblast", keep_open=True)
        return {'FINISHED'}


# ---------------------
# Tombol buka link YouTube
# ---------------------

class OPEN_OT_youtube_info(bpy.types.Operator):
    bl_idname = "wm.open_youtube_info"
    bl_label = "Info Video"
    bl_description = "Watch the tutorial on how to use these tools"
    
    def execute(self, context):
        webbrowser.open("https://www.youtube.com/watch?v=Z61uI8GYOFo")
        
        return {'FINISHED'}
      
    
# ---------------------
# Panel UI
# ---------------------

#class VIEW3D_PT_playblast_ui(bpy.types.Panel):
    bl_label = "Audio HUD Playblast"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Raha_Tools"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Header collapsible
        row = layout.row(align=True)
        row.prop(scene, "show_pb_tools", text="", icon='TRIA_DOWN' if scene.show_pb_tools else 'TRIA_RIGHT', emboss=False)
        row.label(text="A H P Tools")
        row.operator("wm.open_youtube_info", text="", icon='INFO')

        if scene.show_pb_tools:
            box = layout.box()
            row = box.row()
            row.operator("floating.open_audio", text="AUDIO", icon='SPEAKER')
            row.operator("floating.open_hud", text="HUD", icon='SEQUENCE')
            box.operator("floating.open_playblast", text="PLAYBLAST", icon='RENDER_ANIMATION')

# ---------------------
# Property
# ---------------------

def register_props():
    bpy.types.Scene.show_pb_tools = bpy.props.BoolProperty(
        name="Show Playblast Tools",
        default=True,
        description="Show or hide playblast tool panel"
    )

def unregister_props():
    del bpy.types.Scene.show_pb_tools

# ---------------------
# Registrasi
# ---------------------

classes = [
    FLOATING_OT_open_audio,
    FLOATING_OT_open_hud,
    FLOATING_OT_open_playblast,
    OPEN_OT_youtube_info,
#    VIEW3D_PT_playblast_ui,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_props()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_props()

if __name__ == "__main__":
    register()
