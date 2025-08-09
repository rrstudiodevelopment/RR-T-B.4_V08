
import bpy
import webbrowser
from bpy.props import FloatVectorProperty
from mathutils import Matrix
import json

# Dictionary to store bone matrices
stored_matrices = {}

#============================================ Anti-Lag ===================================================================
def update_simplify_subdivision(self, context):
    context.scene.render.simplify_subdivision = context.scene.simplify_subdivision

def pre_save_handler(dummy):
    scene = bpy.context.scene
    
    # Periksa apakah checkbox "Save Aman" aktif
    if not scene.get("save_aman", False):
        return  # Jika tidak aktif, tidak menjalankan script
    
    # Cek apakah use_simplify aktif
    if scene.render.use_simplify:
        scene.render.use_simplify = False
        print("Simplify dinonaktifkan sebelum menyimpan.")  
    
    # Ubah viewport shading ke wireframe
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'WIREFRAME'
                    print("Mode viewport diubah ke wireframe sebelum menyimpan.")
                    break

# ======================================= override_and_make_local  LINK  =================================================

def override_and_make_local(self, context):
    selected_objects = context.selected_objects
    
    if not selected_objects:
        self.report({'WARNING'}, "No objects selected")
        return {'CANCELLED'}
    
    for obj in selected_objects:
        bpy.context.view_layer.objects.active = obj  # Set active object
        bpy.ops.object.make_override_library()  # Override Library
        bpy.ops.object.make_local(type='SELECT_OBJECT')  # Make Local
    
    self.report({'INFO'}, "Overrides and Locals Applied")
    return {'FINISHED'}

class OBJECT_OT_OnlyOverride(bpy.types.Operator):
    """Hanya Make Override Library (tanpa Make Local)"""
    bl_idname = "object.only_override"
    bl_label = "Make Override Only"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.make_override_library()

        self.report({'INFO'}, "Only Override Applied")
        return {'FINISHED'}


#operator tombol untuk override
class OBJECT_OT_OverrideLocal(bpy.types.Operator):
    """Convert selected objects to override and make them local"""
    bl_idname = "object.override_local"
    bl_label = "Override & Make Local"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        return override_and_make_local(self, context)  
     
# Tambahkan properti checkbox dan slider di Scene
bpy.types.Scene.save_aman = bpy.props.BoolProperty(
    name="Save Aman",
    description="Aktifkan untuk menjalankan script sebelum menyimpan",
    default=False
)

bpy.types.Scene.simplify_subdivision = bpy.props.IntProperty(
    name="Simplify Subdivision",
    description="Atur nilai simplify subdivision",
    default=2,
    min=0,
    max=10,
    update=update_simplify_subdivision
)

# Mendaftarkan fungsi pre_save_handler ke event penyimpanan
bpy.app.handlers.save_pre.append(pre_save_handler)    
#=======================================================================================================================
 # CURSOR SELECTED 

class OBJECT_OT_CursorToSelected(bpy.types.Operator):
    """Move Cursor to Selected Bone (Shift+S, then 2 on numpad)"""
    bl_idname = "object.cursor_to_selected"
    bl_label = "Cursor to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object and context.active_object.type == 'ARMATURE':
            bpy.ops.view3d.snap_cursor_to_selected()
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Please select bones in Pose Mode!")
            return {'CANCELLED'}

class OBJECT_OT_SelectToCursor(bpy.types.Operator):
    """Move Selected Bone to Cursor (Shift+S, then 8 on numpad)"""
    bl_idname = "object.select_to_cursor"
    bl_label = "Select to Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object and context.active_object.type == 'ARMATURE':
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Please select bones in Pose Mode!")
            return {'CANCELLED'}
# ======================================================================================================================
#                                  ALLIGN TOOLS

