bl_info = {
    "name": "Raha Temporary Rig Layers + Groups (Fixed UI + Export/Import)",
    "author": "ChatGPT (for you)",
    "version": (1, 0, 1),
    "blender": (4, 0, 0),
    "location": "3D View > Sidebar > Raha_Tools",
    "description": "Temporary rig layers & groups with improved UI, kick-by-selection, join/group popup, and export/import (JSON/.py). Fixed select operator bug.",
    "category": "Rigging",
}

import bpy
import json
import os

# -------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------
class TemporaryRigItem(bpy.types.PropertyGroup):
    owner: bpy.props.StringProperty(name="Owner")
    name: bpy.props.StringProperty(name="Item Name")

class TemporaryRigLayer(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Layer Name", default="New Layer")
    items: bpy.props.CollectionProperty(type=TemporaryRigItem)
    is_visible: bpy.props.BoolProperty(name="Visible", default=True)
    show_extra_buttons_group: bpy.props.BoolProperty(name="Show Extra (Group)", default=False)  # ✅ unik per layer
   
    show_extra_buttons: bpy.props.BoolProperty(
        name="Show Extra Buttons",
        description="Tampilkan tombol tambahan untuk layer ini",
        default=False
    )

    export_mark: bpy.props.BoolProperty(
        name="Export Mark",
        description="Tandai untuk diexport",
        default=False
    )
    
    def toggle_visibility(self, context):
        self.is_visible = not self.is_visible
        is_visible = self.is_visible
        for item in self.items:
            arm = bpy.data.objects.get(item.owner)
            if arm and arm.type == 'ARMATURE':
                bone = arm.data.bones.get(item.name)
                if bone:
                    bone.hide = not is_visible
            else:
                obj = bpy.data.objects.get(item.name)
                if obj:
                    obj.hide_set(not is_visible)
        for area in context.screen.areas:
            area.tag_redraw()

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
def get_layer_by_index(scene, layer_index):
    if not hasattr(scene, "temp_layers"):
        return None
    if layer_index is None:
        return None
    if 0 <= layer_index < len(scene.temp_layers.layers):
        return scene.temp_layers.layers[layer_index]
    return None

def layer_is_in_any_group(scene, layer_index):
    if not hasattr(scene, "temp_groups"):
        return False
    for g in scene.temp_groups.groups:
        for idx in g.layer_indices:
            if idx.index == layer_index:
                return True
    return False

def find_group_and_entry_for_layer(scene, layer_index):
    if not hasattr(scene, "temp_groups"):
        return (None, None)
    for gi, g in enumerate(scene.temp_groups.groups):
        for ei, idx in enumerate(g.layer_indices):
            if idx.index == layer_index:
                return (gi, ei)
    return (None, None)

def ensure_pose_mode_for_object(obj):
    try:
        bpy.context.view_layer.objects.active = obj
        if bpy.context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        return True
    except Exception:
        return False

# -------------------------------------------------------------------
# Operators - Isolate (preserve behavior)
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
class RIG_OT_add_selection_to_layer(bpy.types.Operator):
    bl_idname = "rig.add_selection_to_layer"
    bl_label = "Add Layer from Selection"
    bl_description = "Create a new global layer from current selection (objects or pose bones)"
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

        arm = context.object if context.object and context.object.type == 'ARMATURE' else None
        if arm and context.selected_pose_bones:
            for bone in context.selected_pose_bones:
                item = new_layer.items.add()
                item.owner = arm.name
                item.name = bone.name
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

        for obj in context.selected_objects:
            exists = any(it.owner == obj.name and it.name == obj.name for it in layer.items)
            if not exists:
                it = layer.items.add()
                it.owner = obj.name
                it.name = obj.name

        arm = context.object if context.object and context.object.type == 'ARMATURE' else None
        if arm and context.selected_pose_bones:
            for bone in context.selected_pose_bones:
                exists = any(it.owner == arm.name and it.name == bone.name for it in layer.items)
                if not exists:
                    it = layer.items.add()
                    it.owner = arm.name
                    it.name = bone.name
        return {'FINISHED'}

class RIG_OT_delete_layer(bpy.types.Operator):
    bl_idname = "rig.delete_layer"
    bl_label = "Delete Layer"
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
        # Objects
        for obj in context.selected_objects:
            for i, it in enumerate(list(layer.items)):
                if it.owner == obj.name and it.name == obj.name:
                    layer.items.remove(i)
                    removed += 1
                    break

        # Bones (only from active armature in pose mode)
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
# Select operator (fixed proper class)
# -------------------------------------------------------------------
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
        layer = get_layer_by_index(context.scene, self.layer_index)
        if not layer:
            self.report({'WARNING'}, "Layer not found")
            return {'CANCELLED'}

        if not self.extend:
            try:
                bpy.ops.object.select_all(action='DESELECT')
            except Exception:
                pass
            try:
                bpy.ops.pose.select_all(action='DESELECT')
            except Exception:
                pass

        for it in layer.items:
            arm = bpy.data.objects.get(it.owner)
            if arm and arm.type == 'ARMATURE':
                try:
                    context.view_layer.objects.active = arm
                    if context.mode != 'POSE':
                        bpy.ops.object.mode_set(mode='POSE')
                    pb = arm.pose.bones.get(it.name)
                    if pb:
                        pb.bone.select = True
                except Exception:
                    pass
            else:
                obj = bpy.data.objects.get(it.name)
                if obj:
                    obj.select_set(True)
                    context.view_layer.objects.active = obj

        return {'FINISHED'}

# -------------------------------------------------------------------
# Remove a specific item by index (kept as optional)
# -------------------------------------------------------------------
class RIG_OT_remove_item_from_layer(bpy.types.Operator):
    bl_idname = "rig.remove_item_from_layer"
    bl_label = "Remove Item From Layer"
    bl_description = "Remove a specific item (object or bone) from a layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()
    item_index: bpy.props.IntProperty()

    def execute(self, context):
        layer = get_layer_by_index(context.scene, self.layer_index)
        if not layer:
            self.report({'WARNING'}, "Layer not found")
            return {'CANCELLED'}
        if 0 <= self.item_index < len(layer.items):
            layer.items.remove(self.item_index)
            return {'FINISHED'}
        self.report({'WARNING'}, "Invalid item index")
        return {'CANCELLED'}

# -------------------------------------------------------------------
# Groups + join/add via enum
# -------------------------------------------------------------------
def enum_groups(self, context):
    items = []
    scene = context.scene
    if not hasattr(scene, "temp_groups") or not scene.temp_groups.groups:
        return [("NONE", "No Groups", "")]
    for i, g in enumerate(scene.temp_groups.groups):
        items.append((str(i), g.name or f"Group {i}", ""))
    return items

def enum_layers(self, context):
    items = []
    scene = context.scene
    if not hasattr(scene, "temp_layers") or not scene.temp_layers.layers:
        return [("NONE", "No Layers", "")]
    for i, l in enumerate(scene.temp_layers.layers):
        items.append((str(i), l.name or f"Layer {i}", ""))
    return items

class RIG_OT_join_group_from_layer(bpy.types.Operator):
    bl_idname = "rig.join_group_from_layer"
    bl_label = "Join Group"
    bl_description = "Move this layer into a selected group"
    bl_options = {'REGISTER', 'UNDO'}

    layer_index: bpy.props.IntProperty()
    group_choice: bpy.props.EnumProperty(items=enum_groups)

    def execute(self, context):
        scene = context.scene
        if self.group_choice == "NONE":
            self.report({'WARNING'}, "No groups available")
            return {'CANCELLED'}
        try:
            gi = int(self.group_choice)
        except Exception:
            self.report({'WARNING'}, "Invalid group selection")
            return {'CANCELLED'}
        grp = scene.temp_groups.groups[gi]
        already = any(idx.index == self.layer_index for idx in grp.layer_indices)
        if not already:
            new_idx = grp.layer_indices.add()
            new_idx.index = self.layer_index
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_add_layer_to_group_via_enum(bpy.types.Operator):
    bl_idname = "rig.add_layer_to_group_via_enum"
    bl_label = "Add Layer to Group (choose)"
    bl_description = "Choose a global layer to add into this group"
    bl_options = {'REGISTER', 'UNDO'}

    group_index: bpy.props.IntProperty()
    layer_choice: bpy.props.EnumProperty(items=enum_layers)

    def execute(self, context):
        scene = context.scene
        if self.layer_choice == "NONE":
            self.report({'WARNING'}, "No layers available")
            return {'CANCELLED'}
        try:
            li = int(self.layer_choice)
        except Exception:
            self.report({'WARNING'}, "Invalid layer selection")
            return {'CANCELLED'}
        grp = scene.temp_groups.groups[self.group_index]
        if not any(idx.index == li for idx in grp.layer_indices):
            new_idx = grp.layer_indices.add()
            new_idx.index = li
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class RIG_OT_remove_layer_from_group(bpy.types.Operator):
    bl_idname = "rig.remove_layer_from_group"
    bl_label = "Remove Layer From Group"
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
    group_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        if not hasattr(scene, "temp_groups"):
            return {'CANCELLED'}
        if 0 <= self.group_index < len(scene.temp_groups.groups):
            scene.temp_groups.groups.remove(self.group_index)
            return {'FINISHED'}
        return {'CANCELLED'}

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
        return context.window_manager.invoke_props_dialog(self)

# -------------------------------------------------------------------
# Export / Import Operators
# -------------------------------------------------------------------
class RIG_OT_export_layers_groups(bpy.types.Operator):
    bl_idname = "rig.export_layers_groups"
    bl_label = "Export Layers/Groups"
    bl_description = "Mark layers/groups to export (if none marked, all exported)."
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext: bpy.props.StringProperty(default=".json")
    filter_glob: bpy.props.StringProperty(default="*.json;*.py", options={'HIDDEN'})

    def execute(self, context):
        scene = context.scene
        layers_out = []
        groups_out = []

        if hasattr(scene, "temp_layers"):
            any_mark = any(l.export_mark for l in scene.temp_layers.layers)
            for l in scene.temp_layers.layers:
                if l.export_mark or not any_mark:
                    layers_out.append({
                        "name": l.name,
                        "is_visible": bool(l.is_visible),
                        "items": [{"owner": it.owner, "name": it.name} for it in l.items],
                    })

        if hasattr(scene, "temp_groups"):
            any_mark_g = any(g.export_mark for g in scene.temp_groups.groups)
            for g in scene.temp_groups.groups:
                if g.export_mark or not any_mark_g:
                    layer_names = []
                    for idx in g.layer_indices:
                        li = idx.index
                        layer = get_layer_by_index(scene, li)
                        if layer:
                            layer_names.append(layer.name)
                    groups_out.append({
                        "name": g.name,
                        "is_visible": bool(g.is_visible),
                        "layers": layer_names,
                    })

        data = {"layers": layers_out, "groups": groups_out}
        fp = bpy.path.abspath(self.filepath)
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

        self.report({'INFO'}, f"Exported to {fp}")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = bpy.path.abspath("//raha_layers_export.json")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class RIG_OT_import_layers_groups(bpy.types.Operator):
    bl_idname = "rig.import_layers_groups"
    bl_label = "Import Layers/Groups"
    bl_description = "Import layers/groups from JSON or .py exported data"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json;*.py", options={'HIDDEN'})

    def execute(self, context):
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

        name_to_index = {}
        for ld in data.get("layers", []):
            name = ld.get("name", "Layer")
            found_idx = None
            for i, existing in enumerate(scene.temp_layers.layers):
                if existing.name == name:
                    found_idx = i
                    break
            if found_idx is None:
                nl = scene.temp_layers.layers.add()
                nl.name = name
                nl.is_visible = bool(ld.get("is_visible", True))
                for it in ld.get("items", []):
                    itn = nl.items.add()
                    itn.owner = it.get("owner", "")
                    itn.name = it.get("name", "")
                new_index = len(scene.temp_layers.layers) - 1
                name_to_index[name] = new_index
            else:
                existing = scene.temp_layers.layers[found_idx]
                for it in ld.get("items", []):
                    exists = any(x.owner == it.get("owner", "") and x.name == it.get("name", "") for x in existing.items)
                    if not exists:
                        e = existing.items.add()
                        e.owner = it.get("owner", "")
                        e.name = it.get("name", "")
                name_to_index[name] = found_idx

        for gd in data.get("groups", []):
            gname = gd.get("name", "Group")
            g = scene.temp_groups.groups.add()
            g.name = gname
            g.is_visible = bool(gd.get("is_visible", True))
            for lname in gd.get("layers", []):
                li = name_to_index.get(lname)
                if li is None:
                    for i, ex in enumerate(scene.temp_layers.layers):
                        if ex.name == lname:
                            li = i
                            break
                if li is not None:
                    new_idx = g.layer_indices.add()
                    new_idx.index = li

        self.report({'INFO'}, "Imported layers & groups")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# -------------------------------------------------------------------
# Panel UI
# -------------------------------------------------------------------
class VIEW3D_PT_rig_layers_panel(bpy.types.Panel):
    """Panel UI untuk menampilkan daftar layer sementara."""
    bl_label = "Temporary Rig Layers"
    bl_idname = "VIEW3D_PT_rig_layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Raha_Tools'
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row(align=True)
        row.operator("view3d.isolate_toggle", text="Toggle Isolate View", icon='HIDE_OFF')
        row = layout.row(align=True)        
        layout.separator()        
        row.operator("rig.add_selection_to_layer", text="Add Selection", icon='ADD')
        row.operator("rig.add_group", text="+ Add Group", icon='GROUP')
        row.operator("rig.export_layers_groups", text="", icon='EXPORT')
        row.operator("rig.import_layers_groups", text="", icon='IMPORT')
        layout.separator() 
        
        
        # GLOBAL LAYERS
        if hasattr(scene, "temp_layers") and scene.temp_layers.layers:
            visible_globals = []
            for i, layer in enumerate(scene.temp_layers.layers):
                try:
                    if not layer_is_in_any_group(scene, i):
                        visible_globals.append((i, layer))
                except Exception:
                    continue

            if visible_globals:
                layout.label(text="Layers (global):")
                for i, layer in visible_globals:
                    try:
                        box = layout.box()
                        row = box.row(align=True)
                        sel = row.operator("rig.select_layer_items", text=layer.name, icon='RESTRICT_SELECT_OFF')
                        sel.layer_index = i
                        vis_op = row.operator("rig.toggle_layer_visibility", text="", 
                                              icon='HIDE_OFF' if layer.is_visible else 'HIDE_ON')
                        vis_op.layer_index = i
                        row.prop(layer, "show_extra_buttons", text="", icon='TOOL_SETTINGS')

                        if layer.show_extra_buttons:                    
                            sub_box = box.box()
                            r = sub_box.row(align=True)
                            r.operator("rig.delete_layer", text="", icon='TRASH').layer_index = i
                            r.operator("rig.rename_layer", text="", icon='GREASEPENCIL').layer_index = i
                            r.operator("rig.join_group_from_layer", text="", icon='GROUP').layer_index = i
                            r.operator("rig.add_to_existing_layer", text="", icon='ADD').layer_index = i
                            r.operator("rig.kick_selected_from_layer", text="", icon='X').layer_index = i
                            r.prop(layer, "export_mark", text="Mark for export")
                    except Exception as e:
                        box = layout.box()
                        box.label(text=f"⚠ Error in layer UI: {e}")


#======== GROUPS ==================================================================
        if hasattr(scene, "temp_groups") and scene.temp_groups.groups:
            layout.label(text="Groups:")
            for g_index, group in enumerate(scene.temp_groups.groups):
                box = layout.box()
                header = box.row()
                header.prop(group, "expanded", text="", 
                            icon='TRIA_DOWN' if group.expanded else 'TRIA_RIGHT', emboss=False)
                header.label(text=group.name)
                header.operator("rig.toggle_group_visibility", text="", 
                                icon='HIDE_OFF' if group.is_visible else 'HIDE_ON').group_index = g_index 
                                
                header.operator("rig.add_layer_to_group_via_enum", 
                                 text="", icon='ADD').group_index = g_index                                               
                header.operator("rig.rename_group", text="", icon='GREASEPENCIL').group_index = g_index
                header.operator("rig.delete_group", text="", icon='TRASH').group_index = g_index                  


                sub = header.row()
                sub.prop(group, "export_mark", text="")
                sub.label(text="Mark for export")              


                if group.expanded:
                    row_add = box.row(align=True)
#                    row_add.operator("rig.add_layer_to_group_via_enum", 
#                                     text="Add Layers", icon='ADD').group_index = g_index

                    if group.layer_indices:
                        box.label(text="Layers in group:")
                        for entry_idx, idx in enumerate(group.layer_indices):
                            li = idx.index
                            if 0 <= li < len(scene.temp_layers.layers):
                                layer_ref = scene.temp_layers.layers[li]

                                # Header bar per layer
                                row = box.row(align=True)
                                sel_op = row.operator("rig.select_layer_items", 
                                                      text=layer_ref.name, 
                                                      icon='RESTRICT_SELECT_OFF')
                                sel_op.layer_index = li
                                row.operator("rig.toggle_layer_visibility", text="", 
                                             icon='HIDE_OFF' if layer_ref.is_visible else 'HIDE_ON').layer_index = li
                                row.prop(layer_ref, "show_extra_buttons_group", text="", icon='TOOL_SETTINGS')

                                # Extra buttons
                                if layer_ref.show_extra_buttons_group:
                                    sub_box = box.box()
                                    r = sub_box.row(align=True)
                                    r.operator("rig.delete_layer", text="", icon='TRASH').layer_index = li
                                    r.operator("rig.rename_layer", text="", icon='GREASEPENCIL').layer_index = li
                                    r.operator("rig.join_group_from_layer", text="", icon='GROUP').layer_index = li
                                    r.operator("rig.add_to_existing_layer", text="", icon='ADD').layer_index = li
                                    r.operator("rig.kick_selected_from_layer", text="", icon='X').layer_index = li

                                    # remove from group
                                    rem = sub_box.operator("rig.remove_layer_from_group", 
                                                           text="Kick From Group", icon='X')
                                    rem.group_index = g_index
                                    rem.entry_index = entry_idx

        layout.separator()
        layout.label(text="Tips: Select bones/objects then use 'Kick Selected' on a layer to remove them.")

        
        

# -------------------------------------------------------------------



# Registration
# -------------------------------------------------------------------
classes = (
    TemporaryRigItem,
    TemporaryRigLayer,
    RigLayerManager,
    GroupLayerIndex,
    TemporaryRigGroup,
    RigGroupManager,

    VIEW3D_OT_isolate_toggle,

    RIG_OT_add_selection_to_layer,
    RIG_OT_add_to_existing_layer,
    RIG_OT_delete_layer,
    RIG_OT_rename_layer,
    RIG_OT_kick_selected_from_layer,

    RIG_OT_select_layer_items,
    RIG_OT_remove_item_from_layer,

    RIG_OT_join_group_from_layer,
    RIG_OT_add_layer_to_group_via_enum,
    RIG_OT_remove_layer_from_group,
    RIG_OT_toggle_group_visibility,

    RIG_OT_add_group,
    RIG_OT_delete_group,
    RIG_OT_rename_group,

    RIG_OT_export_layers_groups,
    RIG_OT_import_layers_groups,

    VIEW3D_PT_rig_layers_panel,
    
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.temp_layers = bpy.props.PointerProperty(type=RigLayerManager)
    bpy.types.Scene.temp_groups = bpy.props.PointerProperty(type=RigGroupManager)

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
