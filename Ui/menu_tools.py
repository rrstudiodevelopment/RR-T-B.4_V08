
import bpy
import webbrowser
import os
import requests
import bpy.utils.previews
import atexit
import shutil
import getpass
import ctypes

#============================ Download image ===========================
# Konstanta dan variabel global
FOLDER_ID = "1ovu2YSN-rPmvBp7a-G_w1lNS4uEGpEFN"
API_KEY = "AIzaSyD5epC5ofWTgh0PvAbLVy28W34NnwkkNyM"
USERNAME = getpass.getuser()
TEMP_DIR = f"C:\\Users\\{USERNAME}\\AppData\\Local\\Temp"
IMAGE_FOLDER = os.path.join(TEMP_DIR, "download_image")
CACHED_IMAGE_PATH = os.path.join(IMAGE_FOLDER, "google_drive_image.jpg")
IS_DOWNLOADED = False
preview_collections = {}

def remove_readonly(func, path, _):
    """Mengubah atribut file agar bisa dihapus."""
    os.chmod(path, 0o777)
    func(path)

def ensure_image_folder():
    """Hapus folder jika ada, lalu buat ulang."""
    if os.path.exists(IMAGE_FOLDER):
        shutil.rmtree(IMAGE_FOLDER, onerror=remove_readonly)
    os.makedirs(IMAGE_FOLDER)

def get_image_url():
    """Mencari gambar 'news' terlebih dahulu, jika tidak ada cari 'RRS-logo' di Google Drive."""
    url = f"https://www.googleapis.com/drive/v3/files?q='{FOLDER_ID}'+in+parents&key={API_KEY}&fields=files(id,name,mimeType)"
    try:
        response = requests.get(url)
        data = response.json()
        
        if "files" in data and data["files"]:
            for file in data["files"]:
                if "news" in file["name"].lower() and file["mimeType"].startswith("image/"):
                    return f"https://drive.google.com/uc?export=view&id={file['id']}"
            for file in data["files"]:
                if "rrs-logo" in file["name"].lower() and file["mimeType"].startswith("image/"):
                    return f"https://drive.google.com/uc?export=view&id={file['id']}"
    except Exception as e:
        print(f"Error mengambil data dari Google Drive: {e}")
    return None

def download_image():
    """Download gambar hanya jika belum ada."""
    global IS_DOWNLOADED
    ensure_image_folder()
    
    img_url = get_image_url()
    if not img_url:
        return None
    
    try:
        response = requests.get(img_url, stream=True)
        if response.status_code == 200:
            with open(CACHED_IMAGE_PATH, 'wb') as file:
                file.write(response.content)
            print(f"Gambar berhasil diunduh: {CACHED_IMAGE_PATH}")
            IS_DOWNLOADED = True
            return CACHED_IMAGE_PATH
    except Exception as e:
        print(f"Error mengunduh gambar: {e}")
    return None
#=====================================================================================================================

#                   SLIDE INFLUENCE    

def get_copy_constraints(bone):
    constraint_rot = next((c for c in bone.constraints if c.type == 'COPY_ROTATION' and c.name.startswith("CopasRot")), None)
    constraint_loc = next((c for c in bone.constraints if c.type == 'COPY_LOCATION' and c.name.startswith("CopasPos")), None)
    return constraint_rot, constraint_loc

    
# Fungsi untuk memperbarui influence kedua constraint
def update_constraints_influence(self, context):
    bone = self
    constraint_rot, constraint_loc = get_copy_constraints(bone)
    
    if constraint_rot:
        constraint_rot.influence = bone.copy_constraints_influence
        constraint_rot.keyframe_insert("influence", frame=bpy.context.scene.frame_current)
    
    if constraint_loc:
        constraint_loc.influence = bone.copy_constraints_influence
        constraint_loc.keyframe_insert("influence", frame=bpy.context.scene.frame_current)

# Pastikan property di bone sudah ada agar bisa diubah di UI
bpy.types.PoseBone.copy_constraints_influence = bpy.props.FloatProperty(
    name="Constraints Influence",
    default=1.0,
    min=0.0,
    max=1.0,
    update=update_constraints_influence
)

