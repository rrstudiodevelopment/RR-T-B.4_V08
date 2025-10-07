import bpy
import json
import os

# -------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------

class TemporaryRigItem(bpy.types.PropertyGroup):
    owner: bpy.props.StringProperty(name="Owner")
    name: bpy.props.StringProperty(name="Item Name")
    is_bone: bpy.props.BoolProperty(default=False)

class TemporaryRigLayer(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Layer Name", default="New Layer")
    items: bpy.props.CollectionProperty(type=TemporaryRigItem)
    is_visible: bpy.props.BoolProperty(name="Visible", default=True)
    show_extra_buttons: bpy.props.BoolProperty(name="Show Extra Buttons", default=False)
    show_extra_buttons_group: bpy.props.BoolProperty(name="Show Extra Buttons (Group)", default=False)
    export_mark: bpy.props.BoolProperty(name="Mark for Export", default=False)

class RigLayerManager(bpy.types.PropertyGroup):
    layers: bpy.props.CollectionProperty(type=TemporaryRigLayer)
    active_layer_index: bpy.props.IntProperty(default=-1)

class GroupLayerIndex(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty()

class TemporaryRigGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Group Name", default="New Group")
    expanded: bpy.props.BoolProperty(name="Expanded", default=True)
    layer_indices: bpy.props.CollectionProperty(type=GroupLayerIndex)
    export_mark: bpy.props.BoolProperty(name="Export Mark", default=False)
    is_visible: bpy.props.BoolProperty(name="Is Visible", default=True)

class RigGroupManager(bpy.types.PropertyGroup):
    groups: bpy.props.CollectionProperty(type=TemporaryRigGroup)
    active_group_index: bpy.props.IntProperty(default=-1)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def enum_layers(self, context):
    items = [("NONE", "No Layers", "")]
    scene = context.scene
    if not hasattr(scene, "temp_layers") or not scene.temp_layers.layers:
        return items
    for i, l in enumerate(scene.temp_layers.layers):
        items.append((str(i), l.name or f"Layer {i}", f"Layer {l.name}"))
    return items

def get_layer_by_index(scene, layer_index):
    if not hasattr(scene, "temp_layers"):
        return None
    if layer_index is None:
        return None
    if 0 <= layer_index < len(scene.temp_layers.layers):
        return scene.temp_layers.layers[layer_index]
    return None

def layer_is_in_any_group(scene, layer_index):
    """Cek apakah layer sudah ada dalam group."""
    if not hasattr(scene, "temp_groups"):
        return False
    for group in scene.temp_groups.groups:
        for idx in group.layer_indices:
            if idx.index == layer_index:
                return True
    return False

def validate_and_fix_layer_duplication_operator(context):
    """Operator-safe version of duplication fix"""
    scene = context.scene
    if not hasattr(scene, "temp_groups"):
        return 0
        
    layer_to_groups = {}
    fixed_count = 0
    
    for group_idx, group in enumerate(scene.temp_groups.groups):
        for entry_idx, entry in enumerate(group.layer_indices):
            layer_index = entry.index
            if layer_index not in layer_to_groups:
                layer_to_groups[layer_index] = []
            layer_to_groups[layer_index].append((group_idx, entry_idx))
    
    for layer_index, groups in layer_to_groups.items():
        if len(groups) > 1:
            for i in range(1, len(groups)):
                group_idx, entry_idx = groups[i]
                if (0 <= group_idx < len(scene.temp_groups.groups) and 
                    0 <= entry_idx < len(scene.temp_groups.groups[group_idx].layer_indices)):
                    current_entry = scene.temp_groups.groups[group_idx].layer_indices[entry_idx]
                    if current_entry.index == layer_index:
                        scene.temp_groups.groups[group_idx].layer_indices.remove(entry_idx)
                        fixed_count += 1
    
    return fixed_count

def check_layer_duplication(scene):
    """Hanya check tanpa modify - untuk UI display"""
    if not hasattr(scene, "temp_groups"):
        return 0
        
    layer_to_groups = {}
    duplicate_count = 0
    
    for group in scene.temp_groups.groups:
        for entry in group.layer_indices:
            layer_index = entry.index
            if layer_index not in layer_to_groups:
                layer_to_groups[layer_index] = 0
            layer_to_groups[layer_index] += 1
    
    for layer_index, count in layer_to_groups.items():
        if count > 1:
            duplicate_count += (count - 1)
    
    return duplicate_count

# -------------------------------------------------------------------
# Operator untuk fix duplication
# -------------------------------------------------------------------
class RIG_OT_fix_layer_duplication(bpy.types.Operator):
    bl_idname = "rig.fix_layer_duplication"
    bl_label = "Fix Layer Duplication"
    bl_description = "Fix layers that are in multiple groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        fixed_count = validate_and_fix_layer_duplication_operator(context)
        if fixed_count > 0:
            self.report({'INFO'}, f"Fixed {fixed_count} layer duplications")
        else:
            self.report({'INFO'}, "No layer duplications found")
        return {'FINISHED'}

# -------------------------------------------------------------------
# Operators - Isolate
# -------------------------------------------------------------------
class VIEW3D_OT_isolate_toggle(bpy.types.Operator):
    bl_idname = "view3d.isolate_toggle"
    bl_label = "Toggle Isolate View"
    bl_description = "Isolate selected object or bone, toggle to reveal"
    bl_options = {'REGISTER', 'UNDO'}

    stored_selection: bpy.props.CollectionProperty(type=TemporaryRigItem)
    is_hidden: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        obj = context.active_object
        mode = obj.mode if obj else 'OBJECT'

        if mode == 'POSE' and obj and obj.type == 'ARMATURE':
            armature = obj
            if self.is_hidden:
                bpy.ops.pose.reveal()
                bpy.ops.pose.select_all(action='DESELECT')
                for it in self.stored_selection:
                    if it.owner == armature.name:
                        pb = armature.pose.bones.get(it.name)
                        if pb:
                            pb.bone.select = True
                self._check_layer_visibility(context, mode)
            else:
                self.stored_selection.clear()
                for bone in context.selected_pose_bones:
                    item = self.stored_selection.add()
                    item.owner = armature.name
                    item.name = bone.name
                bpy.ops.pose.hide(unselected=True)
        else:
            if self.is_hidden:
                bpy.ops.object.hide_view_clear()
                bpy.ops.object.select_all(action='DESELECT')
                for it in self.stored_selection:
                    obj_restore = bpy.data.objects.get(it.name)
                    if obj_restore and it.owner == obj_restore.name:
                        obj_restore.select_set(True)
                self._check_layer_visibility(context, mode)
            else:
                self.stored_selection.clear()
                for sel in context.selected_objects:
                    item = self.stored_selection.add()
                    item.owner = sel.name
                    item.name = sel.name
                bpy.ops.object.hide_view_set(unselected=True)

        self.is_hidden = not self.is_hidden
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}

    def _check_layer_visibility(self, context, mode):
        scene = context.scene
        if hasattr(scene, "temp_layers"):
            for layer in scene.temp_layers.layers:
                if not layer.is_visible:
                    if mode == 'POSE':
                        armature = context.object
                        if armature and armature.type == 'ARMATURE':
                            for item in layer.items:
                                if item.owner == armature.name:
                                    pb = armature.pose.bones.get(item.name)
                                    if pb:
                                        pb.bone.hide = True
                    else:
                        for item in layer.items:
                            obj = bpy.data.objects.get(item.name)
                            if obj:
                                obj.hide_set(True)
        if hasattr(scene, "temp_groups"):
            for group in scene.temp_groups.groups:
                for idx in group.layer_indices:
                    layer = get_layer_by_index(scene, idx.index)
                    if not layer:
                        continue
                    if not layer.is_visible:
                        if mode == 'POSE':
                            armature = context.object
                            if armature and armature.type == 'ARMATURE':
                                for item in layer.items:
                                    if item.owner == armature.name:
                                        pb = armature.pose.bones.get(item.name)
                                        if pb:
                                            pb.bone.hide = True
                        else:
                            for item in layer.items:
                                obj = bpy.data.objects.get(item.name)
                                if obj:
                                    obj.hide_set(True)

# -------------------------------------------------------------------
# Operators - Layers (global)
# -------------------------------------------------------------------

class ToggleLayerVisibility(bpy.types.Operator):
    """Toggle visibility dari layer sementara."""
    bl_idname = "rig.toggle_layer_visibility"
    bl_label = "Toggle Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        temp_layer = scene.temp_layers.layers[self.layer_index]
        is_visible = not temp_layer.is_visible
        temp_layer.is_visible = is_visible

        for item in temp_layer.items:
            arm_obj = bpy.data.objects.get(item.owner)
            if arm_obj and arm_obj.type == 'ARMATURE':
                if arm_obj.name not in context.view_layer.objects:
                    continue
                context.view_layer.objects.active = arm_obj
                if context.mode != 'POSE':
                    try:
                        bpy.ops.object.mode_set(mode='POSE')
                    except RuntimeError:
                        continue
                bone = arm_obj.data.bones.get(item.name)
                if bone:
                    bone.hide = not is_visible
                continue

            obj = bpy.data.objects.get(item.name)
            if obj:
                if obj.name not in context.view_layer.objects:
                    continue
                obj.hide_set(not is_visible)

        return {'FINISHED'}
    
class RIG_OT_add_selection_to_layer(bpy.types.Operator):
    bl_idname = "rig.add_selection_to_layer"
    bl_label = "Add Layer from Selection"
    bl_description = "Create a new global layer from current selection"
    bl_options = {'REGISTER', 'UNDO'}

    layer_name: bpy.props.StringProperty(name="Layer Name", default="New Layer")

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_layers"):
            scene.temp_layers = bpy.props.PointerProperty(type=RigLayerManager)

        new_layer = scene.temp_layers.layers.add()
        new_layer.name = self.layer_name

        for obj in context.selected_objects:
            item = new_layer.items.add()
            item.owner = obj.name
            item.name = obj.name
            item.is_bone = False

        arm = context.object if context.object and context.object.type == 'ARMATURE' else None
        if arm and context.selected_pose_bones:
            for bone in context.selected_pose_bones:
                item = new_layer.items.add()
                item.owner = arm.name
                item.name = bone.name
                item.is_bone = True

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_add_to_existing_layer(bpy.types.Operator):
    bl_idname = "rig.add_to_existing_layer"
    bl_label = "Add Bone Selected to Layer"
    bl_description = "Add current selection into an existing global layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        layer = get_layer_by_index(scene, self.layer_index)
        if not layer:
            self.report({'WARNING'}, "Layer not found")
            return {'CANCELLED'}

        added_count = 0

        if context.mode == 'OBJECT':
            for obj in context.selected_objects:
                exists = any(it.owner == obj.name and it.name == obj.name and not it.is_bone for it in layer.items)
                if not exists:
                    item = layer.items.add()
                    item.owner = obj.name
                    item.name = obj.name
                    item.is_bone = False
                    added_count += 1

        elif context.mode == 'POSE' and context.object and context.object.type == 'ARMATURE':
            armature = context.object
            for bone in context.selected_pose_bones:
                exists = any(it.owner == armature.name and it.name == bone.name and it.is_bone for it in layer.items)
                if not exists:
                    item = layer.items.add()
                    item.owner = armature.name
                    item.name = bone.name
                    item.is_bone = True
                    added_count += 1

        elif context.mode == 'EDIT_ARMATURE' and context.object and context.object.type == 'ARMATURE':
            armature = context.object
            for bone in context.selected_bones:
                exists = any(it.owner == armature.name and it.name == bone.name and it.is_bone for it in layer.items)
                if not exists:
                    item = layer.items.add()
                    item.owner = armature.name
                    item.name = bone.name
                    item.is_bone = True
                    added_count += 1

        if added_count > 0:
            self.report({'INFO'}, f"Added {added_count} item(s) to layer")
        else:
            self.report({'INFO'}, "No new items added")

        return {'FINISHED'}

class RIG_OT_delete_layer(bpy.types.Operator):
    bl_idname = "rig.delete_layer"
    bl_label = "Delete Layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        if 0 <= self.layer_index < len(scene.temp_layers.layers):
            scene.temp_layers.layers.remove(self.layer_index)
            if hasattr(scene, "temp_groups"):
                for g in scene.temp_groups.groups:
                    to_remove = []
                    for i, idx in enumerate(g.layer_indices):
                        if idx.index == self.layer_index:
                            to_remove.append(i)
                        elif idx.index > self.layer_index:
                            idx.index -= 1
                    for j in reversed(to_remove):
                        g.layer_indices.remove(j)
            self.report({'INFO'}, f"Layer {self.layer_index} deleted")
        else:
            self.report({'WARNING'}, "Invalid layer index")
        return {'FINISHED'}

class RIG_OT_rename_layer(bpy.types.Operator):
    bl_idname = "rig.rename_layer"
    bl_label = "Rename Layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()
    new_name: bpy.props.StringProperty(name="New Name", default="")

    def execute(self, context):
        layer = get_layer_by_index(context.scene, self.layer_index)
        if not layer:
            return {'CANCELLED'}
        layer.name = self.new_name
        return {'FINISHED'}

    def invoke(self, context, event):
        # Ambil nama existing dari layer yang akan di-rename
        layer = get_layer_by_index(context.scene, self.layer_index)
        if layer:
            # Set default value new_name dengan nama yang sudah ada
            self.new_name = layer.name if layer.name else ""
        
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_kick_selected_from_layer(bpy.types.Operator):
    bl_idname = "rig.kick_selected_from_layer"
    bl_label = "Kick Bone Selected From Layer"
    bl_description = "Remove currently selected bones/objects from the specified layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        layer = get_layer_by_index(context.scene, self.layer_index)
        if not layer:
            self.report({'WARNING'}, "Layer not found")
            return {'CANCELLED'}

        removed = 0
        for obj in context.selected_objects:
            for i, it in enumerate(list(layer.items)):
                if it.owner == obj.name and it.name == obj.name:
                    layer.items.remove(i)
                    removed += 1
                    break

        if context.mode == 'POSE' and context.object and context.object.type == 'ARMATURE':
            arm = context.object
            for pb in context.selected_pose_bones:
                for i, it in enumerate(list(layer.items)):
                    if it.owner == arm.name and it.name == pb.name:
                        layer.items.remove(i)
                        removed += 1
                        break

        self.report({'INFO'}, f"Removed {removed} item(s) from layer")
        return {'FINISHED'}

# -------------------------------------------------------------------
# Select dan Deselect operator

class RIG_OT_select_layer_items(bpy.types.Operator):
    bl_idname = "rig.select_layer_items"
    bl_label = "Select Layer Items"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()
    extend: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        self.extend = event.shift
        return self.execute(context)

    def execute(self, context):
        # ambil layer
        try:
            layer = get_layer_by_index(context.scene, self.layer_index)
        except Exception:
            layer = None

        if not layer:
            self.report({'WARNING'}, "Layer not found")
            return {'CANCELLED'}

        # cek apakah layer berisi bone atau object (atau campuran)
        has_bone = any(getattr(it, "is_bone", False) for it in layer.items)
        has_object = any(not getattr(it, "is_bone", False) for it in layer.items)

        # helper: unselect semua object
        def unselect_all_objects():
            for obj in context.selected_objects:
                try:
                    obj.select_set(False)
                except Exception:
                    pass

        # helper: unselect semua pose-bones
        def unselect_all_pose_bones():
            for obj in context.view_layer.objects:
                if obj.type == 'ARMATURE' and obj.mode == 'POSE' and obj.pose:
                    for pb in obj.pose.bones:
                        try:
                            pb.bone.select = False
                        except Exception:
                            pass

        # Clear selection hanya jika BUKAN extend
        if not self.extend:
            if has_bone and not has_object:
                # Target: Bone(s) - unselect objects dan bones
                unselect_all_objects()
                unselect_all_pose_bones()
            elif has_object and not has_bone:
                # Target: Object(s) - unselect objects saja
                unselect_all_objects()
            else:
                # Campuran - unselect semua
                unselect_all_objects()
                unselect_all_pose_bones()

        # Process items - untuk extend, items akan ditambahkan ke selection yang ada
        for it in layer.items:
            if getattr(it, "is_bone", False):
                # Handle bone selection
                arm = bpy.data.objects.get(getattr(it, "owner", None))
                if not arm or arm.type != 'ARMATURE':
                    continue

                try:
                    # Untuk bone selection, pastikan armature active dan dalam pose mode
                    context.view_layer.objects.active = arm
                    
                    # Pastikan dalam pose mode
                    if context.mode != 'POSE':
                        bpy.ops.object.mode_set(mode='POSE')
                    
                    # Select bone (akan menambah ke selection jika extend=True)
                    pb = arm.pose.bones.get(getattr(it, "name", ""))
                    if pb:
                        pb.bone.select = True
                except Exception as e:
                    print(f"Error selecting bone: {e}")
            else:
                # Handle object selection
                obj = bpy.data.objects.get(getattr(it, "name", ""))
                if obj:
                    # Jika sedang di pose mode, pindah ke object mode dulu
                    if context.mode == 'POSE':
                        try:
                            bpy.ops.object.mode_set(mode='OBJECT')
                        except Exception:
                            pass
                    
                    # Select object (akan menambah ke selection jika extend=True)
                    obj.select_set(True)
                    context.view_layer.objects.active = obj

        return {'FINISHED'}



class RIG_OT_deselect_layer_items(bpy.types.Operator):
    """Deselect all items in the chosen layer"""
    bl_idname = "rig.deselect_layer_items"
    bl_label = "Deselect Layer Items"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()

    def execute(self, context):
        layer = get_layer_by_index(context.scene, self.layer_index)
        if not layer:
            self.report({'WARNING'}, "Layer not found")
            return {'CANCELLED'}

        has_bone = any(it.is_bone for it in layer.items)

        if has_bone:
            arm = bpy.context.object if bpy.context.object and bpy.context.object.type == 'ARMATURE' else None
            if arm and arm.mode == 'POSE':
                for it in layer.items:
                    pb = arm.pose.bones.get(it.name)
                    if pb:
                        pb.bone.select = False
        else:
            for it in layer.items:
                obj = bpy.data.objects.get(it.name)
                if obj:
                    obj.select_set(False)

        self.report({'INFO'}, f"Deselected all items in layer '{layer.name}'")
        return {'FINISHED'}

# -------------------------------------------------------------------
# Groups operators
# -------------------------------------------------------------------
def get_group_items(self, context):
    scene = context.scene
    if not hasattr(scene, "temp_groups") or not scene.temp_groups.groups:
        return [("0", "No Groups", "")]
    return [(str(i), g.name, "") for i, g in enumerate(scene.temp_groups.groups)]

class RIG_OT_join_group_from_layer(bpy.types.Operator):
    bl_idname = "rig.join_group_from_layer"
    bl_label = "Join Group"
    bl_description = "Move this layer into a selected group"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()
    group_choice: bpy.props.EnumProperty(name="Group", items=get_group_items)

    @classmethod
    def poll(cls, context):
        return hasattr(context.scene, "temp_groups") and len(context.scene.temp_groups.groups) > 0

    def execute(self, context):
        scene = context.scene
        target_group_index = int(self.group_choice)
        target_group = scene.temp_groups.groups[target_group_index]

        for idx, group in enumerate(scene.temp_groups.groups):
            if idx == target_group_index:
                continue
            items_to_remove = [i for i, entry in enumerate(group.layer_indices) if entry.index == self.layer_index]
            for i in reversed(items_to_remove):
                group.layer_indices.remove(i)

        new_entry = target_group.layer_indices.add()
        new_entry.index = self.layer_index

        self.report({'INFO'}, f"Layer moved to '{target_group.name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        scene = context.scene
        if not hasattr(scene, "temp_groups") or len(scene.temp_groups.groups) == 0:
            self.report({'WARNING'}, "No groups available. Create a group first.")
            return {'CANCELLED'}

        self.group_choice = "0"
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select Group:")
        layout.prop(self, "group_choice", text="")

class RIG_OT_add_layer_to_group_via_enum(bpy.types.Operator):
    bl_idname = "rig.add_layer_to_group_via_enum"
    bl_label = "Add Layer to Group"
    bl_description = "Choose a global layer to add into this group"
    bl_options = {'REGISTER', 'UNDO'}

    group_index: bpy.props.IntProperty()
    layer_choice: bpy.props.EnumProperty(items=enum_layers)

    def execute(self, context):
        scene = context.scene
        
        if self.layer_choice == "NONE":
            self.report({'WARNING'}, "No layer selected")
            return {'CANCELLED'}
            
        try:
            layer_index = int(self.layer_choice)
        except Exception:
            self.report({'WARNING'}, "Invalid layer selection")
            return {'CANCELLED'}

        if not hasattr(scene, "temp_layers") or layer_index >= len(scene.temp_layers.layers):
            self.report({'WARNING'}, "Layer data not found")
            return {'CANCELLED'}

        grp = scene.temp_groups.groups[self.group_index]
        
        if any(entry.index == layer_index for entry in grp.layer_indices):
            self.report({'INFO'}, "Layer already in this group")
            return {'FINISHED'}

        removed_from_other_groups = False
        for other_group_idx, other_group in enumerate(scene.temp_groups.groups):
            if other_group_idx == self.group_index:
                continue
                
            items_to_remove = []
            for entry_idx, entry in enumerate(other_group.layer_indices):
                if entry.index == layer_index:
                    items_to_remove.append(entry_idx)
                    removed_from_other_groups = True
            
            for entry_idx in reversed(items_to_remove):
                if 0 <= entry_idx < len(other_group.layer_indices):
                    other_group.layer_indices.remove(entry_idx)

        new_entry = grp.layer_indices.add()
        new_entry.index = layer_index
        
        layer_name = scene.temp_layers.layers[layer_index].name
        
        if removed_from_other_groups:
            self.report({'INFO'}, f"Moved '{layer_name}' to group '{grp.name}'")
        else:
            self.report({'INFO'}, f"Added '{layer_name}' to group '{grp.name}'")
        
        return {'FINISHED'}

    def invoke(self, context, event):
        self.layer_choice = "NONE"
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_remove_layer_from_group(bpy.types.Operator):
    bl_idname = "rig.remove_layer_from_group"
    bl_label = "Remove Layer From Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_index: bpy.props.IntProperty()
    entry_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        grp = scene.temp_groups.groups[self.group_index]
        if 0 <= self.entry_index < len(grp.layer_indices):
            grp.layer_indices.remove(self.entry_index)
            return {'FINISHED'}
        return {'CANCELLED'}

class RIG_OT_toggle_group_visibility(bpy.types.Operator):
    bl_idname = "rig.toggle_group_visibility"
    bl_label = "Toggle Group Visibility"
    bl_description = "Toggle visibility for all layers inside this group"
    bl_options = {'REGISTER', 'UNDO'}

    group_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        grp = scene.temp_groups.groups[self.group_index]
        any_hidden = False
        for idx in grp.layer_indices:
            layer = get_layer_by_index(scene, idx.index)
            if layer and not layer.is_visible:
                any_hidden = True
                break
        target_visible = True if any_hidden else False
        for idx in grp.layer_indices:
            layer = get_layer_by_index(scene, idx.index)
            if layer:
                layer.is_visible = target_visible
                for item in layer.items:
                    arm = bpy.data.objects.get(item.owner)
                    if arm and arm.type == 'ARMATURE':
                        bone = arm.data.bones.get(item.name)
                        if bone:
                            bone.hide = not target_visible
                    else:
                        obj = bpy.data.objects.get(item.name)
                        if obj:
                            obj.hide_set(not target_visible)
        grp.is_visible = target_visible
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}

class RIG_OT_add_group(bpy.types.Operator):
    bl_idname = "rig.add_group"
    bl_label = "Add Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: bpy.props.StringProperty(name="Group Name", default="New Group")

    def execute(self, context):
        grp = context.scene.temp_groups.groups.add()
        grp.name = self.group_name
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_delete_group(bpy.types.Operator):
    bl_idname = "rig.delete_group"
    bl_label = "Delete Group"
    bl_description = "Delete group with options: group only or group with layers"
    bl_options = {'REGISTER', 'UNDO'}

    group_index: bpy.props.IntProperty()
    delete_mode: bpy.props.EnumProperty(
        name="Delete Mode",
        items=[
            ('GROUP_ONLY', "Group Only", "Delete group only, keep layers as global"),
            ('GROUP_AND_LAYERS', "Group & Layers", "Delete group and all layers inside it")
        ],
        default='GROUP_ONLY'
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene
        temp_groups = getattr(scene, "temp_groups", None)

        if not temp_groups or self.group_index < 0 or self.group_index >= len(temp_groups.groups):
            return {'CANCELLED'}

        group = temp_groups.groups[self.group_index]

        if self.delete_mode == 'GROUP_AND_LAYERS':
            layer_indices_to_remove = []
            for idx in group.layer_indices:
                layer_indices_to_remove.append(idx.index)
            
            layer_indices_to_remove.sort(reverse=True)
            for li in layer_indices_to_remove:
                if 0 <= li < len(scene.temp_layers.layers):
                    scene.temp_layers.layers.remove(li)
            
            for other_group in scene.temp_groups.groups:
                for idx_entry in other_group.layer_indices:
                    for li in layer_indices_to_remove:
                        if idx_entry.index > li:
                            idx_entry.index -= 1

        temp_groups.groups.remove(self.group_index)

        if self.delete_mode == 'GROUP_ONLY':
            self.report({'INFO'}, f"Group '{group.name}' deleted, layers kept as global")
        else:
            self.report({'INFO'}, f"Group '{group.name}' and its layers deleted")

        return {'FINISHED'}

class RIG_OT_rename_group(bpy.types.Operator):
    bl_idname = "rig.rename_group"
    bl_label = "Rename Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_index: bpy.props.IntProperty()
    new_name: bpy.props.StringProperty(name="New Name", default="")

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_groups"):
            return {'CANCELLED'}
        if not (0 <= self.group_index < len(scene.temp_groups.groups)):
            return {'CANCELLED'}
        scene.temp_groups.groups[self.group_index].name = self.new_name
        return {'FINISHED'}

    def invoke(self, context, event):
        # Ambil nama existing dari group yang akan di-rename
        scene = context.scene
        if (hasattr(scene, "temp_groups") and 
            0 <= self.group_index < len(scene.temp_groups.groups)):
            
            existing_group = scene.temp_groups.groups[self.group_index]
            # Set default value new_name dengan nama yang sudah ada
            self.new_name = existing_group.name if existing_group.name else ""
        
        return context.window_manager.invoke_props_dialog(self)

# -------------------------------------------------------------------
# Export / Import Operators
# -------------------------------------------------------------------
class RIG_OT_export_layers_groups(bpy.types.Operator):
    bl_idname = "rig.export_layers_groups"
    bl_label = "Export Layers/Groups"
    bl_description = "Mark layers/groups to export (only marked items will be exported)."
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext: bpy.props.StringProperty(default=".json")
    filter_glob: bpy.props.StringProperty(default="*.json;*.py", options={'HIDDEN'})

    def execute(self, context):
        scene = context.scene
        
        layers_out = []
        groups_out = []
        exported_layer_names = set()  # UNTUK MELACAK LAYER YANG SUDAH DIEKSPOR

        # EKSPOR LAYERS YANG DICENTANG LANGSUNG
        if hasattr(scene, "temp_layers"):
            for l in scene.temp_layers.layers:
                if l.export_mark:  # HANYA JIKA DICENTANG
                    items_data = []
                    for it in l.items:
                        item_data = {
                            "owner": it.owner,
                            "name": it.name,
                            "is_bone": it.is_bone
                        }
                        items_data.append(item_data)
                    
                    layer_data = {
                        "name": l.name,
                        "is_visible": bool(l.is_visible),
                        "items": items_data,
                    }
                    layers_out.append(layer_data)
                    exported_layer_names.add(l.name)  # TANDAI LAYER INI SUDAH DIEKSPOR

        # EKSPOR GROUPS YANG DICENTANG BESERTA SEMUA LAYER DI DALAMNYA
        if hasattr(scene, "temp_groups"):
            for g in scene.temp_groups.groups:
                if g.export_mark:  # HANYA JIKA DICENTANG
                    # EKSPOR INFORMASI GROUP
                    layer_indices = []
                    for idx in g.layer_indices:
                        layer_indices.append(idx.index)
                    
                    groups_out.append({
                        "name": g.name,
                        "is_visible": bool(g.is_visible),
                        "layer_indices": layer_indices,
                    })

                    # EKSPOR SEMUA LAYER YANG ADA DI GROUP INI
                    if hasattr(scene, "temp_layers"):
                        for layer_idx in layer_indices:
                            if 0 <= layer_idx < len(scene.temp_layers.layers):
                                l = scene.temp_layers.layers[layer_idx]
                                
                                # HANYA EKSPOR JIKA LAYER BELUM DIEKSPOR SEBELUMNYA
                                if l.name not in exported_layer_names:
                                    items_data = []
                                    for it in l.items:
                                        item_data = {
                                            "owner": it.owner,
                                            "name": it.name,
                                            "is_bone": it.is_bone
                                        }
                                        items_data.append(item_data)
                                    
                                    layer_data = {
                                        "name": l.name,
                                        "is_visible": bool(l.is_visible),
                                        "items": items_data,
                                    }
                                    layers_out.append(layer_data)
                                    exported_layer_names.add(l.name)  # TANDAI SUDAH DIEKSPOR

        # PERIKSA APAKAH ADA YANG DICENTANG
        if not layers_out and not groups_out:
            self.report({'WARNING'}, "No layers or groups marked for export")
            return {'CANCELLED'}

        data = {
            "layers": layers_out, 
            "groups": groups_out,
            "metadata": {
                "version": "1.1",
                "blender_version": bpy.app.version_string,
                "export_time": str(bpy.context.scene.frame_current)
            }
        }
        
        # OTOMATIS TAMBAH .json JIKA TIDAK ADA EKSTENSI
        fp = bpy.path.abspath(self.filepath)
        if not fp.lower().endswith(('.json', '.py')):
            fp += ".json"
        
        ext = os.path.splitext(fp)[1].lower()
        try:
            if ext == ".py":
                with open(fp, "w", encoding="utf-8") as f:
                    f.write("# exported by Raha Temporary Rig Layers addon\n")
                    f.write("exported_data = ")
                    json.dump(data, f, ensure_ascii=False, indent=4)
            else:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write file: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {len(layers_out)} layers and {len(groups_out)} groups to {fp}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # SET DEFAULT FILENAME DENGAN EKSTENSI .json
        self.filepath = bpy.path.abspath("//raha_layers_export.json")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class RIG_OT_choose_import_mode(bpy.types.Operator):
    bl_idname = "rig.choose_import_mode"
    bl_label = "Import Layers/Groups"
    bl_description = "Choose import mode before importing JSON or .py data"
    bl_options = {'REGISTER'}

    import_mode: bpy.props.EnumProperty(
        name="Import Mode",
        items=[
            ('REPLACE', "Replace All", "Replace existing layers and groups"),
            ('APPEND', "Append", "Add to existing layers and groups"),
        ],
        default='APPEND'
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Choose Import Mode:")
        layout.prop(self, "import_mode", expand=True)

    def execute(self, context):
        bpy.ops.rig.import_layers_groups('INVOKE_DEFAULT', import_mode=self.import_mode)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_import_layers_groups(bpy.types.Operator):
    bl_idname = "rig.import_layers_groups"
    bl_label = "Import Layers/Groups"
    bl_description = "Import layers/groups from JSON or .py exported data"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json;*.py", options={'HIDDEN'})
    
    import_mode: bpy.props.EnumProperty(
        name="Import Mode",
        items=[
            ('REPLACE', "Replace All", "Replace existing layers and groups"),
            ('APPEND', "Append", "Add to existing layers and groups"),
        ],
        default='APPEND'
    )

    def invoke(self, context, event):
        if hasattr(self, 'import_mode') and self.import_mode:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "import_mode")

    def execute(self, context):
        return self.load_file(context)

    def load_file(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}
            
        fp = bpy.path.abspath(self.filepath)
        if not os.path.exists(fp):
            self.report({'ERROR'}, "File not found")
            return {'CANCELLED'}
        
        ext = os.path.splitext(fp)[1].lower()
        try:
            if ext == ".py":
                loc = {}
                with open(fp, "r", encoding="utf-8") as f:
                    code = f.read()
                exec(code, {}, loc)
                data = loc.get("exported_data") or loc.get("exported")
            else:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read file: {e}")
            return {'CANCELLED'}

        if not data:
            self.report({'ERROR'}, "No data found in file")
            return {'CANCELLED'}

        scene = context.scene

        if not hasattr(scene, "temp_layers"):
            scene.temp_layers = bpy.props.PointerProperty(type=RigLayerManager)
        if not hasattr(scene, "temp_groups"):
            scene.temp_groups = bpy.props.PointerProperty(type=RigGroupManager)

        if self.import_mode == 'REPLACE':
            scene.temp_layers.layers.clear()
            scene.temp_groups.groups.clear()

        imported_layer_indices = {}
        
        for ld in data.get("layers", []):
            name = ld.get("name", "Imported Layer")
            items_data = ld.get("items", [])
            
            existing_layer_index = None
            for i, existing_layer in enumerate(scene.temp_layers.layers):
                if existing_layer.name == name:
                    existing_layer_index = i
                    break
            
            if existing_layer_index is not None and self.import_mode == 'APPEND':
                layer = scene.temp_layers.layers[existing_layer_index]
                imported_layer_indices[name] = existing_layer_index
            else:
                layer = scene.temp_layers.layers.add()
                layer.name = name
                layer.is_visible = bool(ld.get("is_visible", True))
                imported_layer_indices[name] = len(scene.temp_layers.layers) - 1

            for item_data in items_data:
                owner_name = item_data.get("owner", "")
                item_name = item_data.get("name", "")
                is_bone = item_data.get("is_bone", False)
                
                item_exists = False
                for existing_item in layer.items:
                    if (existing_item.owner == owner_name and 
                        existing_item.name == item_name and 
                        existing_item.is_bone == is_bone):
                        item_exists = True
                        break
                
                if not item_exists:
                    if is_bone:
                        armature = bpy.data.objects.get(owner_name)
                        if armature and armature.type == 'ARMATURE':
                            bone = armature.data.bones.get(item_name)
                            if bone:
                                new_item = layer.items.add()
                                new_item.owner = owner_name
                                new_item.name = item_name
                                new_item.is_bone = True
                    else:
                        obj = bpy.data.objects.get(item_name)
                        if obj:
                            new_item = layer.items.add()
                            new_item.owner = owner_name
                            new_item.name = item_name
                            new_item.is_bone = False

        for gd in data.get("groups", []):
            gname = gd.get("name", "Imported Group")
            group_exists = False
            target_group = None
            
            for existing_group in scene.temp_groups.groups:
                if existing_group.name == gname:
                    group_exists = True
                    target_group = existing_group
                    break
            
            if not group_exists:
                target_group = scene.temp_groups.groups.add()
                target_group.name = gname
            
            target_group.is_visible = bool(gd.get("is_visible", True))
            
            layer_indices = gd.get("layer_indices", [])
            layer_names = gd.get("layers", [])
            
            if self.import_mode == 'REPLACE' and not group_exists:
                target_group.layer_indices.clear()
            
            for layer_index in layer_indices:
                if 0 <= layer_index < len(scene.temp_layers.layers):
                    if not any(idx.index == layer_index for idx in target_group.layer_indices):
                        new_idx = target_group.layer_indices.add()
                        new_idx.index = layer_index
            
            for layer_name in layer_names:
                if layer_name in imported_layer_indices:
                    layer_index = imported_layer_indices[layer_name]
                    if not any(idx.index == layer_index for idx in target_group.layer_indices):
                        new_idx = target_group.layer_indices.add()
                        new_idx.index = layer_index

        imported_layers_count = len(data.get("layers", []))
        imported_groups_count = len(data.get("groups", []))
        
        self.report({'INFO'}, f"Imported {imported_layers_count} layers and {imported_groups_count} groups")
        return {'FINISHED'}

# -------------------------------------------------------------------
# Move Operators
# -------------------------------------------------------------------
class RIG_OT_move_layer_up(bpy.types.Operator):
    """Move layer up in global or group"""
    bl_idname = "rig.move_layer_up"
    bl_label = "Move Layer Up"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer_index: bpy.props.IntProperty()
    group_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_layers"):
            return {'CANCELLED'}

        if self.group_index >= 0 and hasattr(scene, "temp_groups"):
            groups = scene.temp_groups.groups
            if 0 <= self.group_index < len(groups):
                group = groups[self.group_index]
                entries = group.layer_indices
                pos = next((i for i, e in enumerate(entries) if e.index == self.layer_index), -1)
                if pos > 0:
                    entries.move(pos, pos - 1)
                    return {'FINISHED'}
                else:
                    return {'CANCELLED'}

        layers = scene.temp_layers.layers
        if self.layer_index <= 0 or self.layer_index >= len(layers):
            return {'CANCELLED'}

        layers.move(self.layer_index, self.layer_index - 1)
        return {'FINISHED'}

class RIG_OT_move_layer_down(bpy.types.Operator):
    """Move layer down in global or group"""
    bl_idname = "rig.move_layer_down"
    bl_label = "Move Layer Down"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer_index: bpy.props.IntProperty()
    group_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_layers"):
            return {'CANCELLED'}

        if self.group_index >= 0 and hasattr(scene, "temp_groups"):
            groups = scene.temp_groups.groups
            if 0 <= self.group_index < len(groups):
                group = groups[self.group_index]
                entries = group.layer_indices
                pos = next((i for i, e in enumerate(entries) if e.index == self.layer_index), -1)
                if 0 <= pos < len(entries) - 1:
                    entries.move(pos, pos + 1)
                    return {'FINISHED'}
                else:
                    return {'CANCELLED'}

        layers = scene.temp_layers.layers
        if self.layer_index < 0 or self.layer_index >= len(layers) - 1:
            return {'CANCELLED'}

        layers.move(self.layer_index, self.layer_index + 1)
        return {'FINISHED'}

class RIG_OT_move_group_up(bpy.types.Operator):
    """Move group up"""
    bl_idname = "rig.move_group_up"
    bl_label = "Move Group Up"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_groups"):
            return {'CANCELLED'}
            
        groups = scene.temp_groups.groups
        if self.group_index <= 0 or self.group_index >= len(groups):
            return {'CANCELLED'}

        groups.move(self.group_index, self.group_index - 1)
        return {'FINISHED'}

class RIG_OT_move_group_down(bpy.types.Operator):
    """Move group down"""
    bl_idname = "rig.move_group_down"
    bl_label = "Move Group Down"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_groups"):
            return {'CANCELLED'}
            
        groups = scene.temp_groups.groups
        if self.group_index < 0 or self.group_index >= len(groups) - 1:
            return {'CANCELLED'}

        groups.move(self.group_index, self.group_index + 1)
        return {'FINISHED'}

# -------------------------------------------------------------------
# Panel utama
# -------------------------------------------------------------------
class VIEW3D_PT_rig_layers_panel(bpy.types.Panel):
    bl_label = "Flexi Picker"
    bl_idname = "VIEW3D_PT_rig_layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Raha_Tools'
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        duplicate_count = check_layer_duplication(scene)
        if duplicate_count > 0:
            warning_box = layout.box()
            warning_box.alert = True
            warning_box.label(text=f"Warning: {duplicate_count} layer duplications found", icon='ERROR')
            op_row = warning_box.row()
            op_row.operator("rig.fix_layer_duplication", text="Fix Now", icon='TRASH')
        
        layout.use_property_split = False
        layout.use_property_decorate = False

        def safe_op(container, idname, props=None, **kwargs):
            try:
                op = container.operator(idname, **kwargs)
                if props:
                    for k, v in props.items():
                        setattr(op, k, v)
                return op
            except Exception as e:
                print(f"[Flexi Picker UI] Operator failed: {idname} → {e}")
                return None

        header = layout.row(align=True)
        header.scale_y = 1.1
        header.label(text="Quick Actions", icon='OUTLINER_COLLECTION')
        row = layout.row(align=True)
        safe_op(row, "view3d.isolate_toggle", text="Isolate", icon='HIDE_OFF')
  
        row = layout.row(align=True)              
        safe_op(row, "rig.add_selection_to_layer", text="Add Sel", icon='ADD')
        safe_op(row, "rig.add_group", text="New Group", icon='GROUP')
      
        row.separator()        
        safe_op(row, "rig.export_layers_groups", text="", icon='EXPORT')
        row.separator()         
        safe_op(row, "rig.choose_import_mode", text="", icon='IMPORT')        

#======================== GLobal =======================================
        layout.separator(factor=1.2)

        if hasattr(scene, "temp_layers") and scene.temp_layers.layers:
            visible_globals = []
            for i, layer in enumerate(scene.temp_layers.layers):
                try:
                    if layer_is_in_any_group(scene, i):
                        continue
                    visible_globals.append((i, layer))
                except:
                    visible_globals.append((i, layer))

            if visible_globals:
                col = layout.column()
                col.label(text="Global Layers", icon='LAYER_ACTIVE')

                for i, layer in visible_globals:
                    box = col.box()
                    box.use_property_split = False

                    row = box.row(align=True)
                    row.scale_y = 1.2
                    safe_op(row, "rig.select_layer_items", {"layer_index": i}, text=layer.name, icon='RESTRICT_SELECT_OFF')
                    safe_op(row, "rig.deselect_layer_items", {"layer_index": i}, text="", icon='RESTRICT_SELECT_ON')                    
                    safe_op(row, "rig.toggle_layer_visibility", {"layer_index": i}, text="", 
                            icon='HIDE_OFF' if getattr(layer, "is_visible", True) else 'HIDE_ON')

                    row.prop(layer, "show_extra_buttons", text="", icon='SETTINGS')
                    row.prop(layer, "export_mark", text="", icon='EXPORT')                     
                  

                    if getattr(layer, "show_extra_buttons", False):
                        sub = box.column(align=True)
                        sub.separator(factor=0.3)
                        r = sub.row(align=True)
                        safe_op(r, "rig.rename_layer", {"layer_index": i}, text="", icon='GREASEPENCIL')
                        safe_op(r, "rig.add_to_existing_layer", {"layer_index": i}, text="", icon='ADD')
                        safe_op(r, "rig.kick_selected_from_layer", {"layer_index": i}, text="", icon='X')
                        safe_op(r, "rig.delete_layer", {"layer_index": i}, text="", icon='TRASH')
                        
                        if len(visible_globals) > 1:
                            r.separator()
                            safe_op(r, "rig.move_layer_up", {"layer_index": i, "group_index": -1}, text="", icon='TRIA_UP')
                            safe_op(r, "rig.move_layer_down", {"layer_index": i, "group_index": -1}, text="", icon='TRIA_DOWN')                        

                        r.separator(factor=8.0)                                                                                                                                                                                           
                        safe_op(r, "rig.join_group_from_layer", {"layer_index": i}, text="", icon='GROUP')                        


########## GROUP ==========================================
        layout.separator(factor=1.4)

        if hasattr(scene, "temp_groups") and getattr(scene.temp_groups, "groups", []):
            col = layout.column()
            col.label(text="Groups", icon='GROUP')

            for g_index, group in enumerate(scene.temp_groups.groups):
                try:
                    group_box = col.box()
                    group_header = group_box.row(align=True)

                    expanded_icon = 'TRIA_DOWN' if getattr(group, "expanded", True) else 'TRIA_RIGHT'
                    group_header.prop(group, "expanded", text="", icon=expanded_icon, emboss=False)
                    group_header.label(text=getattr(group, "name", f"Group {g_index}"))

                    move_row = group_header.row(align=True)
                    move_row.scale_x = 0.9
                    safe_op(move_row, "rig.move_group_up", {"group_index": g_index}, text="", icon='TRIA_UP')
                    safe_op(move_row, "rig.move_group_down", {"group_index": g_index}, text="", icon='TRIA_DOWN')
                    group_header.separator(factor=2.0)
                
                    safe_op(group_header, "rig.add_layer_to_group_via_enum", {"group_index": g_index}, text="", icon='ADD')                        
                    safe_op(group_header, "rig.toggle_group_visibility", {"group_index": g_index}, text="", 
                            icon='HIDE_OFF' if getattr(group, "is_visible", True) else 'HIDE_ON')
                    safe_op(group_header, "rig.rename_group", {"group_index": g_index}, text="", icon='GREASEPENCIL')
                    safe_op(group_header, "rig.delete_group", {"group_index": g_index}, text="", icon='TRASH')
               
                    group_header.separator(factor=2.0) 
                    group_header.prop(group, "export_mark", text="", icon='EXPORT')

########## layer didalam group  ==========================================

                    if getattr(group, "expanded", True):
                        if group.layer_indices:
                            for entry_idx, entry in enumerate(group.layer_indices):
                                li = getattr(entry, "index", -1)
                                if li < 0 or li >= len(scene.temp_layers.layers):
                                    continue

                                layer_ref = scene.temp_layers.layers[li]
                                layer_box = group_box.box()
                                lr = layer_box.row(align=True)
                                lr.scale_y = 1.0
                                safe_op(lr, "rig.select_layer_items", {"layer_index": li}, text=layer_ref.name, icon='RESTRICT_SELECT_OFF')
                                safe_op(lr, "rig.deselect_layer_items", {"layer_index": li}, text="", icon='RESTRICT_SELECT_ON')                                                            
                                safe_op(lr, "rig.toggle_layer_visibility", {"layer_index": li}, text="", 
                                        icon='HIDE_OFF' if getattr(layer_ref, "is_visible", True) else 'HIDE_ON')
                                lr.prop(layer_ref, "show_extra_buttons_group", text="", icon='SETTINGS')

                                if getattr(layer_ref, "show_extra_buttons_group", False):
                                    sub_box = layer_box.box()
                                    sub_box.scale_y = 0.9
                                    r = sub_box.row(align=True)                                                                                                                               
                                    safe_op(r, "rig.rename_layer", {"layer_index": li}, text="", icon='GREASEPENCIL')
                                    safe_op(r, "rig.add_to_existing_layer", {"layer_index": li}, text="", icon='ADD')
                                    safe_op(r, "rig.kick_selected_from_layer", {"layer_index": li}, text="", icon='X')
                                    safe_op(r, "rig.delete_layer", {"layer_index": li}, text="", icon='TRASH') 
                                    safe_op(r, "rig.remove_layer_from_group", {"group_index": g_index, "entry_index": entry_idx}, text="", icon='TRACKING_CLEAR_FORWARDS') 
                                    

                                    if len(group.layer_indices) > 1:
                                        r.separator()
                                        safe_op(r, "rig.move_layer_up", {"layer_index": li, "group_index": g_index}, text="", icon='TRIA_UP')
                                        safe_op(r, "rig.move_layer_down", {"layer_index": li, "group_index": g_index}, text="", icon='TRIA_DOWN')

                                        r.separator(factor=7.0)    
                                                                               
                                        safe_op(r, "rig.join_group_from_layer", {"layer_index": li}, text="", icon='GROUP')
                                        r.separator()                                                                                                                                                                                                                                                                                    
                                        safe_op(r, "rig.remove_layer_from_group", {"group_index": g_index, "entry_index": entry_idx}, text="", icon='TRACKING_CLEAR_FORWARDS')                                        
                        else:
                            empty = group_box.box()
                            empty.label(text="(Empty Group)", icon='INFO')

                except Exception as e:
                    err = col.box()
                    err.label(text=f"Error drawing group {g_index}: {e}", icon='ERROR')

# -------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------
classes = [
    TemporaryRigItem,
    TemporaryRigLayer,
    RigLayerManager,
    GroupLayerIndex,
    TemporaryRigGroup,
    RigGroupManager,
    
    VIEW3D_OT_isolate_toggle,
    ToggleLayerVisibility,
    RIG_OT_add_selection_to_layer,
    RIG_OT_add_to_existing_layer,
    RIG_OT_delete_layer,
    RIG_OT_rename_layer,
    RIG_OT_kick_selected_from_layer,
    RIG_OT_select_layer_items,
    RIG_OT_deselect_layer_items,
    RIG_OT_join_group_from_layer,
    RIG_OT_add_layer_to_group_via_enum,
    RIG_OT_remove_layer_from_group,
    RIG_OT_toggle_group_visibility,
    RIG_OT_add_group,
    RIG_OT_delete_group,
    RIG_OT_rename_group,
    RIG_OT_export_layers_groups,
    RIG_OT_import_layers_groups,
    RIG_OT_choose_import_mode,
    RIG_OT_fix_layer_duplication,
    RIG_OT_move_layer_up,
    RIG_OT_move_layer_down,
    RIG_OT_move_group_up,
    RIG_OT_move_group_down,
    VIEW3D_PT_rig_layers_panel,
]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Failed to register {cls}: {e}")
    
    try:
        bpy.types.Scene.temp_layers = bpy.props.PointerProperty(type=RigLayerManager)
        bpy.types.Scene.temp_groups = bpy.props.PointerProperty(type=RigGroupManager)
    except Exception as e:
        print(f"Failed to register properties: {e}")

def unregister():
    try:
        del bpy.types.Scene.temp_layers
    except Exception:
        pass
    try:
        del bpy.types.Scene.temp_groups
    except Exception:
        pass
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

if __name__ == "__main__":
    register()