class OBJECT_OT_AlignTool(bpy.types.Operator):
    """Apply Copy Rotation and Location Constraints"""
    bl_idname = "pose.align_tool"
    bl_label = "Align Tool"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Please switch to Pose Mode!")
            return {'CANCELLED'}

        selected_bones = context.selected_pose_bones
        active_bone = context.active_pose_bone

        if len(selected_bones) < 2 or active_bone is None:
            self.report({'WARNING'}, "Please select at least 2 bones and ensure one is active!")
            return {'CANCELLED'}

        target_bone = active_bone
        source_bone = next((bone for bone in selected_bones if bone != target_bone), None)

        if not source_bone:
            self.report({'ERROR'}, "Unable to determine the source bone!")
            return {'CANCELLED'}

        # Add Copy Rotation and Copy Location Constraints
        copy_rot_constraint = source_bone.constraints.new(type='COPY_ROTATION')
        copy_rot_constraint.name = "CopasRot"
        copy_rot_constraint.target = context.object
        copy_rot_constraint.subtarget = target_bone.name

        copy_loc_constraint = source_bone.constraints.new(type='COPY_LOCATION')
        copy_loc_constraint.name = "CopasPos"
        copy_loc_constraint.target = context.object
        copy_loc_constraint.subtarget = target_bone.name

        # Apply constraints
        bpy.context.view_layer.update()
        bpy.ops.pose.visual_transform_apply()

        # Remove constraints
        source_bone.constraints.remove(copy_rot_constraint)
        source_bone.constraints.remove(copy_loc_constraint)

        self.report({'INFO'}, f"Applied Align Tool: {target_bone.name} to {source_bone.name}")
        return {'FINISHED'}
 #====================================================================================================================
 
 #                                      COPY ROTATE    
 
 # Operator untuk Auto Copy Rotation Constraint
class OBJECT_OT_CopyRotation(bpy.types.Operator):
    """Copy Rotation from Selected Bone to Active"""
    bl_idname = "pose.auto_copy_rotation_constraint"
    bl_label = "Auto Copy Rotation Constraint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Ensure the operator is run in Pose Mode with at least two bones selected
        if not context.mode == 'POSE':
            self.report({'WARNING'}, "Please switch to Pose Mode!")
            return {'CANCELLED'}

        selected_bones = context.selected_pose_bones
        active_bone = context.active_pose_bone

        if len(selected_bones) < 2 or active_bone is None:
            self.report({'WARNING'}, "Please select at least 2 bones and ensure one is active!")
            return {'CANCELLED'}

        # Active bone as target (second selected bone)
        target_bone = active_bone

        # Determine the source bone (the other bone in the selection)
        source_bone = next((bone for bone in selected_bones if bone != target_bone), None)

        if not source_bone:
            self.report({'ERROR'}, "Unable to determine the source bone!")
            return {'CANCELLED'}

        # Add a Copy Rotation Constraint to the source bone
        constraint = source_bone.constraints.new(type='COPY_ROTATION')
        constraint.name = "CopasRot"
        constraint.target = context.object  # Armature object
        constraint.subtarget = target_bone.name  # Set target to the active bone

        # Update the scene to ensure constraints are applied correctly
        bpy.context.view_layer.update()

        # Apply the constraint (Ctrl + A equivalent in Blender for pose transforms)
        bpy.ops.pose.visual_transform_apply()

        # Remove the constraint after applying (to bake the transformation)
        source_bone.constraints.remove(constraint)

        self.report({'INFO'}, f"Copy Rotation Constraint applied from {target_bone.name} to {source_bone.name}.")
        return {'FINISHED'}
    
#======================================= Copy Miror ============================================================= 
class OBJECT_OT_CopyMirrorPose(bpy.types.Operator):
    """Copy Pose and Mirror it to the other side"""
    bl_idname = "pose.copy_mirror_pose"
    bl_label = "Copy Mirror Pose"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Switch to Pose Mode to use this.")
            return {'CANCELLED'}

        bpy.ops.pose.copy()
        bpy.ops.pose.paste(flipped=True)
        self.report({'INFO'}, "Pose copied and mirrored.")
        return {'FINISHED'}
    
    
       

#=========================================================================================================================
class FLOATING_OT_Decimate_Temporary(bpy.types.Operator):
    bl_idname = "floating.open_decimate_temporary"
    bl_label = "open_decimate_temporary"
    
    def execute(self, context):
        bpy.ops.wm.call_panel(name="VIEW3D_PT_decimate_panel", keep_open=True)  
        return {'FINISHED'}  



# ==================== Properties ====================
class PoseCopyPasteProps(bpy.types.PropertyGroup):
    flipped: bpy.props.BoolProperty(
        name="Flipped Paste",
        description="Paste pose as mirror",
        default=False
    )

# ==================== Operators ====================
class POSE_OT_CopyPose(bpy.types.Operator):
    bl_idname = "pose_tools.copy_pose"
    bl_label = "Copy Pose"
    bl_description = "Copy current pose"

    def execute(self, context):
        bpy.ops.pose.copy()
        self.report({'INFO'}, "Pose copied")
        return {'FINISHED'}


