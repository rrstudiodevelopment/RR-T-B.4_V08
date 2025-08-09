import bpy
import collections

layout_mode = "COLUMN"  # Bisa juga "ROW"

def get_bone_collections(armature):
    if hasattr(armature, "collections_all"):
        return armature.collections_all
    elif hasattr(armature, "collections"):
        return armature.collections
    return []

def has_rigify_ui(armature):
    for coll in get_bone_collections(armature):
        if 'rigify_ui_row' in coll:
            return True
    return False

class RIGLAYERS_OT_popup(bpy.types.Operator):
    bl_idname = "riglayers.popup"
    bl_label = "Bone Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            layout.label(text="No armature selected", icon='ERROR')
            return

        armature = obj.data
        is_rigify = has_rigify_ui(armature)
        row_table = collections.defaultdict(list)

        for coll in get_bone_collections(armature):
            if is_rigify:
                row_id = coll.get('rigify_ui_row', 0)
                if row_id > 0:
                    row_table[row_id].append(coll)
            else:
                row_table[0].append(coll)

        if not row_table:
            layout.label(text="No Bone Collections Found")
            return

        if is_rigify:
            for row_id in sorted(row_table.keys()):
                row = layout.row(align=True)
                row.scale_y = 1.2
                for coll in row_table[row_id]:
                    title = coll.get('rigify_ui_title') or coll.name
                    sub = row.row(align=True)
                    sub.active = coll.is_visible_ancestors
                    sub.prop(coll, 'is_visible', toggle=True, text=title)
        else:
            main = layout.row() if layout_mode == "ROW" else layout.column()
            for coll in row_table[0]:
                title = coll.name
                main.prop(coll, 'is_visible', toggle=True, text=title)

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)


class RIGLAYERS_HT_tool_header(bpy.types.Header):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOL_HEADER'
    bl_label = ""

    def draw(self, context):
        layout = self.layout
        layout.operator("riglayers.popup", text="Bone Collections", icon='GROUP_BONE')


classes = (
    RIGLAYERS_OT_popup,
    RIGLAYERS_HT_tool_header,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_HT_tool_header.append(RIGLAYERS_HT_tool_header.draw)

def unregister():
    bpy.types.VIEW3D_HT_tool_header.remove(RIGLAYERS_HT_tool_header.draw)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
