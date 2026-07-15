#pragma once

#include "constants.h"
#include <pipewire/pipewire.h>

// PipeWire core
struct PwCore {
  // TODO: implement
  int a;
};

struct SinkCore {
  struct PwCore pw_core;

  char device_id[MAX_DEVICE_ID];
  int dB;
};

struct DeviceCore {
  struct PwCore pw_core;
  struct SinkCore *bridged_sinks[MAX_ROUTES_PER_DEVICE];
  int bridged_sinks_count;

  char device_id[MAX_DEVICE_ID];
  int dB;
};

struct PwManager {
  struct pw_thread_loop *threaded_loop;
  struct pw_loop *loop;
  int pw_inited;
};

struct Manager {
  struct DeviceCore *devices[MAX_DEVICES];
  struct SinkCore *sinks[MAX_DEVICES];

  int devices_count, sinks_count;

  struct PwManager pw_manager;
};