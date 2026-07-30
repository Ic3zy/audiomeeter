#pragma once
#include "types.h"

/* --- SINK --- */

// allocs a new sink core, aborst if no memory left
struct SinkCore *sink_create(const char *device_id);

// returns -1 on error or if sink pointer is null
int sink_get_dB(struct SinkCore *sink);

int sink_set_dB(struct SinkCore *sink, int dB);

/* --- DEVICES --- */

// creates device core, will abort if calloc fails
struct DeviceCore *device_create(const char *device_id);

void device_init(struct DeviceCore *device);

int device_get_dB(struct DeviceCore *device);

int device_set_dB(struct DeviceCore *device, int dB);

// bridges a sink to device. returns -1 on null args, -2 if reached max routes
// limit
int device_set_bridged_sink(struct DeviceCore *device, struct SinkCore *sink);

void sink_link(struct SinkCore *sink);
void device_link(struct DeviceCore *device);