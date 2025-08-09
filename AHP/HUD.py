import bpy
import os

# ====== Cek safe_area.png di dua folder ======
ADDONS_PATH = bpy.utils.user_resource('SCRIPTS', path="addons")
RAHA_TOOLS_PATH = os.path.join(ADDONS_PATH, "Raha_Tools", "safe_area.png")
RAHA_LAUNCHER_PATH = os.path.join(ADDONS_PATH, "Raha_Tools_LAUNCHER", "safe_area.png")

if os.path.exists(RAHA_TOOLS_PATH):
    DEFAULT_SAFE_AREA_IMAGE_PATH = RAHA_TOOLS_PATH
elif os.path.exists(RAHA_LAUNCHER_PATH):
    DEFAULT_SAFE_AREA_IMAGE_PATH = RAHA_LAUNCHER_PATH
else:
    DEFAULT_SAFE_AREA_IMAGE_PATH = ""

# ========== OPERATOR AKTIFKAN HUD ==========
class RAHA_OT_ActivateHUD(bpy.types.Operator):
    """Aktifkan HUD background image"""
    bl_idname = "raha.activate_hud"
    bl_label = "Activate HUD"

    def execute(self, context):
        scene = context.scene
        obj = context.object

        if obj and obj.type == 'CAMERA':
            obj.data.show_background_images = True

        cams = [cam for cam in bpy.data.objects if cam.type == 'CAMERA']
        if cams:
            bpy.context.view_layer.objects.active = cams[0]
            cams[0].select_set(True)

        scene.render.use_stamp = True
        scene.render.use_stamp_render_time = False            # ✅ hanya aktifkan stamp saja

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_bones = False
                        space.overlay.show_cursor = False
                        space.overlay.show_extras = False
                        space.overlay.show_motion_paths = False
                        space.overlay.show_relationship_lines = False

        cam = scene.camera
        if not cam:
            self.report({'ERROR'}, "No active camera found")
            return {'CANCELLED'}

        if not cam.data.background_images:
            bg_image = cam.data.background_images.new()
        else:
            bg_image = cam.data.background_images[0]

        if scene.raha_hud_use_custom_path:
            custom_path = scene.raha_hud_custom_path
            if os.path.exists(custom_path):
                bg_image.image = bpy.data.images.load(custom_path)
            else:
                self.report({'ERROR'}, "Custom image not found")
                return {'CANCELLED'}
        else:
            if DEFAULT_SAFE_AREA_IMAGE_PATH:
                bg_image.image = bpy.data.images.load(DEFAULT_SAFE_AREA_IMAGE_PATH)
            else:
                self.report({'ERROR'}, "Default safe area image not found")
                return {'CANCELLED'}

        bg_image.show_background_image = True
        bg_image.display_depth = 'FRONT'
        bg_image.frame_method = 'FIT'
        cam.data.show_background_images = True

        self.report({'INFO'}, "HUD activated")
        return {'FINISHED'}

# ========== OPERATOR LAINNYA ==========
class VIEW3D_OT_ToggleSafeArea(bpy.types.Operator):
    """visibility when HUD is on/off"""    
    bl_idname = "view3d.toggle_safe_area"
    bl_label = "Toggle Safe Area"

    def execute(self, context):
        cam = context.scene.camera
        if not cam:
            self.report({'ERROR'}, "No active camera")
            return {'CANCELLED'}

        if cam.data.background_images:
            bg = cam.data.background_images[0]
            bg.show_background_image = not bg.show_background_image
            context.scene.render.use_stamp = bg.show_background_image
            status = "ON" if bg.show_background_image else "OFF"
            self.report({'INFO'}, f"Safe area {status}")
        else:
            self.report({'ERROR'}, "No background image found")
            return {'CANCELLED'}

        return {'FINISHED'}

class VIEW3D_OT_DeleteSafeAreaImage(bpy.types.Operator):
    """Delete HUD and safe area"""     
    bl_idname = "view3d.delete_safe_area_image"
    bl_label = "Delete Safe Area"

    def execute(self, context):
        cam = context.scene.camera
        if cam and cam.data.background_images:
            cam.data.background_images.clear()
            cam.data.show_background_images = False
            context.scene.render.use_stamp = False
            self.report({'INFO'}, "Safe area image deleted")
        else:
            self.report({'ERROR'}, "No image to delete")
        return {'FINISHED'}

