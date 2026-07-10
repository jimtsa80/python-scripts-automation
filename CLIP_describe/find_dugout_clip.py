"""
Find baseball dugout images with CLIP (text + optional image examples).

Usage example:
python find_dugout_clip.py ^
  --input "F:\\downloads\\batch10\\20260407_TripleA_IowaCubs\\reduced_20260407_TripleA_IowaCubs" ^
  --refs "C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\CLIP_describe\\dugout"
"""

import argparse
import csv
import shutil
from pathlib import Path
from typing import List, Sequence

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

DEFAULT_TEXT_PROMPTS = [
    # TruGreen-specific (when branding is visible)
    "baseball dugout with TruGreen advertisement",
    "TruGreen dugout back sign in baseball stadium",
    "TruGreen dugout lip advertisement in baseball game",
    "TruGreen dugout railing advertisement during baseball broadcast",
    "baseball dugout bench area with green TruGreen branding board",
    "TruGreen logo on baseball dugout back wall",
    "TruGreen branding on dugout lip ledge in minor league baseball",
    "TruGreen sponsor sign on dugout railing fence",
    # Generic dugout (when logo is not visible)
    "baseball dugout bench area with players and coaches",
    "baseball dugout back wall and bench during a game",
    "baseball dugout lip and front edge near the field",
    "baseball dugout railing and fence along the bench",
    "camera view of a baseball dugout from the field",
    "minor league baseball dugout interior shot",
]

NEGATIVE_TEXT_PROMPTS = [
    "baseball field gameplay with pitcher and batter, no dugout ad",
    "baseball crowd shot and stands, no dugout signage",
    "close-up player shot without dugout background",
    "scoreboard or replay graphic, not dugout railing",
    "baseball infield grass and dirt with no dugout advertisement",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find dugout frames using CLIP text+image similarity."
    )
    parser.add_argument("--input", required=True, help="Root folder to scan recursively.")
    parser.add_argument(
        "--refs",
        default=None,
        help="Folder with example dugout images (optional but recommended).",
    )
    parser.add_argument(
        "--output-name",
        default="dugout_only",
        help="Output folder name created under input root.",
    )
    parser.add_argument(
        "--model",
        default="openai/clip-vit-base-patch32",
        help="CLIP model id from HuggingFace.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.42,
        help="Final strict score threshold.",
    )
    parser.add_argument(
        "--text-weight",
        type=float,
        default=0.55,
        help="Weight for text score in final score (0..1).",
    )
    parser.add_argument(
        "--min-pos-score",
        type=float,
        default=0.30,
        help="Minimum positive text similarity.",
    )
    parser.add_argument(
        "--min-ref-score",
        type=float,
        default=0.29,
        help="Minimum similarity to reference images.",
    )
    parser.add_argument(
        "--min-margin",
        type=float,
        default=0.08,
        help="Minimum (positive text score - negative text score).",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=0,
        help="If >0, select top-N by final score (overrides threshold mode).",
    )
    parser.add_argument(
        "--target-percent",
        type=float,
        default=0.0,
        help="If >0, select top percent by final score, e.g. 2.0 = top 2%%.",
    )
    parser.add_argument(
        "--also-ref-above",
        type=float,
        default=0.0,
        help="Also include images with ref_score >= this (hybrid recall boost).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max images to process (0 = all).",
    )
    parser.add_argument(
        "--copy-mode",
        choices=["copy", "move"],
        default="copy",
        help="Copy or move matched images to output folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only evaluate and print stats, do not copy/move files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-image decisions.",
    )
    return parser.parse_args()


def list_images(root: Path) -> List[Path]:
    images: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(p)
    return sorted(images)


def load_clip(model_name: str):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name).to(device)
    model.eval()
    torch.set_grad_enabled(False)
    return processor, model, device


