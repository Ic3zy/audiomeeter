#include "globals.h"
#include "types.h"
#include <assert.h>
#include <pipewire/pipewire.h>
#include <spa/param/audio/format-utils.h>
#include <stdlib.h>

// SINK CLASS
struct SinkCore *sink_create() {
  struct SinkCore *sink = calloc(1, sizeof(*sink));

  if (sink == NULL)
    abort();

  return sink;
}

void sink_init(struct SinkCore *sink) {
  if (sink == NULL)
    abort();

  struct pw_properties *props = pw_properties_new(
      PW_KEY_MEDIA_TYPE, "Audio", PW_KEY_MEDIA_CATEGORY, "Capture",
      PW_KEY_MEDIA_ROLE, "DSP", PW_KEY_TARGET_OBJECT, sink->device_id, NULL);

  if (props == NULL) {
    abort();
  }

  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  sink->pw_core.stream = pw_stream_new_simple(
      global_manager.pw_manager.loop, "AudioMeeter-Sink-Capture", props,
      &(struct pw_stream_events){.version = PW_VERSION_STREAM_EVENTS}, NULL);

  if (sink->pw_core.stream == NULL) {
    pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
    abort();
  }

  uint8_t buffer[1024];
  struct spa_pod_builder b = SPA_POD_BUILDER_INIT(buffer, sizeof(buffer));
  const struct spa_pod *params[1];

  params[0] = spa_format_audio_raw_build(
      &b, SPA_PARAM_EnumFormat,
      &SPA_AUDIO_INFO_RAW_INIT(.format = SPA_AUDIO_FORMAT_F32, .channels = 2,
                               .rate = 48000));

  int res = pw_stream_connect(
      sink->pw_core.stream, PW_DIRECTION_INPUT, PW_ID_ANY,
      PW_STREAM_FLAG_AUTOCONNECT | PW_STREAM_FLAG_MAP_BUFFERS |
          PW_STREAM_FLAG_RT_PROCESS,
      params, 1);

  if (res < 0) {
    pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
    abort();
  }

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
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
