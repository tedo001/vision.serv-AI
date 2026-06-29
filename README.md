# AI Vision Platform

> An AI-powered computer vision platform that turns existing CCTV cameras into
> intelligent workplace assistants — improving **safety, security, compliance,
> productivity, and operational monitoring** across industries.

The product name is intentionally a configurable setting (`product_name` in
`config/default.yaml`) so the platform can be rebranded without code changes.

---

## Vision

Rather than asking operators to enable dozens of AI modules by hand, the user
selects an **industry profile** (Construction, Classroom, Office, Hospital,
Warehouse, Factory, Retail). Each profile automatically loads the right AI
models, detection rules, dashboard layout, alert policies, and reports.
Profiles are fully customizable.

---

## Architecture

The platform follows **Clean Architecture**. Source-code dependencies point
only *inward*, toward the core. UI code never mixes with AI code.

```
                ┌──────────────────────────────────────────┐
                │                  UI (Tkinter/ttk)          │  ← Phase 5
                └──────────────────────────────────────────┘
                                    │ depends on
                                    ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  Application services: Camera · Detection · Tracking · Events   │
   │  · Alerts · Profiles · Plugins · Database                       │
   └───────────────────────────────────────────────────────────────┘
                                    │ depends on
                                    ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  CORE  (no outward dependencies)                                │
   │  models · interfaces (ports) · DI container · logging · errors  │
   └───────────────────────────────────────────────────────────────┘
```

- **Core** (`app/core`): domain models, `Protocol` interfaces (ports), the DI
  container, the exception hierarchy, and logging. Depends on nothing else.
- **Outer layers** implement the core's interfaces and are wired together at a
  single **composition root** (`main.py`).
- **Plugins** (`app/plugins`): each AI feature is a self-contained module
  implementing `DetectorPlugin`; new features install without touching core.

### Swappable front-ends

The UI binds to a **framework-agnostic presentation state** (`app/ui/state.py`)
and a declarative navigation/profile model — no business logic lives inside
Tkinter widgets. Backend engines push updates into `AppState`; the UI
subscribes and re-renders. Replacing Tkinter with a web or Qt front-end means
rewriting only the widget layer (`app/ui/components`, `app/ui/views`,
`app/ui/app.py`) while `AppState`, navigation, the profile catalog, and all
backend services stay intact.

### The detection-to-alert pipeline (target design)

```
frame → detector plugins → detections → tracker → event engine
      → (confirm over time window) → Event → screenshot → SQLite
      → EventSinks (Alerts, UI, Reports) → operator
```

---

## Project structure

```
app/
  core/        # models, interfaces, DI container, logging, exceptions
  config/      # YAML loading + typed/validated settings
  camera/      # USB/RTSP/IP/file capture adapters         (Phase 7)
  detection/   # inference orchestration over plugins       (Phase 8)
  tracking/    # cross-frame object tracking                (Phase 9)
  events/      # confirmation pipeline + event bus          (Phase 10)
  alerts/      # alert policy + notification                (Phase 13)
  profiles/    # industry profile system                    (Phase 6)
  plugins/     # pluggable AI modules (helmet, fire, ...)
  database/    # SQLite repositories                        (Phase 11)
  ui/          # Tkinter/ttk presentation                   (Phase 5)
config/        # default.yaml
assets/  logs/  screenshots/  reports/  tests/  docs/
main.py        # composition root / entry point
```

---

## Industry profiles drive detection

Activating a profile (Industry Profiles tab) is now functional: it updates the
live state, **persists** as the default in `config/default.yaml`, and **focuses
detection** on the object classes relevant to that vertical. Each profile maps
to the COCO classes the stock YOLO model can already detect (e.g. Construction
→ person/truck/car/bus/motorcycle/bicycle; Office → person/laptop/cell
phone/keyboard/…). In Video Detection, "Focus on active profile" filters the
model output to those classes; untick it to see everything. PPE/fire/fall and
other safety-specific modules require custom-trained weights — a later phase.

## Video Detection (live)

The **Video Detection** tab runs the active model on a live source and draws
bounding boxes in real time:

