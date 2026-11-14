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

Datasets and weight files go to ``--work-dir/<project>/``, outside the repository,
so each annotool project keeps its own classes and ``best.pt``. Base weights
must already be on disk; this process does not download them.

``--frames-folder`` is optional. Without it, the ``project`` field in the live
file (the folder name annotool writes) is looked up under each ``--frames-root``
(default ``D:\\downloads``). The usual path is
``<root>/batchNN/<match>/reduced_<match>/<project>``. Otherwise the search
stops at the first directory with that exact name that directly contains a
jpg, down to ``--frames-max-depth`` (default 6), and does not walk into frame
dumps. The result is cached in the work dir. A new project switches folder and model.

``anno2026/scripts/{convert_to_yolo,predict_to_json,train}.py`` and
``anno_video/NEW_PROJECT_RUNBOOK.md`` are not in this checkout. The geometry,
class names (``brand|tpoint``), confidence 0.25, IoU 0.5, class-agnostic NMS,
and AMP-off default follow that toolchain and ``LogoDetection/annoToYOLO.py``.
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
)


class ConfigError(Exception):
    """Bad paths or arguments. The loop should not start."""


class DatasetError(Exception):
    """Reviewed frames are not ready to train (no match, or no boxes)."""


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


def dataset_filename(frame: Frame) -> str:
    return safe_stem(frame.rel) + frame.path.suffix.lower()


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


def select_predict_frames(frames, current_index: int, margin: int, lookahead: int, blocked: set[str]):
    """Frames after ``current + margin``, skipping reviewed and already annotated ones."""
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


def build_prediction_document(live, images: dict) -> dict:
    """Annotool document, the shape ``predict_to_json.py`` writes. No brand|tpoint dedupe."""
    project = "auto_export"
    annotator = "-"
    presets = {}
    live_prefs = None
    if isinstance(live, dict):
        if isinstance(live.get("project"), str) and live["project"].strip():
            project = live["project"]
        if isinstance(live.get("Annotator"), str) and live["Annotator"].strip():
            annotator = live["Annotator"]
        if isinstance(live.get("presets"), dict):
            presets = live["presets"]
        live_prefs = live.get("prefs")
    first = next(iter(images), "")
    return {
        "project": project,
        "imageNum": len(images),
        "prefs": default_prefs(project, live_prefs),
        "images": images,
        "currentImage": first,
        "presets": presets,
        "Annotator": annotator,
    }


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
        "last_error": None,
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


# A directory with this many jpgs is a frames dump. Do not walk into it.
FRAMES_DIR_MIN_JPEGS = 8
DEFAULT_FRAMES_MAX_DEPTH = 6
_BATCH_DIR = re.compile(r"batch\d+\Z", re.IGNORECASE)


def _jpeg_count(filenames) -> int:
    return sum(1 for filename in filenames if Path(filename).suffix.lower() in {".jpg", ".jpeg"})


def searching_message(project: str) -> str:
    return f"Αναζήτηση φακέλου frames για {project}…"


def mark_searching(status: Status, live, project: str):
    """Publish before the frames walk so the UI does not stay on the startup line."""
    reviewed = len(reviewed_names(live)) if isinstance(live, dict) else 0
    status.update(
        state="searching",
        project=project,
        frames_folder=None,
        reviewed=reviewed,
        current_image=current_name(live) if isinstance(live, dict) else None,
        last_error=None,
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


def idle_message(reviewed: int, next_at: int, unmatched: int) -> str:
    text = f"Αναμονή · {reviewed}/{next_at} reviewed"
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
):
    reviewed_list = reviewed_names(live) if isinstance(live, dict) else []
    reviewed = len(reviewed_list)
    count, start, end = summarize_predictions(pred_path, frames)
    weights = resolve_weights(state, work)
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
        message=idle_message(reviewed, int(state["next_cycle_at"]), unmatched),
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


def blocked_rels(frames: list[Frame], names: list[str], images: dict) -> set[str]:
    rels = set(annotated_rels(frames, images))
    for frame in frames:
        if any(name_hits_frame(name, frame) for name in names):
            rels.add(frame.rel)
    return rels


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
    train_frames, val_frames = split_examples(examples, val_fraction)
    by_rel = {frame.rel: boxes for frame, boxes in examples}
    dataset = work / "dataset"
    if dataset.exists():
        shutil.rmtree(dataset)
    counts = Counter()
    for split, split_frames in ("train", train_frames), ("val", val_frames):
        image_dir = dataset / "images" / split
        label_dir = dataset / "labels" / split
        for frame in split_frames:
            filename = dataset_filename(frame)
            counts[place_image(frame.path, image_dir / filename)] += 1
            lines = []
            for name, (xc, yc, bw, bh) in by_rel[frame.rel]:
                lines.append(f"{classes.index(name)} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")
            (label_dir / f"{Path(filename).stem}.txt").parent.mkdir(parents=True, exist_ok=True)
            (label_dir / f"{Path(filename).stem}.txt").write_text("".join(lines), encoding="utf-8")
    yaml_path = dataset / "data.yaml"
    write_data_yaml(yaml_path, dataset, classes)
    boxes = sum(len(items) for _frame, items in examples)
    negatives = sum(1 for _frame, items in examples if not items)
    LOG.info(
        "dataset train=%s val=%s boxes=%s negatives=%s classes=%s (%s)",
        len(train_frames),
        len(val_frames),
        boxes,
        negatives,
        len(classes),
        ", ".join(classes),
    )
    if counts["copy"]:
        LOG.info("copied %s frames into the dataset (hard link unavailable)", counts["copy"])
    return {
        "classes": classes,
        "new_names": new_names,
        "unmatched": unmatched,
        "train_images": len(train_frames),
        "val_images": len(val_frames),
        "boxes": boxes,
        "negatives": negatives,
        "data_yaml": yaml_path,
        "skipped": skipped,
    }


def make_epoch_callback(status: Status, cycle: int, total_epochs: int, holder: dict, from_base: bool):
    kind = "από τα βασικά βάρη" if from_base else "fine-tune"

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
            message = f"Εκπαίδευση κύκλου {cycle} · epoch {epoch}/{total_epochs} · {kind}"
            status.update(
                state="training",
                cycle=cycle,
                epoch=epoch,
                epochs=total_epochs,
                last_map50=holder["map50"],
                from_base=from_base,
                message=message,
            )
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


