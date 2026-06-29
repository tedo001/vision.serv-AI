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
| 6 | Industry profile system | ☐ |
| 7 | Camera manager | ☐ |
| 8 | Detection engine | ☐ |
| 9 | Tracking | ☐ |
| 10 | Event engine | ☐ |
| 11 | Database | ☐ |
| 12 | Reports | ☐ |
| 13 | Alert system | ☐ |
| 14 | Optimization | ☐ |

---

## Coding standards

Python 3.12 · PEP 8 · full type hints · dataclasses · structured logging ·
threading + queues for concurrency · dependency injection at the composition
root · no global state · explicit exception handling · unit-test-friendly design.
