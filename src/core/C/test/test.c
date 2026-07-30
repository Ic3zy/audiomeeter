#include "devices.h"
#include "main.h"
#include "types.h"
#include <stdio.h>
#include <unistd.h>

int main() {
  init_audio_core();
  // struct SinkCore *sink =
  //     sink_create("alsa_output.pci-0000_00_1b.0.analog-stereo");

  struct DeviceCore *device = device_create("audiomeeter-aux-input");
  struct DeviceCore *devicet = device_create("audiomeeter-input");
  struct SinkCore *sink = sink_create("alsa_output.usb-XiiSound_Technology_"
                                      "Corporation_Fuxi-H7-00.iec958-stereo");

  // Wait 100ms for ports to register dynamically on the PipeWire server
  usleep(100000);

  // Link the ports now that they are registered
  device_link(device);
  device_link(devicet);
  sink_link(sink);

  device_set_bridged_sink(device, sink);
  device_set_bridged_sink(devicet, sink);

  printf("Hello World!\n");
  while (1) {
    sleep(1);
  }
  return 0;
}