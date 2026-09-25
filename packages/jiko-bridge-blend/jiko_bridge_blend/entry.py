from jiko_bridge_blend.jb_plugin import register, unregister

# Blender reads bl_info and calls both entry points on the addon module.
__all__ = ["bl_info", "register", "unregister"]

bl_info = {
    "name": "Jiko Bridge",
    "author": "JIKO",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar > Jiko Bridge",
    "description": "Jiko Bridge",
    "category": "3D View",
    "doc_url": "https://with-jiko.com",
    "tracker_url": "https://t.me/withjiko",
}

if __name__ == "__main__":
    register()
