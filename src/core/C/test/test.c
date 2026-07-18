#include "devices.h"
#include "main.h"
#include "types.h"
#include <stdio.h>

int main() {
  init_audio_core();
  sleep(1);
  // struct SinkCore *sink =
  //     sink_create("alsa_output.pci-0000_00_1b.0.analog-stereo");

  struct DeviceCore *device =
      device_create("alsa_output.pci-0000_00_1b.0.analog-stereo.monitor");

  printf("Hello World!\n");
  while (1) {
    sleep(1);
  }
  return 0;
}