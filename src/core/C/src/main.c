#include "globals.h"
#include "stdlib.h"
#include "types.h"
#include <pipewire/pipewire.h>

int init_audio_core() {
  pw_init(NULL, NULL);

  global_manager.pw_manager.threaded_loop =
      pw_thread_loop_new("AudioMeeter_thread", NULL);

  if (global_manager.pw_manager.threaded_loop == NULL)
    abort();

  global_manager.pw_manager.loop =
      pw_thread_loop_get_loop(global_manager.pw_manager.threaded_loop);

  if (global_manager.pw_manager.loop == NULL)
    abort();

  global_manager.pw_manager.global_pw_context =
      pw_context_new(global_manager.pw_manager.loop, NULL, 0);

  if (global_manager.pw_manager.global_pw_context == NULL)
    abort();

  global_manager.pw_manager.core =
      pw_context_connect(global_manager.pw_manager.global_pw_context, NULL, 0);

  if (global_manager.pw_manager.core == NULL)
    abort();

  if (pw_thread_loop_start(global_manager.pw_manager.threaded_loop) < 0)
    abort();

  global_manager.pw_manager.pw_inited = 1;

  return 0;
}