- **Source:** laptop / USB camera (index `0` is the built-in cam) or a video
  file (`.mp4/.avi/.mov/.mkv/.webm`).
- **Device:** Auto / CPU / GPU. "Auto" picks CUDA when available, else CPU;
  GPU falls back to CPU automatically if no CUDA device is present. Detected
  GPU name shows in the top bar.
- **Resolution:** Default (uses `camera.width/height` from config) or a forced
  640×480 / 1280×720 / 1920×1080. The capture backend is chosen per platform
  (DirectShow on Windows, AVFoundation on macOS, V4L2 on Linux) so laptop
  cameras open quickly and reliably.
- Press **Start** to stream annotated frames; **Stop** to end.
- **Scan** finds working camera indices; **Preview only (test camera, no
  model)** streams the raw feed with no model — the quickest way to confirm
  your laptop camera works before any weights download.

### Test the camera from the terminal

No GUI needed — verify the lap cam and measure capture FPS:

```bash
python -m tools.camera_test --scan              # list working camera indices
python -m tools.camera_test --index 0 --frames 60   # capture + FPS test
python -m tools.camera_test --index 0 --snapshot    # save a frame to screenshots/
```

Under the hood: an OpenCV `CameraSource` and a `YoloDetector` are handed to a
background `DetectionRunner` (capture → detect → annotate); the UI polls the
runner's latest frame on the Tk event loop. Capture/inference never touch the
GUI thread. This is the Phase 7–8 vertical slice; multi-camera management and
the event pipeline build on these same pieces.

## Detection models

Choose the YOLO backbone from **Settings → AI Detection Model**: `YOLO11 Nano`
(fast/edge), `YOLO26 Nano` (newest, NMS-free), or `YOLO26 X-Large` (highest
accuracy, GPU recommended). Toggle **Enable for detection** and tune the
confidence / IoU thresholds; **Apply & Save** updates the live state and
persists to `config/default.yaml`. Weights auto-download from Ultralytics on
first use. The selection is consumed by `YoloDetector` (which implements the
core `DetectorPlugin` port); the live camera→detector pipeline is wired in
Phases 7–8. Add a model by appending one entry to
`app/detection/model_catalog.py`.

## Configuration

All runtime configuration lives in `config/default.yaml`, loaded and
**validated** at startup into a typed `AppConfig` (`app/config/settings.py`).
Invalid values fail fast with a clear error rather than surfacing deep in the
detection loop. No other layer reads YAML directly.

---

## Requirements

- Python **3.12+**
- See `requirements.txt` (Tkinter/ttk ship with CPython — no third-party UI dep)

```bash
pip install -r requirements.txt
python main.py        # boots the foundation (UI arrives in Phase 5)
pytest                # run the test suite
```

---

## Development roadmap

Built incrementally; each phase is reviewed before the next begins.

| Phase | Scope | Status |
|------:|-------|--------|
| 1 | Project architecture | ✅ |
| 2 | Folder structure | ✅ |
| 3 | Configuration manager | ✅ |
| 4 | Logging | ✅ |
| 5 | Tkinter framework | ✅ |
| 6 | Industry profile system | ◐ engine + detection focus (rules/dashboards pending) |
| 7 | Camera manager | ◐ capture works (multi-cam mgmt pending) |
| 8 | Detection engine | ◐ runner + YOLO + event generation (multi-cam pending) |
| 9 | Tracking | ◐ per-label debounce (full tracking pending) |
| 10 | Event engine | ✅ debounced events + sinks + screenshots |
| 11 | Database | ◐ SQLite events store (other tables pending) |
| 12 | Reports | ◐ generate + list (DB aggregation pending) |
| 13 | Alert system | ◐ alerts from high-severity events (policies/sound pending) |
| 14 | Optimization | ☐ |

---

## Coding standards

Python 3.12 · PEP 8 · full type hints · dataclasses · structured logging ·
threading + queues for concurrency · dependency injection at the composition
root · no global state · explicit exception handling · unit-test-friendly design.