#============================================= Panel info ==================================
class RAHA_OT_InfoPopup(bpy.types.Operator):
    """Info update"""
    bl_idname = "raha.info_update"
    bl_label = "Info update"

    def execute(self, context):
        def draw_popup(self, context):
            layout = self.layout
            
            col = layout.column()
            col.label(text="update 09/08/2025 - 14:30")
            col.label(text="Raha Tools v08 (beta) blender 4++")            
            col.separator() 
            col.label(text="- ")
                                   
            col.label(text="- lots of updates")
            col.label(text="- Restrictions: only Indonesian users are allowed to use it")
            col.label(text="- snap fk-ik")
            col.separator()
            col.label(text="- update smart bake - fake constraint")
#            col.label(text="- )        
#            col.separator()
#            col.operator("raha.pb_tool", text="How to Use")            
 #           col.operator("raha.pb_tool", text="Report A Bug")          
        
        bpy.context.window_manager.popup_menu(draw_popup, title="Info", icon='INFO')
        return {'FINISHED'}    
    
    
#========================================== KEY MAP ===============================================================     
    
import bpy
import os
import shutil
import tempfile


TEMP_KEYMAP_DIR = os.path.join(tempfile.gettempdir(), "keymap_temp")
os.makedirs(TEMP_KEYMAP_DIR, exist_ok=True)

def get_keymap_presets(self, context):
    presets_dir = os.path.join(bpy.utils.resource_path('LOCAL'), "scripts", "presets", "keyconfig")
    items = []

    # Tambahkan keymap bawaan Blender
    if os.path.isdir(presets_dir):
        for file in os.listdir(presets_dir):
            if file.endswith(".py"):
                name = os.path.splitext(file)[0]
                full_path = os.path.join(presets_dir, file)
                items.append((full_path, f"{name}", ""))

    # Tambahkan keymap dari luar (disalin ke TEMP)
    if os.path.isdir(TEMP_KEYMAP_DIR):
        for file in os.listdir(TEMP_KEYMAP_DIR):
            if file.endswith(".py"):
                name = os.path.splitext(file)[0]
                full_path = os.path.join(TEMP_KEYMAP_DIR, file)
                items.append((full_path, f"{name}", ""))

    items.sort(key=lambda x: x[1])
    return items

def update_keymap(self, context):
    path = context.scene.keymap_ui_enum
    if os.path.isfile(path):
        bpy.ops.preferences.keyconfig_activate(filepath=path)

bpy.types.Scene.keymap_ui_enum = bpy.props.EnumProperty(
    name="Keymap",
    description="Pilih keymap preset",
    items=get_keymap_presets,
    update=update_keymap
)

class KEYMAP_OT_OpenPrefs(bpy.types.Operator):
    bl_idname = "keymap.open_preferences"
    bl_label = "Edit Keymap"
    bl_description = "Buka Preferences > Keymap"

    def execute(self, context):
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        context.preferences.active_section = 'KEYMAP'
        return {'FINISHED'}

class KEYMAP_OT_Import(bpy.types.Operator):
    bl_idname = "keymap.import_preset"
    bl_label = "Import Keymap dari File"
    bl_description = "Impor preset keymap dari file eksternal"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            if not self.filepath.lower().endswith(".py"):
                self.report({'ERROR'}, "File harus berekstensi .py")
                return {'CANCELLED'}

            dest_path = os.path.join(TEMP_KEYMAP_DIR, os.path.basename(self.filepath))
            shutil.copy2(self.filepath, dest_path)
            context.scene.keymap_ui_enum = dest_path
            self.report({'INFO'}, "Keymap berhasil diimpor dan diaktifkan")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Gagal mengimpor: {e}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class DeleteCustomKeymapOperator(bpy.types.Operator):
    bl_idname = "wm.delete_custom_keymap"
    bl_label = "Delete Custom Keymap"
    bl_description = "Hapus keymap yang diimpor secara manual"

    keymap_name: bpy.props.StringProperty()

    def execute(self, context):
        wm = context.window_manager
        keyconfigs = wm.keyconfigs

        try:
            temp_path = os.path.join(TEMP_KEYMAP_DIR, f"{self.keymap_name}.py")

            if os.path.exists(temp_path):
                os.remove(temp_path)
                self.report({'INFO'}, f"Keymap '{self.keymap_name}' berhasil dihapus.")
            else:
                self.report({'WARNING'}, f"Tidak ditemukan: {temp_path}")

            # Coba kembalikan ke keymap default Blender
            if "Blender" in keyconfigs:
                keyconfigs.active = keyconfigs["Blender"]
            else:
                # Jika Blender tidak ada, fallback ke keymap pertama
                keyconfigs.active = list(keyconfigs.values())[0]
                self.report({'INFO'}, f"Fallback ke keymap: {keyconfigs.active.name}")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Gagal hapus: {e}")
            return {'CANCELLED'}
    