def encode_texts(
    processor: CLIPProcessor,
    model: CLIPModel,
    device: str,
    texts: Sequence[str],
) -> torch.Tensor:
    inputs = processor(text=list(texts), return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    return text_features / text_features.norm(dim=-1, keepdim=True)


def encode_image(
    processor: CLIPProcessor,
    model: CLIPModel,
    device: str,
    image_path: Path,
) -> torch.Tensor:
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
    return image_features / image_features.norm(dim=-1, keepdim=True)


def build_reference_features(
    refs_dir: Path | None,
    processor: CLIPProcessor,
    model: CLIPModel,
    device: str,
) -> torch.Tensor | None:
    if refs_dir is None or not refs_dir.is_dir():
        return None
    ref_images = list_images(refs_dir)
    if not ref_images:
        return None

    rows: List[torch.Tensor] = []
    for ref_path in ref_images:
        try:
            rows.append(encode_image(processor, model, device, ref_path))
        except Exception as exc:
            print(f"[WARN] Cannot encode ref image {ref_path}: {exc}")
    if not rows:
        return None
    return torch.cat(rows, dim=0)


def safe_relative_path(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def main() -> None:
    args = parse_args()
    input_root = Path(args.input).resolve()
    refs_dir = Path(args.refs).resolve() if args.refs else None
    output_root = input_root / args.output_name

    if not input_root.is_dir():
        raise SystemExit(f"Input folder not found: {input_root}")

    print(f"Input root: {input_root}")
    print(f"Refs dir:   {refs_dir if refs_dir else '(none)'}")
    print(f"Output dir: {output_root}")
    print(f"Threshold:  {args.threshold:.3f}")
    print(f"Text weight:{args.text_weight:.2f}")
    print(f"Min pos:    {args.min_pos_score:.3f}")
    print(f"Min ref:    {args.min_ref_score:.3f}")
    print(f"Min margin: {args.min_margin:.3f}")
    if args.target_count > 0:
        print(f"Selection:  top-{args.target_count} by score")
    elif args.target_percent > 0:
        print(f"Selection:  top-{args.target_percent:.2f}% by score")
    else:
        print("Selection:  threshold mode")
    if args.also_ref_above > 0:
        print(f"Recall boost: ref_score >= {args.also_ref_above:.3f}")
    print("-" * 60)

    processor, model, device = load_clip(args.model)
    text_features = encode_texts(processor, model, device, DEFAULT_TEXT_PROMPTS)
    neg_text_features = encode_texts(processor, model, device, NEGATIVE_TEXT_PROMPTS)
    ref_features = build_reference_features(refs_dir, processor, model, device)

    print(f"Device: {device}")
    print(f"Prompts loaded: {len(DEFAULT_TEXT_PROMPTS)}")
    print(f"Reference images loaded: {0 if ref_features is None else ref_features.shape[0]}")
    print("-" * 60)

    all_images = list_images(input_root)
    # Avoid scanning output folder from previous runs.
    all_images = [p for p in all_images if args.output_name not in p.parts]
    if args.limit and args.limit > 0:
        all_images = all_images[: args.limit]

    if not all_images:
        print("No images found to process.")
        return

    if not args.dry_run:
        output_root.mkdir(parents=True, exist_ok=True)

    processed = 0
    scored_rows = []

    for image_path in all_images:
        processed += 1
        try:
            image_feature = encode_image(processor, model, device, image_path)
            text_sims = (image_feature @ text_features.T).squeeze(0)
            pos_text_score = float(text_sims.max().item())
            text_idx = int(text_sims.argmax().item())
            best_prompt = DEFAULT_TEXT_PROMPTS[text_idx]
            neg_sims = (image_feature @ neg_text_features.T).squeeze(0)
            neg_text_score = float(neg_sims.max().item())
            margin_score = pos_text_score - neg_text_score

            if ref_features is not None:
                ref_sims = (image_feature @ ref_features.T).squeeze(0)
                ref_score = float(ref_sims.max().item())
            else:
                ref_score = pos_text_score

            # Strict scoring:
            # - high positive similarity
            # - low similarity to negative prompts (via margin)
            # - high similarity to reference dugout images
            final_score = (
                args.text_weight * pos_text_score
                + (1.0 - args.text_weight) * ref_score
                + 0.15 * margin_score
            )
            threshold_match = (
                final_score >= args.threshold
                and pos_text_score >= args.min_pos_score
                and ref_score >= args.min_ref_score
                and margin_score >= args.min_margin
            )
            scored_rows.append(
                {
                    "image": image_path,
                    "threshold_match": threshold_match,
                    "final_score": final_score,
                    "text_score": pos_text_score,
                    "neg_text_score": neg_text_score,
                    "margin_score": margin_score,
                    "ref_score": ref_score,
                    "best_prompt": best_prompt,
                }
            )

            if args.verbose:
                status = "CANDIDATE" if threshold_match else "SKIP"
                print(
                    f"[{status}] {image_path.name} | final={final_score:.3f} "
                    f"pos={pos_text_score:.3f} neg={neg_text_score:.3f} "
                    f"margin={margin_score:.3f} ref={ref_score:.3f}"
                )

            if processed % 250 == 0:
                print(f"Processed {processed}/{len(all_images)}")

        except Exception as exc:
            print(f"[WARN] Failed image {image_path}: {exc}")

    # Final selection: threshold mode (default) or top-N/top-percent mode.
    selected_paths: dict[Path, str] = {}
    if args.target_count > 0 or args.target_percent > 0:
        candidates = [
            row
            for row in scored_rows
            if row["text_score"] >= args.min_pos_score
            and row["ref_score"] >= args.min_ref_score
            and row["margin_score"] >= args.min_margin
        ]
        ranked = sorted(candidates, key=lambda r: r["final_score"], reverse=True)
        if args.target_count > 0:
            keep_n = min(args.target_count, len(ranked))
        else:
            pct = max(0.0, min(args.target_percent, 100.0))
            keep_n = int(round((pct / 100.0) * len(ranked)))
            if pct > 0 and keep_n == 0 and ranked:
                keep_n = 1
        for row in ranked[:keep_n]:
            selected_paths[row["image"]] = "top_rank"
        print(
            f"Ranking pool: {len(candidates)} candidates passed quality filters, "
            f"keeping top {keep_n}"
        )
    else:
        for row in scored_rows:
            if row["threshold_match"]:
                selected_paths[row["image"]] = "threshold"

    # Hybrid recall: also grab high ref-similarity frames missed by ranking cutoff.
    if args.also_ref_above > 0:
        ref_boost_count = 0
        for row in scored_rows:
            if row["image"] in selected_paths:
                continue
            if (
                row["ref_score"] >= args.also_ref_above
                and row["text_score"] >= max(0.0, args.min_pos_score - 0.02)
                and row["margin_score"] >= max(0.0, args.min_margin - 0.005)
            ):
                selected_paths[row["image"]] = "ref_boost"
                ref_boost_count += 1
        print(f"Ref boost added: {ref_boost_count} extra images (ref >= {args.also_ref_above:.3f})")

    # Copy/move selected files.
    if not args.dry_run:
        for row in scored_rows:
            image_path = row["image"]
            if image_path not in selected_paths:
                continue
            rel = safe_relative_path(image_path, input_root)
            dest = output_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if args.copy_mode == "move":
                shutil.move(str(image_path), str(dest))
            else:
                shutil.copy2(str(image_path), str(dest))

    matches = len(selected_paths)
    report_rows = []
    for row in scored_rows:
        image_path = row["image"]
        report_rows.append(
            {
                "image": str(image_path),
                "is_dugout": int(image_path in selected_paths),
                "selection_reason": selected_paths.get(image_path, ""),
                "threshold_match": int(row["threshold_match"]),
                "final_score": f"{row['final_score']:.4f}",
                "text_score": f"{row['text_score']:.4f}",
                "neg_text_score": f"{row['neg_text_score']:.4f}",
                "margin_score": f"{row['margin_score']:.4f}",
                "ref_score": f"{row['ref_score']:.4f}",
                "best_prompt": row["best_prompt"],
            }
        )

    # Save CSV report inside input root.
    report_path = input_root / "dugout_clip_report.csv"
    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image",
                "is_dugout",
                "selection_reason",
                "threshold_match",
                "final_score",
                "text_score",
                "neg_text_score",
                "margin_score",
                "ref_score",
                "best_prompt",
            ],
        )
        writer.writeheader()
        writer.writerows(report_rows)

    print("-" * 60)
    print(f"Total images processed: {processed}")
    print(f"Total dugout matches:   {matches}")
    print(f"Match ratio:            {((matches / processed) * 100):.2f}%")
    print(f"Output folder:          {output_root}")
    print(f"CSV report:             {report_path}")
    if args.dry_run:
        print("Dry-run mode: no files copied/moved.")


if __name__ == "__main__":
    main()

