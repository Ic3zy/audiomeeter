# 🎛️ AudioMeeter

A professional, low-latency virtual audio mixer and routing engine for Linux (PipeWire / PulseAudio). 

AudioMeeter pairs a high-performance native DSP routing engine written in **Pure C** (compiled with SSE4.2 SIMD optimizations) with a flexible asynchronous **Python (PyQt6)** orchestration layer. By leveraging modern Linux audio systems, it dynamically routes user-space application streams with near-zero latency and zero kernel-mode drivers.

---

> 📖 **Official Website & Visual User Guide:**  
> For an interactive audio matrix simulator, step-by-step screenshot walkthroughs, and detailed documentation, check out the **[AudioMeeter Wiki & Portal](https://ic3zy.github.io/audiomeeter-wiki/)**.

---

## ⚡ Installation & Quick Start

You can find the latest pre-compiled packages and single-command installers on the **[GitHub Releases Page](https://github.com/Ic3zy/audiomeeter/releases/latest)** or directly on our **[AudioMeeter Web Portal](https://ic3zy.github.io/audiomeeter-wiki/)** (which automatically fetches the newest release command).

To run AudioMeeter directly from source:

```bash
git clone https://github.com/Ic3zy/audiomeeter.git
cd audiomeeter
pip install -r req.txt
python src/main.py
```

---

## 🚀 Key Features

- **High-Performance C Core:** A lightweight, pure C engine (`libengine.so`) compiled directly for maximum execution speed with SSE4.2 SIMD instructions for hot-path audio routing.
- **Parametric Equalizer:** Real-time 3-band RT-Biquad DSP filter (Bass, Mid, Treble) for precise audio manipulation.
- **Logarithmic Gain Control:** Smooth fader adjustments from `-60 dB` (mute) up to `+12 dB` (~3.98x amplitude boost).
- **Flexible Routing Matrix:** Direct audio streams to 3 Hardware Inputs (Microphones), 2 Virtual Inputs (`AudioMeeter_Input` & `AudioMeeter_AUX`), 3 Hardware Outputs (A1, A2, A3), and 2 Virtual Microphones (B1 & B2 for Discord/OBS/voice chat).
- **Python & PyQt6 GUI:** Asynchronous, non-blocking control brain for managing application states and user interfaces, with Cython compatibility caching.
- **Wayland OSD Overlay Support:** Integrated hardware-accelerated Volume OSD rendered via `zwlr_layer_shell_v1` ([wayland-volume-osd](https://github.com/Ic3zy/wayland-volume-osd)).

---

## 📖 User Guide & Documentation

For detailed instructions on routing Discord audio, Spotify, gaming streams, and microphone setups, please refer to the **[AudioMeeter Interactive Wiki](https://ic3zy.github.io/audiomeeter-wiki/)**.

---

## 🏗️ Architecture

```
[ Hardware Mics ] ──┐
[ Desktop Audio ] ──┼──► [ AudioMeeter C Core (SSE4.2 DSP) ] ──┬──► [ A1 / A2 / A3 Speakers ]
[ Media/Discord ] ──┘     └─ RT-Biquad Filters (Eq)          └──► [ B1 / B2  Virtual Mics ]
                                       ▲
                            [ Python / PyQt6 GUI ]
```

---

## 📜 License & Dependencies

- **License:** MIT License (100% Open Source)
- **CI/CD:** Transparent automated builds via GitHub Actions.
- **Sub-dependencies:**
  - [Wayland Custom OSD](https://github.com/Ic3zy/wayland-volume-osd)
  - [RT-Biquad Filter](https://github.com/Ic3zy/rt-biquad-filter)