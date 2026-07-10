"""
Fast Ad Remover - CLIP-based Classification
Uses CLIP (OpenAI) for fast zero-shot image classification.
Much faster than BLIP (5-10x speedup).
"""
import os
import sys
import shutil
from pathlib import Path

try:
    from PIL import Image
    import torch
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
    import warnings
    warnings.filterwarnings("ignore")
except ImportError:
    CLIP_AVAILABLE = False
    print("Error: Required packages not installed!")
    print("Install: pip install torch transformers pillow")
    sys.exit(1)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

def initialize_clip_model():
    """Initialize CLIP model (much faster than BLIP)."""
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Use smaller model for speed (ViT-B/32 is faster than ViT-L/14)
        model_name = "openai/clip-vit-base-patch32"
        
        print(f"Loading CLIP model: {model_name}")
        print(f"Device: {device}")
        
        processor = CLIPProcessor.from_pretrained(model_name)
        model = CLIPModel.from_pretrained(model_name)
        model = model.to(device)
        model.eval()
        
        # Disable gradients for speed
        torch.set_grad_enabled(False)
        
        print("CLIP model loaded successfully!")
        return processor, model, device
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        sys.exit(1)

def classify_image_clip(processor, model, image_path, device="cpu", debug=False):
    """
    Classify image using CLIP with text prompts.
    Returns: (is_ad, confidence, match_text, top_matches, all_probs)
    """
    try:
        # Text prompts for classification
        # Positive: live game content (generic + baseball specific)
        # Negative: ad/commercial/break graphics
        text_prompts = [
            "a live sports game with players on the field",
            "a sports match in progress on broadcast tv",
            "athletes actively playing a sport",
            "a baseball game live action on the field",
            "baseball pitcher and batter during a live play",
            "baseball home plate game camera during a live at-bat",
            "baseball infield or outfield action during live game",
            "scorebug overlay during a live sports match",
            "a sports advertisement",
            "a commercial advertisement on tv",
            "an advertisement with big text and logos",
            "a product close-up advertisement shot",
            "a sponsor board or promo full-screen graphic",
            "a tv commercial break bumper",
            "a replay transition graphic with branding",
            "a static ad card with logo and slogan"
        ]
        
        # Load and preprocess image
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            if debug:
                print(f"  Error loading image: {e}")
            return False, 0.0, None, [], []
        
        # Process image and text
        inputs = processor(text=text_prompts, images=image, return_tensors="pt", padding=True)
        
        # Move to device
        if device == "cuda":
            inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
        
        # Get CLIP embeddings
        with torch.no_grad():
            outputs = model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
        
        # Get probabilities
        probs_cpu = probs.cpu().numpy()[0]
        
        # First 8 prompts are gameplay-related (positive)
        # Last 8 prompts are ad/commercial-related (negative)
        sports_score = sum(probs_cpu[:8])  # Sum of first 8 (sports game)
        ad_score = sum(probs_cpu[8:])      # Sum of last 8 (advertisement)
        
        # If ad_score > sports_score, it's likely an ad
        is_ad = ad_score > sports_score
        confidence = max(ad_score, sports_score)
        
        # Determine which text matched best
        best_idx = probs_cpu.argmax()
        match_text = text_prompts[best_idx]
        
        # Get top 3 matches for detailed output
        top_indices = probs_cpu.argsort()[-3:][::-1]  # Top 3 in descending order
        top_matches = [(text_prompts[i], probs_cpu[i]) for i in top_indices]
        
        return is_ad, confidence, match_text, top_matches, probs_cpu
    except Exception as e:
        if debug:
            print(f"  Error in CLIP classification: {e}")
        return False, 0.0, None, [], []

