import bpy

#============================ Utility ============================
def is_quaternion_mode(obj_or_bone):
    return getattr(obj_or_bone, "rotation_mode", "") == 'QUATERNION'

#============================ Operators ============================

class ApplyLocationOperator(bpy.types.Operator):
    bl_idname = "object.apply_location"
    bl_label = "Apply Location"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    for i in range(3):
                        if scene.custom_location_axes[i]:
                            bone.location[i] = scene.custom_location[i]
        else:
            for i in range(3):
                if scene.custom_location_axes[i]:
                    obj.location[i] = scene.custom_location[i]

        self.report({'INFO'}, "Applied Location")
        return {'FINISHED'}


class ResetLocationOperator(bpy.types.Operator):
    bl_idname = "object.reset_location"
    bl_label = "Reset Location"

    def execute(self, context):
        obj = context.active_object

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    bone.location = (0.0, 0.0, 0.0)
        else:
            obj.location = (0.0, 0.0, 0.0)

        self.report({'INFO'}, "Reset Location to default (0,0,0)")
        return {'FINISHED'}


class ApplyRotationOperator(bpy.types.Operator):
    bl_idname = "object.apply_rotation"
    bl_label = "Apply Rotation"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        def apply_rotation(target):
            if is_quaternion_mode(target):
                quat = target.rotation_quaternion.copy()
                for i in range(1, 4):  # x,y,z => index 1,2,3 (skip w)
                    if scene.custom_rotation_axes[i - 1]:
                        quat[i] = scene.custom_rotation[i - 1]
                target.rotation_quaternion = quat
            else:
                for i in range(3):
                    if scene.custom_rotation_axes[i]:
                        target.rotation_euler[i] = scene.custom_rotation[i]

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    apply_rotation(bone)
        else:
            apply_rotation(obj)

        self.report({'INFO'}, "Applied Rotation")
        return {'FINISHED'}


class ResetRotationOperator(bpy.types.Operator):
    bl_idname = "object.reset_rotation"
    bl_label = "Reset Rotation"

    def execute(self, context):
        obj = context.active_object

        def reset_rotation(target):
            if is_quaternion_mode(target):
                target.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            else:
                target.rotation_euler = (0.0, 0.0, 0.0)

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    reset_rotation(bone)
        else:
            reset_rotation(obj)

        self.report({'INFO'}, "Reset Rotation")
        return {'FINISHED'}


class ApplyScaleOperator(bpy.types.Operator):
    bl_idname = "object.apply_scale"
    bl_label = "Apply Scale"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    for i in range(3):
                        if scene.custom_scale_axes[i]:
                            bone.scale[i] = scene.custom_scale[i]
        else:
            for i in range(3):
                if scene.custom_scale_axes[i]:
                    obj.scale[i] = scene.custom_scale[i]

        self.report({'INFO'}, "Applied Scale")
        return {'FINISHED'}


class ResetScaleOperator(bpy.types.Operator):
    bl_idname = "object.reset_scale"
    bl_label = "Reset Scale"

    def execute(self, context):
        obj = context.active_object

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    bone.scale = (1.0, 1.0, 1.0)
        else:
            obj.scale = (1.0, 1.0, 1.0)

        self.report({'INFO'}, "Reset Scale")
        return {'FINISHED'}


class ResetAllOperator(bpy.types.Operator):
    bl_idname = "object.reset_all"
    bl_label = "Reset All"

    def execute(self, context):
        obj = context.active_object

        def reset(target):
            target.location = (0.0, 0.0, 0.0)
            target.scale = (1.0, 1.0, 1.0)
            if is_quaternion_mode(target):
                target.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            else:
                target.rotation_euler = (0.0, 0.0, 0.0)

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in obj.pose.bones:
                if bone.bone.select:
                    reset(bone)
        else:
            reset(obj)

        self.report({'INFO'}, "Reset All Transformations")
        return {'FINISHED'}


class ConvertRotationToEulerOperator(bpy.types.Operator):
    bl_idname = "object.convert_quaternion_to_euler"
    bl_label = "Convert Quaternion to Euler"

    def execute(self, context):
        obj = context.active_object

        if obj.type == 'ARMATURE' and obj.mode == 'POSE':
            for bone in context.selected_pose_bones:
                if bone.rotation_mode == 'QUATERNION':
                    bone.rotation_mode = 'XYZ'
        else:
            if obj.rotation_mode == 'QUATERNION':
                obj.rotation_mode = 'XYZ'

        self.report({'INFO'}, "Converted rotation to Euler")
        return {'FINISHED'}


