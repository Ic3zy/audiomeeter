#include "globals.h"
#include "stdlib.h"
#include "types.h"
#include <pipewire/pipewire.h>

// INIT
int init_audio_core() {
  pw_init(NULL, NULL);

  struct pw_thread_loop *threaded_loop =
      pw_thread_loop_new("AudioMeeter_thread", NULL);

  if (threaded_loop == NULL)
    abort();

  struct pw_loop *loop = pw_thread_loop_get_loop(threaded_loop);

  if (pw_thread_loop_start(threaded_loop) < 0)
    abort();

  if (loop == NULL)
    abort();

  global_manager.pw_manager.threaded_loop = threaded_loop;
  global_manager.pw_manager.loop = loop;

  return 0;
}