class POSE_OT_PastePose(bpy.types.Operator):
    bl_idname = "pose_tools.paste_pose"
    bl_label = "Paste Pose"
    bl_description = "Paste pose normally (not flipped)"

    def execute(self, context):
        bpy.ops.pose.paste(flipped=False)
        self.report({'INFO'}, "Pose pasted")
        return {'FINISHED'}


class POSE_OT_PastePoseFlipped(bpy.types.Operator):
    bl_idname = "pose_tools.paste_pose_flipped"
    bl_label = "Paste Mirror"
    bl_description = "Paste pose as mirror (flipped)"

    def execute(self, context):
        bpy.ops.pose.paste(flipped=True)
        self.report({'INFO'}, "Pose pasted (flipped)")
        return {'FINISHED'}
    
        
#=========================================================================================================================
############# ADD CONTROLER ############################################# 


import bpy
from mathutils import Matrix

class OBJECT_OT_add_controler(bpy.types.Operator):
    bl_idname = "object.add_controler"
    bl_label = "Add Controller"
    bl_description = "Membuat controller armature dengan transformasi yang sama dengan bone aktif (pose mode) atau di origin (object mode)"
    
    def execute(self, context):
        # === 1. Persiapan Awal ===
        # Simpan mode dan seleksi awal untuk dikembalikan nanti
        current_mode = context.mode
        original_active = context.active_object
        original_selected = context.selected_objects.copy()
        
        # Variabel untuk menyimpan transformasi dari bone sumber (jika di pose mode)
        source_bone_matrix = None
        source_rig = None
        
        # === 2. Handle Pose Mode ===
        # Jika operator dijalankan di pose mode dengan bone aktif
        if current_mode == 'POSE' and context.active_pose_bone:
            source_rig = context.active_object
            bone = context.active_pose_bone
            
            # Simpan transformasi GLOBAL bone:
            # Matrix world armature * matrix local bone = matrix global bone
            source_bone_matrix = source_rig.matrix_world @ bone.matrix
            
            # Catat nama bone untuk debug
            print(f"Menyalin transform dari bone: {bone.name} di armature: {source_rig.name}")
            
            # Beralih ke object mode sementara untuk membuat controller
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # === 3. Pastikan Object Mode ===
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # === 4. Buat Curve sebagai Custom Shape ===
        bpy.ops.curve.primitive_bezier_circle_add(
            enter_editmode=False, 
            align='WORLD', 
            location=(0, 0, 0), 
            scale=(1, 1, 1)
        )
        curve_obj = context.active_object
        curve_obj.name = "For_add_CTRL_BezierCircle"
        
        # === 5. Buat Armature Controller ===
        bpy.ops.object.armature_add(
            enter_editmode=False, 
            align='WORLD', 
            location=(0, 0, 0)
        )
        ctrl_armature = context.active_object
        ctrl_armature.name = "add_ctrl_armature"
        
        # === 6. Edit Bones ===
        bpy.ops.object.editmode_toggle()
        
        # Dapatkan referensi ke edit bones
        armature_data = ctrl_armature.data
        bone1 = armature_data.edit_bones[0]
        
        # Setup bone induk
        bone1.name = "induk"
        bone1.head = (0, 0, 0)
        bone1.tail = (0, 0, 1)  # Panjang default
        
        # Buat bone child
        bone2 = armature_data.edit_bones.new("child")
        bone2.head = (0, 0, 0)
        bone2.tail = (0, 0, 1)
        bone2.parent = bone1
        bone2.use_connect = False  # Parent tanpa koneksi visual
        
        bpy.ops.object.editmode_toggle()
        
        # === 7. Setup Pose Bones ===
        bpy.ops.object.posemode_toggle()
        
        # Assign custom shape untuk semua bones
        for bone_name in ["induk", "child"]:
            pose_bone = ctrl_armature.pose.bones[bone_name]
            
            # Setup dasar
            pose_bone.rotation_mode = 'XYZ'
            pose_bone.custom_shape = curve_obj
            pose_bone.custom_shape_rotation_euler[0] = 1.5708  # Rotasi 90 derajat di sumbu X
            
            # Bedakan ukuran induk dan child
            if bone_name == "induk":
                pose_bone.custom_shape_scale_xyz = (1.3, 1.3, 1.3)
        
        bpy.ops.object.posemode_toggle()
        
        # === 8. Organisasi Koleksi ===
        collection_name = "ETC"
        if collection_name not in bpy.data.collections:
            bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(bpy.data.collections[collection_name])
        
        # Pindahkan semua objek ke koleksi ETC
        for obj in [curve_obj, ctrl_armature]:
            # Hapus dari koleksi lama
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            # Tambahkan ke koleksi baru
            bpy.data.collections[collection_name].objects.link(obj)
        
        # === 9. Bersihkan Curve ===
        bpy.ops.object.select_all(action='DESELECT')
        curve_obj.select_set(True)
        bpy.ops.object.delete()
        
        # === 10. Handle Transformasi dari Pose Mode ===
        if source_bone_matrix and source_rig:
            print("Memulai proses paste transform...")
            
            # Select armature control dan source
            bpy.ops.object.select_all(action='DESELECT')
            ctrl_armature.select_set(True)
            source_rig.select_set(True)
            context.view_layer.objects.active = source_rig
            
            # Masuk ke pose mode bersama
            bpy.ops.object.posemode_toggle()
            
            # Pilih bone induk di control armature
            bpy.ops.pose.select_all(action='DESELECT')
            ctrl_armature.pose.bones["induk"].bone.select = True
            context.view_layer.objects.active = ctrl_armature
            
            # Hitung transformasi LOCAL untuk bone controller:
            # matrix_world control armature -> ke local -> matrix global bone sumber
            local_matrix = ctrl_armature.matrix_world.inverted() @ source_bone_matrix
            
            # Terapkan langsung ke matrix bone
            ctrl_armature.pose.bones["induk"].matrix = local_matrix
            
            # Pastikan rotasi dalam mode XYZ
            ctrl_armature.pose.bones["induk"].rotation_mode = 'XYZ'
            
            print("Transformasi berhasil dipaste!")
            
            # Bersihkan seleksi
            bpy.ops.pose.select_all(action='DESELECT')
            
            # === 11. Kembalikan Seleksi Awal ===
            if original_active:
                # Coba select objek asli jika masih ada
                try:
                    original_active.select_set(True)
                    context.view_layer.objects.active = original_active
                except:
                    pass
            
            # Kembalikan ke mode awal jika bukan pose mode
            if current_mode != 'POSE':
                bpy.ops.object.mode_set(mode=current_mode.lower().replace('_pose', ''))
        
        return {'FINISHED'}


#=====================================================================================================================  

#  ======================================================  TOMBOL ============================================== 






class VIEW3D_PT_MiniTools(bpy.types.Panel):
    bl_label = "Raha Mini Tools"
    bl_idname = "VIEW3D_PT_mini_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'    
    bl_ui_units_x = 10

    def draw_setter(self, layout, label, slot_name, value):
        row = layout.row(align=True)
        row.label(text=f"{label}: {value if value else '(Not set)'}")
        op = row.operator("pose.set_custom_bone", text="", icon="BONE_DATA")
        op.slot_name = slot_name

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.use_property_split = True
        layout.use_property_decorate = False  

        # ==================== SAFETY & SIMPLIFY ====================
        safety_box = layout.box()
        safety_box.label(text="Performance", icon='TIME')               
        safety_box.prop(scene, "save_aman", text="Safety Mode", icon='LOCKED' if scene.save_aman else 'UNLOCKED')
        safety_box.prop(scene.render, "use_simplify", text="Simplify Render")
        
        if scene.render.use_simplify:
            simplify_row = safety_box.row()
            simplify_row.prop(scene, "simplify_subdivision", text="Subdivision", slider=True)
        
        # ==================== LINK TOOLS ====================
        link_box = layout.box()
        link_box.label(text="Linking Tools", icon='LINKED')
        
        flow = link_box.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
        flow.operator("object.only_override", text="Make Override", icon="LINKED")
        flow.operator("object.override_local", text="Local Override", icon="FILE_TICK")
        
        # ==================== ALIGNMENT TOOLS ====================
        align_box = layout.box()
        align_box.label(text="Bone Alignment", icon='BONE_DATA')
        
        align_grid = align_box.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        align_grid.operator("object.cursor_to_selected", text="", icon="CURSOR")
        align_grid.operator("object.select_to_cursor", text="", icon="PIVOT_CURSOR")
        align_grid.operator("pose.align_tool", text="", icon="CON_TRANSFORM")

        # --- SNAP FK/IK SECTION ---
        align_box.separator()
        snap_header = align_box.row()               
        snap_header.label(text="FK/IK Snapping")
        snap_header.prop(scene, "snap_mode", text="")

        snap_content = align_box.box()

        if scene.snap_mode == 'DEFAULT':
            suffix = '.L'
            active_bone = context.active_pose_bone
            if active_bone:
                if active_bone.name.endswith('.R'):
                    suffix = '.R'
                elif active_bone.name.endswith('.L'):
                    suffix = '.L'

            snap_buttons = snap_content.row(align=True)
            snap_buttons.scale_y = 1.2
            
            op = snap_buttons.operator("pose.snap_fk_to_ik_custom", 
                                    text=f"FK → IK ({suffix})",
                                    icon='EVENT_RIGHT_ARROW')
            op.input_bones = json.dumps([
                f"upper_arm_ik{suffix}",
                f"MCH-forearm_ik{suffix}",
                f"MCH-upper_arm_ik_target{suffix}"
            ])
            op.output_bones = json.dumps([
                f"upper_arm_fk{suffix}",
                f"forearm_fk{suffix}",
                f"hand_fk{suffix}"
            ])
            op.is_rigify_default = True

            snap_buttons.separator()
            
            op2 = snap_buttons.operator("pose.snap_ik_to_fk_custom", 
                                    text=f"IK → FK ({suffix})",
                                    icon='EVENT_LEFT_ARROW')
            op2.fk_bones = json.dumps([
                f"upper_arm_fk{suffix}",
                f"forearm_fk{suffix}",
                f"hand_fk{suffix}"
            ])
            op2.ctrl_bones = json.dumps([
                f"upper_arm_ik{suffix}",
                f"upper_arm_ik_target{suffix}",
                f"hand_ik{suffix}"
            ])
            op2.is_rigify_default = True

            snap_content.label(text=f"Auto-detected {suffix} side bones", icon='INFO')

        elif scene.snap_mode == 'CUSTOM':
            fk_col = snap_content.column(align=True)
            fk_col.label(text="FK Bones:", icon='BONE_DATA')
            
            self.draw_setter(fk_col, "Upper Arm", "custom_fk_upper", scene.custom_fk_upper)
            self.draw_setter(fk_col, "Forearm", "custom_fk_forearm", scene.custom_fk_forearm)
            self.draw_setter(fk_col, "Hand", "custom_fk_hand", scene.custom_fk_hand)

            snap_content.separator()
            
            ik_col = snap_content.column(align=True)
            ik_col.label(text="IK Bones:", icon='CON_KINEMATIC')
            
            self.draw_setter(ik_col, "Upper Arm", "custom_ik_upper", scene.custom_ik_upper)
            self.draw_setter(ik_col, "Pole", "custom_ik_pole", scene.custom_ik_pole)
            self.draw_setter(ik_col, "Hand", "custom_ik_hand", scene.custom_ik_hand)

            snap_buttons = snap_content.row(align=True)
            snap_buttons.scale_y = 1.2
            
            op = snap_buttons.operator("pose.snap_fk_to_ik_custom", 
                                    text="FK → IK (Custom)",
                                    icon='EVENT_RIGHT_ARROW')
            op.input_bones = json.dumps([scene.custom_ik_upper, scene.custom_ik_pole, scene.custom_ik_hand])
            op.output_bones = json.dumps([scene.custom_fk_upper, scene.custom_fk_forearm, scene.custom_fk_hand])
            op.is_rigify_default = False

            snap_buttons.separator()
            
            op2 = snap_buttons.operator("pose.snap_ik_to_fk_custom", 
                                    text="IK → FK (Custom)",
                                    icon='EVENT_LEFT_ARROW')
            op2.fk_bones = json.dumps([scene.custom_fk_upper, scene.custom_fk_forearm, scene.custom_fk_hand])
            op2.ctrl_bones = json.dumps([scene.custom_ik_upper, scene.custom_ik_pole, scene.custom_ik_hand])
            op2.is_rigify_default = False
        
        # ==================== POSE TOOLS ====================
        pose_box = layout.box()
        pose_box.label(text="Pose Tools", icon='ARMATURE_DATA')
        
        pose_grid = pose_box.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        pose_grid.operator("pose.auto_copy_rotation_constraint", text="Copy Rotation", icon="AUTOMERGE_ON")
        pose_grid.operator("pose.copy_mirror_pose", text="Mirror Pose", icon="ARMATURE_DATA")  

        pose_grid = pose_box.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        pose_grid.operator("pose_tools.copy_pose", text="", icon='COPYDOWN')
        pose_grid.operator("pose_tools.paste_pose", text="", icon='PASTEDOWN')
        pose_grid.operator("pose_tools.paste_pose_flipped", text="", icon='MOD_MIRROR')        
        
        pose_box.operator("object.add_controler", text="Add Controller", icon="BONE_DATA")


