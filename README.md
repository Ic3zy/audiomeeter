# 🎛️ Voicemeeter Linux Alternative (Working Title)

A professional virtual audio mixer and router for Linux, built entirely in **Python**. This project leverages modern Linux audio systems (PipeWire/PulseAudio) to dynamically create virtual audio inputs/outputs and route application streams—completely in user-space, with zero kernel-mode drivers required.

---

## 🚀 Key Features

- **Pure Python Orchestration:** No complex low-level code. Python acts as the brain, commanding the native audio server.
- **User-Space Virtual Cables:** Dynamically creates virtual playback sinks and capture sources on the fly.
- **Smart Audio Routing:** Seamlessly route individual application audio (e.g., Discord, Spotify, Games) into dedicated mix buses.
- **Resource Efficient:** Designed to be lightweight, utilizing modern asynchronous Python and clean GUI bindings.

---

## 🏗️ Architectural Concept

To prevent audio latency or UI freezing, the project uses a decoupled design: