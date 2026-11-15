"""Checks for the live trainer that do not need a GPU.

    python anno_live/test_live_trainer.py
    python anno_live/test_live_trainer.py --train --weights D:\\models\\yolov8n.pt

The --train path runs one real cycle on a tiny synthetic set. It does not
download weights; pass a local .pt file.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anno_live import live_trainer as lt  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_coords():
    box = lt.canvas_box_to_yolo((10, 10), (40, 30), 100, 50, 200, 100)
    check(box is not None, "box")
    xc, yc, bw, bh = box
    check(abs(xc - 0.25) < 1e-6, xc)
    check(abs(yc - 0.4) < 1e-6, yc)
    check(abs(bw - 0.3) < 1e-6, bw)
    check(abs(bh - 0.4) < 1e-6, bh)
    flipped = lt.canvas_box_to_yolo((40, 30), (10, 10), 100, 50, 200, 100)
    check(flipped == box, flipped)
    x1 = (xc - bw / 2) * 200
    y1 = (yc - bh / 2) * 100
    x2 = (xc + bw / 2) * 200
    y2 = (yc + bh / 2) * 100
    back = lt.xyxy_to_canvas(x1, y1, x2, y2, 200, 100, 100, 50)
    check(back == ([10, 10], [40, 30]), back)
    clamped = lt.canvas_box_to_yolo((-10, -5), (10, 10), 100, 50, 200, 100)
    check(clamped is not None, "clamped")
    cxc, cyc, cbw, cbh = clamped
    check(abs(cxc - 0.05) < 1e-6 and abs(cyc - 0.1) < 1e-6, clamped)
    check(abs(cbw - 0.1) < 1e-6 and abs(cbh - 0.2) < 1e-6, clamped)
    check(lt.canvas_box_to_yolo((0, 0), (0.2, 0.2), 100, 50, 200, 100) is None, "tiny box")


def test_classes_and_window():
    classes, new_names = lt.extend_classes(["Nike|Board", "Adidas|LED"], {"Adidas|LED", "Puma|Sleeve", "Zeta|A"})
    check(classes == ["Nike|Board", "Adidas|LED", "Puma|Sleeve", "Zeta|A"], classes)
    check(new_names == ["Puma|Sleeve", "Zeta|A"], new_names)
    again, none_new = lt.extend_classes(classes, {"Adidas|LED"})
    check(again == classes and none_new == [], again)
    check(lt.wants_finetune(None, []) is False, "no previous")
    check(lt.wants_finetune(Path("/no/such.pt"), []) is False, "missing file")
    check(lt.class_name("Adidas", "LED") == "Adidas|LED", "class name")
    check(lt.split_class("Adidas|LED") == ("Adidas", "LED"), "split")

    frames = [lt.Frame(path=Path(f"/frames/{i:05d}.jpg"), rel=f"{i:05d}", stem=f"{i:05d}") for i in range(16)]
    blocked = {"00004", "00005"}
    chosen = lt.select_predict_frames(frames, 6, 2, 3, blocked)
    check([frame.rel for frame in chosen] == ["00009", "00010", "00011"], [frame.rel for frame in chosen])
    chosen = lt.select_predict_frames(frames, 6, 2, 3, blocked | {"00010"})
    check([frame.rel for frame in chosen] == ["00009", "00011", "00012"], [frame.rel for frame in chosen])
    check(lt.find_current_index(frames, "00006") == 6, "index")
    check(lt.find_current_index(frames, "missing") == -1, "missing")


def image_entry(key, annotations):
    return {
        "imageName": key,
        "imageIndex": 0,
        "width": 100,
        "height": 50,
        "annotations": annotations,
        "exifdata": {},
    }


def box(brand, tpoint, start, diag, hits=1, confidence=None):
    ann = {
        "startPoint": list(start),
        "diagPoint": list(diag),
        "group": "",
        "brand": brand,
        "tpoint": tpoint,
        "hits": hits,
    }
    if confidence is not None:
        ann["confidence"] = confidence
    return ann


def test_suppress_contained():
    large = lt.detection_annotation("Nike", "Board", (0, 0), (100, 100), 0.9)
    inside = lt.detection_annotation("Adidas", "LED", (10, 10), (50, 50), 0.4)
    kept = lt.suppress_contained([inside, large], 0.6)
    check(len(kept) == 1 and kept[0]["brand"] == "Nike", [(ann["brand"], ann["confidence"]) for ann in kept])
    small_sure = lt.detection_annotation("Adidas", "LED", (10, 10), (50, 50), 0.95)
    large_weak = lt.detection_annotation("Nike", "Board", (0, 0), (100, 100), 0.4)
    kept = lt.suppress_contained([large_weak, small_sure], 0.6)
    check(len(kept) == 1 and kept[0]["brand"] == "Adidas", [(ann["brand"], ann["confidence"]) for ann in kept])
    left = lt.detection_annotation("Nike", "Board", (0, 0), (10, 10), 0.8)
    right = lt.detection_annotation("Puma", "Sleeve", (6, 0), (16, 10), 0.7)
    kept = lt.suppress_contained([left, right], 0.6)
    check(len(kept) == 2, "40 percent of the smaller box stays")
    overlap = lt.detection_annotation("Puma", "Sleeve", (4, 0), (14, 10), 0.3)
    kept = lt.suppress_contained([left, overlap], 0.6)
    check(len(kept) == 1 and kept[0]["confidence"] == 0.8, [(ann["confidence"]) for ann in kept])
    apart = lt.detection_annotation("Adidas", "LED", (110, 0), (120, 10), 0.2)
    kept = lt.suppress_contained([large, inside, apart], 0.6)
    brands = [(ann["brand"], ann["confidence"]) for ann in kept]
    check(brands == [("Nike", 0.9), ("Adidas", 0.2)], brands)
    check(lt.suppress_contained([inside, large], 0) == [inside, large], "contain 0 keeps both")
    args = lt.parse_args(["--sync-folder", "s", "--work-dir", "w", "--base-weights", "b.pt"])
    check(args.iou == 0.3 and args.contain == 0.6, (args.iou, args.contain))


class _Tensor:
    def __init__(self, data):
        self.data = data

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.data


def test_model_families():
    grouped = {"project": "match", "prefs": {"groups": ["2026 RLWC", "other"]}}
    check(lt.resolve_model_plan(grouped)["family"] == "2026 RLWC", lt.resolve_model_plan(grouped))
    named = {"modelFamily": " custom ", "prefs": {"groups": ["2026 RLWC"]}, "modelChoice": "continue"}
    check(lt.resolve_model_plan(named)["family"] == "custom", lt.resolve_model_plan(named))
    fresh = {"modelChoice": "new", "modelFamily": "2026 RLWC", "prefs": {"groups": ["other"]}}
    plan = lt.resolve_model_plan(fresh)
    check(plan["fresh"] is True and plan["family"] == "2026 RLWC" and plan["choice"] == "new", plan)
    picked = lt.resolve_model_plan({"modelChoice": "from:2025 Finals", "modelFamily": "custom"})
    check(picked["family"] == "2025 Finals" and picked["fresh"] is False, picked)
    check(lt.resolve_model_plan({"project": "x"})["family"] == "default", "fallback family")

    class BoxMetric:
        ap50 = [0.5, 0.25]
        ap_class_index = [0, 1]

    class Validator:
        class Metrics:
            box = BoxMetric()

        metrics = Metrics()

    class Trainer:
        validator = Validator()

    scores = lt.per_class_ap50(Trainer(), ["Adidas|LED", "Nike|Board"])
    check(scores == {"Adidas|LED": 0.5, "Nike|Board": 0.25}, scores)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        weights = root / "cycle.pt"
        weights.write_bytes(b"1" * 2048)
        check(lt.maybe_update_family(root, "2026 RLWC", weights, 0.4, {"Nike|Board": 0.5}) is True, "first family save")
        stored = root / "models" / "2026 RLWC" / "best.pt"
        check(stored.is_file() and stored.read_bytes() == b"1" * 2048, stored)
        check(lt.maybe_update_family(root, "2026 RLWC", weights, 0.2, {}) is False, "worse map is kept")
        meta = json.loads((stored.parent / "meta.json").read_text(encoding="utf-8"))
        check(meta["map50"] == 0.4 and meta["family"] == "2026 RLWC", meta)
        check(lt.maybe_update_family(root, "2026 RLWC", weights, 0.41, {"Nike|Board": 0.6}) is True, "better map replaces")
        state = lt.blank_state(40)
        assigned = lt.assign_model_plan(state, {"modelChoice": "from:2026 RLWC"}, root)
        check(assigned == stored.resolve() or assigned == stored, assigned)
        check(state["model_mode"] == "συνέχεια" and state["model_family"] == "2026 RLWC", state)
        check(lt.needs_family_seed(state) is True, state)
        state["seeded_family"] = "2026 RLWC"
        check(lt.needs_family_seed(state) is False, "seeded once")
        fresh_state = lt.blank_state(40)
        check(lt.assign_model_plan(fresh_state, {"modelChoice": "new", "modelFamily": "2026 RLWC"}, root) is None, "new ignores library")
        check(fresh_state["model_mode"] == "νέο", fresh_state["model_mode"])

        frames = [lt.Frame(path=Path(f"/frames/{i:05d}.jpg"), rel=f"{i:05d}", stem=f"{i:05d}") for i in range(6)]
        chosen = lt.select_predict_frames(frames, 4, 20, 1, {"00001"}, coverage="all")
        check([frame.rel for frame in chosen] == ["00000", "00002", "00003", "00004", "00005"], [f.rel for f in chosen])

        sync = root / "sync"
        sync.mkdir()

        class Boxes:
            def __init__(self):
                self.xyxy = _Tensor([[0, 0, 50, 50], [2, 2, 40, 40]])
                self.conf = _Tensor([0.9, 0.3])
                self.cls = _Tensor([0, 1])

            def __len__(self):
                return 2

        class Result:
            def __init__(self, path):
                self.path = path
                self.orig_shape = (100, 200)
                self.names = {0: "Nike|Board", 1: "Adidas|LED"}
                self.boxes = Boxes()

        class Model:
            def predict(self, **kwargs):
                return [Result(path) for path in kwargs["source"]]

        class Args:
            conf = 0.25
            iou = 0.3
            imgsz = 64
            workers = 0
            batch = 1
            device = "cpu"
            predict_margin = 20
            lookahead = 1
            contain = 0.6
            sync_folder = sync

        live = {
            "project": "match",
            "currentImage": "00004",
            "currentImageIndex": 4,
            "reviewed": ["00001"],
            "images": {},
            "Annotator": "-",
            "prefs": {},
            "presets": {},
        }
        count, start, end = lt.predict_frames(Model(), Args(), live, frames, root / "work", coverage="all")
        doc = json.loads((sync / lt.PRED_NAME).read_text(encoding="utf-8"))
        check(start == "00000" and "00000" in doc["images"], (start, list(doc["images"])))
        check("00001" not in doc["images"], doc["images"])
        check(len(doc["images"]["00000"]["annotations"]) == 1, doc["images"]["00000"]["annotations"])
        check(doc["images"]["00000"]["annotations"][0]["confidence"] == 0.9, doc["images"]["00000"])
        check(count == 5, count)
        check(end == "00005", end)


def test_merge_and_shape():
    frames = [lt.Frame(path=Path(f"/frames/{i:05d}.jpg"), rel=f"{i:05d}", stem=f"{i:05d}") for i in range(16)]
    old = {
        key: image_entry(key, [box("Sentinel", "Old", (1, 2), (8, 9), confidence=0.5)])
        for key in ("00002", "00004", "00006", "00007", "00009", "00014")
    }
    new = {
        "00010": image_entry(
            "00010",
            [
                lt.detection_annotation("Adidas", "LED", (1, 1), (4, 4), 0.8),
                lt.detection_annotation("Adidas", "LED", (5, 1), (9, 4), 0.4),
            ],
        )
    }
    blocked = {f"{i:05d}" for i in range(6)}
    merged = lt.merge_prediction_images(old, new, {"00009", "00010", "00011"}, frames, 6, blocked)
    check(list(merged) == ["00006", "00007", "00010", "00014"], list(merged))
    check(merged["00007"]["annotations"][0]["brand"] == "Sentinel", "kept margin")
    check(len(merged["00010"]["annotations"]) == 2, "no dedupe")
    check(merged["00010"]["annotations"][0]["hits"] == 1, "hits")
    check("00009" not in merged and "00002" not in merged and "00004" not in merged, "dropped")
    doc = lt.build_prediction_document({"project": "match", "Annotator": "ada", "prefs": {}, "presets": {}}, merged)
    errors = lt.prediction_shape_errors(doc)
    check(errors == [], errors)
    check(doc["project"] == "match", doc["project"])
    check(doc["imageNum"] == 4, doc["imageNum"])
    check(doc["currentImage"] == "00006", doc["currentImage"])
    check(tuple(doc.keys()) == lt.PREDICTION_KEYS, tuple(doc.keys()))
    start, end = lt.prediction_span(merged, frames)
    check(start == "00006" and end == "00014", (start, end))


def write_jpeg(path: Path, box_xy=None):
    image = Image.new("RGB", (200, 100), "black")
    if box_xy:
        ImageDraw.Draw(image).rectangle(box_xy, fill=(255, 80, 20))
    image.save(path, "JPEG")


def make_live_frames(root: Path, with_window: bool):
    frames = root / "frames"
    frames.mkdir()
    count = 16 if with_window else 8
    for i in range(count):
        write_jpeg(frames / f"{i:05d}.jpg", (20, 20, 80, 60) if i < 4 else None)
    images = {
        "00000": image_entry(
            "00000",
            [
                box("Adidas", "LED", (10, 10), (40, 30), hits=3),
                box("Adidas", "LED", (50, 10), (80, 30), hits=1),
            ],
        ),
        "00001": image_entry("00001", [box("Nike", "Board", (0, 0), (100, 50))]),
        "00002": image_entry("00002", [box("Adidas", "LED", (40, 30), (10, 10))]),
        "00003": image_entry("00003", [box("Nike", "Board", (10, 10), (40, 30))]),
        "00005": image_entry("00005", []),
    }
    if not with_window:
        images["00999"] = image_entry("00999", [box("Puma", "Sleeve", (10, 10), (40, 30))])
        write_jpeg(frames / "00999.jpg", (20, 20, 80, 60))
        write_jpeg(frames / "unseen.jpg")
    live = {
        "project": "match",
        "images": images,
        "currentImage": "00006" if with_window else "00000",
        "Annotator": "ada",
        "prefs": {"projectName": "other", "AnnotatorName": "ada"},
        "presets": {},
        "reviewed": ["00000", "00001", "00002", "00003", "00004", "00005"],
        "rejected": {
            "00004": [
                {"brand": "Nike", "tpoint": "Board", "x": 10, "y": 10, "width": 30, "height": 20, "confidence": 0.55}
            ],
            "00000": [
                {"brand": "Puma", "tpoint": "Sleeve", "x": 1, "y": 2, "width": 8, "height": 6, "confidence": 0.2}
            ],
            "00999": [
                {"brand": "Nike", "tpoint": "Board", "x": 0, "y": 0, "width": 10, "height": 10, "confidence": 0.9}
            ],
            "00005": [],
        },
        "syncedAt": "2026-11-14T00:00:00+00:00",
        "currentImageIndex": 6 if with_window else 0,
    }
    return frames, live


def labels_of(dataset: Path):
    found = {}
    for path in dataset.rglob("*.txt"):
        found[path.stem] = path.read_text(encoding="utf-8")
    return found


def test_dataset():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        frames, live = make_live_frames(root, with_window=False)
        built = lt.build_dataset(root / "work", lt.list_frames(frames), live, [], 0.1)
        check(built["classes"] == ["Adidas|LED", "Nike|Board"], built["classes"])
        check(built["boxes"] == 5, built["boxes"])
        check(built["negatives"] == 2, built["negatives"])
        labels = labels_of(root / "work" / "dataset")
        check("00999" not in labels and "unseen" not in labels, labels.keys())
        check(labels["00004"] == "" and labels["00005"] == "", "negatives")
        lines = [line for line in labels["00000"].splitlines() if line]
        check(len(lines) == 2, labels["00000"])
        check(all(line.startswith("0 ") for line in lines), lines)
        check(any(line.startswith("0 0.250000 0.400000 0.300000 0.400000") for line in lines), lines)
        check(any(line.startswith("0 0.650000 0.400000 0.300000 0.400000") for line in lines), lines)
        check(labels["00002"].strip() == "0 0.250000 0.400000 0.300000 0.400000", labels["00002"])
        check(labels["00001"].strip() == "1 0.500000 0.500000 1.000000 1.000000", labels["00001"])
        check(built["train_images"] >= 1 and built["val_images"] >= 1, built)
        check(built["hard_negative_frames"] == 2, built["hard_negative_frames"])
        check(built["classes"] == ["Adidas|LED", "Nike|Board"], built["classes"])
        train_dir = root / "work" / "dataset" / "labels" / "train"
        val_dir = root / "work" / "dataset" / "labels" / "val"

        def copy_names(folder, stem):
            return sorted(
                path.stem for path in folder.glob("*.txt") if path.stem == stem or path.stem.startswith(stem + "__hn")
            )

        for stem in ("00000", "00004"):
            train_names = copy_names(train_dir, stem)
            val_names = copy_names(val_dir, stem)
            check(len(train_names) in (0, lt.HARD_NEGATIVE_COPIES), (stem, train_names))
            check(len(val_names) in (0, 1), (stem, val_names))
            check(len(train_names) + len(val_names) >= 1, stem)
            for name in train_names + val_names:
                folder = train_dir if name in train_names else val_dir
                text = (folder / f"{name}.txt").read_text(encoding="utf-8")
                if stem == "00004":
                    check(text == "", text)
                else:
                    check(text.count("\n") == 2 or text.strip().count("\n") == 1, text)
                    check("0.250000" in text and "0.650000" in text, text)


CLUSTER = "part8_reduced_20261017_RLWC_MensEnglandvTonga_Live_Seven_1930-cluster_7"


def test_frames_lookup():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        downloads = root / "downloads"
        direct = downloads / "season" / CLUSTER
        direct.mkdir(parents=True)
        write_jpeg(direct / "00001.jpg")
        nested = downloads / "other" / CLUSTER
        (nested / "sub").mkdir(parents=True)
        write_jpeg(nested / "sub" / "00002.jpg")
        decoy = downloads / "decoy" / (CLUSTER + "_extra")
        decoy.mkdir(parents=True)
        write_jpeg(decoy / "00003.jpg")
        empty = downloads / "empty" / CLUSTER
        empty.mkdir(parents=True)
        (empty / "notes.txt").write_text("no jpg", encoding="utf-8")
        found = lt.find_project_folder(CLUSTER, [downloads])
        check(found == direct.resolve(), found)
        only = root / "only"
        nested_only = only / "a" / "b" / "nested_only"
        (nested_only / "frames").mkdir(parents=True)
        write_jpeg(nested_only / "frames" / "00001.jpg")
        check(lt.find_project_folder("nested_only", [only]) is None, "jpg must sit in the project folder")
        solo = only / "a" / "b" / "solo_project"
        solo.mkdir(parents=True)
        write_jpeg(solo / "00001.jpg")
        check(lt.find_project_folder("solo_project", [only]) == solo.resolve(), "direct jpg")
        check(lt.find_project_folder("missing_project", [only]) is None, "missing name")

        hint_root = root / "hint"
        match_name = "MensEnglandvTonga"
        hinted = hint_root / "batch07" / match_name / f"reduced_{match_name}" / "hint_project"
        hinted.mkdir(parents=True)
        write_jpeg(hinted / "00001.jpg")
        early = hint_root / "aaa_early" / "hint_project"
        early.mkdir(parents=True)
        write_jpeg(early / "00001.jpg")
        check(lt.find_project_folder("hint_project", [hint_root]) == hinted.resolve(), "batch layout wins")

        depth_root = root / "depth"

        def place(depth, name):
            path = depth_root
            for i in range(depth - 1):
                path = path / f"d{i}"
            path = path / name
            path.mkdir(parents=True)
            write_jpeg(path / "00001.jpg")
            return path

        at_limit = place(6, "at_limit")
        too_deep = place(7, "too_deep")
        check(lt.find_project_folder("at_limit", [depth_root], max_depth=6) == at_limit.resolve(), "depth 6")
        check(lt.find_project_folder("too_deep", [depth_root], max_depth=6) is None, "depth 7 hidden")
        check(lt.find_project_folder("too_deep", [depth_root], max_depth=7) == too_deep.resolve(), "depth 7 allowed")

        prune_root = root / "prune"
        dump = prune_root / "dump"
        dump.mkdir(parents=True)
        for i in range(lt.FRAMES_DIR_MIN_JPEGS):
            write_jpeg(dump / f"{i:05d}.jpg")
        hidden = dump / "hidden_project"
        hidden.mkdir()
        write_jpeg(hidden / "00001.jpg")
        check(lt.find_project_folder("hidden_project", [prune_root]) is None, "frames dump was entered")
        visible = prune_root / "keep" / "visible_project"
        visible.mkdir(parents=True)
        for i in range(lt.FRAMES_DIR_MIN_JPEGS):
            write_jpeg(visible / f"{i:05d}.jpg")
        check(lt.find_project_folder("visible_project", [prune_root]) == visible.resolve(), "named frames folder")

        search_sync = root / "search-sync"
        search_sync.mkdir()
        search_status = lt.Status(search_sync / lt.STATUS_NAME, "cpu", 40)
        calls = []

        def on_search(project):
            calls.append(project)
            lt.mark_searching(
                search_status,
                {"project": project, "reviewed": ["a", "b"], "currentImage": "00010"},
                project,
            )
            calls.append(json.loads((search_sync / lt.STATUS_NAME).read_text(encoding="utf-8"))["state"])

        cache_path = root / "fresh-cache.json"
        searching = lt.FrameLocator([hint_root], cache_path, on_search=on_search)
        check(searching.resolve("hint_project") == hinted.resolve(), "search resolve")
        check(calls == ["hint_project", "searching"], calls)
        written = json.loads((search_sync / lt.STATUS_NAME).read_text(encoding="utf-8"))
        check(written["message"] == lt.searching_message("hint_project"), written["message"])
        check(written["reviewed"] == 2 and written["current_image"] == "00010", written)
        check(written["project"] == "hint_project" and written["frames_folder"] is None, written)
        restarted = lt.FrameLocator([hint_root], cache_path, on_search=lambda project: calls.append("restart"))
        check(restarted.resolve("hint_project") == hinted.resolve(), "cached restart")
        check("restart" not in calls, calls)

        work = root / "work"
        work.mkdir()
        locator = lt.FrameLocator([downloads], work / "frames_cache.json", miss_seconds=0)
        check(locator.resolve(CLUSTER) == direct.resolve(), "first resolve")
        elsewhere = root / "elsewhere" / CLUSTER
        elsewhere.mkdir(parents=True)
        write_jpeg(elsewhere / "00009.jpg")
        locator.roots = [elsewhere]
        check(locator.resolve(CLUSTER) == direct.resolve(), "cache ignores a newer copy")
        cache = json.loads((work / "frames_cache.json").read_text(encoding="utf-8"))
        check(cache[CLUSTER] == str(direct.resolve()), cache)

        active = {}
        live_a = {"project": CLUSTER, "reviewed": [], "images": {}}
        err = lt.bind_project(live_a, None, locator, work, 40, active)
        check(err is None, err)
        check(active["frames"] == direct.resolve(), active["frames"])
        check(active["work"] == (work / CLUSTER).resolve(), active["work"])
        active["state"]["cycle"] = 4
        lt.save_state(active["work"] / "state.json", active["state"])

        beta = "beta_match"
        beta_dir = downloads / "beta" / beta
        beta_dir.mkdir(parents=True)
        write_jpeg(beta_dir / "00001.jpg")
        locator.roots = [downloads]
        err = lt.bind_project({"project": beta, "reviewed": [], "images": {}}, None, locator, work, 40, active)
        check(err is None, err)
        check(active["state"]["cycle"] == 0, active["state"]["cycle"])
        check(active["work"] == (work / beta).resolve(), active["work"])
        check(active["frames"] == beta_dir.resolve(), active["frames"])
        err = lt.bind_project(live_a, None, locator, work, 40, active)
        check(err is None and active["state"]["cycle"] == 4, active.get("state"))
        check(active["frames"] == direct.resolve(), active["frames"])

        fixed = root / "fixed"
        fixed.mkdir()
        write_jpeg(fixed / "00001.jpg")
        explicit = {}
        err = lt.bind_project({"project": beta}, fixed, locator, work, 40, explicit)
        check(err is None and explicit["frames"] == fixed, explicit.get("frames"))
        check(explicit["work"].name == beta, explicit["work"])

        missing = {}
        err = lt.bind_project({"project": "no-such-cluster"}, None, locator, work, 40, missing)
        check(err and "no-such-cluster" in err, err)
        check(missing.get("ready") is False, missing)

        sync = root / "sync"
        sync.mkdir()
        old = lt.build_prediction_document({"project": "alpha", "Annotator": "-", "prefs": {}, "presets": {}}, {})
        (sync / lt.PRED_NAME).write_text(json.dumps(old), encoding="utf-8")
        lt.ensure_predictions_project(sync, {"project": beta})
        cleared = json.loads((sync / lt.PRED_NAME).read_text(encoding="utf-8"))
        check(cleared["project"] == beta and cleared["images"] == {}, cleared)
        lt.ensure_predictions_project(sync, {"project": beta})
        check(json.loads((sync / lt.PRED_NAME).read_text(encoding="utf-8")) == cleared, "cleared twice")

        weights = root / "fake.pt"
        weights.write_bytes(b"0" * 2048)
        (sync / lt.LIVE_NAME).write_text(
            json.dumps({"project": "no-such-cluster", "reviewed": [], "images": {}}),
            encoding="utf-8",
        )
        code = lt.main(
            [
                "--sync-folder",
                str(sync),
                "--frames-root",
                str(downloads),
                "--work-dir",
                str(root / "once-work"),
                "--base-weights",
                str(weights),
                "--once",
            ]
        )
        check(code == 1, code)
        status = json.loads((sync / lt.STATUS_NAME).read_text(encoding="utf-8"))
        check(list(status) == list(lt.STATUS_KEYS), list(status))
        check(status["state"] == "idle" and status["project"] == "no-such-cluster", status)
        check(status["frames_folder"] is None, status["frames_folder"])
        check("no-such-cluster" in status["last_error"] and str(downloads) in status["last_error"], status["last_error"])


def test_init_weights():
    class Fake:
        def __init__(self, path):
            self.path = str(path)
            self.names = {0: "Other|X"} if str(path).endswith("previous.pt") else {0: "Adidas|LED"}

    def YOLO(path):
        return Fake(path)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base = root / "base.pt"
        init = root / "init.pt"
        previous = root / "previous.pt"
        for path in (base, init, previous):
            path.write_bytes(b"0" * 2048)
        model, from_base, kind = lt.load_training_model(YOLO, base, None, ["Adidas|LED"], [], init)
        check(kind == "init" and from_base and model.path == str(init), (kind, getattr(model, "path", None)))
        model, from_base, kind = lt.load_training_model(YOLO, base, None, ["Adidas|LED"], [], None)
        check(kind == "base" and model.path == str(base), (kind, model.path))
        model, from_base, kind = lt.load_training_model(YOLO, base, previous, ["Other|X"], [], init)
        check(kind == "finetune" and not from_base and model.path == str(previous), (kind, model.path))
        model, from_base, kind = lt.load_training_model(YOLO, base, previous, ["Adidas|LED"], [], init)
        check(kind == "base" and model.path == str(base), (kind, model.path))
        model, from_base, kind = lt.load_training_model(
            YOLO, base, previous, ["Adidas|LED", "Nike|Board"], ["Nike|Board"], init
        )
        check(kind == "base" and model.path == str(base), (kind, model.path))


def test_config_and_status():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sync = root / "sync"
        frames = root / "frames"
        work = root / "work"
        sync.mkdir()
        frames.mkdir()
        weights = root / "fake.pt"
        weights.write_bytes(b"0" * 2048)
        args = lt.parse_args(
            [
                "--sync-folder",
                str(sync),
                "--frames-folder",
                str(frames),
                "--work-dir",
                str(work),
                "--base-weights",
                str(weights),
            ]
        )
        lt.validate_config(args)
        check(args.workers == 2, args.workers)
        check(args.batch == 4, args.batch)
        check(args.gpu_mem_fraction == 0.7, args.gpu_mem_fraction)
        check(args.min_free_vram_mb == 1536, args.min_free_vram_mb)
        check(args.oom_wait == 45, args.oom_wait)
        optional = lt.parse_args(
            [
                "--sync-folder",
                str(sync),
                "--work-dir",
                str(root / "opt-work"),
                "--base-weights",
                str(weights),
            ]
        )
        check(optional.frames_folder is None, optional.frames_folder)
        check(optional.frames_max_depth == 6, optional.frames_max_depth)
        lt.validate_config(optional)
        check(optional.frames_roots == [Path(r"D:\downloads")], optional.frames_roots)
        bad = lt.parse_args(
            [
                "--sync-folder",
                str(sync),
                "--frames-folder",
                str(frames),
                "--work-dir",
                str(lt.repo_root() / "anno_live"),
                "--base-weights",
                str(weights),
            ]
        )
        try:
            lt.validate_config(bad)
        except lt.ConfigError:
            pass
        else:
            raise AssertionError("work dir inside the repo was accepted")
        missing = lt.parse_args(
            [
                "--sync-folder",
                str(sync),
                "--frames-folder",
                str(frames),
                "--work-dir",
                str(root / "other-work"),
                "--base-weights",
                str(root / "missing.pt"),
            ]
        )
        try:
            lt.validate_config(missing)
        except lt.ConfigError as exc:
            check("not found" in str(exc), exc)
        else:
            raise AssertionError("missing weights were accepted")
        heavy = lt.parse_args(
            [
                "--sync-folder",
                str(sync),
                "--frames-folder",
                str(frames),
                "--work-dir",
                str(root / "gpu-work"),
                "--base-weights",
                str(weights),
                "--gpu-mem-fraction",
                "1.5",
            ]
        )
        try:
            lt.validate_config(heavy)
        except lt.ConfigError as exc:
            check("gpu-mem-fraction" in str(exc), exc)
        else:
            raise AssertionError("gpu fraction above 1 was accepted")
        status = lt.Status(sync / lt.STATUS_NAME, "cpu", 40)
        status.update(reviewed=3, message="Αναμονή", classes=["Adidas|LED"])
        text = (sync / lt.STATUS_NAME).read_text(encoding="utf-8")
        data = json.loads(text)
        check(list(data) == list(lt.STATUS_KEYS), list(data))
        check(data["schema"] == 1 and data["next_cycle_at"] == 40, data)
        check(data["classes"] == ["Adidas|LED"] and data["reviewed"] == 3, data)
        check(data["project"] is None and data["frames_folder"] is None, data)
        check(data["hard_negative_frames"] == 0, data["hard_negative_frames"])
        check(list(sync.glob(".live_trainer_status.json.*.tmp")) == [], "temp status file left behind")
        check("Αναμονή" in text, "greek message")


def test_cycle(weights: Path):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        frames, live = make_live_frames(root, with_window=True)
        sync = root / "sync"
        work = root / "work"
        sync.mkdir()
        (sync / lt.LIVE_NAME).write_text(json.dumps(live), encoding="utf-8")
        old_keys = ["00002", "00004", "00006", "00007", "00009", "00014"]
        old_images = {
            key: image_entry(key, [box("Sentinel", "Old", (1, 2), (8, 9), confidence=0.42)]) for key in old_keys
        }
        old_doc = lt.build_prediction_document(live, old_images)
        (sync / lt.PRED_NAME).write_text(json.dumps(old_doc), encoding="utf-8")
        code = lt.main(
            [
                "--sync-folder",
                str(sync),
                "--frames-folder",
                str(frames),
                "--work-dir",
                str(work),
                "--base-weights",
                str(weights),
                "--min-reviewed",
                "4",
                "--every",
                "30",
                "--lookahead",
                "3",
                "--predict-margin",
                "2",
                "--epochs",
                "1",
                "--finetune-epochs",
                "1",
                "--imgsz",
                "64",
                "--batch",
                "2",
                "--workers",
                "0",
                "--device",
                "cpu",
                "--val-fraction",
                "0.1",
                "--once",
            ]
        )
        check(code == 0, f"exit {code}")
        names = sorted(path.name for path in sync.iterdir())
        check(names == [lt.LIVE_NAME, lt.PRED_NAME, lt.STATUS_NAME], names)
        check(list(sync.glob(".*.tmp")) == [], "temp file left in the sync folder")
        doc = json.loads((sync / lt.PRED_NAME).read_text(encoding="utf-8"))
        errors = lt.prediction_shape_errors(doc)
        check(errors == [], errors)
        images = doc["images"]
        check("00002" not in images and "00004" not in images, images.keys())
        check("00007" in images and images["00007"]["annotations"][0]["brand"] == "Sentinel", "margin kept")
        check("00014" in images and images["00014"]["annotations"][0]["brand"] == "Sentinel", "far kept")
        check("00006" in images and images["00006"]["annotations"][0]["brand"] == "Sentinel", "current kept")
        if "00009" in images:
            brands = {ann["brand"] for ann in images["00009"]["annotations"]}
            check("Sentinel" not in brands, brands)
        status = json.loads((sync / lt.STATUS_NAME).read_text(encoding="utf-8"))
        check(list(status) == list(lt.STATUS_KEYS), list(status))
        check(status["state"] == "idle", status["state"])
        check(status["cycle"] == 1, status["cycle"])
        check(status["reviewed"] == 6, status["reviewed"])
        check(status["reviewed_since_last_cycle"] == 0, status["reviewed_since_last_cycle"])
        check(status["next_cycle_at"] == 36, status["next_cycle_at"])
        check(status["predicted_frames"] == len(images), status["predicted_frames"])
        keys = list(images)
        check(status["predicted_from"] == keys[0] and status["predicted_to"] == keys[-1], status)
        check(status["last_error"] is None, status["last_error"])
        check(status["epoch"] == 1 and status["epochs"] == 1, (status["epoch"], status["epochs"]))
        check(status["from_base"] is True, status["from_base"])
        check(status["classes"] == ["Adidas|LED", "Nike|Board"], status["classes"])
        check(doc["project"] == "match", doc["project"])
        check(status["hard_negative_frames"] == 2, status.get("hard_negative_frames"))
        check(status["model_family"] == "default", status.get("model_family"))
        check(status["model_mode"] == "νέο", status.get("model_mode"))
        check(isinstance(status["per_class_map50"], dict), status.get("per_class_map50"))
        check((work / "models" / "default" / "best.pt").is_file(), "family best.pt")
        check(status["device"] == "cpu", status["device"])
        check(isinstance(status["last_map50"], (int, float)), status["last_map50"])
        check(status["project"] == "match", status["project"])
        check(Path(status["frames_folder"]).resolve() == frames.resolve(), status["frames_folder"])
        project_work = work / "match"
        check((project_work / "best.pt").is_file(), "best.pt missing")
        check(not (work / "frames_cache.json").exists(), "search cache written for an explicit frames folder")
        labels = labels_of(project_work / "dataset")
        check("0 0.250000 0.400000 0.300000 0.400000" in labels["00000"], labels["00000"])
        state = json.loads((project_work / "state.json").read_text(encoding="utf-8"))
        check(state["pending_predict"] is False, state)
        check(state["cycle"] == 1 and state["next_cycle_at"] == 36, state)


def test_gpu_backoff():
    class AcceleratorError(Exception):
        pass

    class OutOfMemoryError(Exception):
        pass

    check(lt.is_cuda_oom(OutOfMemoryError("CUDA out of memory")), "oom type")
    check(lt.is_cuda_oom(AcceleratorError("CUDA error: out of memory")), "accelerator")
    check(lt.is_cuda_oom(RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")), "runtime")
    wrapped = RuntimeError("train failed")
    wrapped.__cause__ = AcceleratorError("CUDA error: out of memory")
    check(lt.is_cuda_oom(wrapped), "cause")
    check(not lt.is_cuda_oom(RuntimeError("dataloader worker exited")), "plain runtime")
    check(not lt.is_cuda_oom(ValueError("out of memory")), "other type")
    check(not lt.is_cuda_oom(AcceleratorError("device busy")), "accelerator without oom")

    args = argparse.Namespace(batch=4, workers=2)
    check(lt.shrink_after_oom(args) == "batch 2" and args.batch == 2, args.batch)
    args.batch = 3
    check(lt.shrink_after_oom(args) == "batch 1" and args.batch == 1, args.batch)
    check(lt.shrink_after_oom(args) == "workers 0" and args.workers == 0, args.workers)
    check(lt.shrink_after_oom(args) == "", "nothing left to shrink")

    with tempfile.TemporaryDirectory() as tmp:
        status = lt.Status(Path(tmp) / "live_trainer_status.json", "cpu", 40)
        retry_args = argparse.Namespace(batch=4, workers=2, oom_wait=0)
        calls = {"n": 0}

        def action():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("CUDA out of memory. Tried to allocate 512.00 MiB")
            status.update(state="training", last_error=None, message="ok")
            return "done"

        result = lt.call_with_oom_retry(status, retry_args, action, "training")
        check(result == "done", result)
        check(retry_args.batch == 2, retry_args.batch)
        check(status.data["last_error"] is None, status.data["last_error"])
        check(status.data["state"] == "training", status.data["state"])
        written = json.loads(status.path.read_text(encoding="utf-8"))
        check(written["last_error"] is None and written["state"] == "training", written["state"])

        def always():
            raise RuntimeError("CUDA out of memory")

        stuck = argparse.Namespace(batch=1, workers=0, oom_wait=0)
        try:
            lt.call_with_oom_retry(status, stuck, always, "predict")
        except RuntimeError as exc:
            check("out of memory" in str(exc).lower(), exc)
        else:
            raise AssertionError("oom retry should re-raise when nothing is left to shrink")

    tight = argparse.Namespace(device="0", min_free_vram_mb=1536)
    waiting = lt.gpu_memory_message(tight, free_mb=100)
    check(waiting is not None and waiting.startswith("Αναμονή GPU"), waiting)
    check("1536" in waiting and "100" in waiting, waiting)
    check(lt.gpu_memory_message(tight, free_mb=4000) is None, "enough vram")
    check(lt.gpu_memory_message(argparse.Namespace(device="cpu", min_free_vram_mb=1536), free_mb=100) is None, "cpu")
    check(lt.gpu_memory_message(argparse.Namespace(device="0", min_free_vram_mb=0), free_mb=1) is None, "disabled")
    lt.lower_process_priority()


def main():
    test_coords()
    test_classes_and_window()
    test_suppress_contained()
    test_model_families()
    test_merge_and_shape()
    test_dataset()
    test_init_weights()
    test_frames_lookup()
    test_config_and_status()
    test_gpu_backoff()
    print("pure checks ok")
    if "--train" in sys.argv:
        if "--weights" not in sys.argv:
            raise SystemExit("pass --weights /path/to/yolov8n.pt")
        weights = Path(sys.argv[sys.argv.index("--weights") + 1])
        test_cycle(weights)
        print("training cycle ok")


if __name__ == "__main__":
    main()