#=========================================== Panel UI Menu Tools ========================================================
class RAHA_PT_Tools_For_Animation(bpy.types.Panel):
    """Panel tambahan yang muncul setelah Run Tools ditekan"""
    bl_label = "Raha Tools blender 4+"
    bl_idname = "RAHA_PT_For_Animation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Raha_Tools"
    bl_order = 1
    
    preview_collection = None 

    def draw(self, context):
        layout = self.layout
        wm = bpy.context.window_manager  # Pastikan ini ada sebelum digunakan        
        obj = context.object
        scene = context.scene   
        scn = context.scene
        wm = context.window_manager
        keyconfigs = wm.keyconfigs                
        
        preview_collection = None             

        if not IS_DOWNLOADED:  # Download hanya sekali saat pertama kali
            download_image()

        img_path = CACHED_IMAGE_PATH if os.path.exists(CACHED_IMAGE_PATH) else None

        if img_path:
            if RAHA_PT_Tools_For_Animation.preview_collection is None:
                RAHA_PT_Tools_For_Animation.preview_collection = bpy.utils.previews.new()
                RAHA_PT_Tools_For_Animation.preview_collection.load("google_drive_image", img_path, 'IMAGE')

            layout.template_icon(RAHA_PT_Tools_For_Animation.preview_collection["google_drive_image"].icon_id, scale=10)
        else:
            layout.label(text="Gambar tidak ditemukan")
            
        
#============================ SUbscribe DOnate  ====================================================

        row = layout.row()
        row.alignment = 'RIGHT'
        row.operator("raha.subscribe", text="", icon='PLAY')            
        row.operator("raha.donate", text="", icon='FUND')  
        row.operator("raha.info_update", text="", icon='INFO')         
                       
#===================================== KEY MAP UI ===========================================

        row = layout.row(align=True)
        
        row.prop(scn, "keymap_ui_enum", text="Keymap")  
        row.operator("keymap.open_preferences", text="", icon="PREFERENCES")
        row.operator("keymap.import_preset", text="", icon="IMPORT")         

        # Tampilkan tombol Delete jika keymap berada di folder TEMP
        active_name = keyconfigs.active.name
        temp_file_path = os.path.join(TEMP_KEYMAP_DIR, f"{active_name}.py")

        if os.path.exists(temp_file_path):
            op = row.operator("wm.delete_custom_keymap", text="", icon='TRASH')
            op.keymap_name = active_name
                        
#==================================== Studio lib + Mini Tools =========================================                     
        row = layout.row(align=True)     
        row.operator("floating.open_import_animation", text="STUDIO LIBRARY ")
        row.operator("floating.open_mini_tools", text="MINI TOOLS")         
    
 # ===================================== AHP ============================================== 
        # Header collapse + tombol info
        row = layout.row(align=True)
        row.prop(scene, "show_pb_tools", text="", icon='TRIA_DOWN' if scene.show_pb_tools else 'TRIA_RIGHT', emboss=False)
        row.label(text="AHP")

        if scene.show_pb_tools:


            # Baris pertama: tombol INFO di kanan atas

            row.alignment = 'RIGHT'
            row.operator("wm.open_youtube_info", text="", icon='INFO')
            
            box = layout.box()
            row = box.row()            
            # Baris berikutnya: tombol AUDIO dan HUD
            row = box.row(align=True)
            row.operator("floating.open_audio", text="AUDIO", icon='SPEAKER')
            row.operator("floating.open_hud", text="HUD Safe Area", icon='SEQUENCE')

            # Tombol PLAYBLAST di baris tersendiri
            box.operator("floating.open_playblast", text="PLAYBLAST", icon='RENDER_ANIMATION')


        
