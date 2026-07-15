# 🎛️ Voicemeeter Linux Alternative (Working Title)

A professional, low-latency virtual audio mixer and router for Linux. This project pairs a high-performance, native routing engine written in **Pure C** with a flexible, asynchronous **Python** orchestration layer. By leveraging modern Linux audio systems (PipeWire/PulseAudio), it dynamically routes user-space application streams with near-zero latency and zero kernel-mode drivers.

---

## 🚀 Key Features

- **High-Performance C Core:** A lightweight, pure C engine compiled directly for maximum execution speed, handling hot-path audio routing and native audio server interactions with deterministic efficiency.
- **Python-Driven Orchestration:** Pure Python acts as the high-level control brain—managing app states, configuration, and the GUI—and communicates seamlessly with the C core via native bindings.
- **User-Space Virtual Cables:** Dynamically creates virtual playback sinks and capture sources on the fly.
- **Smart Audio Routing:** Seamlessly route individual application audio (e.g., Discord, Spotify, Games) into dedicated mix buses.
- **Ultra-Low Resource Footprint:** Designed with extreme efficiency in mind, combining raw C execution speed with non-blocking, asynchronous Python event loops.

---

## 🏗️ Architectural Concept

To prevent audio latency or UI freezing, the project uses a decoupled design: