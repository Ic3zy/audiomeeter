#include "globals.h"
#include "pipe_process.h"
#include "types.h"
#include <assert.h>
#include <math.h>
#include <pipewire/pipewire.h>
#include <spa/param/audio/format-utils.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ENGINE_NODE_NAME "AudioMeeterEngine"

struct link_proxy_data {
  struct spa_hook proxy_listener;
};

static void on_link_proxy_error(void *data, int seq, int res,
                                const char *message) {
  (void)seq;
  fprintf(stderr, "[pipe_process] link error (res=%d): %s\n", res, message);
}

static void on_link_proxy_destroy(void *data) {
  struct link_proxy_data *pdata = data;
  free(pdata);
}

static const struct pw_proxy_events link_proxy_events = {
    PW_VERSION_PROXY_EVENTS,
    .destroy = on_link_proxy_destroy,
    .error = on_link_proxy_error,
};

struct pw_link *create_pw_link(struct pw_core *core, const char *output_node,
                               const char *output_port, const char *input_node,
                               const char *input_port) {
  struct pw_properties *props =
      pw_properties_new("link.output.port", output_port, "link.input.port",
                        input_port, "object.linger", "false", NULL);

  if (props == NULL)
    return NULL;

  if (output_node != NULL)
    pw_properties_set(props, "link.output.node", output_node);
  if (input_node != NULL)
    pw_properties_set(props, "link.input.node", input_node);

  struct pw_proxy *proxy =
      pw_core_create_object(core, "link-factory", "PipeWire:Interface:Link",
                            PW_VERSION_LINK, &props->dict, 0);

  pw_properties_free(props);

  if (proxy == NULL)
    return NULL;

  struct link_proxy_data *pdata = calloc(1, sizeof(*pdata));
  if (pdata != NULL) {
    pw_proxy_add_listener(proxy, &pdata->proxy_listener, &link_proxy_events,
                          pdata);
  }

  return (struct pw_link *)proxy;
}

void sink_init(struct SinkCore *sink);
void device_init(struct DeviceCore *device);

// SINK CLASS
struct SinkCore *sink_create(const char *device_id) {
  if (global_manager.sinks_count >=
      (int)(sizeof(global_manager.sinks) / sizeof(global_manager.sinks[0]))) {
    fprintf(stderr, "[pipe_process] sink_create: max sink count reached\n");
    return NULL;
  }

  struct SinkCore *sink = calloc(1, sizeof(*sink));
  if (sink == NULL)
    abort();

  strncpy(sink->device_id, device_id, sizeof(sink->device_id) - 1);
  sink->dB = 0; // Default volume is 0 dB (gain = 1.0)

  global_manager.sinks[global_manager.sinks_count] = sink;
  global_manager.sinks_count++;

  sink_init(sink);

  return sink;
}

void sink_init(struct SinkCore *sink) {
  if (sink == NULL)
    abort();

  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  char port_name_l[256];
  char port_name_r[256];
  snprintf(port_name_l, sizeof(port_name_l), "%s_L", sink->device_id);
  snprintf(port_name_r, sizeof(port_name_r), "%s_R", sink->device_id);

  struct pw_properties *props_l =
      pw_properties_new(PW_KEY_FORMAT_DSP, "32 bit float mono audio",
                        PW_KEY_PORT_NAME, port_name_l, NULL);
  struct pw_properties *props_r =
      pw_properties_new(PW_KEY_FORMAT_DSP, "32 bit float mono audio",
                        PW_KEY_PORT_NAME, port_name_r, NULL);

  sink->pw_core.port_l =
      pw_filter_add_port(global_manager.filter, PW_DIRECTION_OUTPUT,
                         PW_FILTER_PORT_FLAG_MAP_BUFFERS, 0, props_l, NULL, 0);

  sink->pw_core.port_r =
      pw_filter_add_port(global_manager.filter, PW_DIRECTION_OUTPUT,
                         PW_FILTER_PORT_FLAG_MAP_BUFFERS, 0, props_r, NULL, 0);

  if (sink->pw_core.port_l == NULL || sink->pw_core.port_r == NULL) {
    pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
    abort();
  }

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
}