#==================================== Tween Machine ===================================================================   
        row = layout.row(align=True)
        row.prop(scene, "show_tween_machine", text="", icon='TRIA_DOWN' if scene.show_tween_machine else 'TRIA_RIGHT', emboss=False)
        row.label(text="Tween Machine")
        
        # Jika checkbox dicentang, tampilkan tombol Tween Machine
        if scene.show_tween_machine:
            
            row.alignment = 'RIGHT'            
            row.operator("raha.tween_machine", text="", icon='INFO') 
                       
            layout.label(text="Tween Slider:")
            layout.prop(scene, "pose_breakdowner_factor", text="Factor")


            box = layout.box()
            row = box.row(align=True)
            
            row.label(text="Tween Button") 
            sub = row.row(align=True)                 
            row = box.row(align=True)
            sub = row.row(align=True)
    #        sub.operator("pose.apply_breakdowner_button", text="-1").factor = -1.0        
            sub.operator("pose.apply_breakdowner_button", text="0").factor = 0.0
            sub.operator("pose.apply_breakdowner_button", text="_").factor = 0.12
            sub.operator("pose.apply_breakdowner_button", text="_").factor = 0.25
            sub.operator("pose.apply_breakdowner_button", text="_").factor = 0.37
            sub.operator("pose.apply_breakdowner_button", text="T").factor = 0.5        
            # Tombol 6-10 (nilai positif)
            sub = row.row(align=True)
            sub.operator("pose.apply_breakdowner_button", text="_").factor = 0.62
            sub.operator("pose.apply_breakdowner_button", text="_").factor = 0.75
            sub.operator("pose.apply_breakdowner_button", text="_").factor = 0.87
            sub.operator("pose.apply_breakdowner_button", text="100").factor = 1.0

            row = box.row(align=True)
            row.label(text="OverShoot - +")  
            sub = row.row(align=True)              
            row = box.row(align=True)

            sub = row.row(align=True)
            sub.operator("pose.apply_breakdowner_button", text="-").factor = -0.50
            sub.operator("pose.apply_breakdowner_button", text="-").factor = -0.30
            sub.operator("pose.apply_breakdowner_button", text="-").factor = -0.10 
        
            sub.operator("pose.dummy_button", text="  T  ")

           
            sub.operator("pose.apply_breakdowner_button", text="+").factor = 1.10
            sub.operator("pose.apply_breakdowner_button", text="+").factor = 1.30
            sub.operator("pose.apply_breakdowner_button", text="+").factor = 1.50                      
            layout.label(text="==================================================")                
#================================ Menu parent conststraint ==================================================================      
#================================ Menu parent constraint ==================================================================      
        # Checkbox untuk menampilkan Tween Machine
        row = layout.row(align=True)
        row.prop(scene, "show_parent", text="", icon='TRIA_DOWN' if scene.show_parent else 'TRIA_RIGHT', emboss=False)
        row.label(text="Parent - Smart Bake")        

        if scene.show_parent:
            # Create main box for all parent constraint controls
            box = layout.box()
            
            # Info button at top right
            row = box.row()
            row.alignment = 'RIGHT'
            row.operator("raha.parent_constraint", text="", icon='INFO')
            
            # Main constraint buttons
            row = box.row(align=True)        
            row.operator("floating.open_childof", text="Child-of")
            row.operator("floating.open_locrote", text="Locrote")  
            
            # Additional tools
            box.operator("floating.open_smart_bake", text="Smart Bake")               

            # Separator
            box.separator()
            
            # Influence controls
            obj = context.object
            if obj and obj.pose:
                # Child Of influence
                for bone in obj.pose.bones:
                    if bone.bone.select:
                        constraints = [c for c in bone.constraints 
                                     if c.type == 'CHILD_OF' 
                                     and c.name.startswith("parent_child")]
                        for constraint in constraints:
                            row = box.row()
                            row.label(text=f"Child Of: {constraint.subtarget}")
                            row.prop(constraint, "influence", text="Influence Child off", slider=True)
                
                # LocRot influence
                for bone in obj.pose.bones:
                    if bone.bone.select:
                        constraint_rot, constraint_loc = get_copy_constraints(bone)
                        if constraint_rot or constraint_loc:
                            row = box.row()
                            row.label(text="LocRot Influence:")
                            # Use the bone property we defined earlier which has the update function
                            row.prop(bone, "copy_constraints_influence", text="influence Locrote", slider=True)
                            
                            # The actual constraint updates will be handled by the update_constraints_influence function
                            # that we connected to the bone property
                            
