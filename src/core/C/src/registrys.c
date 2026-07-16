#include "constants.h"
#include "devices.h"
#include "globals.h"
#include "types.h"

#include <stdlib.h>

// SINK REGISTRY CLASS
int SinkRegistry_check_if_exists(char device_id[128]) {
  if (device_id == NULL)
    abort();

  for (int i = 0; i < MAX_DEVICES; i++) {
    if (global_manager.devices[i] == NULL)
      continue;

    if (strcmp(global_manager.devices[i]->device_id, device_id) == 0)
      return 1;
  }

  return 0;
}

void SinkRegistry_create(char device_id[128]) {
  struct SinkCore *sink = sink_create();

  if (global_manager.sinks_count >= MAX_DEVICES)
    return;

  if (SinkRegistry_check_if_exists(device_id) == 1)
    return;

  global_manager.sinks[global_manager.sinks_count] = sink;
  global_manager.sinks_count++;
}
// END SINK REGISTRY CLASS

// DEVICE REGISRY CLASS
int DeviceRegistry_check_if_exists(char device_id[128]) {
  if (device_id == NULL)
    abort();

  for (int i = 0; i < MAX_DEVICES; i++) {
    if (global_manager.devices[i] == NULL)
      continue;

    if (strcmp(global_manager.devices[i]->device_id, device_id) == 0)
      return 1;
  }

  return 0;
}

void DeviceRegistry(char device_id[128]) {
  struct DeviceCore *device = device_create();
  device_init(device);

  if (global_manager.devices_count >= MAX_DEVICES)
    return;

  if (SinkRegistry_check_if_exists(device_id) == 1)
    return;
}

// END DEVICE REGISTRY CLASS