#============================ UI Panel ============================

class SimpleTransformPanel(bpy.types.Panel):
    bl_label = "✦ Raha Transform Tools"
    bl_idname = "OBJECT_PT_transform_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Raha_Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object

        if not obj:
            layout.label(text="No active object selected", icon='ERROR')
            return

        # === Transform Panel Toggle ===
        layout.prop(scene, "panel_transform", toggle=True, icon='ORIENTATION_GLOBAL')

        if scene.panel_transform:
            col = layout.column(align=True)
            box = col.box()
            box.label(text="Active Object: " + obj.name, icon='OBJECT_DATAMODE')

            if obj.type == 'ARMATURE' and obj.mode == 'POSE':
                selected_bones = context.selected_pose_bones
                if selected_bones:
                    bone = selected_bones[0]
                    box.label(text=f"Bone Mode: {bone.rotation_mode}", icon='GESTURE_ROTATE')

                    col_b = box.column(align=True)
                    col_b.prop(bone, "location", text="Location")
                    col_b.operator("object.reset_location", text="Reset Location", icon='LOOP_BACK')

                    if bone.rotation_mode == 'QUATERNION':
                        col_b.prop(bone, "rotation_quaternion", text="Rotation")
                    else:
                        col_b.prop(bone, "rotation_euler", text="Rotation")
                    row = col_b.row(align=True)
                    row.operator("object.reset_rotation", text="Reset", icon='LOOP_BACK')
                    row.operator("object.convert_quaternion_to_euler", text="To Euler", icon='FILE_REFRESH')

                    col_b.prop(bone, "scale", text="Scale")
                    col_b.operator("object.reset_scale", text="Reset Scale", icon='LOOP_BACK')

                    col_b.operator("object.reset_all", text="Reset ALL", icon='FILE_REFRESH')
                else:
                    box.label(text="No pose bone selected", icon='INFO')
            else:
                box.label(text=f"Rotation Mode: {obj.rotation_mode}", icon='OBJECT_DATAMODE')
                col_b = box.column(align=True)

                col_b.prop(obj, "location", text="Location")
                col_b.operator("object.reset_location", text="Reset Location", icon='LOOP_BACK')

                if obj.rotation_mode == 'QUATERNION':
                    col_b.prop(obj, "rotation_quaternion", text="Rotation")
                else:
                    col_b.prop(obj, "rotation_euler", text="Rotation")
                row = col_b.row(align=True)
                row.operator("object.reset_rotation", text="Reset", icon='LOOP_BACK')
                row.operator("object.convert_quaternion_to_euler", text="To Euler", icon='FILE_REFRESH')

                col_b.prop(obj, "scale", text="Scale")
                col_b.operator("object.reset_scale", text="Reset Scale", icon='LOOP_BACK')

                col_b.operator("object.reset_all", text="Reset ALL", icon='FILE_REFRESH')