void sink_link(struct SinkCore *sink) {
  if (sink == NULL)
    abort();

  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  char port_name_l[256];
  char port_name_r[256];
  snprintf(port_name_l, sizeof(port_name_l), "%s_L", sink->device_id);
  snprintf(port_name_r, sizeof(port_name_r), "%s_R", sink->device_id);

  sink->pw_core.link_l =
      create_pw_link(global_manager.pw_manager.core, ENGINE_NODE_NAME,
                     port_name_l, sink->device_id, "playback_FL");

  sink->pw_core.link_r =
      create_pw_link(global_manager.pw_manager.core, ENGINE_NODE_NAME,
                     port_name_r, sink->device_id, "playback_FR");

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
struct DeviceCore *device_create(const char *device_id) {
  if (global_manager.devices_count >=
      (int)(sizeof(global_manager.devices) /
            sizeof(global_manager.devices[0]))) {
    fprintf(stderr, "[pipe_process] device_create: max device count reached\n");
    return NULL;
  }

  struct DeviceCore *device = calloc(1, sizeof(*device));
  if (device == NULL)
    abort();

  strncpy(device->device_id, device_id, sizeof(device->device_id) - 1);
  device->dB = 0; // Default volume is 0 dB (gain = 1.0)

  global_manager.devices[global_manager.devices_count] = device;
  global_manager.devices_count++;

  device_init(device);

  return device;
}

void device_init(struct DeviceCore *device) {
  if (device == NULL)
    abort();

  // PipeWire Thread Kilitlenir
  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  char port_name_l[256];
  char port_name_r[256];
  snprintf(port_name_l, sizeof(port_name_l), "%s_L", device->device_id);
  snprintf(port_name_r, sizeof(port_name_r), "%s_R", device->device_id);

  struct pw_properties *props_l =
      pw_properties_new(PW_KEY_FORMAT_DSP, "32 bit float mono audio",
                        PW_KEY_PORT_NAME, port_name_l, NULL);
  struct pw_properties *props_r =
      pw_properties_new(PW_KEY_FORMAT_DSP, "32 bit float mono audio",
                        PW_KEY_PORT_NAME, port_name_r, NULL);

  device->pw_core.port_l =
      pw_filter_add_port(global_manager.filter, PW_DIRECTION_INPUT,
                         PW_FILTER_PORT_FLAG_MAP_BUFFERS, 0, props_l, NULL, 0);

  device->pw_core.port_r =
      pw_filter_add_port(global_manager.filter, PW_DIRECTION_INPUT,
                         PW_FILTER_PORT_FLAG_MAP_BUFFERS, 0, props_r, NULL, 0);

  if (device->pw_core.port_l == NULL || device->pw_core.port_r == NULL) {
    pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
    abort();
  }

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
}

void device_link(struct DeviceCore *device) {
  if (device == NULL)
    abort();

  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  char port_name_l[256];
  char port_name_r[256];
  snprintf(port_name_l, sizeof(port_name_l), "%s_L", device->device_id);
  snprintf(port_name_r, sizeof(port_name_r), "%s_R", device->device_id);

  const char *prefix = "capture";
  if (strstr(device->device_id, "output") != NULL ||
      strstr(device->device_id, "audiomeeter") != NULL) {
    prefix = "monitor";
  }

  char src_port_l[64];
  char src_port_r[64];
  if (strstr(device->device_id, "mono") != NULL ||
      strstr(device->device_id, "Mono") != NULL ||
      strstr(device->device_id, "MONO") != NULL) {
    snprintf(src_port_l, sizeof(src_port_l), "%s_MONO", prefix);
    snprintf(src_port_r, sizeof(src_port_r), "%s_MONO", prefix);
  } else {
    snprintf(src_port_l, sizeof(src_port_l), "%s_FL", prefix);
    snprintf(src_port_r, sizeof(src_port_r), "%s_FR", prefix);
  }

  device->pw_core.link_l =
      create_pw_link(global_manager.pw_manager.core, device->device_id,
                     src_port_l, ENGINE_NODE_NAME, port_name_l);

  device->pw_core.link_r =
      create_pw_link(global_manager.pw_manager.core, device->device_id,
                     src_port_r, ENGINE_NODE_NAME, port_name_r);

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
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
