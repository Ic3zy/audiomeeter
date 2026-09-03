#include <math.h>
#include <pipewire/filter.h>
#include <pipewire/pipewire.h>
#include <string.h>

#include "globals.h"
#include "types.h"

#define max_steps 10
#define step 10

// Helper function to convert peak amplitude to dB
static inline int amplitude_to_db(float max_val) {
  if (max_val < 0.00001f) {
    return -100; // Silence floor
  }
  float db = 20.0f * log10f(max_val);
  return (int)roundf(db);
}

static inline void device_apply_filter(struct DeviceCore *device, float *in_l,
                                       float *in_r, uint32_t n_samples) {
  if (in_l == NULL && in_r == NULL)
    return;

  if (device->eq.gain == 0.0f) {
    if (in_l)
      memset(in_l, 0, n_samples * sizeof(float));
    if (in_r)
      memset(in_r, 0, n_samples * sizeof(float));
    return;
  }

  for (uint32_t i = 0; i < n_samples; i++) {
    if (in_l)
      in_l[i] = in_l[i] * device->eq.gain;
    if (in_r)
      in_r[i] = in_r[i] * device->eq.gain;

    if (device->eq.bass == NULL || device->eq.mid == NULL ||
        device->eq.treble == NULL)
      continue;

    if (device->eq.bass->db_gain != 0.0f) {
      if (in_l)
        in_l[i] = process_sample(device->eq.bass->state_left, in_l[i]);
      if (in_r)
        in_r[i] = process_sample(device->eq.bass->state_right, in_r[i]);
    }
    if (device->eq.mid->db_gain != 0.0f) {
      if (in_l)
        in_l[i] = process_sample(device->eq.mid->state_left, in_l[i]);
      if (in_r)
        in_r[i] = process_sample(device->eq.mid->state_right, in_r[i]);
    }
    if (device->eq.treble->db_gain != 0.0f) {
      if (in_l)
        in_l[i] = process_sample(device->eq.treble->state_left, in_l[i]);
      if (in_r)
        in_r[i] = process_sample(device->eq.treble->state_right, in_r[i]);
    }
    if (device->eq.mono && in_l && in_r) {
      float top = (in_l[i] + in_r[i]) * 0.5f;
      in_r[i] = top;
      in_l[i] = top;
    }
  }
}

static inline void sink_apply_filter(struct SinkCore *sink, float *in_l,
                                     float *in_r, uint32_t n_samples) {
  if (in_l == NULL && in_r == NULL)
    return;

  if (sink->eq.gain != 1.0f) {
    for (uint32_t i = 0; i < n_samples; i++) {
      if (in_l)
        in_l[i] = in_l[i] * sink->eq.gain;
      if (in_r)
        in_r[i] = in_r[i] * sink->eq.gain;
    }
  }
}

