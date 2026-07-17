#include "constants.h"
#include "globals.h"
#include "pipewire/stream.h"
#include "types.h"
#include <pipewire/pipewire.h>
#include <stdio.h>

void route_audio() {}

struct pw_buffer *read_from_device(struct DeviceCore *core) {
  struct pw_buffer *b = pw_stream_dequeue_buffer(core->pw_core.stream);
  pw_stream_queue_buffer(core->pw_core.stream, b);
  return b;
}

void read_all_device() {
  for (int i = 0; i < MAX_DEVICES; i++) {
    struct DeviceCore *current_core = global_manager.devices[i];
    if (current_core == NULL)
      continue;

    struct pw_buffer *buffer = read_from_device(current_core);
    if (buffer != NULL) {
    }
    printf("read_all_device\n");
  };
}

void pipewire_process(void *userdata) {
  // TODO: implement
  printf("pipewire_process\n");
  read_all_device();
}