# ========== PANEL ==========
class VIEW3D_PT_HUDPanel(bpy.types.Panel):
    bl_label = "HUD Tools"
    bl_idname = "RAHA_PT_HUD"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        render = scene.render

        layout.label(text="HUD Settings")
        layout.prop(scene, "name", text="Scene Name")
        layout.prop(render, "stamp_note_text", text="Animator Name")
        layout.prop(scene, "raha_hud_use_custom_path", text="Use Custom Safe Area Path")

        if scene.raha_hud_use_custom_path:
            layout.prop(scene, "raha_hud_custom_path", text="Safe Area Image")

        row = layout.row()
        row = layout.row(align=True)
        row.prop(scene, "raha_show_stamp_settings", toggle=False, text="", icon='PREFERENCES')  
        row.operator("raha.activate_hud", text="Activate HUD Safe Area")
        row.operator("view3d.delete_safe_area_image", text="", icon='X')
        row.operator("view3d.toggle_safe_area", text="", icon='HIDE_OFF')


        row = layout.row()        
        if scene.raha_show_stamp_settings:
            box = layout.box()
            col = box.column(align=True)
            col.prop(render, "use_stamp", text="Burn into Image")  
            col.prop(render, "use_stamp_note", text="ANIMATOR")                       
            col.prop(render, "use_stamp_date", text="Date")
            col.prop(render, "use_stamp_time", text="Time")
            col.prop(render, "use_stamp_render_time", text="Render Time")
            col.prop(render, "use_stamp_frame", text="Frame")
            col.prop(render, "use_stamp_frame_range", text="Frame Range")
            col.prop(render, "use_stamp_memory", text="Memory")
            col.prop(render, "use_stamp_hostname", text="Hostname")
            col.prop(render, "use_stamp_camera", text="Camera")
            col.prop(render, "use_stamp_lens", text="Lens")
            col.prop(render, "use_stamp_scene", text="Scene")
            col.prop(render, "use_stamp_marker", text="Marker")
            col.prop(render, "use_stamp_filename", text="Filename")
            col.prop(render, "use_stamp_sequencer_strip", text="Sequencer Strip")
        
            box.prop(render, "stamp_font_size", text="Font Size")


# ========== REGISTER ==========
def register():
    bpy.utils.register_class(RAHA_OT_ActivateHUD)
    bpy.utils.register_class(VIEW3D_OT_ToggleSafeArea)
    bpy.utils.register_class(VIEW3D_OT_DeleteSafeAreaImage)
    bpy.utils.register_class(VIEW3D_PT_HUDPanel)

    bpy.types.Scene.raha_hud_use_custom_path = bpy.props.BoolProperty(name="Use Custom Safe Area Path", default=False)
    bpy.types.Scene.raha_hud_custom_path = bpy.props.StringProperty(name="Custom Image Path", subtype='FILE_PATH')
    
    bpy.types.Scene.raha_show_stamp_settings = bpy.props.BoolProperty(
        name="Show Stamp Settings",
        default=False,
        description="Tampilkan pengaturan HUD stamp"
    )
    

    # ✅ Auto aktifkan 'burn to image'
    bpy.context.scene.render.use_stamp = False
    bpy.context.scene.render.stamp_font_size = 32
        
    bpy.context.scene.render.use_stamp_date = True
    bpy.context.scene.render.use_stamp_time = True    
    bpy.context.scene.render.use_stamp_frame = True
    bpy.context.scene.render.use_stamp_lens = True
    bpy.context.scene.render.use_stamp_scene = True
    bpy.context.scene.render.use_stamp_camera = False
    
    
    
    

    
    bpy.context.scene.render.use_stamp_note = True
  
    bpy.context.scene.render.use_stamp_filename = False

    
    
    

def unregister():
    bpy.utils.unregister_class(RAHA_OT_ActivateHUD)
    bpy.utils.unregister_class(VIEW3D_OT_ToggleSafeArea)
    bpy.utils.unregister_class(VIEW3D_OT_DeleteSafeAreaImage)
    bpy.utils.unregister_class(VIEW3D_PT_HUDPanel)
    
    del bpy.types.Scene.raha_show_stamp_settings

    del bpy.types.Scene.raha_hud_use_custom_path
    del bpy.types.Scene.raha_hud_custom_path

    del bpy.types.Scene.use_stamp_date
    del bpy.types.Scene.use_stamp_time
    del bpy.types.Scene.use_stamp_render_time
    del bpy.types.Scene.use_stamp_frame
    del bpy.types.Scene.use_stamp_frame_range
    del bpy.types.Scene.use_stamp_memory
    del bpy.types.Scene.use_stamp_hostname
    del bpy.types.Scene.use_stamp_camera
    del bpy.types.Scene.use_stamp_lens
    del bpy.types.Scene.use_stamp_scene
    del bpy.types.Scene.use_stamp_marker
    del bpy.types.Scene.use_stamp_filename
    del bpy.types.Scene.use_stamp_sequencer_strip
    del bpy.types.Scene.use_stamp_note

if __name__ == "__main__":
    register()
