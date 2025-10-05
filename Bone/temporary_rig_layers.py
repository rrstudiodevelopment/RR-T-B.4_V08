import bpy
import os
import subprocess
import sys

# Simpan path file .py yang dipilih
class FileItem(bpy.types.PropertyGroup):
    filepath: bpy.props.StringProperty(name="File Path")

# UI Panel
class PYC_Converter_PT_UI(bpy.types.Panel):
    bl_label = "Py to PYC Converter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PyC Converter"

    def draw(self, context):
        layout = self.layout
        layout.operator("pyc_converter.select_files", icon='FILE_FOLDER')

        file_list = context.scene.pyc_converter_file_list
        if file_list:
            for item in file_list:
                layout.label(text=os.path.basename(item.filepath), icon="FILE_SCRIPT")
            layout.separator()
            layout.operator("pyc_converter.convert", icon='FILE_TICK')
            layout.operator("pyc_converter.unconvert", icon='TRASH')
        else:
            layout.label(text="Belum ada file .py dipilih", icon="INFO")

# Operator: Pilih File .py
class PYC_Converter_OT_SelectFiles(bpy.types.Operator):
    bl_idname = "pyc_converter.select_files"
    bl_label = "Pilih File .py"

    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        file_list = context.scene.pyc_converter_file_list
        file_list.clear()

        for f in self.files:
            if f.name.endswith(".py"):
                item = file_list.add()
                item.filepath = os.path.join(self.directory, f.name)

        self.report({'INFO'}, f"{len(file_list)} file dipilih.")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Operator: Convert .py ke .pyc
class PYC_Converter_OT_Convert(bpy.types.Operator):
    bl_idname = "pyc_converter.convert"
    bl_label = "Convert ke .pyc"

    def execute(self, context):
        blender_python = sys.executable
        total = 0
        for item in context.scene.pyc_converter_file_list:
            filepath = item.filepath
            if os.path.exists(filepath):
                try:
                    # Compile .py ke .pyc di __pycache__
                    subprocess.run([blender_python, "-m", "py_compile", filepath], check=True)

                    # Ambil nama file
                    filename = os.path.splitext(os.path.basename(filepath))[0]
                    dirpath = os.path.dirname(filepath)
                    pycache = os.path.join(dirpath, "__pycache__")

                    # Cari file .pyc dan rename ke format sederhana
                    for f in os.listdir(pycache):
                        if f.startswith(filename) and f.endswith(".pyc"):
                            src = os.path.join(pycache, f)
                            dst = os.path.join(dirpath, filename + ".pyc")
                            os.replace(src, dst)
                            break
                    total += 1
                except Exception as e:
                    self.report({'ERROR'}, f"Gagal compile: {filepath}\n{e}")
        self.report({'INFO'}, f"{total} file berhasil dikompilasi & disederhanakan.")
        return {'FINISHED'}

# Operator: Unconvert (hapus file .pyc)
class PYC_Converter_OT_Unconvert(bpy.types.Operator):
    bl_idname = "pyc_converter.unconvert"
    bl_label = "Hapus File .pyc"

    def execute(self, context):
        total = 0
        for item in context.scene.pyc_converter_file_list:
            path_pyc = os.path.splitext(item.filepath)[0] + ".pyc"
            if os.path.exists(path_pyc):
                try:
                    os.remove(path_pyc)
                    total += 1
                except Exception as e:
                    self.report({'ERROR'}, f"Gagal hapus: {path_pyc}")
        self.report({'INFO'}, f"{total} file .pyc berhasil dihapus.")
        return {'FINISHED'}

# Registrasi kelas
classes = (
    FileItem,
    PYC_Converter_PT_UI,
    PYC_Converter_OT_SelectFiles,
    PYC_Converter_OT_Convert,
    PYC_Converter_OT_Unconvert,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pyc_converter_file_list = bpy.props.CollectionProperty(type=FileItem)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.pyc_converter_file_list

register()