def train_model(model, args, data_yaml: Path, epochs: int, cycle: int, work: Path, status: Status, from_base: bool):
    holder = {"score": None, "map50": None}
    model.add_callback("on_fit_epoch_end", make_epoch_callback(status, cycle, epochs, holder, from_base))
    run_dir = work / "runs" / f"cycle_{cycle}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    kind = "base weights" if from_base else "previous best.pt"
    LOG.info("training cycle %s from %s for %s epochs imgsz=%s batch=%s", cycle, kind, epochs, args.imgsz, args.batch)
    status.update(
        state="training",
        cycle=cycle,
        epoch=0,
        epochs=epochs,
        from_base=from_base,
        message=f"Εκπαίδευση κύκλου {cycle} · epoch 0/{epochs} · {'από τα βασικά βάρη' if from_base else 'fine-tune'}",
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
    return stable, measured, save_dir


def load_training_model(YOLO, base: Path, previous: Path | None, classes: list[str], new_names: list[str]):
    if wants_finetune(previous, new_names):
        model = YOLO(str(previous))
        names = model_class_names(model)
        if names == list(classes):
            LOG.info("fine-tuning %s", previous)
            return model, False
        LOG.warning("checkpoint classes %s differ from %s; retraining from base weights", names, classes)
    elif new_names and previous:
        LOG.info("new classes (%s); training from base weights", ", ".join(new_names))
    else:
        LOG.info("training from base weights %s", base)
    return YOLO(str(base)), True


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


def predict_frames(model, args, live, frames, work: Path):
    images = live_images(live)
    names = reviewed_names(live)
    blocked = blocked_rels(frames, names, images)
    current = current_name(live)
    current_index = find_current_index(frames, current)
    if current and current_index < 0:
        LOG.warning("currentImage %s is not in the frames folder; predicting from the start", current)
    stems_unique = len({frame.stem for frame in frames}) == len(frames)
    chosen = select_predict_frames(frames, current_index, args.predict_margin, args.lookahead, blocked)
    LOG.info(
        "predict window current=%s index=%s margin=%s chosen=%s first=%s last=%s",
        current,
        current_index,
        args.predict_margin,
        len(chosen),
        chosen[0].rel if chosen else None,
        chosen[-1].rel if chosen else None,
    )
    replaced = {prediction_key(frame, stems_unique) for frame in chosen}
    new_images = {}
    if chosen:
        predict_kwargs = {
            "source": [str(frame.path) for frame in chosen],
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
            "batch": args.batch,
            "project": str((work / "predict").resolve()),
            "name": "latest",
            "exist_ok": True,
        }
        if args.device:
            predict_kwargs["device"] = args.device
        results = model.predict(**predict_kwargs)
        by_path = {frame.path.resolve(): frame for frame in chosen}
        seen = 0
        dominant = dominant_canvas(images)
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
                new_images[key] = entry
        if seen != len(chosen):
            LOG.warning("model returned %s results for %s frames", seen, len(chosen))
    old = {}
    pred_path = args.sync_folder / PRED_NAME
    if pred_path.is_file():
        old_doc = read_json(pred_path)
        if isinstance(old_doc.get("images"), dict):
            old = old_doc["images"]
    merged = merge_prediction_images(old, new_images, replaced, frames, current_index, blocked)
    document = build_prediction_document(live, merged)
    errors = prediction_shape_errors(document)
    if errors:
        raise ConfigError("prediction document failed its shape check: " + "; ".join(errors))
    atomic_write_json(pred_path, document)
    start, end = prediction_span(merged, frames)
    LOG.info("wrote %s frames=%s from=%s to=%s", pred_path, len(merged), start, end)
    return len(merged), start, end


def finish_predict(args, state: dict, status: Status, frames_index: FrameIndex):
    weights = resolve_weights(state, args.work_dir)
    if weights is None or not weights.is_file():
        raise ConfigError("no trained weights to predict with")
    status.update(
        state="predicting",
        cycle=int(state["cycle"]),
        weights=str(weights),
        message=f"Προβλέψεις κύκλου {state['cycle']}",
    )
    live = read_json(args.sync_folder / LIVE_NAME)
    frames = frames_index.get(force=True)
    YOLO = yolo_class()
    model = YOLO(str(weights))
    count, start, end = predict_frames(model, args, live, frames, args.work_dir)
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
    )
    status.update(predicted_frames=count, predicted_from=start, predicted_to=end)
    return count, start, end


