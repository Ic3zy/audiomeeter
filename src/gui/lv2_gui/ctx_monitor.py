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


def device_name_to_ctx_name(name):
    return f"Lv2Device_{name}"


def get_plugins_from_device_name(name):
    pass
