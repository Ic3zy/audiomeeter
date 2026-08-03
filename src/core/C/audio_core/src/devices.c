#include "globals.h"
#include "rt_biquad.h"
#include "types.h"
#include <assert.h>
#include <pipewire/pipewire.h>
#include <spa/param/audio/format-utils.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ENGINE_NODE_NAME "AudioMeeterEngine"

struct link_proxy_data {
  struct spa_hook proxy_listener;
  char info[256];
};

static void on_link_proxy_error(void *data, int seq, int res,
                                const char *message) {
  (void)seq;
  struct link_proxy_data *pdata = data;
  if (pdata && pdata->info[0] != '\0') {
    fprintf(stderr, "[pipe_process] link error [%s] (res=%d): %s\n",
            pdata->info, res, message);
  } else {
    fprintf(stderr, "[pipe_process] link error (res=%d): %s\n", res, message);
  }
}

static void on_link_proxy_destroy(void *data) {
  struct link_proxy_data *pdata = data;
  spa_hook_remove(&pdata->proxy_listener);
  free(pdata);
}

static const struct pw_proxy_events link_proxy_events = {
    PW_VERSION_PROXY_EVENTS,
    .destroy = on_link_proxy_destroy,
    .error = on_link_proxy_error,
};

/* ── Sync roundtrip helper ─────────────────────────────────────────────────
 * Blocks (with loop already locked) until the PipeWire server has processed
 * all pending requests up to this point.  Use after pw_proxy_destroy() calls
 * to guarantee the server has removed the old links before we create new ones.
 */
struct _sync_state {
  struct pw_thread_loop *loop;
  int pending_seq;
  bool done;
};

static void _on_core_done(void *data, uint32_t id, int seq) {
  struct _sync_state *s = data;
  if (id == PW_ID_CORE && seq == s->pending_seq) {
    s->done = true;
    pw_thread_loop_signal(s->loop, false);
  }
}

static const struct pw_core_events _sync_core_events = {
    PW_VERSION_CORE_EVENTS,
    .done = _on_core_done,
};

/* Must be called with the thread loop already locked. */
static void pw_sync_roundtrip(struct pw_thread_loop *loop,
                              struct pw_core *core) {
  struct _sync_state state = {.loop = loop, .done = false};
  struct spa_hook core_listener;
  pw_core_add_listener(core, &core_listener, &_sync_core_events, &state);
  state.pending_seq = pw_core_sync(core, PW_ID_CORE, 0);
  while (!state.done)
    pw_thread_loop_wait(loop);
  spa_hook_remove(&core_listener);
}

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
    snprintf(pdata->info, sizeof(pdata->info), "%s:%s -> %s:%s",
             output_node ? output_node : "*", output_port ? output_port : "*",
             input_node ? input_node : "*", input_port ? input_port : "*");
    pw_proxy_add_listener(proxy, &pdata->proxy_listener, &link_proxy_events,
                          pdata);
  }

  return (struct pw_link *)proxy;
}

void sink_init(struct SinkCore *sink);
void device_init(struct DeviceCore *device);

// SINK CLASS

// Internal: tear down PipeWire resources of a sink (links + ports) inside an
// already-held lock, then sync roundtrip so the server fully processes the
// removes before we reuse port IDs.
static void sink_teardown_pw_locked(struct SinkCore *sink) {
  // Destroy links
  if (sink->pw_core.link_l != NULL) {
    pw_proxy_destroy((struct pw_proxy *)sink->pw_core.link_l);
    sink->pw_core.link_l = NULL;
  }
  if (sink->pw_core.link_r != NULL) {
    pw_proxy_destroy((struct pw_proxy *)sink->pw_core.link_r);
    sink->pw_core.link_r = NULL;
  }

  // Remove ports
  if (sink->pw_core.port_l != NULL) {
    pw_filter_remove_port(sink->pw_core.port_l);
    sink->pw_core.port_l = NULL;
  }
  if (sink->pw_core.port_r != NULL) {
    pw_filter_remove_port(sink->pw_core.port_r);
    sink->pw_core.port_r = NULL;
  }

  // Roundtrip: wait for server to confirm all destroys
  pw_sync_roundtrip(global_manager.pw_manager.threaded_loop,
                    global_manager.pw_manager.core);
}