class SimpleTransformPanel(bpy.types.Panel):
    bl_label = "Raha Transform Panel"
    bl_idname = "OBJECT_PT_transform_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Raha_Tools'
    bl_order = 2    

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object

        if not obj:
            layout.label(text="No active object")
            return

        layout.prop(scene, "panel_transform", toggle=True)

        if scene.panel_transform:
            if obj.type == 'ARMATURE' and obj.mode == 'POSE':
                bones = context.selected_pose_bones
                if bones:
                    bone = bones[0]
                    layout.label(text=f"Rotation Mode: {bone.rotation_mode}", icon='GESTURE_ROTATE')
                    col = layout.column(align=True)
                    col.prop(bone, "location", text="Location")
                    col.operator("object.reset_location", text="Reset Location", icon='LOOP_BACK')

                    if bone.rotation_mode == 'QUATERNION':
                        col.prop(bone, "rotation_quaternion", text="Rotation")
                    else:
                        col.prop(bone, "rotation_euler", text="Rotation")
                      
                    row = col.row(align=True)
                    row.operator("object.reset_rotation", text="Reset", icon='LOOP_BACK')
                    row.operator("object.convert_quaternion_to_euler", text="To Euler", icon='CON_ROTLIKE')

                    col.prop(bone, "scale", text="Scale")
                    col.operator("object.reset_scale", text="Reset Scale", icon='LOOP_BACK')
                    col.operator("object.reset_all", text="Reset ALL", icon='RECOVER_LAST')
                else:
                    layout.label(text="No bones selected.")
            else:
                layout.label(text=f"Object Mode: {obj.rotation_mode}", icon='OBJECT_DATA')
                col = layout.column(align=True)
                col.prop(obj, "location", text="Location")
                col.operator("object.reset_location", text="Reset Location", icon='LOOP_BACK')

                if obj.rotation_mode == 'QUATERNION':
                    col.prop(obj, "rotation_quaternion", text="Rotation")
                else:
                    col.prop(obj, "rotation_euler", text="Rotation")
                row = col.row(align=True)
                row.operator("object.reset_rotation", text="Reset", icon='LOOP_BACK')
                row.operator("object.convert_quaternion_to_euler", text="To Euler", icon='CON_ROTLIKE')

                col.prop(obj, "scale", text="Scale")
                col.operator("object.reset_scale", text="Reset Scale", icon='LOOP_BACK')               
                col.operator("object.reset_all", text="Reset ALL", icon='RECOVER_LAST')

        # ======================== Edit Value Section ========================
        layout.prop(scene, "panel_edit_value", toggle=True)

        if scene.panel_edit_value:
            layout.label(text="Edit Value", icon='TOOL_SETTINGS')
            col = layout.column(align=True)

            # LOCATION
            col.label(text="Location", icon='EMPTY_AXIS')
            col.prop(scene, "custom_location", text="Value")
            row = col.row(align=True)
            row.label(text="Axes:")
            for i, axis in enumerate(["X", "Y", "Z"]):
                row.prop(scene, "custom_location_axes", index=i, text=axis, toggle=True)
            col.operator("object.apply_location", text="Apply Location", icon='CHECKMARK')

            # ROTATION
            col.separator()
            col.label(text="Rotation", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            col.prop(scene, "custom_rotation", text="Value")
            row = col.row(align=True)
            row.label(text="Axes:")
            for i, axis in enumerate(["X", "Y", "Z"]):
                row.prop(scene, "custom_rotation_axes", index=i, text=axis, toggle=True)
            col.operator("object.apply_rotation", text="Apply Rotation", icon='CHECKMARK')

            # SCALE
            col.separator()
            col.label(text="Scale", icon='FULLSCREEN_EXIT')
            col.prop(scene, "custom_scale", text="Value")
            row = col.row(align=True)
            row.label(text="Axes:")
            for i, axis in enumerate(["X", "Y", "Z"]):
                row.prop(scene, "custom_scale_axes", index=i, text=axis, toggle=True)
            col.operator("object.apply_scale", text="Apply Scale", icon='CHECKMARK')




#============================ Registration ============================

classes = (
    ApplyLocationOperator,
    ResetLocationOperator,
    ApplyRotationOperator,
    ResetRotationOperator,
    ApplyScaleOperator,
    ResetScaleOperator,
    ResetAllOperator,
    ConvertRotationToEulerOperator,
    SimpleTransformPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.custom_location = bpy.props.FloatVectorProperty(
        name="Custom Location", default=(0.0, 0.0, 0.0), subtype='TRANSLATION')
    bpy.types.Scene.custom_rotation = bpy.props.FloatVectorProperty(
        name="Custom Rotation", default=(0.0, 0.0, 0.0), subtype='EULER')
    bpy.types.Scene.custom_scale = bpy.props.FloatVectorProperty(
        name="Custom Scale", default=(1.0, 1.0, 1.0), subtype='XYZ')
    bpy.types.Scene.custom_location_axes = bpy.props.BoolVectorProperty(
        name="Location Axes", default=(False, False, False), subtype='XYZ')
    bpy.types.Scene.custom_rotation_axes = bpy.props.BoolVectorProperty(
        name="Rotation Axes", default=(False, False, False), subtype='XYZ')
    bpy.types.Scene.custom_scale_axes = bpy.props.BoolVectorProperty(
        name="Scale Axes", default=(False, False, False), subtype='XYZ')
    bpy.types.Scene.panel_transform = bpy.props.BoolProperty(
        name="Show Panel Transform", default=False)
    bpy.types.Scene.panel_edit_value = bpy.props.BoolProperty(
        name="Show Panel edit value", default=False)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.custom_location
    del bpy.types.Scene.custom_rotation
    del bpy.types.Scene.custom_scale
    del bpy.types.Scene.custom_location_axes
    del bpy.types.Scene.custom_rotation_axes
    del bpy.types.Scene.custom_scale_axes
    del bpy.types.Scene.panel_transform
    del bpy.types.Scene.panel_edit_value

if __name__ == "__main__":
    register()
