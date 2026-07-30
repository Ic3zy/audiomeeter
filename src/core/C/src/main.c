#include "globals.h"
#include "pipe_process.h"
#include "types.h"
#include <pipewire/pipewire.h>
#include <spa/param/audio/format-utils.h>
#include <spa/pod/builder.h>
#include <stdio.h>
#include <stdlib.h>

static struct spa_hook filter_listener;

static void filter_state_changed(void *data, enum pw_filter_state old,
                                 enum pw_filter_state state,
                                 const char *error) {
  (void)data;
  printf("[AudioMeeter] PipeWire Filter State: %s -> %s %s\n",
         pw_filter_state_as_string(old), pw_filter_state_as_string(state),
         error ? error : "");
  fflush(stdout);
}

static const struct pw_filter_events filter_events = {
    .version = PW_VERSION_FILTER_EVENTS,
    .process = pipewire_process,
    .state_changed = filter_state_changed,
};

static uint8_t param_buffer[1024];

void init_default_port_params(void) {
  struct spa_pod_builder b =
      SPA_POD_BUILDER_INIT(param_buffer, sizeof(param_buffer));

  struct spa_audio_info_raw info =
      SPA_AUDIO_INFO_RAW_INIT(.format =
                                  SPA_AUDIO_FORMAT_F32P, // 32-bit Float Planar
                              .channels = 2,             // Stereo
                              .rate = 48000              // 48 kHz
      );
  info.position[0] = SPA_AUDIO_CHANNEL_FL;
  info.position[1] = SPA_AUDIO_CHANNEL_FR;

  global_manager.default_port_params[0] =
      spa_format_audio_raw_build(&b, SPA_PARAM_EnumFormat, &info);
}

void init_pipewire_engine(void) {
  struct pw_properties *props = pw_properties_new(
      PW_KEY_MEDIA_TYPE, "Audio", PW_KEY_MEDIA_CATEGORY, "Filter",
      PW_KEY_NODE_NAME, "AudioMeeterEngine", PW_KEY_NODE_DESCRIPTION,
      "AudioMeeter Virtual Mixer Engine", "node.autoconnect", "false",
      "node.always-process", "true", NULL);

  if (props == NULL)
    abort();

  global_manager.filter =
      pw_filter_new(global_manager.pw_manager.core, "AudioMeeterEngine", props);

  if (global_manager.filter == NULL) {
    abort();
  }

  pw_filter_add_listener(global_manager.filter, &filter_listener,
                         &filter_events, &global_manager);

  int res = pw_filter_connect(global_manager.filter, PW_FILTER_FLAG_RT_PROCESS,
                              NULL, 0);

  if (res < 0) {
    abort();
  }
}

int init_audio_core() {
  pw_init(NULL, NULL);

  init_default_port_params();

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

  init_pipewire_engine();

  if (pw_thread_loop_start(global_manager.pw_manager.threaded_loop) < 0)
    abort();

  global_manager.pw_manager.pw_inited = 1;

  return 0;
}