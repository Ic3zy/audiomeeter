#pragma once

#include "constants.h"
#include <pipewire/pipewire.h>

// PipeWire core
struct PwCore {
  struct pw_stream *stream;
  struct spa_hook listener;

  int sample_rate;
  int channels;
};

struct Equalizer {
  // TODO: implement
  int k;
};

// output device
struct SinkCore {
  struct PwCore pw_core;

  char device_id[MAX_DEVICE_ID];
  int dB;
};

// input device
struct DeviceCore {
  struct PwCore pw_core;
  struct SinkCore *bridged_sinks[MAX_ROUTES_PER_DEVICE];
  int bridged_sinks_count;

  char device_id[MAX_DEVICE_ID];
  int dB;
  int is_main;
};

struct PwManager {
  struct pw_loop *loop;
  struct pw_thread_loop *threaded_loop;

  struct pw_context *global_pw_context;
  struct pw_core *core;

  int pw_inited;
};

struct Manager {
  struct SinkCore *sinks[MAX_DEVICES];
  struct DeviceCore *devices[MAX_DEVICES];

  int devices_count, sinks_count, instance_id;
  struct PwManager pw_manager;
  int sink_main_device_init;
};