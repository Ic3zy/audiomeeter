from base import Ctx
from core import Lv2Core
import asyncio

_CTX_NAMES = [
    "Lv2_H_in_A1",
    "Lv2_H_in_A2",
    "Lv2_H_in_A3",
    "Lv2_V_in_main",
    "Lv2_V_in_aux",
    "Lv2_H_out_A1",
    "Lv2_H_out_A2",
    "Lv2_H_out_A3",
    "Lv2_V_out_b1",
    "Lv2_V_out_b2",
]
_DEVICE_NAMES = [
    "Hardware Input 1",
    "Hardware Input 2",
    "Hardware Input 3",
    "Virtual Input main",
    "Virtual Input aux",
    "Hardware Output 1",
    "Hardware Output 2",
    "Hardware Output 3",
    "Virtual Output B1",
    "Virtual Output B2",
]
CTX_TO_DEVICE = dict(zip(_CTX_NAMES, _DEVICE_NAMES))
DEVICE_TO_CTX = dict(zip(_DEVICE_NAMES, _CTX_NAMES))


def ctx_to_device(ctx_name):
    return CTX_TO_DEVICE[ctx_name]


def device_to_ctx(device_name):
    return DEVICE_TO_CTX[device_name]


def get_ctx_names():
    return _CTX_NAMES


def get_device_names():
    return _DEVICE_NAMES


def device_name_to_ctx_name(d_name):
    name = DEVICE_TO_CTX.get(d_name, d_name)
    return f"Lv2Device_{name}"


def device_id_to_ctx_name(d_id):
    if d_id in DEVICE_TO_CTX:
        d_id = DEVICE_TO_CTX[d_id]
    return f"Lv2Device_{d_id}"


def get_plugins_from_ctx_name(name):
    return Ctx.get(f"{name}_plugins")


def get_plugins_from_device_name(name):
    ctx_name = device_name_to_ctx_name(name)
    return get_plugins_from_ctx_name(ctx_name) or []


def get_last_plugin_id_from_device_name(name):
    ctx_name = device_name_to_ctx_name(name)
    c = 0
    last_id = 0

    while Ctx.get(f"{ctx_name}_pl_s_{c}") is not None:
        if c > last_id:
            last_id = c
        c += 1

    return last_id


CTX_TO_AUDIO_CORE_TARGET = {
    "Lv2_H_in_A1": ("device", "in_1"),
    "Lv2_H_in_A2": ("device", "in_2"),
    "Lv2_H_in_A3": ("device", "in_3"),
    "Lv2_V_in_main": ("device", "V_in_main"),
    "Lv2_V_in_aux": ("device", "V_in_aux"),
    "Lv2_H_out_A1": ("sink", "A1"),
    "Lv2_H_out_A2": ("sink", "A2"),
    "Lv2_H_out_A3": ("sink", "A3"),
    "Lv2_V_out_b1": ("sink", "B1"),
    "Lv2_V_out_b2": ("sink", "B2"),
}


def get_audio_device_or_sink_by_name(ctx_or_dev_name):
    if ctx_or_dev_name in DEVICE_TO_CTX:
        raw_ctx = DEVICE_TO_CTX[ctx_or_dev_name]
    else:
        raw_ctx = ctx_or_dev_name.replace("Lv2Device_", "")

    target_info = CTX_TO_AUDIO_CORE_TARGET.get(raw_ctx)
    if not target_info:
        return None

    audio_core = Ctx.get("audio_core")
    if audio_core is None:
        return None

    kind, key = target_info
    if kind == "device":
        return audio_core.devices.get(key)
    elif kind == "sink":
        return audio_core.sinks.get(key)

    return None


def bind_lv2_to_audio_device(name, lv2_manager):
    if lv2_manager is None:
        return
    audio_obj = get_audio_device_or_sink_by_name(name)
    if audio_obj is not None and hasattr(audio_obj, "set_lv2_manager"):
        audio_obj.set_lv2_manager(lv2_manager)


def add_plugin_to_device_from_device_name(name, plugin):
    ctx_name = device_name_to_ctx_name(name)
    if not Ctx.get(f"{ctx_name}_plugins"):
        Ctx.set_custom_list(f"{ctx_name}_plugins", [plugin])
    else:
        Ctx.get(f"{ctx_name}_plugins").append(plugin)

    core = Ctx.get(f"{ctx_name}_core")
    if core is None:
        core = Lv2Core()
        Ctx[f"{ctx_name}_core"] = core

    if core.is_initialized:
        core.add_plugin(plugin)
        bind_lv2_to_audio_device(name, core.lv2_manager)
    else:

        def _on_init(l):
            core.add_plugin(plugin)
            bind_lv2_to_audio_device(name, core.lv2_manager)

        asyncio.create_task(core.get_available_plugins(_on_init))


def delete_plugin_from_device_name(name, plugin):
    ctx_name = device_name_to_ctx_name(name)
    plugins = Ctx.get(f"{ctx_name}_plugins")
    if not plugins:
        return

    if plugin in plugins:
        plugins.remove(plugin)


def get_plugin_index_from_plugin(device_name, plugin):
    ctx_name = device_name_to_ctx_name(device_name)
    plugins = Ctx.get(f"{ctx_name}_plugins") or []
    for c, pl in enumerate(plugins):
        if isinstance(pl, dict) and pl.get("uri") == plugin.get("uri"):
            return c
    return None


def get_plugin_info(device_name, plugin):
    ctx_name = device_name_to_ctx_name(device_name)
    core = Ctx.get(f"{ctx_name}_core")
    if core is None or not core.is_initialized:
        raise ValueError("Lv2Core not initialized.")

    index = get_plugin_index_from_plugin(device_name, plugin)
    if index is None:
        raise ValueError(f"Plugin not found: {plugin}")

    info = core.get_info(index)
    return info


def save_callback_all_devices(callback):
    for name in get_ctx_names():
        Ctx.add_callback(f"{device_id_to_ctx_name(name)}_plugins", callback)


def get_available_plugins_for_callback(name, callback):
    ctx_name = device_name_to_ctx_name(name)
    core = Ctx.get(f"{ctx_name}_core")
    if core is None:
        core = Lv2Core()
        Ctx[f"{ctx_name}_core"] = core
        asyncio.create_task(core.get_available_plugins(callback))
    else:
        core.get_available_plugins_for_callback(callback)


def add_plugins_to_device_from_core(core, plugins):
    for plugin in plugins:
        core.add_plugin(plugin)


def init_lv2():
    top_plugins = {}
    for name in get_ctx_names():
        ctx_key = device_id_to_ctx_name(name)
        plugins = Ctx.get(f"{ctx_key}_plugins")
        if plugins:
            top_plugins[name] = plugins

    if not top_plugins:
        print("No plugins found.")
        return

    async def _async_init_all():
        for name, plugins in top_plugins.items():
            ctx_key = device_id_to_ctx_name(name)
            core = Ctx.get(f"{ctx_key}_core")
            if core is None:
                core = Lv2Core()
                Ctx[f"{ctx_key}_core"] = core
            if not core.is_initialized:
                await core.get_available_plugins()
            add_plugins_to_device_from_core(core, plugins)

            bind_lv2_to_audio_device(name, core.lv2_manager)

    asyncio.create_task(_async_init_all())


# TODO: optimize
Ctx.add_callback("ctx_init", init_lv2)
