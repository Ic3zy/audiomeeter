#include "types.h"
#include <assert.h>
#include <stdlib.h>

// SINK CLASS
struct SinkCore *sink_create() {
  struct SinkCore *sink = calloc(1, sizeof(*sink));

  if (sink == NULL)
    abort();

  return sink;
}

int sink_get_dB(struct SinkCore *sink) {
  if (sink == NULL)
    return -1;

  return sink->dB;
}

int sink_set_dB(struct SinkCore *sink, int dB) {
  if (sink == NULL)
    return -1;

  sink->dB = dB;

  return 0;
}
// END SINK CLASS

// DEVICE CLASS
struct DeviceCore *device_create() {

  struct DeviceCore *device = calloc(1, sizeof(*device));

  if (device == NULL)
    abort();

  return device;
}

void device_init(struct DeviceCore *device) {
  if (device == NULL)
    abort();
}

int device_get_dB(struct DeviceCore *device) {
  if (device == NULL)
    return -1;

  return device->dB;
}

int device_set_dB(struct DeviceCore *device, int dB) {
  if (device == NULL)
    return -1;

  device->dB = dB;
  return 0;
}

int device_set_bridged_sink(struct DeviceCore *device, struct SinkCore *sink) {
  if (device == NULL || sink == NULL)
    return -1;

  if (device->bridged_sinks_count >= MAX_ROUTES_PER_DEVICE)
    return -2;

  device->bridged_sinks[device->bridged_sinks_count] = sink;
  device->bridged_sinks_count++;

  return 0;
}
// END DEVICE CLASS
