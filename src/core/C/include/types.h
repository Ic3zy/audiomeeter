#pragma once

#include "constants.h"
#include <pipewire/pipewire.h>

// PipeWire core
struct PwCore {
  // TODO: implement
  struct pw_stream *stream;

  int sample_rate;
  int channels;
};

struct Equalizer {
  // TODO: implement
  int k;
};

struct SinkCore {
  struct PwCore pw_core;

  char device_id[MAX_DEVICE_ID];
  int dB;
  int is_main;
};

struct DeviceCore {
  struct PwCore pw_core;
  struct SinkCore *bridged_sinks[MAX_ROUTES_PER_DEVICE];
  int bridged_sinks_count;

  char device_id[MAX_DEVICE_ID];
  int dB;
};

struct PwManager {
  struct pw_loop *loop;
  struct pw_thread_loop *threaded_loop;
  int pw_inited;
};

struct Manager {
  struct SinkCore *sinks[MAX_DEVICES];
  struct DeviceCore *devices[MAX_DEVICES];

  int devices_count, sinks_count, instance_id;
  struct PwManager pw_manager;
};