#================================ Menu Fake Constraint Dan Step SNap ==================================================================      
        # Checkbox untuk menampilkan Tween Machine
        row = layout.row(align=True)
        row.prop(scene, "show_step", text="", icon='TRIA_DOWN' if scene.show_step else 'TRIA_RIGHT', emboss=False)
        row.label(text="Fake Constraint & Step snap")        

        if scene.show_step:  # Ini yang diubah dari show_parent ke show_step
            # Create main box for all parent constraint controls
            box = layout.box()
            
            # Info button at top right
            row = box.row()
            row.alignment = 'RIGHT'
            row.operator("raha.step_snap", text="", icon='INFO')
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
                         

#========================================= Def Donate Link ===================================================
class RAHA_OT_Donate(bpy.types.Operator):
    """donasi"""
    bl_idname = "raha.donate"
    bl_label = "Donate"

    def execute(self, context):
        webbrowser.open("https://saweria.co/rrstudio26")
        return {'FINISHED'}
#========================================= Def Subcribe Link ===================================================    
class RAHA_OT_Subscribe(bpy.types.Operator):
    """subscribe"""
    bl_idname = "raha.subscribe"
    bl_label = "subscribe"

    def execute(self, context):
        webbrowser.open("https://www.youtube.com/@RR_STUDIO26")
        return {'FINISHED'}    

#========================================= Def Tutorial Tween Machine ===================================================    
class RAHA_OT_Tween_Machine_Tutor(bpy.types.Operator):
    """Tutorial Tween Machine"""
    bl_idname = "raha.tween_machine"
    bl_label = "Tween Machine"

    def execute(self, context):
        webbrowser.open("https://www.youtube.com/watch?v=x9gs3Sz8S_Q")
        return {'FINISHED'}  
    
#========================================= Def Tutorial Parent Constraint ===================================================    
class RAHA_OT_Parent_Constraint_Tutor(bpy.types.Operator):
    """Tutorial parent constraint"""
    bl_idname = "raha.parent_constraint"
    bl_label = "Parent Constraint"

    def execute(self, context):
        webbrowser.open("https://www.youtube.com/watch?v=zkUT4vZdL_8")
        return {'FINISHED'}     
    
#========================================= Def Tutorial Step-Snap ===================================================    
class RAHA_OT_Step_Snap_Tutor(bpy.types.Operator):
    """Tutorial Step - Snap"""
    bl_idname = "raha.step_snap"
    bl_label = "Step_Snap"

    def execute(self, context):
        webbrowser.open("https://www.youtube.com/watch?v=D_LfBv4v9QI")
        return {'FINISHED'}       


    
#================================================ Def untuk memunculkan PANEL Raha Tools For Animation ==========================
class RAHA_OT_RunTools(bpy.types.Operator):
    """Menampilkan tombol alat tambahan dan membuka tautan YouTube"""
    bl_idname = "raha.run_tween_machine"
    bl_label = "Run run machine"

    def execute(self, context):
        self.toggle_tools(context)  # Memanggil fungsi pertama
#        self.open_youtube()         # Memanggil fungsi kedua
        return {'FINISHED'}

    def toggle_tools(self, context):
        """Menampilkan / menyembunyikan alat tambahan"""
        if hasattr(context.window_manager, "show_raha_tools_For_Animation"):
            context.window_manager.show_raha_tools_For_Animation = not context.window_manager.show_raha_tools_For_Animation
        else:
            context.window_manager.show_raha_tools_For_Animation = True  
            

#    def open_youtube(self):
#        """Membuka tautan YouTube"""
#        webbrowser.open("https://www.youtube.com/@RR_STUDIO26")  
            
            
#============================================================================================================    

    
    
#========================================= panggil panel floating Save_Animation=========================== 
    
class FLOATING_OT_Open_Save_Animation(bpy.types.Operator):
    bl_idname = "floating.open_save_animation"
    bl_label = "Open_Save_Animation"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="OBJECT_PT_bone_keyframe", keep_open=True)  # Memanggil panel dari script kedua
        return {'FINISHED'}       
      
 
#========================================= panggil panel floating import animation =========================== 
    
class FLOATING_OT_Open_Import_Animation(bpy.types.Operator):
    """Animation-pose Library"""    
    bl_idname = "floating.open_import_animation"
    bl_label = "Open_import_Animation"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="VIDEO_PT_Browser", keep_open=True)  # Memanggil panel dari script kedua
        return {'FINISHED'}     
    
    
#========================================= panggil panel floating Child-of =========================== 
    
