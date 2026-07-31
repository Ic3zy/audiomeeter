#include "devices.h"
#include "main.h"
#include "types.h"
#include <stdio.h>
#include <unistd.h>

int main() {
  init_audio_core();

  struct DeviceCore *device = device_create("audiomeeter-aux-input");
  struct DeviceCore *devicet = device_create("audiomeeter-input");

  // Wait 100ms for device ports to register
  usleep(100000);

  device_link(device);
  device_link(devicet);

  // sink_create now handles port creation + sync + linking atomically
  struct SinkCore *sink = sink_create("A1",
      "alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.iec958-stereo");

  device_set_bridged_sink(device, sink);
  device_set_bridged_sink(devicet, sink);

  printf("Hello World!\n");
  while (1) {
    sleep(1);
  }
  return 0;
}