#include "globals.h"
#include "pipe_process.h"
#include "types.h"
#include <assert.h>
#include <math.h>
#include <pipewire/pipewire.h>
#include <spa/param/audio/format-utils.h>
#include <stdbool.h>
#include <stdlib.h>

void sink_init(struct SinkCore *sink);
void device_init(struct DeviceCore *device);

static void on_stream_state_changed(void *data, enum pw_stream_state old,
                                    enum pw_stream_state state,
                                    const char *error) {

  struct SinkCore *sink = data;
  printf("[AudioMeeter-Debug] Sink (%s) durum değiştirdi: %s -> %s %s\n",
         sink->device_id, pw_stream_state_as_string(old),
         pw_stream_state_as_string(state), error ? error : "");
}

static const struct pw_stream_events passive_events = {
    .version = PW_VERSION_STREAM_EVENTS,
    .process = pipewire_process,
    .state_changed = on_stream_state_changed};

static const struct pw_stream_events master_events = {
    .version = PW_VERSION_STREAM_EVENTS,
    .process = pipewire_process,
    .state_changed = on_stream_state_changed};

// SINK CLASS
struct SinkCore *sink_create(char device_id[128]) {}
void sink_init(struct SinkCore *sink) {}

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
struct DeviceCore *device_create(char device_id[128]) {
  struct DeviceCore *device = calloc(1, sizeof(*device));
  if (device == NULL)
    abort();

  strcpy(device->device_id, device_id);

  global_manager.devices[global_manager.devices_count] = device;
  global_manager.devices_count++;

  struct pw_properties *props;

  if (device->is_main) {
    props = pw_properties_new(PW_KEY_MEDIA_TYPE, "Audio", PW_KEY_MEDIA_CATEGORY,
                              "Capture", PW_KEY_MEDIA_ROLE, "DSP",
                              PW_KEY_NODE_TARGET, device->device_id, NULL);

  } else {
    props = pw_properties_new(
        PW_KEY_MEDIA_TYPE, "Audio", PW_KEY_MEDIA_CATEGORY, "Capture",
        PW_KEY_MEDIA_ROLE, "DSP", PW_KEY_NODE_TARGET, device->device_id,
        "stream.capture.sink", "true", "node.passive", "true", NULL);
  }

  if (props == NULL)
    abort();

  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);
  device->pw_core.stream =
      pw_stream_new(global_manager.pw_manager.core, device->device_id, props);

  if (device->pw_core.stream == NULL) {
    pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
    abort();
  }

  pw_stream_add_listener(device->pw_core.stream, &device->pw_core.listener,
                         device->is_main ? &master_events : &passive_events,
                         device);

  uint8_t buffer[1024];
  struct spa_pod_builder b = SPA_POD_BUILDER_INIT(buffer, sizeof(buffer));
  const struct spa_pod *params[1];

  params[0] = spa_format_audio_raw_build(
      &b, SPA_PARAM_EnumFormat,
      &SPA_AUDIO_INFO_RAW_INIT(.format = SPA_AUDIO_FORMAT_F32, .channels = 2,
                               .rate = 48000));

  char *endptr;
  long id = strtol(device->device_id, &endptr, 10);
  uint32_t target_id = PW_ID_ANY;
  uint32_t flags = PW_STREAM_FLAG_MAP_BUFFERS | PW_STREAM_FLAG_RT_PROCESS;

  if (*endptr == '\0') {
    target_id = (uint32_t)id;
  } else {
    flags |= PW_STREAM_FLAG_AUTOCONNECT;
  }

  int res = pw_stream_connect(device->pw_core.stream, PW_DIRECTION_INPUT,
                              target_id, flags, params, 1);

  if (res < 0) {
    pw_stream_destroy(device->pw_core.stream);
    device->pw_core.stream = NULL;
    pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
    abort();
  }

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
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