class FLOATING_OT_Open_panel_childof(bpy.types.Operator):
    bl_idname = "floating.open_childof"
    bl_label = "open_Open_childof"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="VIEW3D_PT_Raha_Parents", keep_open=True)  
        return {'FINISHED'}      
    
#========================================= panggil panel floating Locrote =========================== 
    
class FLOATING_OT_Open_panel_Locrote(bpy.types.Operator):
    bl_idname = "floating.open_locrote"
    bl_label = "open_Open_locrote"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="VIEW3D_PT_Raha_Parents_Locrote", keep_open=True)  

        return {'FINISHED'}          

#========================================= panggil panel Smart Bake =========================== 
    
class FLOATING_OT_Open_Smart_Bake(bpy.types.Operator):
    bl_idname = "floating.open_smart_bake"
    bl_label = "open_smart_bake"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="OBJECT_PT_bone_bake", keep_open=True)  
        return {'FINISHED'}   
#========================================= panggil panel Fake constraint - Step Snap =========================== 
    
class FLOATING_OT_Open_Fake_Step(bpy.types.Operator):
    bl_idname = "floating.open_fake_step"
    bl_label = "open_fake_step"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="OBJECT_PT_bone_matrix", keep_open=True)  
        return {'FINISHED'}         
    
#========================================= panggil panel VIEW3D_PT_mini_tools =========================== 
    
class FLOATING_OT_Open_Mini_tools(bpy.types.Operator):
    """a collection of familiar tools"""
    bl_idname = "floating.open_mini_tools"
    bl_label = "open_mini_tools"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="VIEW3D_PT_mini_tools", keep_open=True)  
        return {'FINISHED'}     
      

#========================================= panggil panel AUDIO =========================== 


class FLOATING_OT_open_audio(bpy.types.Operator):
    bl_idname = "floating.open_audio"
    bl_label = "Audio"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_audio_tools", keep_open=True)
        return {'FINISHED'}
    
#========================================= panggil panel HUD =========================== 

class FLOATING_OT_open_hud(bpy.types.Operator):
    bl_idname = "floating.open_hud"
    bl_label = "HUD"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_HUD", keep_open=True)
        return {'FINISHED'}
    
#========================================= panggil panel PLAYBLAST =========================== 


class FLOATING_OT_open_playblast(bpy.types.Operator):
    bl_idname = "floating.open_playblast"
    bl_label = "Playblast"

    def execute(self, context):
        bpy.ops.wm.call_panel(name="RAHA_PT_Tools_playblast", keep_open=True)
        return {'FINISHED'}
    
#============================================== Register ========================================    
def register():
    
    global preview_collections
    bpy.types.Scene.show_tween_machine = bpy.props.BoolProperty(
        name="Show Tween Machine", 
        description="Tampilkan tombol Tween Machine", 
        default=False
    )
    
    global preview_collections
    bpy.types.Scene.show_parent = bpy.props.BoolProperty(
        name="Show Parent", 
        description="Tampilkan tombol Parent", 
        default=False
    )  
    
    global preview_collections
    bpy.types.Scene.show_step = bpy.props.BoolProperty(
        name="Show Step", 
        description="Tampilkan tombol Step Snap", 
        default=False
    )              
    
    bpy.types.PoseBone.copy_constraints_influence = bpy.props.FloatProperty(
        name="Copy Constraints Influence",
        description="Control the influence of both Copy Location and Copy Rotation constraints",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_constraints_influence
    
    )


    # Pastikan koleksi preview sudah ada
    global preview_collections
    preview_collections["raha_previews"] = bpy.utils.previews.new()

    # Dapatkan path direktori tempat script ini berada
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Path ke ikon dalam folder yang sama dengan script
    icon_path = os.path.join(script_dir, "ICORRSTUDIO.png")

    if os.path.exists(icon_path):
        preview_collections["raha_previews"].load("raha_icon", icon_path, 'IMAGE')

#=============================== kEY-MAP ===================================================        

    bpy.types.Scene.keymap_ui_enum = bpy.props.EnumProperty(
        name="Keymap",
        description="Pilih keymap preset",
        items=get_keymap_presets,
        update=update_keymap
    )        