// Internal: create PipeWire ports + links for a sink inside an already-held
// lock, then sync roundtrip to ensure ports are registered before linking.
static void sink_setup_pw_locked(struct SinkCore *sink) {
  // Use the slot name for port names so they are stable across reassignments
  char port_name_l[256];
  char port_name_r[256];
  snprintf(port_name_l, sizeof(port_name_l), "%s_L", sink->name);
  snprintf(port_name_r, sizeof(port_name_r), "%s_R", sink->name);

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
    fprintf(stderr, "[AudioMeeter] FATAL: failed to add ports for sink %s\n",
            sink->name);
    abort();
  }

  // Roundtrip: wait for server to register the ports before linking
  pw_sync_roundtrip(global_manager.pw_manager.threaded_loop,
                    global_manager.pw_manager.core);

  // Create links
  // Virtual source sinks (audiomeeter-out-b*) use input_FL/input_FR port names,
  // regular hardware sinks use playback_FL/playback_FR.
  const char *dst_port_l = "playback_FL";
  const char *dst_port_r = "playback_FR";

  if (strstr(sink->device_id, "audiomeeter-out-b") != NULL) {
    dst_port_l = "input_FL";
    dst_port_r = "input_FR";
  }

  sink->pw_core.link_l =
      create_pw_link(global_manager.pw_manager.core, ENGINE_NODE_NAME,
                     port_name_l, sink->device_id, dst_port_l);
  sink->pw_core.link_r =
      create_pw_link(global_manager.pw_manager.core, ENGINE_NODE_NAME,
                     port_name_r, sink->device_id, dst_port_r);
}

struct SinkCore *sink_create(const char *name, const char *device_id) {
  if (name == NULL || device_id == NULL)
    return NULL;

  if (global_manager.sinks_count >=
      (int)(sizeof(global_manager.sinks) / sizeof(global_manager.sinks[0]))) {
    fprintf(stderr, "[AudioMeeter] sink_create: max sink count reached\n");
    return NULL;
  }

  struct SinkCore *sink = calloc(1, sizeof(*sink));
  if (sink == NULL)
    abort();

  strncpy(sink->name, name, sizeof(sink->name) - 1);
  strncpy(sink->device_id, device_id, sizeof(sink->device_id) - 1);
  sink->dB = 0;
  sink->eq.gain = 1.0f; // Default gain is 1.0f (0 dB)

  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  global_manager.sinks[global_manager.sinks_count] = sink;
  global_manager.sinks_count++;

  // Set up PipeWire ports + links atomically
  sink_setup_pw_locked(sink);

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);
  return sink;
}