# ================== REGISTER PROPERTIES ==================


# ================== PROPERTIES ANP FK IK ==================
def register_props():
    bpy.types.Scene.snap_mode = bpy.props.EnumProperty(
        name="mode",
        items=[
            ('DEFAULT', "Rigify Default", ""),
            ('CUSTOM', "Custom (Beta)", "")
        ],
        default='DEFAULT'
    )
    bpy.types.Scene.custom_fk_upper = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_fk_forearm = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_fk_hand = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_ik_upper = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_ik_pole = bpy.props.StringProperty(default="")
    bpy.types.Scene.custom_ik_hand = bpy.props.StringProperty(default="")


def unregister_props():
    del bpy.types.Scene.snap_mode
    del bpy.types.Scene.custom_fk_upper
    del bpy.types.Scene.custom_fk_forearm
    del bpy.types.Scene.custom_fk_hand
    del bpy.types.Scene.custom_ik_upper
    del bpy.types.Scene.custom_ik_pole
    del bpy.types.Scene.custom_ik_hand







                            
          
#=========================================================================================================================
#                                               REGISTER     
# Daftar operator dan panel untuk registrasi
def register():
    
    
    bpy.types.Scene.simplify_subdivision = bpy.props.IntProperty(
        name="Simplify Subdivision",
        description="Atur nilai simplify subdivision",
        default=5,
        min=0,
        max=10,
        update=update_simplify_subdivision
    )    
    
    bpy.utils.register_class(FLOATING_OT_Decimate_Temporary)     
    bpy.utils.register_class(OBJECT_OT_OverrideLocal)
    bpy.utils.register_class(OBJECT_OT_OnlyOverride)    
    
    bpy.utils.register_class(OBJECT_OT_CursorToSelected)
    bpy.utils.register_class(OBJECT_OT_SelectToCursor)
    bpy.utils.register_class(OBJECT_OT_AlignTool)
    bpy.utils.register_class(OBJECT_OT_CopyMirrorPose)     
    bpy.utils.register_class(OBJECT_OT_CopyRotation)  
         
              
    bpy.utils.register_class(VIEW3D_PT_MiniTools)    
    bpy.utils.register_class(OBJECT_OT_add_controler)      
    
    bpy.utils.register_class(PoseCopyPasteProps) 
    bpy.utils.register_class(POSE_OT_CopyPose)            
    bpy.utils.register_class(POSE_OT_PastePose) 
    bpy.utils.register_class(POSE_OT_PastePoseFlipped)      
    
   

        