def run_cycle(args, state: dict, status: Status, frames_index: FrameIndex, live: dict):
    frames = frames_index.get(force=True)
    snapshot = len(reviewed_names(live))
    upcoming = int(state["cycle"]) + 1
    status.update(
        state="training",
        cycle=upcoming,
        epoch=0,
        epochs=None,
        message=f"Φτιάχνω dataset κύκλου {upcoming}",
        last_error=None,
    )
    built = build_dataset(args.work_dir, frames, live, list(state["classes"]), args.val_fraction)
    previous = resolve_weights(state, args.work_dir)
    YOLO = yolo_class()
    model, from_base = load_training_model(
        YOLO, args.base_weights, previous, built["classes"], built["new_names"]
    )
    epochs = args.epochs if from_base else args.finetune_epochs
    weights, map50, _save_dir = train_model(
        model, args, built["data_yaml"], epochs, upcoming, args.work_dir, status, from_base
    )
    state["cycle"] = upcoming
    state["classes"] = built["classes"]
    state["best_weights"] = weights.relative_to(args.work_dir).as_posix()
    if map50 is not None:
        state["last_map50"] = map50
    state["reviewed_at_cycle"] = snapshot
    state["next_cycle_at"] = snapshot + args.every
    state["pending_predict"] = True
    state["epoch"] = epochs
    state["epochs"] = epochs
    state["from_base"] = from_base
    state["train_images"] = built["train_images"]
    state["val_images"] = built["val_images"]
    state["last_error"] = None
    save_state(args.work_dir / STATE_NAME, state)
    status.update(
        classes=built["classes"],
        last_map50=state["last_map50"],
        epoch=epochs,
        epochs=epochs,
        train_images=built["train_images"],
        val_images=built["val_images"],
        weights=str(weights),
        from_base=from_base,
        next_cycle_at=state["next_cycle_at"],
        reviewed_since_last_cycle=0,
    )
    finish_predict(args, state, status, frames_index)


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
    if args.imgsz % 32 != 0:
        raise ConfigError("--imgsz must be a multiple of 32")
    if min(args.min_reviewed, args.every, args.lookahead, args.epochs, args.finetune_epochs, args.batch) < 1:
        raise ConfigError("min-reviewed, every, lookahead, epochs, finetune-epochs, and batch must be >= 1")
    if args.predict_margin < 0:
        raise ConfigError("--predict-margin must be >= 0")
    if args.frames_max_depth < 0:
        raise ConfigError("--frames-max-depth must be >= 0")
    if not 0 <= args.val_fraction <= 0.5:
        raise ConfigError("--val-fraction must be between 0 and 0.5")
    args.workers = 0 if args.workers is None and os.name == "nt" else (2 if args.workers is None else args.workers)
    if args.workers < 0:
        raise ConfigError("--workers must be >= 0")
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
        message="Δεν βρέθηκαν καρέ" if project else "Λείπει το project",
    )


def run(args) -> int:
    configure_logging()
    install_signals()
    if os.name == "nt":
        import multiprocessing

        multiprocessing.freeze_support()
    args = validate_config(args)
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
        "thresholds first=%s every=%s lookahead=%s margin=%s epochs=%s finetune_epochs=%s imgsz=%s",
        args.min_reviewed,
        args.every,
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

            reviewed_now = len(reviewed_names(live))
            if parked_at is not None and reviewed_now == parked_at:
                if args.once:
                    return 1
                time.sleep(args.poll_seconds)
                continue
            if parked_at is not None:
                parked_at = None
                gave_retry = False

            if state["pending_predict"]:
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

            frames = frames_index.get()
            names = reviewed_names(live)
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
            try:
                run_cycle(args, state, status, frames_index, live)
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
    parser.add_argument("--min-reviewed", type=int, default=40, help="reviewed frames before the first cycle (default 40)")
    parser.add_argument("--every", type=int, default=30, help="new reviewed frames between later cycles (default 30)")
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
    parser.add_argument("--batch", type=int, default=4, help="batch size; 4 is sized for an 8GB GPU with AMP off (default 4)")
    parser.add_argument("--workers", type=int, default=None, help="dataloader workers (default 0 on Windows, 2 elsewhere)")
    parser.add_argument("--device", default="", help="ultralytics device, e.g. 0 or cpu (default: auto)")
    parser.add_argument("--conf", type=float, default=0.25, help="predict confidence (default 0.25)")
    parser.add_argument("--iou", type=float, default=0.5, help="predict IoU (default 0.5)")
    parser.add_argument("--amp", action="store_true", help="enable AMP; default is off")
    parser.add_argument("--val-fraction", type=float, default=0.1, help="stable fraction of reviewed frames used as val")
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
