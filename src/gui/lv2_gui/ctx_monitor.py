from base import Ctx

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
    name = DEVICE_TO_CTX[d_name]
    return f"Lv2Device_{name}"


def device_id_to_ctx_name(d_id):
    return f"Lv2Device_{d_id}"


def get_plugins_from_ctx_name(name):
    return Ctx.get(f"{name}_plugins")


def get_plugins_from_device_name(name):
    ctx_name = device_name_to_ctx_name(name)

    t = {
        "name": "LSP A/B Tester x8 Stereo",
        "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x8_stereo",
        "category": "Utility Plugin",
    }

    # add_plugin_to_device_from_device_name(name, t)

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


def add_plugin_to_device_from_device_name(name, plugin):
    ctx_name = device_name_to_ctx_name(name)
    if not Ctx.get(f"{ctx_name}_plugins"):
        Ctx.set_custom_list(f"{ctx_name}_plugins", [plugin])
    else:
        Ctx.get(f"{ctx_name}_plugins").append(plugin)


def save_callback_all_devices(callback):
    for name in get_ctx_names():
        Ctx.add_callback(f"{device_id_to_ctx_name(name)}_plugins", callback)