# Fungsi untuk menghapus pendaftaran class dari Blender
def unregister():
    bpy.utils.unregister_class(FLOATING_OT_Decimate_Temporary)     
    bpy.utils.unregister_class(VIEW3D_PT_MiniTools)  
        
    bpy.utils.unregister_class(OBJECT_OT_OverrideLocal) 
    bpy.utils.unregister_class(OBJECT_OT_OnlyOverride)           
    
    bpy.utils.unregister_class(OBJECT_OT_add_controler)        
    bpy.utils.unregister_class(OBJECT_OT_CursorToSelected)
    bpy.utils.unregister_class(OBJECT_OT_SelectToCursor)
    bpy.utils.unregister_class(OBJECT_OT_CopyMirrorPose)     
    bpy.utils.unregister_class(OBJECT_OT_AlignTool)
    
    bpy.utils.unregister_class(PoseCopyPasteProps) 
    bpy.utils.unregister_class(POSE_OT_CopyPose)            
    bpy.utils.unregister_class(POSE_OT_PastePose) 
    bpy.utils.unregister_class(POSE_OT_PastePoseFlipped)      
        
    
  
    bpy.utils.unregister_class(OBJECT_OT_CopyRotation)  
    bpy.utils.unregister_class(SaveAmanPanel)
    del bpy.types.Scene.simplify_subdivision          
   
    del bpy.types.Scene.capsulman_tools_rotation

if __name__ == "__main__":
    register()