#================================================================================================ 

    bpy.utils.register_class(RAHA_OT_InfoPopup)
    bpy.utils.register_class(RAHA_OT_Donate)
    bpy.utils.register_class(RAHA_OT_Subscribe)
    bpy.utils.register_class(RAHA_OT_Tween_Machine_Tutor)         
    bpy.utils.register_class(RAHA_OT_Parent_Constraint_Tutor)
         
    bpy.utils.register_class(RAHA_OT_RunTools)

    bpy.utils.register_class(KEYMAP_OT_OpenPrefs) 
    bpy.utils.register_class(KEYMAP_OT_Import)  
    bpy.utils.register_class(DeleteCustomKeymapOperator)
         
     
#========================== Animation library ===================
    bpy.utils.register_class(FLOATING_OT_Open_Save_Animation)          
    bpy.utils.register_class(FLOATING_OT_Open_Import_Animation) 

#========================== childof dan locrote =============================    
    bpy.utils.register_class(FLOATING_OT_Open_panel_childof) 
    bpy.utils.register_class(FLOATING_OT_Open_panel_Locrote)

#========================== fake constraint dan step snap =============================      
    bpy.utils.register_class(FLOATING_OT_Open_Smart_Bake )
    bpy.utils.register_class(FLOATING_OT_Open_Fake_Step ) 
    bpy.utils.register_class(RAHA_OT_Step_Snap_Tutor )        
    
#========================== FLOATING_OT_Open_Mini_tools =============================      
    bpy.utils.register_class(FLOATING_OT_Open_Mini_tools ) 
     
#========================== FLOATING_OT_Open__Pb_Hud =============================      
    bpy.utils.register_class(FLOATING_OT_open_audio )   
    bpy.utils.register_class(FLOATING_OT_open_hud )  
    bpy.utils.register_class(FLOATING_OT_open_playblast )  
    
             
   
           
        
    
         
             
    bpy.utils.register_class(RAHA_PT_Tools_For_Animation)
     
    bpy.types.WindowManager.show_raha_tools_For_Animation = bpy.props.BoolProperty(default=False)
    
    download_image()


def unregister():
  
    
    bpy.utils.unregister_class(RAHA_OT_InfoPopup)
    bpy.utils.unregister_class(RAHA_OT_Donate)
    bpy.utils.unregister_class(RAHA_OT_Subscribe)    
    bpy.utils.unregister_class(RAHA_OT_RunTools)
    
    bpy.utils.unregister_class(SetBlenderKeymapOperator) 
    bpy.utils.unregister_class(SetMayaKeymapOperator)   
#========================== Animation library ====================
    bpy.utils.unregister_class(FLOATING_OT_Open_Save_Animation)  
    bpy.utils.unregister_class(FLOATING_OT_Open_Import_Animation) 
    bpy.utils.unregister_class(FLOATING_OT_Open_panel_POSE_LIB)   
#========================== child-of =============================     
    bpy.utils.unregister_class(FLOATING_OT_Open_panel_childof)  
    bpy.utils.unregister_class(FLOATING_OT_Open_panel_Locrote)     
    
#========================== fake constraint dan step snap =============================      

    bpy.utils.unregister_class(FLOATING_OT_Open_Smart_Bake )
    bpy.utils.unregister_class(FLOATING_OT_Open_Fake_Step )
    bpy.utils.unregister_class(RAHA_OT_Step_Snap_Tutor )     

#========================== FLOATING_OT_Open_Mini_tools =============================      
    bpy.utils.unregister_class(FLOATING_OT_Open_Mini_tools ) 
    
#========================== FLOATING_OT_Open__Pb_Hud =============================      
    bpy.utils.unregister_class(FLOATING_OT_open_audio )   
    bpy.utils.unregister_class(FLOATING_OT_open_hud )  
    bpy.utils.unregister_class(FLOATING_OT_open_playblast )       
        
                      
       
    
    bpy.utils.unregister_class(RAHA_PT_Tools_For_Animation)
    del bpy.types.Scene.show_tween_machine

    if hasattr(bpy.types.WindowManager, "show_raha_tools_For_Animation"):
        delattr(bpy.types.WindowManager, "show_raha_tools_For_Animation")
    
    if "raha_previews" in preview_collections:
        bpy.utils.previews.remove(preview_collections["raha_previews"])
        del preview_collections["raha_previews"]

    if RAHA_PT_Tools_For_Animation.preview_collection:
        bpy.utils.previews.remove(RAHA_PT_Tools_For_Animation.preview_collection)
        RAHA_PT_Tools_For_Animation.preview_collection = None
        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.keymap_ui_enum        
        
if __name__ == "__main__":
    register()
