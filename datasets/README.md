# Training datasets

To make the platform detect *your* incidents (helmet violations, falls, fire,
forklift proximity, …) you fine-tune a YOLO model on **labeled images**. This
folder holds those datasets. Datasets are **not committed** (see `.gitignore`)
— they're large and project-specific.

## YOLO dataset format

```
datasets/
  safety/
    data.yaml            # describes classes + paths (template provided)
    images/
      train/  *.jpg
      val/    *.jpg
    labels/
      train/  *.txt       # one .txt per image, same basename
      val/    *.txt
```

Each label `.txt` has one line per object:

```
<class_id> <x_center> <y_center> <width> <height>
```

All values are **normalized 0–1** (relative to image width/height). `class_id`
is the index into the `names` list in `data.yaml`.

## How to get labeled data

1. **Collect images/frames** of the scenes you care about (CCTV stills, video
   frames). Aim for hundreds-to-thousands per class, in realistic conditions.
2. **Annotate** with a tool that exports YOLO format — e.g. [Label Studio],
   [Roboflow], or [CVAT]. Roboflow can also export a ready `data.yaml`.
3. Or **start from a public dataset** (Roboflow Universe has construction-PPE,
   helmet, fire/smoke, and fall datasets) to validate the pipeline before
   collecting your own.

[Label Studio]: https://labelstud.io/
[Roboflow]: https://roboflow.com/
[CVAT]: https://www.cvat.ai/

## Train

```bash
# Prove the pipeline end-to-end on a tiny bundled dataset (downloads itself):
python -m tools.train --data coco8.yaml --base yolo11n.pt --epochs 2

# Train your model:
python -m tools.train --data datasets/safety/data.yaml \
    --base yolo11n.pt --epochs 100 --imgsz 640 --name safety_v1
```

The best weights are copied to `assets/models/<name>.pt`. Launch the app and
pick **Custom — <name>** in Settings → AI Detection Model.

> Choosing a base: `yolo11n.pt` (fast) → `yolo11x.pt` (accurate) for object
> classes; `yolo11n-pose.pt` for keypoint/action models.