void sink_link(struct SinkCore *sink) {
  // Now a no-op: linking is done atomically inside
  // sink_create/sink_setup_pw_locked
  (void)sink;
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

int sink_set_gain_from_db(struct SinkCore *sink, float db) {
  if (sink == NULL)
    return -1;

  float gain = 0.0f;

  if (db <= -60.0f)
    gain = 0.0f;

  else
    gain = powf(10.0f, db / 20.0f);

  sink->eq.gain = gain;
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

  device->eq.gain = 1.0f;

  device->eq.bass =
      create_band(RT_FILTER_LOW_SHELF, BASS_FREQ, 0.0f, 0.0f, 0.0f, 48000.0f);

  device->eq.mid = create_band(RT_FILTER_PEAK, MID_FREQ, 0.0f,
                               0.75f, // Q
                               0.0f, 48000.0f);

  device->eq.treble = create_band(RT_FILTER_HIGH_SHELF, TREBLE_FREQ, 0.0f, 0.0f,
                                  0.0f, 48000.0f);
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

int device_set_gain_from_db(struct DeviceCore *device, float db) {
  if (device == NULL)
    return -1;

  float gain = 0.0f;

  if (db <= -60.0f)
    gain = 0.0f;

  else
    gain = powf(10.0f, db / 20.0f);

  device->eq.gain = gain;
  return 0;
}

int device_set_bass_gain(struct DeviceCore *device, float db) {
  if (device == NULL)
    return -1;

  struct rt_band *band = device->eq.bass;
  if (band == NULL)
    return -1;

  int r = update_band(band, RT_FILTER_LOW_SHELF, BASS_FREQ, 0.0f, 0.0f, db,
                      48000.0f);

  return r;
}

int device_set_mid_gain(struct DeviceCore *device, float db) {
  if (device == NULL)
    return -1;

  struct rt_band *band = device->eq.mid;
  if (band == NULL)
    return -1;

  return update_band(band, RT_FILTER_PEAK, MID_FREQ, 0.0f, 0.75f, db, 48000.0f);
}

int device_set_treble_gain(struct DeviceCore *device, float db) {
  if (device == NULL)
    return -1;

  struct rt_band *band = device->eq.treble;
  if (band == NULL)
    return -1;

  return update_band(band, RT_FILTER_HIGH_SHELF, TREBLE_FREQ, 0.0f, 0.0f, db,
                     48000.0f);
}

int device_set_mono(struct DeviceCore *device, bool is_mono) {
  if (device == NULL)
    return -1;

  device->eq.mono = is_mono;
  return 0;
}

int device_set_bridged_sink(struct DeviceCore *device, struct SinkCore *sink) {
  if (device == NULL || sink == NULL)
    return -1;

  // Check if sink is already bridged to prevent duplicate routes (which
  // multiplies the volume)
  for (int i = 0; i < device->bridged_sinks_count; i++) {
    if (device->bridged_sinks[i] == sink) {
      return 0; // Already bridged, do nothing
    }
  }

  if (device->bridged_sinks_count >= MAX_ROUTES_PER_DEVICE)
    return -2;

  device->bridged_sinks[device->bridged_sinks_count] = sink;
  device->bridged_sinks_count++;
  return 0;
}

int device_remove_bridged_sink(struct DeviceCore *device,
                               struct SinkCore *sink) {
  if (device == NULL || sink == NULL)
    return -1;

  int removed = 0;
  for (int i = 0; i < device->bridged_sinks_count;) {
    if (device->bridged_sinks[i] == sink) {
      for (int j = i; j < device->bridged_sinks_count - 1; j++) {
        device->bridged_sinks[j] = device->bridged_sinks[j + 1];
      }
      device->bridged_sinks[device->bridged_sinks_count - 1] = NULL;
      device->bridged_sinks_count--;
      removed++;
    } else {
      i++;
    }
  }

  return removed > 0 ? 0 : -1;
}

int sink_delete(struct SinkCore *sink) {
  if (sink == NULL)
    return -1;

  // 1. Tear down PipeWire resources atomically
  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);
  sink_teardown_pw_locked(sink);
  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);

  // 2. Remove sink reference from all device bridged_sinks lists
  for (int d = 0; d < global_manager.devices_count; d++) {
    struct DeviceCore *dev = global_manager.devices[d];
    if (dev != NULL) {
      device_remove_bridged_sink(dev, sink);
    }
  }

  // 3. Remove sink from global sinks array
  int found_idx = -1;
  for (int i = 0; i < global_manager.sinks_count; i++) {
    if (global_manager.sinks[i] == sink) {
      found_idx = i;
      break;
    }
  }

  if (found_idx != -1) {
    for (int i = found_idx; i < global_manager.sinks_count - 1; i++) {
      global_manager.sinks[i] = global_manager.sinks[i + 1];
    }
    global_manager.sinks[global_manager.sinks_count - 1] = NULL;
    global_manager.sinks_count--;
  }

  // 4. Free memory
  free(sink);
  return 0;
}

int device_delete(struct DeviceCore *device) {
  if (device == NULL)
    return -1;

  // 1. Lock threaded loop
  pw_thread_loop_lock(global_manager.pw_manager.threaded_loop);

  // 2. Destroy links
  if (device->pw_core.link_l != NULL) {
    pw_proxy_destroy((struct pw_proxy *)device->pw_core.link_l);
    device->pw_core.link_l = NULL;
  }
  if (device->pw_core.link_r != NULL) {
    pw_proxy_destroy((struct pw_proxy *)device->pw_core.link_r);
    device->pw_core.link_r = NULL;
  }

  // 3. Remove ports from filter
  if (device->pw_core.port_l != NULL) {
    pw_filter_remove_port(device->pw_core.port_l);
    device->pw_core.port_l = NULL;
  }
  if (device->pw_core.port_r != NULL) {
    pw_filter_remove_port(device->pw_core.port_r);
    device->pw_core.port_r = NULL;
  }

  // Wait for the server to confirm ALL destroys (links + ports) before
  // returning to avoid port ID reuse causing EEXIST on the next link creation.
  pw_sync_roundtrip(global_manager.pw_manager.threaded_loop,
                    global_manager.pw_manager.core);

  pw_thread_loop_unlock(global_manager.pw_manager.threaded_loop);

  // 4. Remove device from global devices array
  int found_idx = -1;
  for (int i = 0; i < global_manager.devices_count; i++) {
    if (global_manager.devices[i] == device) {
      found_idx = i;
      break;
    }
  }

  if (found_idx != -1) {
    for (int i = found_idx; i < global_manager.devices_count - 1; i++) {
      global_manager.devices[i] = global_manager.devices[i + 1];
    }
    global_manager.devices[global_manager.devices_count - 1] = NULL;
    global_manager.devices_count--;
  }

  // 5. Free band structures and device memory
  if (device->eq.bass)
    destroy_band(device->eq.bass);
  if (device->eq.mid)
    destroy_band(device->eq.mid);
  if (device->eq.treble)
    destroy_band(device->eq.treble);

  free(device);
  return 0;
}
// END DEVICE CLASS