void pipewire_process(void *data, struct spa_io_position *position) {
  (void)data; // Unused parameter warning suppression

  if (position == NULL)
    return;

  uint32_t n_samples = position->clock.duration;
  if (n_samples == 0)
    return;

  // Temporary arrays to store retrieved buffer pointers for this cycle
  float *device_bufs_l[MAX_DEVICES] = {NULL};
  float *device_bufs_r[MAX_DEVICES] = {NULL};
  float *sink_bufs_l[MAX_DEVICES] = {NULL};
  float *sink_bufs_r[MAX_DEVICES] = {NULL};

  // Retrieve and clear all output sink buffers (exactly once!)
  for (int s = 0; s < global_manager.sinks_count; s++) {
    struct SinkCore *sink = global_manager.sinks[s];
    if (sink == NULL || sink->pw_core.port_l == NULL ||
        sink->pw_core.port_r == NULL)
      continue;

    float *out_l = pw_filter_get_dsp_buffer(sink->pw_core.port_l, n_samples);
    float *out_r = pw_filter_get_dsp_buffer(sink->pw_core.port_r, n_samples);

    sink_bufs_l[s] = out_l;
    sink_bufs_r[s] = out_r;

    if (out_l != NULL) {
      memset(out_l, 0, n_samples * sizeof(float));
    }
    if (out_r != NULL) {
      memset(out_r, 0, n_samples * sizeof(float));
    }
  }

  // Retrieve all input device buffers (exactly once!)
  for (int d = 0; d < global_manager.devices_count; d++) {
    struct DeviceCore *device = global_manager.devices[d];
    if (device == NULL || device->pw_core.port_l == NULL ||
        device->pw_core.port_r == NULL)
      continue;

    device_bufs_l[d] =
        pw_filter_get_dsp_buffer(device->pw_core.port_l, n_samples);
    device_bufs_r[d] =
        pw_filter_get_dsp_buffer(device->pw_core.port_r, n_samples);

    device_apply_filter(device, device_bufs_l[d], device_bufs_r[d], n_samples);
  }

  // Mix inputs to target bridged sinks using stored pointers (with 1.0 gain)
  for (int d = 0; d < global_manager.devices_count; d++) {
    struct DeviceCore *device = global_manager.devices[d];
    if (device == NULL)
      continue;

    float *in_l = device_bufs_l[d];
    float *in_r = device_bufs_r[d];

    // If both ports return NULL, skip processing this device
    if (in_l == NULL && in_r == NULL)
      continue;

    // Accumulate/mix into each bridged sink
    for (int bs = 0; bs < device->bridged_sinks_count; bs++) {
      struct SinkCore *sink = device->bridged_sinks[bs];
      if (sink == NULL)
        continue;

      // Find the index of this sink in global_manager.sinks to get its stored
      // buffer pointer
      int sink_idx = -1;
      for (int s = 0; s < global_manager.sinks_count; s++) {
        if (global_manager.sinks[s] == sink) {
          sink_idx = s;
          break;
        }
      }

      if (sink_idx == -1)
        continue;

      float *out_l = sink_bufs_l[sink_idx];
      float *out_r = sink_bufs_r[sink_idx];

      if (out_l == NULL && out_r == NULL)
        continue;

      // Perform the mix operation sample by sample (direct mix without gain
      // filters)
      if (out_l != NULL) {
        for (uint32_t i = 0; i < n_samples; i++) {
          float sample_l = in_l ? in_l[i] : 0.0f;
          out_l[i] += sample_l;
        }
      }

      if (out_r != NULL) {
        for (uint32_t i = 0; i < n_samples; i++) {
          float sample_r = in_r ? in_r[i] : (in_l ? in_l[i] : 0.0f);
          out_r[i] += sample_r;
        }
      }
    }
  }

  // Measure peak amplitude for level meters and store as dB in SinkCore and
  // DeviceCore
  for (int d = 0; d < global_manager.devices_count; d++) {
    struct DeviceCore *device = global_manager.devices[d];
    if (device == NULL)
      continue;

    float *in_l = device_bufs_l[d];
    float *in_r = device_bufs_r[d];
    float max_val = 0.0f;

    if (in_l) {
      for (uint32_t i = 0; i < n_samples; i++) {
        float val = fabsf(in_l[i]);
        if (val > max_val)
          max_val = val;
      }
    }

    if (in_r) {
      for (uint32_t i = 0; i < n_samples; i++) {
        float val = fabsf(in_r[i]);
        if (val > max_val)
          max_val = val;
      }
    }
    device->dB = amplitude_to_db(max_val);
  }

  for (int s = 0; s < global_manager.sinks_count; s++) {
    struct SinkCore *sink = global_manager.sinks[s];
    if (sink == NULL)
      continue;

    float *out_l = sink_bufs_l[s];
    float *out_r = sink_bufs_r[s];
    float max_val = 0.0f;

    sink_apply_filter(sink, out_l, out_r, n_samples);

    if (out_l) {
      for (uint32_t i = 0; i < n_samples; i++) {
        float val = fabsf(out_l[i]);
        if (val > max_val)
          max_val = val;
      }
    }
    if (out_r) {
      for (uint32_t i = 0; i < n_samples; i++) {
        float val = fabsf(out_r[i]);
        if (val > max_val)
          max_val = val;
      }
    }
    sink->dB = amplitude_to_db(max_val);
  }
}