def main(input_folder, threshold=0.5, debug=False):
    """
    Main function - CLIP-based Ad Detection
    
    Args:
        input_folder: Folder with images
        threshold: Confidence threshold (0.0-1.0)
        debug: If True, shows debug info
    """
    if not os.path.isdir(input_folder):
        print(f"Error: Folder '{input_folder}' does not exist")
        sys.exit(1)
    
    # Create ads folder in parent directory
    parent_dir = os.path.dirname(os.path.abspath(input_folder))
    ads_folder = os.path.join(parent_dir, "ads")
    os.makedirs(ads_folder, exist_ok=True)
    
    if debug:
        print("CLIP-based Ad Detection")
        print("=" * 50)
        print(f"Input folder: {input_folder}")
        print(f"Ads folder: {ads_folder}")
        print()
    
    # Initialize CLIP model
    processor, model, device = initialize_clip_model()
    
    if debug:
        print()
    
    # Get all images sorted by name
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(Path(input_folder).glob(f"*{ext}"))
        image_files.extend(Path(input_folder).glob(f"*{ext.upper()}"))
    
    image_files = [f for f in image_files if not str(f).startswith(ads_folder)]
    # Deduplicate paths (extension globbing can include duplicates on Windows).
    image_files = sorted({str(f) for f in image_files})
    
    if not image_files:
        print("No images found for processing")
        return
    
    if debug:
        print(f"Found {len(image_files)} images")
        print("Processing...")
        print()
    
    # Process images
    moved_count = 0
    confidences = []
    
    for i, image_path in enumerate(image_files):
        image_path_str = str(image_path)
        filename = os.path.basename(image_path_str)
        
        if (i + 1) % 500 == 0:
            print(f"  Processing {i+1}/{len(image_files)}...")
        
        is_ad, confidence, match_text, top_matches, all_probs = classify_image_clip(
            processor, model, image_path_str, device, debug
        )
        
        confidences.append(confidence)
        
        # Only move if confidence is above threshold
        if is_ad and confidence >= threshold:
            if not debug:
                try:
                    dest_path = os.path.join(ads_folder, filename)
                    shutil.move(image_path_str, dest_path)
                except Exception as e:
                    if debug:
                        print(f"Error moving {filename}: {e}")
            moved_count += 1
        
        # Always show detailed output (even if not debug mode, but only for first few images)
        if debug or i < 5:  # Show first 5 images even without --debug
            status = "AD" if (is_ad and confidence >= threshold) else "KEEP"
            match_short = match_text[:40] + "..." if match_text and len(match_text) > 40 else match_text
            
            print(f"\n{filename}:")
            print(f"  Decision: {status} | Confidence: {confidence:.3f}")
            print(f"  Best match: {match_text}")
            print(f"  Sports score: {sum(all_probs[:8]):.3f} | Ad score: {sum(all_probs[8:]):.3f}")
            print(f"  Top 3 matches:")
            for j, (prompt, prob) in enumerate(top_matches, 1):
                prompt_short = prompt[:50] + "..." if len(prompt) > 50 else prompt
                print(f"    {j}. {prompt_short}: {prob:.3f}")
            
            # Show all prompt scores if debug
            if debug and len(all_probs) > 0:
                # Define prompts here (same as in classify_image_clip)
                text_prompts = [
                    "a live sports game with players on the field",
                    "a sports match in progress on broadcast tv",
                    "athletes actively playing a sport",
                    "a baseball game live action on the field",
                    "baseball pitcher and batter during a live play",
                    "baseball home plate game camera during a live at-bat",
                    "baseball infield or outfield action during live game",
                    "scorebug overlay during a live sports match",
                    "a sports advertisement",
                    "a commercial advertisement on tv",
                    "an advertisement with big text and logos",
                    "a product close-up advertisement shot",
                    "a sponsor board or promo full-screen graphic",
                    "a tv commercial break bumper",
                    "a replay transition graphic with branding",
                    "a static ad card with logo and slogan"
                ]
                print(f"  All prompt scores:")
                for j, (prompt, prob) in enumerate(zip(text_prompts, all_probs), 1):
                    prompt_short = prompt[:45] + "..." if len(prompt) > 45 else prompt
                    print(f"    {j:2d}. {prompt_short}: {prob:.3f}")
    
    if debug:
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)
            print()
            print("=" * 50)
            print(f"Confidence stats:")
            print(f"  Average: {avg_conf:.3f}")
            print(f"  Min: {min_conf:.3f}")
            print(f"  Max: {max_conf:.3f}")
            print(f"  Moved to ads: {moved_count} images (threshold: {threshold})")
    else:
        print(f"Moved to ads: {moved_count} images")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fast_ad_remover_clip.py <images_folder> [threshold] [--debug]")
        print()
        print("CLIP-based Ad Detection:")
        print("  - Uses CLIP (OpenAI) for fast zero-shot classification")
        print("  - Much faster than BLIP (5-10x speedup)")
        print("  - Compares images with text prompts:")
        print("    * 'sports game' vs 'advertisement'")
        print("  - Works for all sports: tennis, cricket, rugby, football, etc.")
        print()
        print("Examples:")
        print("  1. Normal mode:")
        print("     python fast_ad_remover_clip.py C:\\images")
        print()
        print("  2. Custom threshold (0.6 = more strict):")
        print("     python fast_ad_remover_clip.py C:\\images 0.6")
        print()
        print("  3. Debug mode:")
        print("     python fast_ad_remover_clip.py C:\\images --debug")
        print()
        print("Note: First run will download CLIP model (~150MB)")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    threshold = 0.5
    debug = False
    
    # Parse arguments
    for arg in sys.argv[2:]:
        if arg == '--debug':
            debug = True
        elif not arg.startswith('--'):
            try:
                threshold = float(arg)
            except ValueError:
                pass
    
    main(input_folder, threshold, debug)

