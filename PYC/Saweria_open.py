

import atexit
import webbrowser
import bpy

def open_saweria_link():
    try:
        webbrowser.open("https://saweria.co/rrstudio26")
    except Exception as e:
        print("Gagal membuka link:", e)

@atexit.register
def on_blender_close():
    open_saweria_link()

# Tidak perlu class/operator/add handler tambahan karena hanya trigger saat Blender ditutup.

def register():
    print("Addon 'Auto Open Link on Close' aktif.")

def unregister():
    print("Addon 'Auto Open Link on Close' nonaktif.")

if __name__ == "__main__":
    register()
