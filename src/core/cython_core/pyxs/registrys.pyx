from cython_core.pxds.globals cimport manager
from cython_core.pxds.types cimport AudioCore, SinkCore, MAX_ROUTES_PER_DEVICE, MAX_DEVICES
from cython_core.pyxs.devices cimport ListenDevice, SinkDevice

class registry:
    def __init__(self):
        self.instances = {}
        self.last_instance_id = 0

    def _next_id(self):
        i = self.last_instance_id

        if i >= MAX_DEVICES:
            raise IndexError("Device ID out of bounds")
            
        self.last_instance_id += 1
        return i

    def create(self, *args, **kwargs):
        raise NotImplementedError

    def get(self, name):
        return self.instances.get(name)

    def remove(self, name):
        self.instances.pop(name, None)

    def values(self):
        return self.instances.values()

class DeviceRegistry(registry):
    cdef void register_device(self, int device_id, AudioCore * core):
        manager.listen_devices[device_id] = core

    def create(self, str device_id, str device_name):
        if manager == NULL:
            raise RuntimeError("Manager is not initialized!")
        
        listen = ListenDevice(device_id.encode('utf-8'), self._next_id())

        self.devices[device_name] = listen

        self.register_device(
            <int>listen.get_id(),
            <AudioCore *>listen.core
        )
            
        return listen

class SinkDeviceRegistry(registry):
    cdef void register_sink(self, int device_id, SinkCore * sink_core):
        manager.sink_devices[device_id] = sink_core

    def create(self, str device_id, str device_name):
        if manager == NULL:
            raise RuntimeError("Manager is not initialized!")

        sink = SinkDevice(device_id.encode('utf-8'), self._next_id())

        self.devices[device_name] = sink

        self.register_sink(
            <int>sink.get_id(),
            <SinkCore *>sink.core
        )
            
        return sink

class BridgeManager:
    def __init__(self, devices, sinks):
        self.devices = devices
        self.sinks = sinks

    cdef attach_sink(self, AudioCore * device_core, SinkCore * sink_core) noexcept nogil:
        device_core.bridged_sinks[device_core.active_bridge_count] = sink_core
        device_core.active_bridge_count += 1

    def create(self, device_name, sink_name):
        if manager == NULL:
            raise RuntimeError("Manager is not initialized!")

        device = self.devices.get(device_name)
        sink = self.sinks.get(sink_name)

        if device is None:
            raise ValueError(f"Device not found: {device_name}")

        if sink is None:
            raise ValueError(f"Sink not found: {sink_name}")

        if active_device.core.active_bridge_countbridge_count >= MAX_ROUTES_PER_DEVICE:
            raise OverflowError("Maximum route limit reached for this device!")

        self.attach_sink(
            <AudioCore *>device.core,
            <SinkCore *>sink.core
        )

class Distributor:
    def __init__(self):
        self.device_registry = DeviceRegistry()
        self.sink_registry = SinkDeviceRegistry()
        self.bridge_manager = BridgeManager(
            self.device_registry,
            self.sink_registry
        )
        