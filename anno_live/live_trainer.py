"""Long-running YOLO loop for an annotool live folder.

Reads ``<sync>/annotool_live.json`` (the normal annotool export, one box per
logo, plus ``syncedAt``, ``currentImage``, ``currentImageIndex``, and
``reviewed``). Reviewed frames become the training set. A reviewed frame with
no usable box is a negative. A frame that is in neither ``reviewed`` nor
``images`` has not been seen and is never used as a negative.

Writes only two files into the sync folder:

* ``annotool_predictions.json`` — the annotool document shape used by
  ``anno2026/scripts/predict_to_json.py`` (one row per instance, no
  brand|tpoint merge), with canvas coordinates and ``confidence``
* ``live_trainer_status.json`` — progress for the annotool UI

Datasets and weight files go to ``--work-dir/<project>/``, outside the repository.
Projects in one model family share ``<work-dir>/models/<family>/``: one
``best.pt``, and a ``dataset.json`` of every project's reviewed labels. Class
ids are append-only for that family. Before any prediction, a stale family
model is trained on that union so the checkpoint contains every family class.
Predictions run a few images at a time (``--predict-batch``). Base weights
must already be on disk; this process does not download them.

``--frames-folder`` is optional. Without it, the ``project`` field in the live
file (the folder name annotool writes) is looked up under each ``--frames-root``
(default ``D:\\downloads``). A changed ``project`` switches folder and model
without a restart. The usual path is
``<root>/batchNN/<match>/reduced_<match>/<project>``. Otherwise the search
stops at the first directory with that exact name that directly contains a
jpg, down to ``--frames-max-depth`` (default 6), and does not walk into frame
dumps. The result is cached in the work dir. A new project switches folder and model.

``anno2026/scripts/{convert_to_yolo,predict_to_json,train}.py`` and
``anno_video/NEW_PROJECT_RUNBOOK.md`` are not in this checkout. The geometry,
class names (``brand|tpoint``), confidence 0.25, IoU 0.3, class-agnostic NMS,
a post-NMS containment pass (``--contain`` 0.6), and AMP-off default follow
that toolchain and ``LogoDetection/annoToYOLO.py``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import signal
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

os.environ["YOLO_OFFLINE"] = "True"

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:  # pragma: no cover - pillow comes with ultralytics
    Image = None
    UnidentifiedImageError = OSError


LOG = logging.getLogger("anno_live")

LIVE_NAME = "annotool_live.json"
PRED_NAME = "annotool_predictions.json"
STATUS_NAME = "live_trainer_status.json"
STATE_NAME = "state.json"

PREDICTION_KEYS = (
    "project",
    "imageNum",
    "prefs",
    "images",
    "currentImage",
    "presets",
    "Annotator",
)
PREFS_KEYS = (
    "projectName",
    "AnnotatorName",
    "prefsFilename",
    "imgFoldername",
    "userAdds",
    "groups",
    "brands",
    "tpoints",
    "conns",
    "seelater",
)
IMAGE_KEYS = ("imageName", "imageIndex", "width", "height", "annotations", "exifdata")
ANNOTATION_KEYS = (
    "startPoint",
    "diagPoint",
    "group",
    "brand",
    "tpoint",
    "hits",
    "confidence",
)
STATUS_KEYS = (
    "schema",
    "state",
    "project",
    "frames_folder",
    "cycle",
    "reviewed",
    "reviewed_since_last_cycle",
    "next_cycle_at",
    "predicted_frames",
    "predicted_from",
    "predicted_to",
    "classes",
    "last_map50",
    "epoch",
    "epochs",
    "updated_at",
    "last_error",
    "current_image",
    "weights",
    "message",
    "started_at",
    "device",
    "from_base",
    "train_images",
    "val_images",
    "hard_negative_frames",
    "model_family",
    "model_mode",
    "per_class_map50",
    "predict_total",
    "ready_for_user",
    "cadence",
    "every_now",
    "cadence_reason",
)


class ConfigError(Exception):
    """Bad paths or arguments. The loop should not start."""


class DatasetError(Exception):
    """Reviewed frames are not ready to train (no match, or no boxes)."""


class PredictionDiscarded(Exception):
    """The live project changed while a prediction file was being built."""


@dataclass(frozen=True)
class Frame:
    path: Path
    rel: str
    stem: str


class Status:
    """Atomic ``live_trainer_status.json``. Every key in STATUS_KEYS is always present."""

    def __init__(self, path: Path, device: str, next_cycle_at: int):
        self.path = Path(path)
        now = iso_now()
        self.data = {
            "schema": 1,
            "state": "idle",
            "project": None,
            "frames_folder": None,
            "cycle": 0,
            "reviewed": 0,
            "reviewed_since_last_cycle": 0,
            "next_cycle_at": int(next_cycle_at),
            "predicted_frames": 0,
            "predicted_from": None,
            "predicted_to": None,
            "classes": [],
            "last_map50": None,
            "epoch": None,
            "epochs": None,
            "updated_at": now,
            "last_error": None,
            "current_image": None,
            "weights": None,
            "message": "Εκκίνηση",
            "started_at": now,
            "device": device or "auto",
            "from_base": None,
            "train_images": None,
            "val_images": None,
            "hard_negative_frames": 0,
            "model_family": None,
            "model_mode": None,
            "per_class_map50": {},
            "predict_total": None,
            "ready_for_user": False,
            "cadence": None,
            "every_now": None,
            "cadence_reason": None,
        }
        self.write()

    def update(self, **fields):
        unknown = set(fields) - set(STATUS_KEYS)
        if unknown:
            raise KeyError("unknown status fields: " + ", ".join(sorted(unknown)))
        if "classes" in fields:
            fields["classes"] = list(fields["classes"])
        self.data.update(fields)
        self.data["updated_at"] = iso_now()
        self.write()

    def write(self):
        payload = {key: self.data[key] for key in STATUS_KEYS}
        atomic_write_json(self.path, payload)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_logging():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def atomic_write_json(path: Path, payload: dict, retries: int = 8):
    """Write JSON next to ``path`` and replace it. The temp file does not stay behind."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    last = None
    try:
        for attempt in range(retries):
            try:
                with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except OSError:
                        pass
                os.replace(tmp, path)
                return
            except OSError as exc:
                last = exc
                time.sleep(0.05 * (attempt + 1))
        raise ConfigError(f"could not write {path}: {last}")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def read_json(path: Path, retries: int = 5, pause: float = 0.15) -> dict:
    last = None
    for attempt in range(retries):
        try:
            text = Path(path).read_text(encoding="utf-8")
            if not text.strip():
                raise ValueError("empty file")
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("JSON root is not an object")
            return data
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(pause)
    raise ValueError(f"{path}: {last}")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def natural_key(text: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def norm_name(value) -> str:
    if not isinstance(value, str):
        return ""
    name = value.replace("\\", "/").strip()
    lower = name.lower()
    for ext in (".jpg", ".jpeg"):
        if lower.endswith(ext):
            name = name[: -len(ext)]
            break
    return name


def name_hits_frame(name: str, frame: Frame) -> bool:
    if not name:
        return False
    if "/" in name:
        return name == frame.rel
    return name == frame.stem


def class_name(brand: str, tpoint: str) -> str:
    return f"{brand.strip()}|{tpoint.strip()}"


def split_class(name: str) -> tuple[str, str]:
    text = str(name)
    if "|" in text:
        brand, tpoint = text.split("|", 1)
        return brand, tpoint
    return text, ""


def as_point(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None


def positive_size(width, height):
    try:
        w = int(float(width))
        h = int(float(height))
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return w, h


def as_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def image_size(path: Path) -> tuple[int, int]:
    if Image is None:
        raise ConfigError("Pillow is required to read frame sizes")
    with Image.open(path) as im:
        width, height = im.size
    if width <= 0 or height <= 0:
        raise ValueError(f"bad image size: {path}")
    return int(width), int(height)


def list_frames(folder: Path) -> list[Frame]:
    frames = []
    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg"}:
            continue
        rel = path.relative_to(folder).with_suffix("").as_posix()
        frames.append(Frame(path=path.resolve(), rel=rel, stem=path.stem))
    frames.sort(key=lambda frame: natural_key(frame.rel))
    return frames


def reviewed_names(live: dict) -> list[str]:
    raw = live.get("reviewed") if isinstance(live, dict) else None
    if not isinstance(raw, list):
        return []
    names = []
    seen = set()
    for item in raw:
        name = norm_name(item)
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def current_name(live: dict):
    if not isinstance(live, dict):
        return None
    name = norm_name(live.get("currentImage"))
    return name or None


def parse_annotation(ann):
    if not isinstance(ann, dict):
        return None
    brand = str(ann.get("brand") or "").strip()
    tpoint = str(ann.get("tpoint") or "").strip()
    if not brand or not tpoint:
        return None
    start = as_point(ann.get("startPoint"))
    diag = as_point(ann.get("diagPoint"))
    if start is None or diag is None:
        return None
    return brand, tpoint, start, diag


def usable_annotations(entry) -> list:
    if not isinstance(entry, dict):
        return []
    anns = entry.get("annotations") or []
    if not isinstance(anns, list):
        return []
    return [parsed for parsed in (parse_annotation(ann) for ann in anns) if parsed]


def live_images(live: dict) -> dict:
    images = live.get("images") if isinstance(live, dict) else None
    return images if isinstance(images, dict) else {}


def live_entry_for(images: dict, frame: Frame):
    exact = None
    loose = []
    for key, entry in images.items():
        if not isinstance(entry, dict):
            continue
        labels = []
        if isinstance(key, str):
            labels.append(norm_name(key))
        image_name = entry.get("imageName")
        if isinstance(image_name, str):
            labels.append(norm_name(image_name))
        if frame.rel in labels:
            exact = entry
            break
        if any(name_hits_frame(label, frame) for label in labels):
            loose.append(entry)
    if exact is not None:
        return exact
    if len(loose) == 1:
        return loose[0]
    return None


def canvas_box_to_yolo(start, diag, canvas_w, canvas_h, img_w, img_h):
    """Map a canvas rectangle onto the image file and return a normalized YOLO box.

    ``start`` / ``diag`` are opposite corners in the annotool canvas
    (``width`` / ``height`` on the live image). Those pixels are scaled onto
    the file, then divided by the file size. Corners may arrive in any order.
    """
    if min(canvas_w, canvas_h, img_w, img_h) <= 0:
        return None
    left, right = sorted((float(start[0]), float(diag[0])))
    top, bottom = sorted((float(start[1]), float(diag[1])))
    sx = img_w / float(canvas_w)
    sy = img_h / float(canvas_h)
    left, right = left * sx, right * sx
    top, bottom = top * sy, bottom * sy
    left = min(max(left, 0.0), float(img_w))
    right = min(max(right, 0.0), float(img_w))
    top = min(max(top, 0.0), float(img_h))
    bottom = min(max(bottom, 0.0), float(img_h))
    width = right - left
    height = bottom - top
    if width < 1.0 or height < 1.0:
        return None
    return (
        ((left + right) / 2.0) / float(img_w),
        ((top + bottom) / 2.0) / float(img_h),
        width / float(img_w),
        height / float(img_h),
    )


def xyxy_to_canvas(x1, y1, x2, y2, img_w, img_h, canvas_w, canvas_h):
    """Map a file-pixel box back to integer canvas corners."""
    if min(img_w, img_h, canvas_w, canvas_h) <= 0:
        return None
    sx = float(canvas_w) / float(img_w)
    sy = float(canvas_h) / float(img_h)
    left, right = sorted((float(x1) * sx, float(x2) * sx))
    top, bottom = sorted((float(y1) * sy, float(y2) * sy))
    left = min(max(left, 0.0), float(canvas_w))
    right = min(max(right, 0.0), float(canvas_w))
    top = min(max(top, 0.0), float(canvas_h))
    bottom = min(max(bottom, 0.0), float(canvas_h))
    start = [int(round(left)), int(round(top))]
    diag = [int(round(right)), int(round(bottom))]
    if diag[0] - start[0] < 1 or diag[1] - start[1] < 1:
        return None
    return start, diag


def extend_classes(saved: list[str], found: set[str]) -> tuple[list[str], list[str]]:
    """Keep existing indices. Append new names in sorted order."""
    classes = list(saved)
    known = set(classes)
    new_names = [name for name in sorted(found) if name not in known]
    classes.extend(new_names)
    return classes, new_names


def wants_finetune(previous: Path | None, new_names: list[str]) -> bool:
    return bool(previous) and Path(previous).is_file() and not new_names


def model_class_names(model) -> list[str]:
    names = model.names
    if isinstance(names, dict):
        keys = sorted(names, key=lambda key: int(key))
        return [str(names[key]) for key in keys]
    return [str(name) for name in names]


def val_bucket(rel: str) -> float:
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def split_examples(examples: list, fraction: float):
    """Return (train_frames, val_frames). Both are non-empty when there is more than one frame."""
    frames = [frame for frame, _boxes in examples]
    if len(frames) == 1:
        return list(frames), list(frames)
    fraction = min(max(float(fraction), 0.0), 0.5)
    val = [frame for frame in frames if val_bucket(frame.rel) < fraction]
    train = [frame for frame in frames if frame not in set(val)]
    if not val:
        val.append(train.pop())
    if not train:
        train.append(val[0])
    positives = {frame for frame, boxes in examples if boxes}
    if positives and not any(frame in positives for frame in val):
        donor = next(frame for frame in train if frame in positives)
        if len(train) > 1:
            train.remove(donor)
            val.append(donor)
        elif donor not in val:
            val.append(donor)
    return train, val


def safe_stem(rel: str) -> str:
    cleaned = rel.replace("/", "__").replace("\\", "__")
    cleaned = re.sub(r'[<>:"|?*]+', "_", cleaned).strip(" .")
    return cleaned or "frame"


HARD_NEGATIVE_COPIES = 3


def dataset_filename(frame: Frame, copy: int = 0) -> str:
    stem = safe_stem(frame.rel)
    if copy > 0:
        stem = f"{stem}__hn{copy + 1}"
    return stem + frame.path.suffix.lower()


def place_image(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
        return "link"
    except OSError:
        shutil.copy2(src, dest)
        return "copy"


def yaml_string(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_data_yaml(path: Path, root: Path, classes: list[str]):
    lines = [
        f"path: {yaml_string(root.resolve().as_posix())}",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    for name in classes:
        lines.append(f"  - {yaml_string(name)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dominant_canvas(images: dict):
    counts = Counter()
    for entry in images.values():
        if not isinstance(entry, dict):
            continue
        size = positive_size(entry.get("width"), entry.get("height"))
        if size:
            counts[size] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def find_current_index(frames: list[Frame], name: str | None) -> int:
    if not name:
        return -1
    for index, frame in enumerate(frames):
        if name_hits_frame(name, frame):
            return index
    return -1


def select_predict_frames(frames, current_index: int, margin: int, lookahead: int, blocked: set[str], coverage: str = "window"):
    """Frames to predict, skipping reviewed and already annotated ones.

    ``window`` starts after ``current + margin`` and stops at ``lookahead``.
    ``all`` is every other frame from the first image, used when a family model
    should fill the project before any training.
    """
    if coverage == "all":
        return [frame for frame in frames if frame.rel not in blocked and frame.stem not in blocked]
    if lookahead <= 0:
        return []
    start = 0 if current_index < 0 else current_index + 1 + max(0, margin)
    chosen = []
    for frame in frames[max(0, start):]:
        if frame.rel in blocked or frame.stem in blocked:
            continue
        chosen.append(frame)
        if len(chosen) >= lookahead:
            break
    return chosen


def prediction_key(frame: Frame, stems_unique: bool) -> str:
    return frame.stem if stems_unique else frame.rel


def default_prefs(project: str, live_prefs) -> dict:
    prefs = {
        "projectName": project,
        "AnnotatorName": "-",
        "prefsFilename": "",
        "imgFoldername": "",
        "userAdds": {},
        "groups": [],
        "brands": [],
        "tpoints": [],
        "conns": {},
        "seelater": [],
    }
    if isinstance(live_prefs, dict):
        for key in PREFS_KEYS:
            if key in live_prefs and key != "projectName":
                prefs[key] = live_prefs[key]
    prefs["projectName"] = project
    return prefs


def annotation_box(ann) -> tuple[float, float, float, float] | None:
    start = ann.get("startPoint") if isinstance(ann, dict) else None
    diag = ann.get("diagPoint") if isinstance(ann, dict) else None
    if not (isinstance(start, (list, tuple)) and isinstance(diag, (list, tuple))):
        return None
    if len(start) < 2 or len(diag) < 2:
        return None
    try:
        x1, x2 = sorted((float(start[0]), float(diag[0])))
        y1, y2 = sorted((float(start[1]), float(diag[1])))
    except (TypeError, ValueError):
        return None
    return x1, y1, x2, y2


def box_area(box: tuple[float, float, float, float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def intersection_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return width * height


def suppress_contained(annotations: list, contain: float) -> list:
    """Keep the higher-confidence box when two boxes overlap, any class.

    A box is dropped when the intersection covers at least ``contain`` of the
    smaller box's area. ``contain`` 0.6 means 60 percent. Boxes that only touch
    at an edge stay. The comparison is class-agnostic.
    """
    if contain <= 0 or len(annotations) < 2:
        return list(annotations)
    ranked = sorted(annotations, key=lambda ann: float(ann.get("confidence") or 0), reverse=True)
    kept = []
    kept_boxes = []
    for ann in ranked:
        box = annotation_box(ann)
        area = box_area(box) if box is not None else 0.0
        drop = False
        if box is not None and area > 0:
            for other in kept_boxes:
                if other is None:
                    continue
                smaller = min(area, box_area(other))
                if smaller <= 0:
                    continue
                overlap = intersection_area(box, other)
                if overlap > 0 and overlap / smaller >= contain:
                    drop = True
                    break
        if not drop:
            kept.append(ann)
            kept_boxes.append(box)
    return kept


def detection_annotation(brand: str, tpoint: str, start, diag, confidence: float) -> dict:
    return {
        "startPoint": [int(start[0]), int(start[1])],
        "diagPoint": [int(diag[0]), int(diag[1])],
        "group": "",
        "brand": brand,
        "tpoint": tpoint,
        "hits": 1,
        "confidence": float(f"{float(confidence):.4f}"),
    }


def prediction_image(key: str, index: int, width: int, height: int, annotations: list) -> dict:
    return {
        "imageName": key,
        "imageIndex": int(index),
        "width": int(width),
        "height": int(height),
        "annotations": list(annotations),
        "exifdata": {},
    }


def build_prediction_document(live, images: dict, project: str | None = None) -> dict:
    """Annotool document, the shape ``predict_to_json.py`` writes. No brand|tpoint dedupe.

    ``project`` is the project captured when prediction started. A live file read
    later must not replace that tag: the tool keeps boxes whose project matches
    the folder it has open.
    """
    tag = "auto_export"
    if isinstance(project, str) and project.strip():
        tag = project.strip()
    elif isinstance(live, dict) and isinstance(live.get("project"), str) and live["project"].strip():
        tag = live["project"].strip()
    annotator = "-"
    presets = {}
    live_prefs = None
    if isinstance(live, dict):
        if isinstance(live.get("Annotator"), str) and live["Annotator"].strip():
            annotator = live["Annotator"]
        if isinstance(live.get("presets"), dict):
            presets = live["presets"]
        live_prefs = live.get("prefs")
    first = next(iter(images), "")
    return {
        "project": tag,
        "imageNum": len(images),
        "prefs": default_prefs(tag, live_prefs),
        "images": images,
        "currentImage": first,
        "presets": presets,
        "Annotator": annotator,
    }


def listed_image_names(live) -> set[str] | None:
    """Image keys in the live file, or None when it does not list any."""
    images = live.get("images") if isinstance(live, dict) else None
    if not isinstance(images, dict) or not images:
        return None
    names = set()
    for key, entry in images.items():
        if isinstance(key, str) and key.strip():
            names.add(key)
            names.add(norm_name(key))
        if isinstance(entry, dict) and isinstance(entry.get("imageName"), str):
            names.add(entry["imageName"])
            names.add(norm_name(entry["imageName"]))
    return names or None


def retain_listed_images(images: dict, live) -> dict:
    """Drop prediction keys the current live file does not list."""
    allowed = listed_image_names(live)
    if not allowed:
        return images
    return {key: entry for key, entry in images.items() if key in allowed or norm_name(str(key)) in allowed}


def read_live_file(sync_folder: Path):
    path = Path(sync_folder) / LIVE_NAME
    if not path.is_file():
        return None
    try:
        data = read_json(path, retries=2, pause=0.05)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def reject_if_project_changed(sync_folder: Path, captured_project: str | None):
    """Re-read the live file. A different project means these boxes must not be written."""
    live_now = read_live_file(sync_folder)
    if not isinstance(live_now, dict):
        return None
    current = project_name(live_now)
    if captured_project and current and current != captured_project:
        LOG.info("project changed during predict, discarding")
        raise PredictionDiscarded()
    return live_now


def commit_predictions(sync_folder: Path, captured_project: str | None, live, images: dict) -> dict:
    """Write ``annotool_predictions.json`` for the project prediction started with.

    Re-reads the live file first. A different project discards the results so a
    folder opened during predict cannot inherit the previous folder's boxes.
    """
    live_now = reject_if_project_changed(sync_folder, captured_project)
    if isinstance(live_now, dict):
        images = retain_listed_images(images, live_now)
    document = build_prediction_document(live, images, project=captured_project)
    errors = prediction_shape_errors(document)
    if errors:
        raise ConfigError("prediction document failed its shape check: " + "; ".join(errors))
    atomic_write_json(Path(sync_folder) / PRED_NAME, document)
    return images


def prediction_shape_errors(doc) -> list[str]:
    errors = []
    if not isinstance(doc, dict):
        return ["root is not an object"]
    if tuple(doc.keys()) != PREDICTION_KEYS:
        errors.append(f"top-level keys {list(doc.keys())}")
    prefs = doc.get("prefs")
    if not isinstance(prefs, dict) or tuple(prefs.keys()) != PREFS_KEYS:
        errors.append("prefs keys differ from predict_to_json")
    images = doc.get("images")
    if not isinstance(images, dict):
        errors.append("images is not an object")
        return errors
    if doc.get("imageNum") != len(images):
        errors.append("imageNum does not match images")
    for key, entry in images.items():
        if not isinstance(entry, dict) or tuple(entry.keys()) != IMAGE_KEYS:
            errors.append(f"{key}: image keys differ")
            continue
        if entry.get("imageName") != key:
            errors.append(f"{key}: imageName mismatch")
        anns = entry.get("annotations")
        if not isinstance(anns, list) or not anns:
            errors.append(f"{key}: annotations must be a non-empty list")
            continue
        for ann in anns:
            if not isinstance(ann, dict) or tuple(ann.keys()) != ANNOTATION_KEYS:
                errors.append(f"{key}: annotation keys differ")
                continue
            if ann.get("hits") != 1:
                errors.append(f"{key}: hits is not 1")
            if not isinstance(ann.get("confidence"), (int, float)):
                errors.append(f"{key}: confidence missing")
            if ann.get("group") != "":
                errors.append(f"{key}: group is not empty")
    return errors


def frame_index_map(frames: list[Frame]) -> dict[str, int]:
    order = {}
    stems = {}
    for index, frame in enumerate(frames):
        order[frame.rel] = index
        stems.setdefault(frame.stem, index)
    for stem, index in stems.items():
        order.setdefault(stem, index)
    return order


def normalize_stored_image(key, entry):
    """Rewrite a stored prediction so it matches the annotool document, or drop it."""
    if not isinstance(entry, dict):
        return None
    size = positive_size(entry.get("width"), entry.get("height"))
    if size is None:
        return None
    anns = []
    raw = entry.get("annotations") or []
    if not isinstance(raw, list):
        return None
    for ann in raw:
        parsed = parse_annotation(ann)
        if not parsed or not isinstance(ann, dict):
            continue
        brand, tpoint, start, diag = parsed
        confidence = as_float(ann.get("confidence"))
        if confidence is None:
            confidence = as_float(ann.get("conf"))
        if confidence is None:
            confidence = 0.0
        anns.append(
            detection_annotation(
                brand,
                tpoint,
                (int(round(start[0])), int(round(start[1]))),
                (int(round(diag[0])), int(round(diag[1]))),
                confidence,
            )
        )
    if not anns:
        return None
    try:
        index = int(entry.get("imageIndex"))
    except (TypeError, ValueError):
        index = 0
    return prediction_image(key, index, size[0], size[1], anns)


def merge_prediction_images(old_images, new_images, replaced_keys, frames, current_index, blocked_rels):
    """Keep suggestions at or ahead of the annotator. Newest pass replaces its own frames.

    Frames behind him, reviewed frames, and frames that already have boxes are
    dropped. A frame this pass ran on is replaced even when the new model found
    nothing, so an old box does not survive a newer empty decision.
    """
    order = frame_index_map(frames)
    by_stem = {}
    for frame in frames:
        by_stem.setdefault(frame.stem, frame)

    def frame_for(key: str):
        if key in order and any(frame.rel == key for frame in frames):
            return next(frame for frame in frames if frame.rel == key)
        bare = key.split("/")[-1]
        return by_stem.get(key) or by_stem.get(bare)

    def keep_old(key: str) -> bool:
        if key in replaced_keys:
            return False
        frame = frame_for(key)
        if frame is None:
            return False
        if frame.rel in blocked_rels or frame.stem in blocked_rels:
            return False
        index = order.get(frame.rel, order.get(key))
        if index is None:
            return False
        if current_index >= 0 and index < current_index:
            return False
        return True

    merged = {}
    for key, entry in old_images.items():
        if not keep_old(key):
            continue
        normalized = normalize_stored_image(key, entry)
        if normalized:
            merged[key] = normalized
    for key, entry in new_images.items():
        anns = (entry or {}).get("annotations") if isinstance(entry, dict) else None
        if anns:
            merged[key] = entry
        else:
            merged.pop(key, None)

    def sort_key(key):
        frame = frame_for(key)
        index = order.get(frame.rel, 10**9) if frame else order.get(key, 10**9)
        return (index, key)

    ordered = {}
    for key in sorted(merged, key=sort_key):
        entry = merged[key]
        anns = entry.get("annotations") if isinstance(entry, dict) else None
        if anns:
            ordered[key] = entry
    return ordered


def prediction_span(images: dict, frames: list[Frame]):
    if not images:
        return None, None
    order = frame_index_map(frames)

    def sort_key(key):
        return (order.get(key, order.get(key.split("/")[-1], 10**9)), key)

    keys = sorted(images, key=sort_key)
    return keys[0], keys[-1]


def summarize_predictions(path: Path, frames: list[Frame]):
    if not path.is_file():
        return 0, None, None
    try:
        doc = read_json(path, retries=2, pause=0.05)
    except ValueError:
        return 0, None, None
    images = doc.get("images") if isinstance(doc.get("images"), dict) else {}
    images = {key: entry for key, entry in images.items() if isinstance(entry, dict) and entry.get("annotations")}
    start, end = prediction_span(images, frames)
    return len(images), start, end


def blank_state(min_reviewed: int) -> dict:
    return {
        "cycle": 0,
        "classes": [],
        "best_weights": None,
        "last_map50": None,
        "reviewed_at_cycle": 0,
        "next_cycle_at": int(min_reviewed),
        "pending_predict": False,
        "epoch": None,
        "epochs": None,
        "from_base": None,
        "train_images": None,
        "val_images": None,
        "hard_negative_frames": 0,
        "model_family": None,
        "model_choice": "continue",
        "model_mode": None,
        "per_class_map50": {},
        "seeded_family": None,
        "seeded_weights": None,
        "last_error": None,
        "cadence": None,
        "every_now": None,
        "cadence_reason": None,
        "class_labels_at_cycle": None,
    }


def load_state(path: Path, min_reviewed: int) -> dict:
    state = blank_state(min_reviewed)
    if not path.exists():
        return state
    data = read_json(path, retries=2, pause=0.05)
    state.update({key: data.get(key, state[key]) for key in state})
    if not isinstance(state["classes"], list):
        state["classes"] = []
    state["classes"] = [str(name) for name in state["classes"]]
    state["cycle"] = int(state["cycle"] or 0)
    state["reviewed_at_cycle"] = int(state["reviewed_at_cycle"] or 0)
    if not state["next_cycle_at"]:
        state["next_cycle_at"] = int(min_reviewed)
    else:
        state["next_cycle_at"] = int(state["next_cycle_at"])
    state["pending_predict"] = bool(state["pending_predict"])
    state["hard_negative_frames"] = int(state.get("hard_negative_frames") or 0)
    if not isinstance(state.get("per_class_map50"), dict):
        state["per_class_map50"] = {}
    else:
        cleaned = {}
        for key, value in state["per_class_map50"].items():
            number = as_float(value)
            if number is not None:
                cleaned[str(key)] = round(number, 4)
        state["per_class_map50"] = cleaned
    if state.get("model_choice") not in {"continue", "new", "from"}:
        state["model_choice"] = "continue"
    if state.get("model_mode") not in {None, "συνέχεια", "νέο"}:
        state["model_mode"] = None
    state["seeded_family"] = state.get("seeded_family") or None
    if not isinstance(state.get("seeded_weights"), dict):
        state["seeded_weights"] = None
    if state.get("cadence") not in {None, "young", "mature", "weak_class", "fixed"}:
        state["cadence"] = None
    if state.get("every_now") is not None:
        state["every_now"] = int(state["every_now"])
    state["cadence_reason"] = state.get("cadence_reason") or None
    if not isinstance(state.get("class_labels_at_cycle"), dict):
        state["class_labels_at_cycle"] = None
    return state


def save_state(path: Path, state: dict):
    atomic_write_json(path, state)


def resolve_weights(state: dict, work: Path):
    stored = state.get("best_weights")
    if not stored:
        return None
    path = Path(stored)
    if not path.is_absolute():
        path = work / path
    return path


def metric_from_trainer(trainer, key: str):
    metrics = getattr(trainer, "metrics", None)
    if isinstance(metrics, dict):
        if key in metrics:
            return as_float(metrics.get(key))
        for name, value in metrics.items():
            if str(name).strip() == key:
                return as_float(value)
    validator = getattr(trainer, "validator", None)
    metrics_obj = getattr(validator, "metrics", None) if validator is not None else None
    box = getattr(metrics_obj, "box", None) if metrics_obj is not None else None
    if key == "metrics/mAP50(B)" and box is not None:
        return as_float(getattr(box, "map50", None))
    if key == "metrics/mAP50-95(B)" and box is not None:
        return as_float(getattr(box, "map", None))
    return None


def best_map50_from_csv(path: Path):
    if not path.is_file():
        return None
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    best_map = None
    best_score = None
    for row in rows:
        cleaned = {str(key).strip(): value for key, value in row.items() if key}
        map50 = as_float(cleaned.get("metrics/mAP50(B)"))
        fit = as_float(cleaned.get("metrics/mAP50-95(B)"))
        if map50 is None:
            continue
        score = fit if fit is not None else map50
        if best_score is None or score >= best_score:
            best_score = score
            best_map = map50
    if best_map is None:
        return None
    return round(best_map, 4)


def yolo_class():
    os.environ["YOLO_OFFLINE"] = "True"
    from ultralytics import YOLO

    return YOLO


def install_signals():
    def handle(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, handle)
        except (ValueError, OSError):
            pass


class FrameIndex:
    def __init__(self, folder: Path):
        self.folder = folder
        self.frames: list[Frame] = []
        self.stamp = None

    def get(self, force: bool = False) -> list[Frame]:
        try:
            stamp = self.folder.stat().st_mtime_ns
        except OSError:
            stamp = None
        if force or stamp != self.stamp or not self.frames:
            self.frames = list_frames(self.folder)
            self.stamp = stamp
        return self.frames


def project_name(live) -> str | None:
    """Annotool's project field. That string is also the frames-folder name."""
    if not isinstance(live, dict):
        return None
    name = live.get("project")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def explicit_family(live) -> str | None:
    if not isinstance(live, dict):
        return None
    name = live.get("modelFamily")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def first_group(live) -> str | None:
    """First group name in ``prefs.groups``, for example ``2026 RLWC``."""
    if not isinstance(live, dict):
        return None
    prefs = live.get("prefs")
    groups = prefs.get("groups") if isinstance(prefs, dict) else None
    if isinstance(groups, str) and groups.strip():
        return groups.strip()
    if isinstance(groups, list):
        for item in groups:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def derived_family(live) -> str:
    return explicit_family(live) or first_group(live) or "default"


def parse_model_choice(live) -> tuple[str, str | None]:
    """Return ``(continue|new|from, family name for from:)``."""
    raw = ""
    if isinstance(live, dict) and isinstance(live.get("modelChoice"), str):
        raw = live["modelChoice"].strip()
    lowered = raw.lower()
    if not lowered or lowered == "continue":
        return "continue", None
    if lowered == "new":
        return "new", None
    if lowered.startswith("from:"):
        name = raw.split(":", 1)[1].strip()
        if name:
            return "from", name
    return "continue", None


def resolve_model_plan(live) -> dict:
    """Family this project belongs to, and whether its library weights must be ignored.

    ``modelFamily`` wins, then the first ``prefs.groups`` entry, then ``default``.
    ``modelChoice`` ``new`` starts that family from the base weights.
    ``from:<family>`` uses the named family instead.
    """
    choice, named = parse_model_choice(live)
    if choice == "from" and named:
        return {"choice": "from", "family": named, "fresh": False}
    if choice == "new":
        return {"choice": "new", "family": explicit_family(live) or derived_family(live), "fresh": True}
    return {"choice": "continue", "family": derived_family(live), "fresh": False}


def family_dir(work_root: Path, family: str) -> Path:
    return Path(work_root) / "models" / project_dirname(family)


def family_weights_path(work_root: Path, family: str) -> Path:
    return family_dir(work_root, family) / "best.pt"


def read_family_meta(work_root: Path, family: str) -> dict:
    path = family_dir(work_root, family) / "meta.json"
    if not path.is_file():
        return {}
    try:
        data = read_json(path, retries=2, pause=0.05)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def assign_model_plan(state: dict, live, work_root: Path) -> Path | None:
    """Store the live file's family on ``state``. Return library weights when they seed this project."""
    plan = resolve_model_plan(live)
    weights = family_weights_path(work_root, plan["family"])
    usable = weights.is_file() and not plan["fresh"]
    state["model_family"] = plan["family"]
    state["model_choice"] = plan["choice"]
    state["model_mode"] = "συνέχεια" if usable else "νέο"
    return weights if usable else None


def maybe_update_family(
    work_root: Path,
    family: str,
    weights: Path,
    map50,
    per_class: dict,
    classes: list[str] | None = None,
    dataset_signature: str | None = None,
) -> bool:
    """Copy ``weights`` into the family library when no known class disappeared.

    The previous ``best.pt`` is kept as ``best_prev.pt``. A lower mAP50 still
    replaces the library: losing a class does not. ``classes`` is the trained
    name list, in id order.
    """
    if not family or not Path(weights).is_file():
        return False
    trained = [str(name) for name in (classes or [])]
    protected = protected_family_classes(work_root, family)
    if protected is None:
        LOG.info("family %s keeps best.pt; its class list could not be read", family)
        return False
    missing = [name for name in protected if name not in set(trained)]
    if missing:
        LOG.info("family %s keeps best.pt; this cycle dropped %s", family, ", ".join(missing))
        return False
    measured = as_float(map50)
    meta = read_family_meta(work_root, family)
    if measured is None:
        measured = as_float(meta.get("map50"))
    dest = family_dir(work_root, family)
    dest.mkdir(parents=True, exist_ok=True)
    current = dest / "best.pt"
    if current.is_file():
        shutil.copy2(current, dest / "best_prev.pt")
    shutil.copy2(weights, current)
    signature = dataset_signature if dataset_signature else meta.get("dataset_signature")
    atomic_write_json(
        dest / "meta.json",
        {
            "family": family,
            "map50": None if measured is None else round(measured, 4),
            "per_class_map50": dict(per_class or {}),
            "classes": trained,
            "dataset_signature": signature,
            "updated_at": iso_now(),
        },
    )
    LOG.info("updated family %s best.pt classes=%s mAP50=%s", family, len(trained), measured)
    return True


def project_dirname(project: str | None) -> str:
    """Work subdirectory for one project. Keeps the folder name when it is safe."""
    if not isinstance(project, str) or not project.strip():
        return "_default"
    cleaned = project.strip().replace("/", "__").replace("\\", "__")
    cleaned = re.sub(r'[<>:"|?*]+', "_", cleaned).strip(" .")
    if not cleaned or cleaned in {".", ".."}:
        return "_default"
    if len(cleaned) > 100:
        digest = hashlib.sha1(project.encode("utf-8")).hexdigest()[:8]
        cleaned = cleaned[:90].rstrip(" ._") + "_" + digest
    return cleaned


def weights_stamp(path: Path) -> dict | None:
    """mtime, size, and sha1 of a checkpoint. ``copy2`` keeps mtime, so the hash is the real change."""
    path = Path(path)
    if not path.is_file():
        return None
    st = path.stat()
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    return {"mtime_ns": int(mtime_ns), "size": int(st.st_size), "sha1": digest.hexdigest()}


_CHECKPOINT_NAMES: dict[tuple, list[str]] = {}


def checkpoint_class_names(path: Path) -> list[str]:
    """Class names stored in a YOLO ``.pt``. Empty when the file is not a checkpoint."""
    path = Path(path)
    try:
        st = path.stat()
    except OSError:
        return []
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    key = (str(path.resolve()), int(mtime_ns), int(st.st_size))
    cached = _CHECKPOINT_NAMES.get(key)
    if cached is not None:
        return list(cached)
    names = _read_checkpoint_names(path)
    _CHECKPOINT_NAMES[key] = list(names)
    return names


def _read_checkpoint_names(path: Path) -> list[str]:
    try:
        import torch

        ckpt = torch.load(path, map_location="cpu", weights_only=False)
    except Exception:
        LOG.debug("could not read class names from %s", path, exc_info=True)
        return []
    model = ckpt.get("model") if isinstance(ckpt, dict) else None
    names = getattr(model, "names", None)
    if isinstance(names, dict):
        keys = sorted(names, key=lambda key: int(key))
        return [str(names[key]) for key in keys]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    return []


def family_index_path(work_root: Path, family: str) -> Path:
    return family_dir(work_root, family) / "dataset.json"


def load_family_index(work_root: Path, family: str) -> dict:
    path = family_index_path(work_root, family)
    data = {}
    if path.is_file():
        try:
            loaded = read_json(path, retries=2, pause=0.05)
        except ValueError:
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
    classes = [str(name) for name in data.get("classes") or [] if str(name).strip()]
    projects = data.get("projects") if isinstance(data.get("projects"), dict) else {}
    return {"classes": classes, "projects": projects}


def save_family_index(work_root: Path, family: str, index: dict):
    dest = family_dir(work_root, family)
    dest.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        family_index_path(work_root, family),
        {"classes": list(index.get("classes") or []), "projects": dict(index.get("projects") or {})},
    )


def protected_family_classes(work_root: Path, family: str) -> list[str] | None:
    """Append-only class ids for this family.

    ``dataset.json`` and ``meta.json`` win for order. Logo names (``brand|tpoint``)
    stored in the library ``best.pt`` are added even when a later project saved a
    shorter list. None means a library file is there but its classes could not
    be read, so it must not be replaced.
    """
    index = load_family_index(work_root, family)
    saved = [str(name) for name in index.get("classes") or []]
    meta = read_family_meta(work_root, family)
    meta_classes = []
    if isinstance(meta.get("classes"), list):
        meta_classes = [str(name) for name in meta["classes"] if str(name).strip()]
    weights = family_weights_path(work_root, family)
    checkpoint = checkpoint_class_names(weights) if weights.is_file() else []
    logos = [name for name in checkpoint if "|" in name]
    if saved or meta_classes or logos:
        base = meta_classes or saved or logos
        extra = set(saved) | set(meta_classes) | set(logos)
        classes, _new = extend_classes(base, extra)
        return classes
    if not weights.is_file():
        return []
    if checkpoint:
        return checkpoint
    per_class = meta.get("per_class_map50")
    if isinstance(per_class, dict) and per_class:
        return [str(name) for name in per_class]
    return None


def _stored_box(name: str, yolo) -> list:
    return [name, round(float(yolo[0]), 6), round(float(yolo[1]), 6), round(float(yolo[2]), 6), round(float(yolo[3]), 6)]


def _frame_signature(frames) -> tuple:
    rows = []
    for frame in frames or []:
        if not isinstance(frame, dict):
            continue
        boxes = []
        for box in frame.get("boxes") or []:
            if not isinstance(box, (list, tuple)) or len(box) != 5:
                continue
            boxes.append((str(box[0]), round(float(box[1]), 6), round(float(box[2]), 6), round(float(box[3]), 6), round(float(box[4]), 6)))
        rows.append((str(frame.get("rel") or ""), bool(frame.get("hard_negative")), int(frame.get("order") or 0), tuple(boxes)))
    return tuple(rows)


def extract_project_frames(frames: list[Frame], live: dict) -> tuple[list[dict], list[str]]:
    """Reviewed frames as stored labels. Does not raise when there are no boxes."""
    names = reviewed_names(live)
    chosen, unmatched = match_reviewed(frames, names)
    if unmatched:
        LOG.warning("reviewed names with no jpg (%s): %s", len(unmatched), ", ".join(unmatched[:8]))
    images = live_images(live)
    dominant = dominant_canvas(images)
    hard = hard_negative_rels(frames, live)
    stored = []
    for order, frame in enumerate(chosen):
        entry = live_entry_for(images, frame)
        try:
            img_w, img_h = image_size(frame.path)
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            LOG.warning("skip unreadable frame %s: %s", frame.rel, exc)
            continue
        canvas = None
        if isinstance(entry, dict):
            canvas = positive_size(entry.get("width"), entry.get("height"))
        if canvas is None:
            canvas = dominant or (img_w, img_h)
        boxes = []
        for brand, tpoint, start, diag in usable_annotations(entry):
            yolo = canvas_box_to_yolo(start, diag, canvas[0], canvas[1], img_w, img_h)
            if yolo is None:
                LOG.warning("skip box on %s (empty after scaling onto the image)", frame.rel)
                continue
            boxes.append(_stored_box(class_name(brand, tpoint), yolo))
        stored.append(
            {
                "rel": frame.rel,
                "path": str(frame.path),
                "boxes": boxes,
                "hard_negative": frame.rel in hard,
                "order": order,
            }
        )
    return stored, unmatched


def remember_project(work_root: Path, family: str, project: str, work_dir: Path, frames_folder, frames: list[Frame], live: dict) -> dict:
    """Store this project's reviewed labels in the family index. Class ids only grow."""
    index = load_family_index(work_root, family)
    protected = protected_family_classes(work_root, family)
    protected_grew = False
    if protected:
        seeded, _added = extend_classes(list(index["classes"]), set(protected))
        if seeded != list(index["classes"]):
            index["classes"] = seeded
            protected_grew = True
    projects = index["projects"]
    previous = projects.get(project) if isinstance(projects.get(project), dict) else {}
    previous_frames = previous.get("frames") if isinstance(previous.get("frames"), list) else []
    was_new = project not in projects
    stored, _unmatched = extract_project_frames(frames, live)
    if not stored and previous_frames:
        LOG.warning("keeping stored labels for %s; this snapshot has no readable reviewed frames", project)
        stored = previous_frames
        changed = False
    else:
        changed = _frame_signature(previous_frames) != _frame_signature(stored) or str(previous.get("frames_folder") or "") != str(frames_folder or "")
    found = {str(box[0]) for frame in stored if isinstance(frame, dict) for box in (frame.get("boxes") or []) if box}
    classes, _new = extend_classes(list(index["classes"]), found)
    if changed or was_new:
        projects[project] = {
            "work_dir": str(work_dir),
            "frames_folder": str(frames_folder or ""),
            "updated_at": iso_now(),
            "frames": stored,
        }
    else:
        projects[project]["work_dir"] = str(work_dir)
    grew = classes != list(index["classes"])
    index["classes"] = classes
    for key, entry in list(projects.items()):
        if key == project or not isinstance(entry, dict):
            continue
        if str(entry.get("work_dir") or "") == str(work_dir):
            projects.pop(key, None)
            changed = True
    if changed or was_new or grew or protected_grew:
        save_family_index(work_root, family, index)
    return index


def yaml_class_names(path: Path) -> list[str]:
    """Read the ``names:`` list from a dataset yaml written by this trainer."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    names = []
    in_names = False
    for line in lines:
        if line.startswith("names:"):
            in_names = True
            continue
        if not in_names:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            names.append(stripped[2:].strip().strip("'\""))
        elif stripped and not line.startswith((" ", "\t")):
            break
    return names


def frames_from_yolo_dataset(dataset: Path, names: list[str]) -> list[dict]:
    """Labels already written under a project work dir. Hard-negative copies are skipped."""
    stored = []
    order = 0
    for split in ("train", "val"):
        label_dir = dataset / "labels" / split
        image_dir = dataset / "images" / split
        if not label_dir.is_dir():
            continue
        for label in sorted(label_dir.glob("*.txt")):
            if "__hn" in label.stem:
                continue
            image = None
            for suffix in (".jpg", ".jpeg", ".JPG", ".JPEG"):
                candidate = image_dir / f"{label.stem}{suffix}"
                if candidate.is_file():
                    image = candidate
                    break
            if image is None:
                continue
            boxes = []
            try:
                text = label.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                try:
                    class_index = int(parts[0])
                    coords = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                except ValueError:
                    continue
                if not 0 <= class_index < len(names):
                    continue
                boxes.append(_stored_box(names[class_index], coords))
            stored.append(
                {
                    "rel": label.stem,
                    "path": str(image),
                    "boxes": boxes,
                    "hard_negative": False,
                    "order": order,
                }
            )
            order += 1
    return stored


def backfill_family_projects(work_root: Path, family: str, index: dict) -> dict:
    """Add reviewed labels already saved under other project work dirs of this family.

    A project the live file has already stored is left alone. This is how a
    family keeps frames from clusters that were trained before the shared index
    existed.
    """
    try:
        children = [path for path in Path(work_root).iterdir() if path.is_dir() and path.name != "models"]
    except OSError as exc:
        LOG.warning("cannot list work dir %s: %s", work_root, exc)
        return index
    changed = False
    for child in children:
        state_path = child / "state.json"
        yaml_path = child / "dataset" / "data.yaml"
        if not state_path.is_file() or not yaml_path.is_file():
            continue
        try:
            state = read_json(state_path, retries=1, pause=0.02)
        except ValueError:
            continue
        if not isinstance(state, dict):
            continue
        stored_family = state.get("model_family")
        if stored_family and stored_family != family:
            continue
        existing = index["projects"].get(child.name)
        if isinstance(existing, dict) and existing.get("frames"):
            continue
        known_dirs = {
            str(entry.get("work_dir") or "")
            for entry in index["projects"].values()
            if isinstance(entry, dict) and entry.get("frames")
        }
        if str(child) in known_dirs:
            continue
        names = yaml_class_names(yaml_path)
        if not stored_family:
            known = {str(name) for name in index.get("classes") or []}
            if not known or not (set(names) & known):
                continue
            LOG.info(
                "family %s loading %s by shared classes; state.json has no model_family",
                family,
                child.name,
            )
        frames = frames_from_yolo_dataset(child / "dataset", names) if names else []
        if not frames:
            continue
        index["projects"][child.name] = {
            "work_dir": str(child),
            "frames_folder": "",
            "updated_at": iso_now(),
            "frames": frames,
            "source": "dataset",
        }
        found = {str(box[0]) for frame in frames for box in frame.get("boxes") or []}
        classes, _new = extend_classes(list(index.get("classes") or []), found)
        if classes != list(index.get("classes") or []):
            index["classes"] = classes
        changed = True
        LOG.info("family %s loaded %s stored frames from %s", family, len(frames), child.name)
    if changed:
        loaded = ", ".join(sorted(str(name) for name in index["projects"]))
        LOG.info("family %s dataset projects: %s", family, loaded)
        save_family_index(work_root, family, index)
    return index


def family_dataset_signature(index: dict) -> str:
    """Stable hash of reviewed frames and boxes. Class order is not part of it."""
    lines = []
    projects = index.get("projects") or {}
    for project in sorted(projects):
        entry = projects[project]
        if not isinstance(entry, dict):
            continue
        parts = []
        for frame in entry.get("frames") or []:
            if not isinstance(frame, dict):
                continue
            boxes = []
            for box in frame.get("boxes") or []:
                if isinstance(box, (list, tuple)) and box:
                    boxes.append(",".join(str(item) for item in box))
            boxes.sort()
            parts.append(f"{frame.get('rel')}|{int(bool(frame.get('hard_negative')))}|{' ; '.join(boxes)}")
        parts.sort()
        lines.append(str(project) + "\n" + "\n".join(parts))
    return hashlib.sha1("\n\n".join(lines).encode("utf-8")).hexdigest()


def family_is_stale(work_root: Path, family: str, index: dict) -> bool:
    """True when the library model is missing, or is missing a family class.

    Extra reviewed frames of classes the model already has wait for the
    training cadence. A new ``brand|tpoint`` still makes this true, so the
    union trains before the next prediction.
    """
    classes = [str(name) for name in index.get("classes") or [] if str(name).strip()]
    has_boxes = False
    for entry in (index.get("projects") or {}).values():
        if not isinstance(entry, dict):
            continue
        for frame in entry.get("frames") or []:
            if isinstance(frame, dict) and frame.get("boxes"):
                has_boxes = True
                break
        if has_boxes:
            break
    weights = family_weights_path(work_root, family)
    if not weights.is_file():
        return has_boxes
    meta = read_family_meta(work_root, family)
    known = [str(name) for name in meta.get("classes") or [] if str(name).strip()]
    if not known:
        known = [name for name in checkpoint_class_names(weights) if "|" in name] or checkpoint_class_names(weights)
    return bool(set(classes) - set(known))


def family_reviewed_count(index: dict) -> int:
    total = 0
    projects = index.get("projects") or {}
    for entry in projects.values():
        if isinstance(entry, dict):
            total += len(entry.get("frames") or [])
    return total


def class_label_signatures(index: dict) -> dict[str, str]:
    """Hash of each class's boxes. A new label of that class changes the hash."""
    buckets: dict[str, list[str]] = {}
    projects = index.get("projects") or {}
    for project in sorted(projects):
        entry = projects[project]
        if not isinstance(entry, dict):
            continue
        for frame in entry.get("frames") or []:
            if not isinstance(frame, dict):
                continue
            rel = str(frame.get("rel") or "")
            for box in frame.get("boxes") or []:
                if not isinstance(box, (list, tuple)) or not box:
                    continue
                name = str(box[0])
                buckets.setdefault(name, []).append(f"{project}|{rel}|{','.join(str(item) for item in box)}")
    signatures = {}
    for name, lines in buckets.items():
        signatures[name] = hashlib.sha1("\n".join(sorted(lines)).encode("utf-8")).hexdigest()
    return signatures


def decide_cadence(
    args,
    *,
    frame_count: int,
    map50,
    per_class: dict,
    label_signatures: dict,
    label_snapshot,
    known_classes: set[str],
    cycle: int,
) -> dict:
    """Pick young, mature, weak_class, or fixed. A new class after the first cycle is immediate.

    ``--every`` disables the adaptive choice and keeps that fixed gap. The first
    cycle still waits for ``--min-reviewed``; the caller enforces that.
    """
    new_classes = sorted(set(label_signatures) - set(known_classes))
    immediate = bool(new_classes) and int(cycle) > 0
    if getattr(args, "every", None) is not None:
        every = int(args.every)
        name = "fixed"
        reason = f"σταθερό διάστημα, εκπαίδευση κάθε {every}"
    else:
        weak = []
        snapshot = label_snapshot if isinstance(label_snapshot, dict) else None
        if snapshot is not None:
            for class_name in sorted(per_class or {}):
                score = as_float(per_class.get(class_name))
                if score is None or score >= float(args.weak_class_map):
                    continue
                current = label_signatures.get(str(class_name))
                if current and current != snapshot.get(str(class_name)):
                    weak.append(str(class_name))
        if weak:
            every = int(args.every_young)
            name = "weak_class"
            reason = f"αδύναμη κατηγορία {', '.join(weak)}, κάθε {every}"
        elif int(frame_count) >= int(args.mature_frames) and map50 is not None and float(map50) >= float(args.mature_map):
            every = int(args.every_mature)
            name = "mature"
            reason = f"ώριμο μοντέλο, εκπαίδευση κάθε {every}"
        else:
            every = int(args.every_young)
            name = "young"
            reason = f"νέο μοντέλο, εκπαίδευση κάθε {every}"
    if immediate:
        reason = f"νέα κατηγορία {', '.join(new_classes)}, εκπαίδευση τώρα"
    return {
        "cadence": name,
        "every_now": every,
        "cadence_reason": reason,
        "immediate": immediate,
        "new_classes": new_classes,
    }


def apply_cadence(args, state: dict, index: dict | None, reviewed: int) -> None:
    """Store the cadence and set ``next_cycle_at`` from it. The first cycle stays at ``--min-reviewed``."""
    index = index or {"classes": [], "projects": {}}
    signatures = class_label_signatures(index)
    before = (
        state.get("cadence"),
        state.get("every_now"),
        state.get("cadence_reason"),
        int(state.get("next_cycle_at") or 0),
        state.get("class_labels_at_cycle"),
    )
    if not isinstance(state.get("class_labels_at_cycle"), dict):
        state["class_labels_at_cycle"] = signatures
    family = state.get("model_family")
    meta = read_family_meta(args.work_root, family) if family else {}
    map50 = as_float(meta.get("map50"))
    if map50 is None:
        map50 = as_float(state.get("last_map50"))
    per_class = meta.get("per_class_map50") if isinstance(meta.get("per_class_map50"), dict) and meta.get("per_class_map50") else {}
    if not per_class:
        per_class = state.get("per_class_map50") or {}
    known = set()
    for name in list(meta.get("classes") or []) + list(state.get("classes") or []):
        text = str(name).strip()
        if text:
            known.add(text)
    decision = decide_cadence(
        args,
        frame_count=family_reviewed_count(index),
        map50=map50,
        per_class=per_class,
        label_signatures=signatures,
        label_snapshot=state.get("class_labels_at_cycle"),
        known_classes=known,
        cycle=int(state["cycle"]),
    )
    every = int(decision["every_now"])
    if int(state["cycle"]) == 0:
        target = int(args.min_reviewed)
    else:
        target = int(state["reviewed_at_cycle"]) + every
        if decision["immediate"]:
            target = min(target, int(reviewed))
    state["cadence"] = decision["cadence"]
    state["every_now"] = every
    state["cadence_reason"] = decision["cadence_reason"]
    state["next_cycle_at"] = int(target)
    token = (decision["cadence"], every, decision["cadence_reason"])
    if token != getattr(args, "_cadence_logged", None):
        LOG.info("cadence %s every %s: %s", decision["cadence"], every, decision["cadence_reason"])
        args._cadence_logged = token
    after = (state["cadence"], state["every_now"], state["cadence_reason"], int(state["next_cycle_at"]), state.get("class_labels_at_cycle"))
    if after != before:
        save_state(args.work_dir / STATE_NAME, state)


def family_finetune_ok(weights: Path, classes: list[str]) -> bool:
    """Fine-tune when every logo class in the checkpoint is still in the training list."""
    if not Path(weights).is_file():
        return False
    names = checkpoint_class_names(weights)
    logos = [name for name in names if "|" in name]
    if not logos:
        return False
    return set(logos).issubset(set(classes))


def family_epoch_message(epoch: int, total: int) -> str:
    return f"{FAMILY_UNIFY_MESSAGE} · epoch {epoch}/{total}"


def family_example_rows(index: dict) -> list[dict]:
    rows = []
    for project, entry in (index.get("projects") or {}).items():
        if not isinstance(entry, dict):
            continue
        updated = str(entry.get("updated_at") or "")
        folder = entry.get("frames_folder") or ""
        for frame in entry.get("frames") or []:
            if not isinstance(frame, dict):
                continue
            path = Path(str(frame.get("path") or ""))
            if not path.is_file() and folder and frame.get("rel"):
                alt = Path(folder) / f"{frame['rel']}.jpg"
                if alt.is_file():
                    path = alt
            if not path.is_file():
                LOG.warning("family dataset is missing %s", frame.get("path"))
                continue
            boxes = []
            for box in frame.get("boxes") or []:
                if not isinstance(box, (list, tuple)) or len(box) != 5:
                    continue
                try:
                    coords = (float(box[1]), float(box[2]), float(box[3]), float(box[4]))
                except (TypeError, ValueError):
                    continue
                boxes.append((str(box[0]), coords))
            rows.append(
                {
                    "project": str(project),
                    "rel": str(frame.get("rel") or path.stem),
                    "path": path,
                    "boxes": boxes,
                    "hard_negative": bool(frame.get("hard_negative")),
                    "updated_at": updated,
                    "order": int(frame.get("order") or 0),
                }
            )
    return rows


def sample_family_examples(examples: list[dict], limit: int) -> list[dict]:
    """Keep every frame under the cap. Above it, keep the most recent image of each class, then recent frames."""
    if limit <= 0 or len(examples) <= limit:
        return list(examples)

    def recency(row):
        return (row.get("updated_at") or "", int(row.get("order") or 0))

    def ident(row):
        return (row.get("project"), row.get("rel"))

    positives = [row for row in examples if row.get("boxes")]
    negatives = [row for row in examples if not row.get("boxes")]
    by_class = {}
    for row in positives:
        for name, _coords in row["boxes"]:
            by_class.setdefault(name, []).append(row)
    for rows in by_class.values():
        rows.sort(key=recency, reverse=True)
    classes = sorted(by_class)
    quota = max(1, limit // len(classes)) if classes else 0
    chosen = []
    chosen_ids = set()
    added = {name: 0 for name in classes}
    cursors = {name: 0 for name in classes}
    progressed = True
    while len(chosen) < limit and progressed:
        progressed = False
        for name in classes:
            if added[name] >= quota:
                continue
            rows = by_class[name]
            while cursors[name] < len(rows) and ident(rows[cursors[name]]) in chosen_ids:
                cursors[name] += 1
            if cursors[name] >= len(rows):
                continue
            row = rows[cursors[name]]
            cursors[name] += 1
            chosen.append(row)
            chosen_ids.add(ident(row))
            added[name] += 1
            progressed = True
            if len(chosen) >= limit:
                break
    neg_budget = min(len(negatives), max(0, limit // 10))
    room = max(0, limit - len(chosen) - neg_budget)
    for row in sorted(positives, key=recency, reverse=True):
        if room <= 0:
            break
        if ident(row) in chosen_ids:
            continue
        chosen.append(row)
        chosen_ids.add(ident(row))
        room -= 1
    for row in sorted(negatives, key=recency, reverse=True):
        if len(chosen) >= limit:
            break
        if ident(row) in chosen_ids:
            continue
        chosen.append(row)
        chosen_ids.add(ident(row))
    return chosen


# A directory with this many jpgs is a frames dump. Do not walk into it.
FRAMES_DIR_MIN_JPEGS = 8
DEFAULT_FRAMES_MAX_DEPTH = 6
_BATCH_DIR = re.compile(r"batch\d+\Z", re.IGNORECASE)


def _jpeg_count(filenames) -> int:
    return sum(1 for filename in filenames if Path(filename).suffix.lower() in {".jpg", ".jpeg"})


def searching_message(project: str) -> str:
    return f"Αναζήτηση φακέλου frames για {project}…"


NO_BOXES_MESSAGE = "Αναμονή · δεν υπάρχουν κουτιά λογότυπου στην οικογένεια"
FAMILY_UNIFY_MESSAGE = "Ενιαίο μοντέλο οικογένειας, περίμενε…"
FAMILY_IMAGE_CAP = 1500


def mark_searching(status: Status, live, project: str):
    """Publish before the frames walk so the UI does not stay on the startup line."""
    reviewed = len(reviewed_names(live)) if isinstance(live, dict) else 0
    family = resolve_model_plan(live)["family"] if isinstance(live, dict) else None
    status.update(
        state="searching",
        project=project,
        frames_folder=None,
        reviewed=reviewed,
        current_image=current_name(live) if isinstance(live, dict) else None,
        last_error=None,
        model_family=family,
        model_mode=None,
        message=searching_message(project),
    )


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def _hint_project_folder(name: str, root: Path, max_depth: int) -> Path | None:
    """``<root>/batchNN/<match>/reduced_<match>/<project>`` when that folder holds a jpg."""
    try:
        batches = [entry for entry in root.iterdir() if entry.is_dir() and _BATCH_DIR.fullmatch(entry.name)]
    except OSError as exc:
        LOG.warning("cannot list frames root %s: %s", root, exc)
        return None
    for batch in batches:
        try:
            matches = [entry for entry in batch.iterdir() if entry.is_dir()]
        except OSError:
            continue
        for match in matches:
            candidate = match / f"reduced_{match.name}" / name
            if not candidate.is_dir():
                continue
            try:
                depth = len(candidate.relative_to(root).parts)
            except ValueError:
                depth = max_depth + 1
            if depth > max_depth:
                continue
            try:
                names = [entry.name for entry in candidate.iterdir() if entry.is_file()]
            except OSError:
                continue
            if _jpeg_count(names) < 1:
                continue
            found = _resolved(candidate)
            LOG.info("frames folder %s (batch layout)", found)
            return found
    return None


def _walk_project_folder(name: str, root: Path, max_depth: int) -> Path | None:
    """Stop at the first exact-name directory that directly contains a jpg.

    Descent into that directory is pruned. Directories that already hold many
    jpgs are frames dumps and are not entered either.
    """
    try:
        walker = os.walk(root, topdown=True, followlinks=False)
    except OSError as exc:
        LOG.warning("cannot read frames root %s: %s", root, exc)
        return None
    for dirpath, dirnames, filenames in walker:
        current = Path(dirpath)
        try:
            depth = len(current.relative_to(root).parts)
        except ValueError:
            depth = 0
        jpeg_count = _jpeg_count(filenames)
        if current.name == name and jpeg_count >= 1:
            dirnames[:] = []
            return _resolved(current)
        if jpeg_count >= FRAMES_DIR_MIN_JPEGS or depth >= max_depth:
            dirnames[:] = []
    return None


def find_project_folder(name: str, roots: list[Path], max_depth: int = DEFAULT_FRAMES_MAX_DEPTH, on_search=None) -> Path | None:
    """Find ``name`` under ``roots`` without walking a whole downloads tree.

    Tries ``batchNN/<match>/reduced_<match>/<name>`` first. The bounded walk
    then stops at the first directory with that exact name and a jpg inside it.
    ``on_search`` runs once, before either search, so the status file can leave
    the startup message.
    """
    name = name.strip()
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        return None
    if max_depth < 0:
        raise ConfigError("--frames-max-depth must be >= 0")
    if on_search is not None:
        on_search(name)
    LOG.info("searching for a frames folder named %s (max depth %s)", name, max_depth)
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            LOG.warning("frames root is not a directory: %s", root)
            continue
        hinted = _hint_project_folder(name, root, max_depth)
        if hinted is not None:
            return hinted
        found = _walk_project_folder(name, root, max_depth)
        if found is not None:
            LOG.info("frames folder %s", found)
            return found
    LOG.error("no frames folder named %s", name)
    return None


class FrameLocator:
    """Remember project name → frames folder. Misses are not retried every poll."""

    def __init__(self, roots: list[Path], cache_path: Path, miss_seconds: float = 60, max_depth: int = DEFAULT_FRAMES_MAX_DEPTH, on_search=None):
        self.roots = [Path(root) for root in roots]
        self.cache_path = Path(cache_path)
        self.miss_seconds = miss_seconds
        self.max_depth = max_depth
        self.on_search = on_search
        self.cache: dict[str, str] = {}
        self._miss_at: dict[str, float] = {}
        self._cache_logged: set[str] = set()
        if self.cache_path.is_file():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = None
            if isinstance(data, dict):
                self.cache = {str(key): str(value) for key, value in data.items()}

    def save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.cache_path, dict(sorted(self.cache.items())))

    def resolve(self, project: str) -> Path | None:
        cached = self.cache.get(project)
        if cached:
            path = Path(cached)
            if path.is_dir():
                if project not in self._cache_logged:
                    LOG.info("frames folder from cache: %s", path)
                    self._cache_logged.add(project)
                return path
            LOG.info("cached frames folder is gone, searching again: %s", path)
            self.cache.pop(project, None)
        last = self._miss_at.get(project)
        if last is not None and time.time() - last < self.miss_seconds:
            return None
        found = find_project_folder(project, self.roots, max_depth=self.max_depth, on_search=self.on_search)
        if found is None:
            self._miss_at[project] = time.time()
            if project in self.cache:
                self.cache.pop(project, None)
                self.save()
            return None
        self._miss_at.pop(project, None)
        self.cache[project] = str(found)
        self.save()
        return found


def frames_not_found_error(project: str | None, roots: list[Path]) -> str:
    if not project:
        return (
            "annotool_live.json has no project name, so the frames folder cannot be searched. "
            "Pass --frames-folder or set the project field in the live file."
        )
    listed = ", ".join(str(root) for root in roots) or "(no --frames-root)"
    return (
        f"frames folder for project '{project}' was not found under {listed}. "
        "Need a directory with that exact name that contains .jpg files."
    )


def bind_project(live, explicit_frames: Path | None, locator: FrameLocator | None, work_root: Path, min_reviewed: int, active: dict):
    """Point ``active`` at this live file's project work dir and frames folder.

    ``active`` holds project, frames, work, state, index, ready. Returns a
    last_error string when the frames folder cannot be resolved, else None.
    A different project loads its own state.json and best.pt. The in-memory
    state of the current project is not reloaded on every poll.
    """
    project = project_name(live)
    if explicit_frames is not None:
        folder = Path(explicit_frames)
        error = None
    elif locator is None:
        folder = None
        error = frames_not_found_error(project, [])
    else:
        folder = locator.resolve(project) if project else None
        error = None if folder is not None else frames_not_found_error(project, locator.roots)
    active["requested"] = project
    if error:
        active["ready"] = False
        active["frames"] = None
        active["index"] = None
        return error
    if active.get("project") != project or active.get("work") is None:
        previous = active.get("project")
        work = (Path(work_root) / project_dirname(project)).resolve()
        work.mkdir(parents=True, exist_ok=True)
        try:
            state = load_state(work / STATE_NAME, min_reviewed)
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        if previous not in (None, project):
            LOG.info("switching project %s -> %s", previous, project or "(none)")
        active["project"] = project
        active["work"] = work
        active["state"] = state
        LOG.info("project %s work=%s", project or "(none)", work)
    if active.get("frames") != folder:
        LOG.info("frames folder %s", folder)
        active["frames"] = folder
        active["index"] = FrameIndex(folder)
    active["ready"] = True
    return None


def ensure_predictions_project(sync_folder: Path, live: dict):
    """Drop suggestion boxes written for a different project. Stems collide across matches."""
    project = project_name(live)
    if not project:
        return
    path = sync_folder / PRED_NAME
    if not path.is_file():
        return
    try:
        doc = read_json(path, retries=2, pause=0.05)
    except ValueError:
        return
    current = doc.get("project") if isinstance(doc, dict) else None
    if current == project:
        return
    LOG.info("predictions were for %s; clearing them for %s", current, project)
    atomic_write_json(path, build_prediction_document(live, {}))


def idle_message(reviewed: int, next_at: int, unmatched: int, family: str | None = None, mode: str | None = None) -> str:
    text = f"Αναμονή · {reviewed}/{next_at} reviewed"
    if family:
        text += f" · {family}"
    if mode:
        text += f" · {mode}"
    if unmatched:
        text += f" · {unmatched} χωρίς jpg"
    return text


def publish_idle(
    status: Status,
    state: dict,
    live,
    frames,
    pred_path: Path,
    work: Path,
    unmatched: int = 0,
    project: str | None = None,
    frames_folder: Path | None = None,
    work_root: Path | None = None,
):
    reviewed_list = reviewed_names(live) if isinstance(live, dict) else []
    reviewed = len(reviewed_list)
    count, start, end = summarize_predictions(pred_path, frames)
    weights = resolve_weights(state, work)
    if (weights is None or not weights.is_file()) and work_root and state.get("model_mode") == "συνέχεια":
        family = state.get("model_family")
        if family:
            shared = family_weights_path(work_root, family)
            if shared.is_file():
                weights = shared
    status.update(
        state="idle",
        project=project if project is not None else project_name(live),
        frames_folder=str(frames_folder) if frames_folder else None,
        cycle=int(state["cycle"]),
        reviewed=reviewed,
        reviewed_since_last_cycle=max(0, reviewed - int(state["reviewed_at_cycle"])),
        next_cycle_at=int(state["next_cycle_at"]),
        predicted_frames=count,
        predicted_from=start,
        predicted_to=end,
        classes=list(state["classes"]),
        last_map50=state.get("last_map50"),
        epoch=state.get("epoch"),
        epochs=state.get("epochs"),
        last_error=state.get("last_error"),
        current_image=current_name(live) if isinstance(live, dict) else None,
        weights=str(weights) if weights and weights.is_file() else None,
        from_base=state.get("from_base"),
        train_images=state.get("train_images"),
        val_images=state.get("val_images"),
        hard_negative_frames=int(state.get("hard_negative_frames") or 0),
        model_family=state.get("model_family"),
        model_mode=state.get("model_mode"),
        per_class_map50=dict(state.get("per_class_map50") or {}),
        cadence=state.get("cadence"),
        every_now=state.get("every_now"),
        cadence_reason=state.get("cadence_reason"),
        message=idle_message(
            reviewed,
            int(state["next_cycle_at"]),
            unmatched,
            state.get("model_family"),
            state.get("model_mode"),
        ),
    )


def match_reviewed(frames: list[Frame], names: list[str]):
    chosen = []
    seen = set()
    for name in names:
        for frame in frames:
            if frame.rel in seen:
                continue
            if name_hits_frame(name, frame):
                chosen.append(frame)
                seen.add(frame.rel)
                break
    unmatched = [name for name in names if not any(name_hits_frame(name, frame) for frame in frames)]
    chosen.sort(key=lambda frame: natural_key(frame.rel))
    return chosen, unmatched


def annotated_rels(frames: list[Frame], images: dict) -> set[str]:
    rels = set()
    for frame in frames:
        entry = live_entry_for(images, frame)
        if usable_annotations(entry):
            rels.add(frame.rel)
    return rels


def rejection_names(live) -> set[str]:
    """Image names that have at least one rejected prediction box."""
    raw = live.get("rejected") if isinstance(live, dict) else None
    if not isinstance(raw, dict):
        return set()
    names = set()
    for key, items in raw.items():
        if not isinstance(items, list):
            continue
        kept = False
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("brand") or item.get("tpoint") or item.get("x") is not None or item.get("width") is not None:
                kept = True
                break
        if not kept:
            continue
        name = norm_name(key if isinstance(key, str) else "")
        if name:
            names.add(name)
    return names


def hard_negative_rels(frames: list[Frame], live) -> set[str]:
    """Reviewed frames the user rejected a prediction on.

    A rejection on a frame that is not in ``reviewed`` is ignored. The boxes
    themselves are not labels; the frame is a hard negative.
    """
    reviewed = reviewed_names(live) if isinstance(live, dict) else []
    rejected = rejection_names(live)
    if not reviewed or not rejected:
        return set()
    rels = set()
    for frame in frames:
        if any(name_hits_frame(name, frame) for name in reviewed) and any(
            name_hits_frame(name, frame) for name in rejected
        ):
            rels.add(frame.rel)
    return rels


def place_hard_negatives(train: list[Frame], val: list[Frame], hard_rels: set[str]):
    """Keep hard negatives in train so the extra copies do not also sit in val.

    The one-frame dataset already shares its only image between the splits.
    """
    if len(train) == 1 and len(val) == 1 and train[0].rel == val[0].rel:
        return list(train), list(val)
    train = list(train)
    train_rels = {frame.rel for frame in train}
    moving = [frame for frame in val if frame.rel in hard_rels]
    staying = [frame for frame in val if frame.rel not in hard_rels]
    if not moving:
        return train, list(val)
    if staying:
        for frame in moving:
            if frame.rel not in train_rels:
                train.append(frame)
                train_rels.add(frame.rel)
        return train, staying
    if len(moving) > 1:
        for frame in moving[1:]:
            if frame.rel not in train_rels:
                train.append(frame)
                train_rels.add(frame.rel)
        return train, moving[:1]
    return train, moving


def restore_val_positive(train: list[Frame], val: list[Frame], by_rel: dict, hard_rels: set[str]):
    """Put one ordinary positive in val after hard negatives have been moved to train."""
    if any(by_rel.get(frame.rel) for frame in val):
        return train, val
    donor = next((frame for frame in train if by_rel.get(frame.rel) and frame.rel not in hard_rels), None)
    if donor is None:
        return train, val
    val = list(val)
    if donor not in val:
        val.append(donor)
    if len(train) > 1:
        train = [frame for frame in train if frame.rel != donor.rel]
    return train, val


def blocked_rels(frames: list[Frame], names: list[str], images: dict) -> set[str]:
    rels = set(annotated_rels(frames, images))
    for frame in frames:
        if any(name_hits_frame(name, frame) for name in names):
            rels.add(frame.rel)
    return rels


def _write_yolo_dataset(work: Path, examples: list, classes: list[str], hard_rels: set[str], val_fraction: float) -> dict:
    by_rel = {frame.rel: boxes for frame, boxes in examples}
    train_frames, val_frames = place_hard_negatives(*split_examples(examples, val_fraction), hard_rels)
    train_frames, val_frames = restore_val_positive(train_frames, val_frames, by_rel, hard_rels)
    dataset = work / "dataset"
    if dataset.exists():
        shutil.rmtree(dataset)
    counts = Counter()
    written = {"train": 0, "val": 0}
    for split, split_frames in ("train", train_frames), ("val", val_frames):
        image_dir = dataset / "images" / split
        label_dir = dataset / "labels" / split
        for frame in split_frames:
            copies = HARD_NEGATIVE_COPIES if split == "train" and frame.rel in hard_rels else 1
            lines = []
            for name, (xc, yc, bw, bh) in by_rel[frame.rel]:
                lines.append(f"{classes.index(name)} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")
            text = "".join(lines)
            for copy in range(copies):
                filename = dataset_filename(frame, copy)
                counts[place_image(frame.path, image_dir / filename)] += 1
                label_path = label_dir / f"{Path(filename).stem}.txt"
                label_path.parent.mkdir(parents=True, exist_ok=True)
                label_path.write_text(text, encoding="utf-8")
                written[split] += 1
    yaml_path = dataset / "data.yaml"
    write_data_yaml(yaml_path, dataset, classes)
    boxes = sum(len(items) for _frame, items in examples)
    negatives = sum(1 for _frame, items in examples if not items)
    hard_count = sum(1 for frame, _boxes in examples if frame.rel in hard_rels)
    LOG.info(
        "dataset train=%s val=%s boxes=%s negatives=%s hard_negatives=%s classes=%s (%s)",
        written["train"],
        written["val"],
        boxes,
        negatives,
        hard_count,
        len(classes),
        ", ".join(classes),
    )
    if counts["copy"]:
        LOG.info("copied %s frames into the dataset (hard link unavailable)", counts["copy"])
    return {
        "train_images": written["train"],
        "val_images": written["val"],
        "boxes": boxes,
        "negatives": negatives,
        "hard_negative_frames": hard_count,
        "data_yaml": yaml_path,
    }


def build_dataset(work: Path, frames: list[Frame], live: dict, saved_classes: list[str], val_fraction: float) -> dict:
    names = reviewed_names(live)
    chosen, unmatched = match_reviewed(frames, names)
    if unmatched:
        LOG.warning("reviewed names with no jpg (%s): %s", len(unmatched), ", ".join(unmatched[:8]))
    if not chosen:
        raise DatasetError("none of the reviewed names matched a jpg in the frames folder")
    images = live_images(live)
    dominant = dominant_canvas(images)
    examples = []
    found = set()
    skipped = 0
    for frame in chosen:
        entry = live_entry_for(images, frame)
        try:
            img_w, img_h = image_size(frame.path)
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            LOG.warning("skip unreadable frame %s: %s", frame.rel, exc)
            skipped += 1
            continue
        canvas = None
        if isinstance(entry, dict):
            canvas = positive_size(entry.get("width"), entry.get("height"))
        if canvas is None:
            canvas = dominant or (img_w, img_h)
        boxes = []
        for brand, tpoint, start, diag in usable_annotations(entry):
            yolo = canvas_box_to_yolo(start, diag, canvas[0], canvas[1], img_w, img_h)
            if yolo is None:
                skipped += 1
                LOG.warning("skip box on %s (empty after scaling onto the image)", frame.rel)
                continue
            name = class_name(brand, tpoint)
            boxes.append((name, yolo))
            found.add(name)
        examples.append((frame, boxes))
    if not examples:
        raise DatasetError("reviewed frames could not be read")
    if not found:
        raise DatasetError("reviewed frames have no usable logo boxes")
    classes, new_names = extend_classes(saved_classes, found)
    hard_rels = hard_negative_rels([frame for frame, _boxes in examples], live)
    written = _write_yolo_dataset(work, examples, classes, hard_rels, val_fraction)
    written.update(
        {
            "classes": classes,
            "new_names": new_names,
            "unmatched": unmatched,
            "skipped": skipped,
        }
    )
    return written


def _unique_family_rel(project: str, rel: str, used: set[str], shared: set[str]) -> str:
    candidate = f"{project_dirname(project)}__{rel}" if rel in shared else rel
    if candidate not in used:
        return candidate
    stem = f"{project_dirname(project)}__{rel}"
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}__{suffix}"
        suffix += 1
    return candidate


def build_family_dataset(
    work: Path,
    work_root: Path,
    family: str,
    project: str,
    frames_folder,
    frames: list[Frame],
    live: dict,
    val_fraction: float,
    limit: int,
    dataset_dir: Path | None = None,
) -> dict | None:
    """Train/val from every project stored for ``family``.

    Returns None when the union has no logo boxes. The current project's empty
    reviewed frames stay in the index, but they do not block the other projects.
    """
    index = remember_project(work_root, family, project, work, frames_folder, frames, live)
    index = backfill_family_projects(work_root, family, index)
    rows = family_example_rows(index)
    if not any(row["boxes"] for row in rows):
        return None
    found = {name for row in rows for name, _coords in row["boxes"]}
    classes, new_names = extend_classes(list(index.get("classes") or []), found)
    if classes != list(index.get("classes") or []):
        index["classes"] = classes
        save_family_index(work_root, family, index)
    chosen = sample_family_examples(rows, int(limit))
    if len(chosen) < len(rows):
        LOG.info("family %s sampled %s of %s images (cap %s)", family, len(chosen), len(rows), limit)
    rel_counts = Counter(row["rel"] for row in chosen)
    shared = {rel for rel, count in rel_counts.items() if count > 1}
    used = set()
    examples = []
    hard_rels = set()
    for row in chosen:
        rel = _unique_family_rel(row["project"], row["rel"], used, shared)
        used.add(rel)
        frame = Frame(path=row["path"], rel=rel, stem=Path(row["rel"]).stem)
        examples.append((frame, row["boxes"]))
        if row["hard_negative"]:
            hard_rels.add(rel)
    written = _write_yolo_dataset(dataset_dir or work, examples, classes, hard_rels, val_fraction)
    written.update(
        {
            "classes": classes,
            "new_names": new_names,
            "unmatched": [],
            "skipped": len(rows) - len(chosen),
            "family_images": len(rows),
            "projects": len(index.get("projects") or {}),
        }
    )
    return written


def weight_phrase(weight_kind: str) -> str:
    if weight_kind == "finetune":
        return "βελτίωση"
    if weight_kind == "init":
        return "από τα βάρη εκκίνησης"
    return "από τα βασικά βάρη"


def per_class_ap50(trainer, class_names: list[str]) -> dict:
    """AP50 per class from the epoch that just finished. Missing classes are omitted."""
    validator = getattr(trainer, "validator", None)
    metrics = getattr(validator, "metrics", None) if validator is not None else None
    box = getattr(metrics, "box", None) if metrics is not None else None
    if box is None:
        return {}
    ap50 = getattr(box, "ap50", None)
    if ap50 is None:
        return {}
    try:
        values = list(ap50)
    except TypeError:
        return {}
    indices = getattr(box, "ap_class_index", None)
    if indices is None or len(list(indices)) == 0:
        indices = list(range(len(values)))
    else:
        indices = list(indices)
    found = {}
    for index, value in zip(indices, values):
        number = as_float(value)
        if number is None:
            continue
        try:
            class_index = int(index)
        except (TypeError, ValueError):
            continue
        if 0 <= class_index < len(class_names):
            name = class_names[class_index]
        else:
            name = str(class_index)
        found[name] = round(number, 4)
    return found


def make_epoch_callback(
    status: Status,
    cycle: int,
    total_epochs: int,
    holder: dict,
    from_base: bool,
    weight_kind: str,
    classes: list[str],
    status_state: str = "training",
    message_fn=None,
):
    kind = weight_phrase(weight_kind)

    def on_fit_epoch_end(trainer):
        try:
            epoch = min(int(getattr(trainer, "epoch", 0)) + 1, int(total_epochs))
            map50 = metric_from_trainer(trainer, "metrics/mAP50(B)")
            fit = as_float(getattr(trainer, "fitness", None))
            if fit is None:
                fit = metric_from_trainer(trainer, "metrics/mAP50-95(B)")
            if map50 is not None:
                score = fit if fit is not None else map50
                if holder["score"] is None or score >= holder["score"]:
                    holder["score"] = score
                    holder["map50"] = round(map50, 4)
                    holder["per_class"] = per_class_ap50(trainer, classes)
            if message_fn is not None:
                message = message_fn(epoch, total_epochs)
            else:
                message = f"Εκπαίδευση κύκλου {cycle} · epoch {epoch}/{total_epochs} · {kind}"
            fields = dict(
                state=status_state,
                cycle=cycle,
                epoch=epoch,
                epochs=total_epochs,
                last_map50=holder["map50"],
                from_base=from_base,
                message=message,
            )
            if holder.get("per_class"):
                fields["per_class_map50"] = holder["per_class"]
            status.update(**fields)
            LOG.info(
                "cycle %s epoch %s/%s mAP50=%s",
                cycle,
                epoch,
                total_epochs,
                holder["map50"] if holder["map50"] is not None else "n/a",
            )
        except Exception:
            LOG.exception("status update during training failed")

    return on_fit_epoch_end


MIN_TRAIN_BATCH = 1


def is_cuda_oom(exc: BaseException) -> bool:
    """True for torch CUDA OOM, AcceleratorError, or a RuntimeError that says so."""
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = type(current).__name__
        text = str(current).lower()
        if name in {"OutOfMemoryError", "AcceleratorError"} and ("out of memory" in text or name == "OutOfMemoryError"):
            return True
        if isinstance(current, RuntimeError) and "out of memory" in text:
            return True
        cause = current.__cause__
        context = current.__context__
        current = cause if cause is not None else context
    return False


def release_cuda_cache():
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        LOG.debug("cuda cache clear failed", exc_info=True)


def shrink_after_oom(args) -> str:
    """Halve the train batch, then drop dataloader workers. Image size stays as it is."""
    if int(args.batch) > MIN_TRAIN_BATCH:
        args.batch = max(MIN_TRAIN_BATCH, int(args.batch) // 2)
        return f"batch {args.batch}"
    if int(args.workers) > 0:
        args.workers = 0
        return "workers 0"
    return ""


def chunk_items(items, size: int) -> list[list]:
    step = max(1, int(size))
    return [list(items[i : i + step]) for i in range(0, len(items), step)]


def shrink_predict_batch(args) -> str:
    """Halve how many images one ``model.predict`` call sees. Does not change the train batch."""
    current = int(getattr(args, "predict_batch", 4) or 4)
    if current <= 1:
        return ""
    args.predict_batch = max(1, current // 2)
    return f"predict-batch {args.predict_batch}"


def predict_uses_half(device: str) -> bool:
    """FP16 activations on CUDA only. CPU, including the tests, stays FP32."""
    text = str(device or "").strip().lower()
    if text == "cpu":
        return False
    if text in {"", "auto"}:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False
    return True


def enable_cuda_allocator():
    """Ask PyTorch to grow the caching allocator in expandable segments, before it is imported."""
    key = "PYTORCH_CUDA_ALLOC_CONF"
    current = os.environ.get(key, "")
    if "expandable_segments" in current:
        return
    token = "expandable_segments:True"
    os.environ[key] = f"{current},{token}" if current.strip() else token
    LOG.info("%s=%s", key, os.environ[key])


def call_with_oom_retry(status: Status, args, action, phase: str):
    """Run ``action``. On CUDA OOM, wait, shrink, and try again.

    A successful attempt clears ``last_error``. ``imgsz`` is not changed.
    The reduced batch and worker count stay on ``args`` for later cycles.
    """
    while True:
        try:
            return action()
        except Exception as exc:
            if not is_cuda_oom(exc):
                raise
            change = shrink_after_oom(args)
            release_cuda_cache()
            if not change:
                raise
            wait = max(0.0, float(getattr(args, "oom_wait", 45)))
            note = f"CUDA out of memory; retrying with {change}"
            LOG.warning("%s during %s (%s). Waiting %.0fs, then %s", type(exc).__name__, phase, exc, wait, change)
            if status is not None:
                status.update(
                    state="waiting_gpu",
                    last_error=note,
                    message=f"Αναμονή GPU · εξαντλήθηκε η μνήμη · επανάληψη με {change}",
                )
            if wait:
                time.sleep(wait)
            release_cuda_cache()


def cuda_device_index(device: str) -> int | None:
    text = str(device or "").strip().lower()
    if text == "cpu":
        return None
    if text in {"", "cuda"}:
        return 0
    if text.isdigit():
        return int(text)
    if text.startswith("cuda:"):
        tail = text.split(":", 1)[1]
        return int(tail) if tail.isdigit() else 0
    return 0


def cuda_free_mb(device: str) -> float | None:
    if str(device or "").strip().lower() == "cpu":
        return None
    index = cuda_device_index(device)
    try:
        import torch

        if not torch.cuda.is_available():
            return None
        if index is None:
            index = torch.cuda.current_device()
        free, _total = torch.cuda.mem_get_info(index)
        return free / (1024 * 1024)
    except Exception:
        LOG.debug("free vram query failed", exc_info=True)
        return None


def gpu_memory_message(args, free_mb: float | None = None) -> str | None:
    """Greek status line when free VRAM is under ``--min-free-vram-mb``. None when it is fine."""
    minimum = float(getattr(args, "min_free_vram_mb", 0) or 0)
    if minimum <= 0 or str(getattr(args, "device", "") or "").strip().lower() == "cpu":
        return None
    if free_mb is None:
        free_mb = cuda_free_mb(getattr(args, "device", ""))
    if free_mb is None or free_mb >= minimum:
        return None
    return f"Αναμονή GPU · ελεύθερα {free_mb:.0f} MB, χρειάζονται {minimum:.0f} MB"


def wait_out_gpu(args, status: Status) -> bool:
    """Publish ``waiting_gpu`` and sleep when another job is holding the card. True means skip this pass."""
    message = gpu_memory_message(args)
    if not message:
        return False
    status.update(state="waiting_gpu", message=message)
    LOG.info("%s", message)
    time.sleep(max(float(args.poll_seconds), float(getattr(args, "oom_wait", 0) or 0)))
    return True


def limit_gpu_memory(fraction: float, device: str):
    """Cap this process with ``torch.cuda.set_per_process_memory_fraction``. 0 disables it."""
    if fraction <= 0 or str(device or "").strip().lower() == "cpu":
        return
    if fraction > 1:
        return
    index = cuda_device_index(device)
    try:
        import torch

        if not torch.cuda.is_available():
            return
        if index is None:
            index = torch.cuda.current_device()
        torch.cuda.set_device(index)
        torch.cuda.set_per_process_memory_fraction(float(fraction), index)
        LOG.info("gpu memory fraction %.2f on cuda:%s", fraction, index)
    except Exception as exc:
        LOG.warning("could not set gpu memory fraction: %s", exc)


def lower_process_priority():
    """Below-normal priority on Windows so the browser stays responsive. No-op elsewhere."""
    if os.name != "nt":
        return
    try:
        import psutil

        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        LOG.info("process priority set to below normal")
        return
    except Exception:
        LOG.debug("psutil priority was not set", exc_info=True)
    try:
        import ctypes

        below_normal = 0x00004000
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if not ctypes.windll.kernel32.SetPriorityClass(handle, below_normal):
            LOG.warning("SetPriorityClass failed")
        else:
            LOG.info("process priority set to below normal")
    except Exception as exc:
        LOG.warning("could not lower process priority: %s", exc)


def train_model(
    model,
    args,
    data_yaml: Path,
    epochs: int,
    cycle: int,
    work: Path,
    status: Status,
    from_base: bool,
    weight_kind: str,
    classes: list[str],
    status_state: str = "training",
    message_fn=None,
):
    holder = {"score": None, "map50": None, "per_class": {}}
    model.add_callback(
        "on_fit_epoch_end",
        make_epoch_callback(
            status,
            cycle,
            epochs,
            holder,
            from_base,
            weight_kind,
            classes,
            status_state=status_state,
            message_fn=message_fn,
        ),
    )
    run_dir = work / "runs" / f"cycle_{cycle}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    kind = {"finetune": "previous best.pt", "init": "init weights", "base": "base weights"}.get(weight_kind, weight_kind)

    def train_once():
        if run_dir.exists():
            shutil.rmtree(run_dir)
        LOG.info(
            "training cycle %s from %s for %s epochs imgsz=%s batch=%s workers=%s",
            cycle,
            kind,
            epochs,
            args.imgsz,
            args.batch,
            args.workers,
        )
        if message_fn is not None:
            opening = message_fn(0, epochs)
        else:
            opening = f"Εκπαίδευση κύκλου {cycle} · epoch 0/{epochs} · {weight_phrase(weight_kind)}"
        status.update(
            state=status_state,
            cycle=cycle,
            epoch=0,
            epochs=epochs,
            from_base=from_base,
            last_error=None,
            message=opening,
        )
        train_kwargs = {
            "data": str(data_yaml),
            "epochs": epochs,
            "imgsz": args.imgsz,
            "batch": args.batch,
            "workers": args.workers,
            "amp": bool(args.amp),
            "project": str((work / "runs").resolve()),
            "name": f"cycle_{cycle}",
            "exist_ok": True,
            "patience": args.patience,
            "pretrained": True,
            "plots": False,
            "save": True,
            "val": True,
            "cache": False,
            "verbose": True,
            "seed": 0,
            "deterministic": False,
            "resume": False,
            # ultralytics treats optimizer=auto as "ignore lr0". Set it so the documented rates apply.
            "optimizer": "SGD" if from_base else "AdamW",
            "lr0": args.lr0 if args.lr0 is not None else (0.01 if from_base else 0.001),
            "close_mosaic": 0 if epochs < 5 else max(1, epochs // 5),
        }
        if args.device:
            train_kwargs["device"] = args.device
        model.train(**train_kwargs)

    call_with_oom_retry(status, args, train_once, "training")
    trainer = getattr(model, "trainer", None)
    save_dir = Path(getattr(trainer, "save_dir", run_dir))
    best = save_dir / "weights" / "best.pt"
    if not best.is_file():
        best = save_dir / "weights" / "last.pt"
    if not best.is_file():
        raise FileNotFoundError(f"training finished without a checkpoint in {save_dir}")
    stable = work / "best.pt"
    shutil.copy2(best, stable)
    measured = None
    if holder["map50"] is not None:
        measured = holder["map50"]
    if measured is None:
        measured = best_map50_from_csv(save_dir / "results.csv")
    if not holder["per_class"] and trainer is not None:
        holder["per_class"] = per_class_ap50(trainer, classes)
    return stable, measured, save_dir, holder["per_class"]


def load_training_model(
    YOLO,
    base: Path,
    previous: Path | None,
    classes: list[str],
    new_names: list[str],
    init: Path | None = None,
    prefer_finetune: bool = False,
):
    """Return (model, from_base, weight_kind).

    ``weight_kind`` is ``finetune``, ``init``, or ``base``. ``prefer_finetune``
    keeps the checkpoint when the family class list grew; new names are appended
    and old ids stay put. ``--init-weights`` is used only when this project has
    no checkpoint and no family weights.
    """
    if previous and Path(previous).is_file() and (prefer_finetune or wants_finetune(previous, new_names)):
        model = YOLO(str(previous))
        names = model_class_names(model)
        if prefer_finetune or names == list(classes):
            LOG.info("fine-tuning %s", previous)
            return model, False, "finetune"
        LOG.warning("checkpoint classes %s differ from %s; retraining from base weights", names, classes)
    elif new_names and previous and Path(previous).is_file():
        LOG.info("new classes (%s); training from base weights", ", ".join(new_names))
    fresh = previous is None or not Path(previous).is_file()
    if fresh and init is not None and Path(init).is_file():
        LOG.info("training first cycle from init weights %s", init)
        return YOLO(str(init)), True, "init"
    LOG.info("training from base weights %s", base)
    return YOLO(str(base)), True, "base"


def canvas_for_frame(images: dict, frame: Frame, dominant, fallback):
    entry = live_entry_for(images, frame)
    if isinstance(entry, dict):
        size = positive_size(entry.get("width"), entry.get("height"))
        if size:
            return size
    if dominant:
        return dominant
    return fallback


def boxes_from_result(result, frame: Frame, canvas, key: str, index: int):
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return None
    orig_h, orig_w = result.orig_shape
    names = result.names or {}
    xyxy = boxes.xyxy.detach().cpu().tolist()
    confs = boxes.conf.detach().cpu().tolist()
    clss = boxes.cls.detach().cpu().tolist()
    order = sorted(range(len(confs)), key=lambda i: confs[i], reverse=True)
    annotations = []
    for i in order:
        class_index = int(clss[i])
        if isinstance(names, dict):
            raw = names.get(class_index, names.get(str(class_index), str(class_index)))
        else:
            raw = names[class_index]
        brand, tpoint = split_class(str(raw))
        x1, y1, x2, y2 = xyxy[i]
        corners = xyxy_to_canvas(x1, y1, x2, y2, orig_w, orig_h, canvas[0], canvas[1])
        if corners is None:
            continue
        start, diag = corners
        annotations.append(detection_annotation(brand, tpoint, start, diag, confs[i]))
    if not annotations:
        return None
    return prediction_image(key, index, canvas[0], canvas[1], annotations)


def predict_frames(model, args, live, frames, work: Path, coverage: str = "window", status: Status | None = None):
    frames = list(frames)
    captured_project = getattr(args, "bound_project", None) or project_name(live)
    if isinstance(captured_project, str):
        captured_project = captured_project.strip() or None
    reject_if_project_changed(args.sync_folder, captured_project)
    images = live_images(live)
    names = reviewed_names(live)
    blocked = blocked_rels(frames, names, images)
    current = current_name(live)
    current_index = find_current_index(frames, current)
    if current and current_index < 0:
        LOG.warning("currentImage %s is not in the frames folder; predicting from the start", current)
    stems_unique = len({frame.stem for frame in frames}) == len(frames)
    chosen = select_predict_frames(
        frames, current_index, args.predict_margin, args.lookahead, blocked, coverage=coverage
    )
    LOG.info(
        "predict window current=%s index=%s margin=%s chosen=%s first=%s last=%s batch=%s",
        current,
        current_index,
        args.predict_margin,
        len(chosen),
        chosen[0].rel if chosen else None,
        chosen[-1].rel if chosen else None,
        int(getattr(args, "predict_batch", 4) or 4),
    )
    pred_path = args.sync_folder / PRED_NAME
    dominant = dominant_canvas(images)
    by_path = {frame.path.resolve(): frame for frame in chosen}

    def persist(replaced_keys: set[str], images_out: dict):
        old = {}
        if pred_path.is_file():
            old_doc = read_json(pred_path)
            if isinstance(old_doc.get("images"), dict):
                old = old_doc["images"]
        merged = merge_prediction_images(old, images_out, replaced_keys, frames, current_index, blocked)
        return commit_predictions(args.sync_folder, captured_project, live, merged)

    def predict_chunk(chunk: list[Frame]):
        """One ``model.predict`` call. The result stream is consumed here so an OOM retries this chunk."""
        found = {}
        predict_kwargs = {
            "source": [str(frame.path) for frame in chunk],
            "conf": args.conf,
            "iou": args.iou,
            "agnostic_nms": True,
            "imgsz": args.imgsz,
            "verbose": False,
            "stream": True,
            "save": False,
            "show": False,
            "save_txt": False,
            "save_conf": False,
            "workers": args.workers,
            "batch": max(1, len(chunk)),
            "cache": False,
            "project": str((work / "predict").resolve()),
            "name": "latest",
            "exist_ok": True,
        }
        if args.device:
            predict_kwargs["device"] = args.device
        if predict_uses_half(getattr(args, "device", "")):
            predict_kwargs["half"] = True
        results = model.predict(**predict_kwargs)
        seen = 0
        for result in results:
            seen += 1
            frame = by_path.get(Path(result.path).resolve())
            if frame is None:
                LOG.warning("predict result for an unexpected file: %s", result.path)
                continue
            orig_h, orig_w = result.orig_shape
            canvas = canvas_for_frame(images, frame, dominant, (int(orig_w), int(orig_h)))
            key = prediction_key(frame, stems_unique)
            index = find_current_index(frames, frame.rel)
            entry = boxes_from_result(result, frame, canvas, key, index if index >= 0 else 0)
            if entry:
                before = len(entry["annotations"])
                kept = suppress_contained(entry["annotations"], float(getattr(args, "contain", 0.6)))
                if len(kept) < before:
                    LOG.info(
                        "containment dropped %s of %s boxes on %s",
                        before - len(kept),
                        before,
                        frame.rel,
                    )
                if kept:
                    entry["annotations"] = kept
                    found[key] = entry
        if seen != len(chunk):
            LOG.warning("model returned %s results for %s frames", seen, len(chunk))
        return found

    new_images = {}
    done_keys: set[str] = set()
    total = len(chosen)
    cursor = 0
    if chosen and status is not None:
        status.update(
            state="predicting",
            predicted_frames=0,
            predict_total=total,
            last_error=None,
            message=f"Προβλέψεις σε εξέλιξη, περίμενε… (0/{total})",
        )
    while cursor < total:
        batch = max(1, int(getattr(args, "predict_batch", 4) or 4))
        chunk = chosen[cursor : cursor + batch]
        try:
            found = predict_chunk(chunk)
        except Exception as exc:
            if not is_cuda_oom(exc):
                raise
            change = shrink_predict_batch(args)
            release_cuda_cache()
            if not change:
                raise
            wait = max(0.0, float(getattr(args, "oom_wait", 45)))
            note = f"CUDA out of memory; retrying with {change}"
            LOG.warning("%s during predict (%s). Waiting %.0fs, then %s", type(exc).__name__, exc, wait, change)
            if status is not None:
                status.update(
                    state="waiting_gpu",
                    last_error=note,
                    predict_total=total,
                    message=f"Αναμονή GPU · εξαντλήθηκε η μνήμη · επανάληψη με {change}",
                )
            if wait:
                time.sleep(wait)
            release_cuda_cache()
            continue
        for frame in chunk:
            done_keys.add(prediction_key(frame, stems_unique))
        new_images.update(found)
        cursor += len(chunk)
        merged = persist(done_keys, new_images)
        if status is not None:
            status.update(
                state="predicting",
                predicted_frames=cursor,
                predict_total=total,
                last_error=None,
                message=f"Προβλέψεις σε εξέλιξη, περίμενε… ({cursor}/{total})",
            )
        LOG.info("predict chunk %s/%s", cursor, total)
    if not chosen:
        merged = persist(set(), {})
    start, end = prediction_span(merged, frames)
    LOG.info("wrote %s frames=%s from=%s to=%s", pred_path, len(merged), start, end)
    return len(merged), start, end


def weights_for_predict(args, state: dict) -> Path | None:
    """Family library weights when this project continues that model, else the project file."""
    if state.get("model_mode") == "συνέχεια" and state.get("model_family") and getattr(args, "work_root", None):
        family = family_weights_path(args.work_root, state["model_family"])
        if family.is_file():
            return family
    return resolve_weights(state, args.work_dir)


def finish_predict(args, state: dict, status: Status, frames_index: FrameIndex):
    weights = weights_for_predict(args, state)
    if weights is None or not weights.is_file():
        raise ConfigError("no trained weights to predict with")
    status.update(
        state="predicting",
        cycle=int(state["cycle"]),
        weights=str(weights),
        message=f"Προβλέψεις κύκλου {state['cycle']}",
    )
    live = read_json(args.sync_folder / LIVE_NAME)
    frames = list(frames_index.get(force=True))
    YOLO = yolo_class()
    model = YOLO(str(weights))
    try:
        count, start, end = predict_frames(model, args, live, frames, args.work_dir, status=status)
    except PredictionDiscarded:
        return 0, None, None
    state["pending_predict"] = False
    state["last_error"] = None
    save_state(args.work_dir / STATE_NAME, state)
    publish_idle(
        status,
        state,
        live,
        frames,
        args.sync_folder / PRED_NAME,
        args.work_dir,
        project=getattr(args, "bound_project", None),
        frames_folder=getattr(args, "bound_frames", None),
        work_root=getattr(args, "work_root", None),
    )
    status.update(predicted_frames=count, predicted_from=start, predicted_to=end)
    return count, start, end


def cycle_start_weights(args, state: dict) -> tuple[Path | None, bool]:
    """Return (checkpoint, prefer_finetune) for this cycle.

    A family in ``συνέχεια`` fine-tunes that family's ``best.pt`` on every cycle,
    including after this project already has its own checkpoint. ``νέο`` keeps
    using this project's ``best.pt`` once the first cycle has written it.
    """
    if state.get("model_mode") == "συνέχεια" and state.get("model_family"):
        family = family_weights_path(args.work_root, state["model_family"])
        if family.is_file():
            return family, True
    own = resolve_weights(state, args.work_dir)
    if own and own.is_file() and int(state["cycle"]) > 0:
        return own, True
    return None, False


def seed_family_predictions(args, state: dict, status: Status, frames_index: FrameIndex):
    """Predict every unannotated frame from the family model, before any training."""
    family = state.get("model_family") or ""
    weights = family_weights_path(args.work_root, family)
    status.update(
        state="predicting",
        cycle=int(state["cycle"]),
        weights=str(weights),
        model_family=family,
        model_mode="συνέχεια",
        ready_for_user=False,
        predict_total=None,
        message=f"Προβλέψεις από την οικογένεια {family}, πριν την εκπαίδευση",
    )
    live = read_json(args.sync_folder / LIVE_NAME)
    frames = list(frames_index.get(force=True))
    YOLO = yolo_class()
    model = YOLO(str(weights))
    try:
        count, start, end = predict_frames(model, args, live, frames, args.work_dir, coverage="all", status=status)
    except PredictionDiscarded:
        return 0, None, None
    stamp = weights_stamp(weights) or {}
    state["seeded_family"] = family
    state["seeded_weights"] = {"family": family, **stamp}
    state["pending_predict"] = False
    state["last_error"] = None
    save_state(args.work_dir / STATE_NAME, state)
    publish_idle(
        status,
        state,
        live,
        frames,
        args.sync_folder / PRED_NAME,
        args.work_dir,
        project=getattr(args, "bound_project", None),
        frames_folder=getattr(args, "bound_frames", None),
        work_root=getattr(args, "work_root", None),
    )
    status.update(
        predicted_frames=count,
        predicted_from=start,
        predicted_to=end,
        weights=str(weights),
        ready_for_user=True,
    )
    return count


def needs_family_seed(state: dict, work_root: Path | None = None) -> bool:
    """True when this project has not been predicted with the current family ``best.pt``.

    The stamp is mtime, size, and sha1. A family name alone is not enough: a
    newer library file (another project promoted it, or this process just
    unified the family) is seeded again. Cycle count does not block that.
    """
    if state.get("model_mode") != "συνέχεια":
        return False
    family = state.get("model_family")
    if not family or work_root is None:
        return False
    weights = family_weights_path(work_root, family)
    if not weights.is_file():
        return False
    stored = state.get("seeded_weights")
    if not isinstance(stored, dict) or stored.get("family") != family or not stored.get("sha1"):
        return True
    st = weights.stat()
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    if int(stored.get("mtime_ns") or -1) == int(mtime_ns) and int(stored.get("size") or -1) == int(st.st_size):
        return False
    current = weights_stamp(weights)
    return not current or current.get("sha1") != stored.get("sha1")


def train_family_union(args, state: dict, status: Status, live: dict, frames: list[Frame]) -> bool:
    """Train one family checkpoint that contains every class, before any prediction.

    The project's cycle counter is not advanced. The dataset is written under
    ``models/<family>/unify/`` so the open project's ``dataset/`` stays put.
    Fine-tune the library ``best.pt`` when its logo classes are a subset of the
    union; otherwise start from ``--base-weights``.
    """
    family = state.get("model_family") or ""
    if not family:
        return False
    project = getattr(args, "bound_project", None) or project_name(live) or "_default"
    limit = int(getattr(args, "max_family_images", FAMILY_IMAGE_CAP) or FAMILY_IMAGE_CAP)
    unify_dir = family_dir(args.work_root, family) / "unify"
    status.update(
        state="training_family",
        ready_for_user=False,
        model_family=family,
        model_mode=state.get("model_mode"),
        predict_total=None,
        last_error=None,
        message=FAMILY_UNIFY_MESSAGE,
    )
    built = build_family_dataset(
        args.work_dir,
        args.work_root,
        family,
        project,
        getattr(args, "bound_frames", None),
        frames,
        live,
        args.val_fraction,
        limit,
        dataset_dir=unify_dir,
    )
    if built is None:
        LOG.info("family %s has no logo boxes to unify", family)
        return False
    weights_path = family_weights_path(args.work_root, family)
    prefer = state.get("model_choice") != "new" and family_finetune_ok(weights_path, built["classes"])
    previous = weights_path if prefer else None
    YOLO = yolo_class()
    model, from_base, weight_kind = load_training_model(
        YOLO,
        args.base_weights,
        previous,
        built["classes"],
        built["new_names"],
        None,
        prefer_finetune=prefer,
    )
    epochs = args.finetune_epochs if weight_kind == "finetune" else args.epochs
    weights, map50, _save_dir, per_class = train_model(
        model,
        args,
        built["data_yaml"],
        epochs,
        int(state["cycle"]),
        unify_dir,
        status,
        from_base,
        weight_kind,
        built["classes"],
        status_state="training_family",
        message_fn=family_epoch_message,
    )
    index = load_family_index(args.work_root, family)
    promoted = maybe_update_family(
        args.work_root,
        family,
        weights,
        map50,
        per_class,
        built["classes"],
        dataset_signature=family_dataset_signature(index),
    )
    if not promoted:
        raise ConfigError(f"family {family} model was not promoted; it does not contain every family class")
    LOG.info("family %s unified classes=%s", family, ", ".join(built["classes"]))
    return True


def run_cycle(args, state: dict, status: Status, frames_index: FrameIndex, live: dict):
    frames = frames_index.get(force=True)
    snapshot = len(reviewed_names(live))
    upcoming = int(state["cycle"]) + 1
    status.update(
        state="training",
        cycle=upcoming,
        epoch=0,
        epochs=None,
        model_family=state.get("model_family"),
        model_mode=state.get("model_mode"),
        message=f"Φτιάχνω dataset κύκλου {upcoming}",
        last_error=None,
    )
    family = state.get("model_family") or resolve_model_plan(live)["family"]
    project = getattr(args, "bound_project", None) or project_name(live) or "_default"
    limit = int(getattr(args, "max_family_images", FAMILY_IMAGE_CAP) or FAMILY_IMAGE_CAP)
    built = build_family_dataset(
        args.work_dir,
        args.work_root,
        family,
        project,
        getattr(args, "bound_frames", None),
        frames,
        live,
        args.val_fraction,
        limit,
    )
    if built is None:
        state["last_error"] = None
        save_state(args.work_dir / STATE_NAME, state)
        status.update(
            state="idle",
            last_error=None,
            cycle=int(state["cycle"]),
            model_family=family,
            model_mode=state.get("model_mode"),
            message=NO_BOXES_MESSAGE,
        )
        LOG.info("%s", NO_BOXES_MESSAGE)
        return False
    previous, prefer_finetune = cycle_start_weights(args, state)
    init = None if state.get("model_choice") == "new" else getattr(args, "init_weights", None)
    YOLO = yolo_class()
    model, from_base, weight_kind = load_training_model(
        YOLO,
        args.base_weights,
        previous,
        built["classes"],
        built["new_names"],
        init,
        prefer_finetune=prefer_finetune,
    )
    epochs = args.finetune_epochs if weight_kind == "finetune" else args.epochs
    weights, map50, _save_dir, per_class = train_model(
        model,
        args,
        built["data_yaml"],
        epochs,
        upcoming,
        args.work_dir,
        status,
        from_base,
        weight_kind,
        built["classes"],
    )
    state["cycle"] = upcoming
    state["classes"] = built["classes"]
    state["best_weights"] = weights.relative_to(args.work_dir).as_posix()
    if map50 is not None:
        state["last_map50"] = map50
    state["reviewed_at_cycle"] = snapshot
    state["pending_predict"] = True
    state["epoch"] = epochs
    state["epochs"] = epochs
    state["from_base"] = from_base
    state["train_images"] = built["train_images"]
    state["val_images"] = built["val_images"]
    state["hard_negative_frames"] = built["hard_negative_frames"]
    state["per_class_map50"] = dict(per_class or {})
    state["last_error"] = None
    if state.get("model_family"):
        signature = family_dataset_signature(load_family_index(args.work_root, state["model_family"]))
        promoted = maybe_update_family(
            args.work_root,
            state["model_family"],
            weights,
            state.get("last_map50"),
            state["per_class_map50"],
            built["classes"],
            dataset_signature=signature,
        )
        if promoted:
            family_path = family_weights_path(args.work_root, state["model_family"])
            stamp = weights_stamp(family_path) or {}
            state["seeded_family"] = state["model_family"]
            state["seeded_weights"] = {"family": state["model_family"], **stamp}
    fresh_index = load_family_index(args.work_root, family) if state.get("model_family") else {"classes": [], "projects": {}}
    state["class_labels_at_cycle"] = class_label_signatures(fresh_index)
    apply_cadence(args, state, fresh_index, snapshot)
    status.update(
        classes=built["classes"],
        last_map50=state["last_map50"],
        epoch=epochs,
        epochs=epochs,
        train_images=built["train_images"],
        val_images=built["val_images"],
        hard_negative_frames=built["hard_negative_frames"],
        model_family=state.get("model_family"),
        model_mode=state.get("model_mode"),
        per_class_map50=state["per_class_map50"],
        weights=str(weights),
        from_base=from_base,
        next_cycle_at=state["next_cycle_at"],
        reviewed_since_last_cycle=0,
        cadence=state.get("cadence"),
        every_now=state.get("every_now"),
        cadence_reason=state.get("cadence_reason"),
    )
    finish_predict(args, state, status, frames_index)
    return True


def validate_config(args):
    root = repo_root()
    args.sync_folder = args.sync_folder.expanduser().resolve()
    args.work_dir = args.work_dir.expanduser().resolve()
    args.work_root = args.work_dir
    args.base_weights = args.base_weights.expanduser().resolve()
    if args.frames_folder is not None:
        args.frames_folder = args.frames_folder.expanduser().resolve()
    roots = args.frames_root or [Path(r"D:\downloads")]
    args.frames_roots = []
    for path in roots:
        path = Path(path).expanduser()
        args.frames_roots.append(path.resolve() if path.exists() else path)
    if is_inside(args.sync_folder, root):
        raise ConfigError(f"sync folder must be outside the repository: {args.sync_folder}")
    if is_inside(args.work_dir, root):
        raise ConfigError(f"work dir must be outside the repository: {args.work_dir}")
    if args.work_dir == args.sync_folder or is_inside(args.work_dir, args.sync_folder):
        raise ConfigError("work-dir must not be inside the sync folder")
    if not args.sync_folder.is_dir():
        raise ConfigError(f"sync folder does not exist: {args.sync_folder}")
    if args.frames_folder is not None and not args.frames_folder.is_dir():
        raise ConfigError(f"frames folder does not exist: {args.frames_folder}")
    if not args.base_weights.is_file() or args.base_weights.stat().st_size < 1024:
        raise ConfigError(
            f"base weights not found: {args.base_weights}. Pass a local .pt file; weights are not downloaded."
        )
    if args.init_weights is not None:
        args.init_weights = args.init_weights.expanduser().resolve()
        if not args.init_weights.is_file() or args.init_weights.stat().st_size < 1024:
            raise ConfigError(
                f"init weights not found: {args.init_weights}. Pass a local .pt file; weights are not downloaded."
            )
    if args.imgsz % 32 != 0:
        raise ConfigError("--imgsz must be a multiple of 32")
    if args.every is not None and int(args.every) < 1:
        raise ConfigError("--every must be >= 1")
    if min(args.min_reviewed, args.every_young, args.every_mature, args.mature_frames, args.lookahead, args.epochs, args.finetune_epochs, args.batch) < 1:
        raise ConfigError("min-reviewed, every-young, every-mature, mature-frames, lookahead, epochs, finetune-epochs, and batch must be >= 1")
    if not 0 <= float(args.mature_map) <= 1:
        raise ConfigError("--mature-map must be between 0 and 1")
    if not 0 <= float(args.weak_class_map) <= 1:
        raise ConfigError("--weak-class-map must be between 0 and 1")
    if args.predict_margin < 0:
        raise ConfigError("--predict-margin must be >= 0")
    if args.frames_max_depth < 0:
        raise ConfigError("--frames-max-depth must be >= 0")
    if not 0 <= args.val_fraction <= 0.5:
        raise ConfigError("--val-fraction must be between 0 and 0.5")
    if not 0 <= args.contain <= 1:
        raise ConfigError("--contain must be between 0 and 1")
    if not 0 <= args.gpu_mem_fraction <= 1:
        raise ConfigError("--gpu-mem-fraction must be between 0 and 1")
    if args.min_free_vram_mb < 0:
        raise ConfigError("--min-free-vram-mb must be >= 0")
    if args.oom_wait < 0:
        raise ConfigError("--oom-wait must be >= 0")
    if args.workers < 0:
        raise ConfigError("--workers must be >= 0")
    if args.max_family_images < 1:
        raise ConfigError("--max-family-images must be >= 1")
    if int(getattr(args, "predict_batch", 4)) < 1:
        raise ConfigError("--predict-batch must be >= 1")
    args.poll_seconds = max(1.0, float(args.poll_seconds))
    args.work_dir.mkdir(parents=True, exist_ok=True)
    return args


def report_missing_frames(status: Status, live, error: str, min_reviewed: int):
    reviewed = len(reviewed_names(live)) if isinstance(live, dict) else 0
    project = project_name(live)
    count, start, end = summarize_predictions(status.path.parent / PRED_NAME, [])
    status.update(
        state="idle",
        project=project,
        frames_folder=None,
        cycle=0,
        reviewed=reviewed,
        reviewed_since_last_cycle=reviewed,
        next_cycle_at=int(min_reviewed),
        predicted_frames=count,
        predicted_from=start,
        predicted_to=end,
        classes=[],
        last_map50=None,
        epoch=None,
        epochs=None,
        last_error=error,
        current_image=current_name(live) if isinstance(live, dict) else None,
        weights=None,
        from_base=None,
        train_images=None,
        val_images=None,
        hard_negative_frames=0,
        model_family=resolve_model_plan(live)["family"] if isinstance(live, dict) else None,
        model_mode=None,
        per_class_map50={},
        message="Δεν βρέθηκαν καρέ" if project else "Λείπει το project",
    )


def run(args) -> int:
    configure_logging()
    install_signals()
    if os.name == "nt":
        import multiprocessing

        multiprocessing.freeze_support()
    enable_cuda_allocator()
    args = validate_config(args)
    lower_process_priority()
    limit_gpu_memory(float(args.gpu_mem_fraction), args.device)
    status = Status(
        args.sync_folder / STATUS_NAME,
        device=args.device or "auto",
        next_cycle_at=int(args.min_reviewed),
    )
    locator = None
    if args.frames_folder is None:
        locator = FrameLocator(
            args.frames_roots,
            args.work_root / "frames_cache.json",
            max_depth=args.frames_max_depth,
        )
    active = {"project": None, "frames": None, "work": None, "state": None, "index": None, "ready": False}
    LOG.info(
        "live trainer sync=%s frames=%s roots=%s depth=%s work=%s weights=%s device=%s workers=%s amp=%s",
        args.sync_folder,
        args.frames_folder or "(from project name)",
        ", ".join(str(root) for root in args.frames_roots),
        args.frames_max_depth,
        args.work_root,
        args.base_weights,
        args.device or "auto",
        args.workers,
        args.amp,
    )
    LOG.info(
        "thresholds first=%s every=%s young=%s mature=%s lookahead=%s margin=%s epochs=%s finetune_epochs=%s imgsz=%s",
        args.min_reviewed,
        args.every if args.every is not None else "adaptive",
        args.every_young,
        args.every_mature,
        args.lookahead,
        args.predict_margin,
        args.epochs,
        args.finetune_epochs,
        args.imgsz,
    )
    gave_retry = False
    parked_at = None
    parked_project = None
    last_idle_log = (None, 0.0)
    last_error_logged = None
    try:
        while True:
            live_path = args.sync_folder / LIVE_NAME
            if not live_path.is_file():
                status.update(
                    state="idle",
                    message="Αναμονή για annotool_live.json",
                    next_cycle_at=int(args.min_reviewed) if active["state"] is None else int(active["state"]["next_cycle_at"]),
                    cycle=0 if active["state"] is None else int(active["state"]["cycle"]),
                )
                LOG.info("waiting for %s", live_path)
                if args.once:
                    return 0
                time.sleep(args.poll_seconds)
                continue
            try:
                live = read_json(live_path)
            except ValueError as exc:
                status.update(state="idle", last_error=str(exc), message="Το annotool_live.json δεν διαβάζεται")
                LOG.warning("live file is not readable yet: %s", exc)
                if args.once:
                    return 1
                time.sleep(args.poll_seconds)
                continue

            ensure_predictions_project(args.sync_folder, live)
            if locator is not None:
                locator.on_search = lambda project, live=live: mark_searching(status, live, project)
            try:
                error = bind_project(live, args.frames_folder, locator, args.work_root, args.min_reviewed, active)
            except ConfigError:
                raise
            if error:
                report_missing_frames(status, live, error, args.min_reviewed)
                if error != last_error_logged:
                    LOG.error("%s", error)
                    last_error_logged = error
                if args.once:
                    return 1
                time.sleep(args.poll_seconds)
                continue

            last_error_logged = None
            if parked_project != active["project"]:
                parked_at = None
                gave_retry = False
                parked_project = active["project"]
            args.work_dir = active["work"]
            args.bound_project = active["project"]
            args.bound_frames = active["frames"]
            state = active["state"]
            frames_index = active["index"]
            assign_model_plan(state, live, args.work_root)

            reviewed_now = len(reviewed_names(live))
            if parked_at is not None and reviewed_now == parked_at:
                if args.once:
                    return 1
                time.sleep(args.poll_seconds)
                continue
            if parked_at is not None:
                parked_at = None
                gave_retry = False

            frames = frames_index.get()
            had_pending = bool(state.get("pending_predict"))
            index = None
            if state.get("model_family"):
                try:
                    index = remember_project(
                        args.work_root,
                        state["model_family"],
                        active["project"],
                        active["work"],
                        active["frames"],
                        frames,
                        live,
                    )
                    index = backfill_family_projects(args.work_root, state["model_family"], index)
                except Exception:
                    LOG.exception("could not update the family dataset index")
                    index = None
                if index is not None and family_is_stale(args.work_root, state["model_family"], index):
                    if wait_out_gpu(args, status):
                        if args.once:
                            return 0
                        continue
                    try:
                        train_family_union(args, state, status, live, frames)
                        assign_model_plan(state, live, args.work_root)
                        save_state(args.work_dir / STATE_NAME, state)
                        gave_retry = False
                        parked_at = None
                    except KeyboardInterrupt:
                        raise
                    except Exception as exc:
                        outcome = fail_cycle(args, state, status, frames_index, exc, gave_retry, parked_at)
                        if isinstance(outcome, int):
                            return outcome
                        gave_retry, parked_at = outcome
                        continue

            if needs_family_seed(state, args.work_root):
                if wait_out_gpu(args, status):
                    if args.once:
                        return 0
                    continue
                try:
                    seed_family_predictions(args, state, status, frames_index)
                    gave_retry = False
                    parked_at = None
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    outcome = fail_cycle(args, state, status, frames_index, exc, gave_retry, parked_at)
                    if isinstance(outcome, int):
                        return outcome
                    gave_retry, parked_at = outcome
                    continue
                if had_pending:
                    if args.once:
                        return 0
                    continue
            elif status.data.get("ready_for_user") is not True:
                status.update(ready_for_user=True)

            if state["pending_predict"]:
                if wait_out_gpu(args, status):
                    if args.once:
                        return 0
                    continue
                try:
                    finish_predict(args, state, status, frames_index)
                    gave_retry = False
                    parked_at = None
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    outcome = fail_cycle(args, state, status, frames_index, exc, gave_retry, parked_at)
                    if isinstance(outcome, int):
                        return outcome
                    gave_retry, parked_at = outcome
                    continue
                if args.once:
                    return 0
                continue

            names = reviewed_names(live)
            if index is None and state.get("model_family"):
                index = load_family_index(args.work_root, state["model_family"])
            try:
                apply_cadence(args, state, index, len(names))
            except Exception:
                LOG.exception("could not update the training cadence")
            _chosen, unmatched = match_reviewed(frames, names)
            publish_idle(
                status,
                state,
                live,
                frames,
                args.sync_folder / PRED_NAME,
                args.work_dir,
                unmatched,
                project=active["project"],
                frames_folder=active["frames"],
                work_root=args.work_root,
            )
            reviewed = len(names)
            signature = (active["project"], reviewed, state["cycle"], state["next_cycle_at"])
            now = time.time()
            if signature != last_idle_log[0] or now - last_idle_log[1] >= 60:
                LOG.info(
                    "idle project=%s reviewed=%s next_cycle_at=%s cycle=%s since_last=%s",
                    active["project"],
                    reviewed,
                    state["next_cycle_at"],
                    state["cycle"],
                    max(0, reviewed - int(state["reviewed_at_cycle"])),
                )
                last_idle_log = (signature, now)
            if reviewed < int(state["next_cycle_at"]):
                if args.once:
                    LOG.info("not enough reviewed frames for a cycle (%s/%s)", reviewed, state["next_cycle_at"])
                    return 0
                time.sleep(args.poll_seconds)
                continue
            if wait_out_gpu(args, status):
                if args.once:
                    return 0
                continue
            try:
                trained = run_cycle(args, state, status, frames_index, live)
                gave_retry = False
                if trained is False:
                    parked_at = len(reviewed_names(live))
                    if args.once:
                        return 0
                    continue
                parked_at = None
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                outcome = fail_cycle(args, state, status, frames_index, exc, gave_retry, parked_at)
                if isinstance(outcome, int):
                    return outcome
                gave_retry, parked_at = outcome
                continue
            if args.once:
                return 0
    except KeyboardInterrupt:
        LOG.info("stopped")
        status.update(state="idle", message="Διακοπή")
        return 0


def fail_cycle(args, state, status, frames_index, exc, gave_retry, parked_at):
    message = f"{type(exc).__name__}: {exc}"
    LOG.exception("cycle failed")
    state["last_error"] = message
    try:
        save_state(args.work_dir / STATE_NAME, state)
    except Exception:
        LOG.exception("could not save state after the error")
    try:
        live_path = args.sync_folder / LIVE_NAME
        live = read_json(live_path) if live_path.is_file() else {}
        frames = frames_index.get()
        publish_idle(
            status,
            state,
            live,
            frames,
            args.sync_folder / PRED_NAME,
            args.work_dir,
            project=getattr(args, "bound_project", None),
            frames_folder=getattr(args, "bound_frames", None),
            work_root=getattr(args, "work_root", None),
        )
    except Exception:
        status.update(state="idle", last_error=message, message="Σφάλμα · δες το log")
    if args.once:
        return 1
    if not gave_retry and not isinstance(exc, DatasetError):
        LOG.info("retrying once after %ss", max(args.poll_seconds, 15))
        time.sleep(max(args.poll_seconds, 15))
        return True, None
    reviewed = 0
    try:
        reviewed = len(reviewed_names(read_json(args.sync_folder / LIVE_NAME)))
    except Exception:
        reviewed = parked_at if parked_at is not None else -1
    LOG.info("parked until the reviewed count changes (now %s)", reviewed)
    time.sleep(args.poll_seconds)
    return True, reviewed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Watch an annotool live folder, fine-tune YOLO, and write suggestion boxes."
    )
    parser.add_argument("--sync-folder", required=True, type=Path, help="folder with annotool_live.json")
    parser.add_argument(
        "--frames-folder",
        type=Path,
        default=None,
        help="jpg frames, flat or in subfolders. If omitted, the live file's project name is searched under --frames-root",
    )
    parser.add_argument(
        "--frames-root",
        action="append",
        type=Path,
        default=None,
        help="directory to search for a folder named exactly like the live project (repeatable, default D:\\downloads)",
    )
    parser.add_argument(
        "--frames-max-depth",
        type=int,
        default=DEFAULT_FRAMES_MAX_DEPTH,
        help="directory levels under --frames-root to search (default 6). The usual batchNN/match/reduced_match/project path is tried first",
    )
    parser.add_argument("--work-dir", required=True, type=Path, help="datasets and runs; outside the repo and the sync folder. One subfolder per project")
    parser.add_argument("--base-weights", required=True, type=Path, help="local .pt such as yolov8s.pt; never downloaded")
    parser.add_argument(
        "--init-weights",
        type=Path,
        default=None,
        help="optional local .pt used for the first cycle of a project that has no checkpoint yet (a sibling project's model). Later cycles fine-tune this project's best.pt; a new class still restarts from --base-weights",
    )
    parser.add_argument("--min-reviewed", type=int, default=40, help="reviewed frames before the first cycle (default 40)")
    parser.add_argument(
        "--every",
        type=int,
        default=None,
        help="fixed count of new reviewed frames between cycles. If set, adaptive cadence is off",
    )
    parser.add_argument("--every-young", type=int, default=30, help="new reviewed frames between cycles while the family is young or a weak class has new labels (default 30)")
    parser.add_argument("--every-mature", type=int, default=80, help="new reviewed frames between cycles for a mature family (default 80)")
    parser.add_argument("--mature-frames", type=int, default=300, help="family reviewed frames required, with --mature-map, before the mature cadence (default 300)")
    parser.add_argument("--mature-map", type=float, default=0.8, help="overall mAP50 required, with --mature-frames, before the mature cadence (default 0.8)")
    parser.add_argument("--weak-class-map", type=float, default=0.6, help="per-class mAP50 below this, with new labels of that class, uses the young cadence (default 0.6)")
    parser.add_argument("--lookahead", type=int, default=150, help="unreviewed frames to predict after the margin (default 150)")
    parser.add_argument(
        "--predict-margin",
        type=int,
        default=20,
        help="skip this many frames after currentImage; he will reach them while the model runs (default 20)",
    )
    parser.add_argument("--epochs", type=int, default=20, help="epochs when training from base weights (default 20)")
    parser.add_argument("--finetune-epochs", type=int, default=8, help="epochs when fine-tuning best.pt (default 8)")
    parser.add_argument("--imgsz", type=int, default=640, help="train and predict image size (default 640)")
    parser.add_argument("--batch", type=int, default=4, help="train batch size; 4 leaves room on an 8GB GPU with AMP off (default 4). An out-of-memory retry halves it, down to 1")
    parser.add_argument(
        "--predict-batch",
        type=int,
        default=4,
        help="images per model.predict call (default 4). The frame list is never passed in one call. An out-of-memory retry halves this, down to 1, and retries the same chunk",
    )
    parser.add_argument("--workers", type=int, default=2, help="dataloader workers (default 2). An out-of-memory retry drops this to 0 after the batch is already 1")
    parser.add_argument(
        "--gpu-mem-fraction",
        type=float,
        default=0.7,
        help="cap this process to this fraction of GPU memory via torch.cuda.set_per_process_memory_fraction (default 0.7). 0 disables the cap",
    )
    parser.add_argument(
        "--min-free-vram-mb",
        type=float,
        default=1536,
        help="before train or predict, wait while free VRAM is below this many MB (default 1536). 0 disables the check",
    )
    parser.add_argument(
        "--oom-wait",
        type=float,
        default=45,
        help="seconds to wait after CUDA runs out of memory, and between free-VRAM checks (default 45)",
    )
    parser.add_argument("--device", default="", help="ultralytics device, e.g. 0 or cpu (default: auto)")
    parser.add_argument("--conf", type=float, default=0.25, help="predict confidence (default 0.25)")
    parser.add_argument("--iou", type=float, default=0.3, help="class-agnostic NMS IoU (default 0.3)")
    parser.add_argument(
        "--contain",
        type=float,
        default=0.6,
        help="after NMS, drop the lower-confidence box when the overlap covers at least this fraction of the smaller box, any class (default 0.6). 0 disables the pass",
    )
    parser.add_argument("--amp", action="store_true", help="enable AMP; default is off")
    parser.add_argument("--val-fraction", type=float, default=0.1, help="stable fraction of reviewed frames used as val")
    parser.add_argument(
        "--max-family-images",
        type=int,
        default=FAMILY_IMAGE_CAP,
        help="cap on images in one family training set; recent frames plus a share of each class (default 1500)",
    )
    parser.add_argument("--patience", type=int, default=100, help="early-stop patience (default 100, so short cycles run out)")
    parser.add_argument("--lr0", type=float, default=None, help="initial lr; default 0.01 from base, 0.001 when fine-tuning")
    parser.add_argument("--poll-seconds", type=float, default=5, help="seconds between live-file reads while idle (default 5)")
    parser.add_argument("--once", action="store_true", help="run a single cycle if enough frames are reviewed, then exit")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    try:
        return run(parse_args(argv))
    except ConfigError as exc:
        configure_logging()
        LOG.error("%s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
