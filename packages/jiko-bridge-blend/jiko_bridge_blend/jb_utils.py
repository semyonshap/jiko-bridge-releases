import bpy


addon_keymaps: list = []


def register_keymap():
    """Register keymap"""
    wm = bpy.context.window_manager
    if not wm:
        return

    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.get("3D View")
        if km is None:
            km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

        for item in km.keymap_items:
            if (
                item.idname == "wm.call_menu_pie"
                and item.properties.get("name", "") == "JB_MT_PIE_MAIN"
            ):
                return

        kmi = km.keymap_items.new(
            "wm.call_menu_pie",
            type="J",
            value="PRESS",
            shift=True,
        )
        kmi.properties.name = "JB_MT_PIE_MAIN"
        addon_keymaps.append((km, kmi))


def unregister_keymap():
    """Unregister keymap"""
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
