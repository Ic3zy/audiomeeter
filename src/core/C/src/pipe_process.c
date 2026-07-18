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

    struct pw_buffer *buffer =
        pw_stream_dequeue_buffer(current_core->pw_core.stream);
    if (buffer != NULL) {
      struct spa_data *data = &buffer->buffer->datas[0];

      float *samples = (float *)((uint8_t *)data->data + data->chunk->offset);

      uint32_t sample_count = data->chunk->size / sizeof(float);

      FILE *fl = fopen("incoming_audio.raw", "ab");

      if (fl != NULL) {
        fwrite(samples, sizeof(float), sample_count, fl);
        fclose(fl);
      }
    }
    pw_stream_queue_buffer(current_core->pw_core.stream, buffer);

    printf("read_all_device\n");
  };
}

void pipewire_process(void *userdata) {
  // TODO: implement
  printf("pipewire_process\n");
  read_all_device();
}