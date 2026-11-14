# anno_live

Ζωντανή εκπαίδευση YOLO όσο δουλεύει το annotool. Το `main` δεν αλλάζει· αυτός ο φάκελος είναι καινούργιος.

Το εργαλείο γράφει `annotool_live.json` στον φάκελο συγχρονισμού. Αυτό το script το διαβάζει, φτιάχνει dataset μόνο από τα reviewed καρέ, εκπαιδεύει, και γράφει προτάσεις πίσω. Δεν κατεβάζει βάρη και δεν γράφει μέσα στο repo.

## Εντολή

Διπλό κλικ στο `anno_live\start_live_trainer.bat`, ή από τη ρίζα του repo:

```bat
anno_live\start_live_trainer.bat
```

Το bat δουλεύει με αυτά τα paths:

- sync: `C:\Users\jimts\Documents\projects\live_sync`
- frames root: `D:\downloads` (ψάχνει μόνο του τον φάκελο του project)
- work: `C:\Users\jimts\Documents\projects\live_work`
- βάρη: το πρώτο argument, αλλιώς `C:\Users\jimts\Documents\projects\yolov8s.pt`

Άλλο αρχείο βαρών, χωρίς να αλλάξεις το bat:

```bat
anno_live\start_live_trainer.bat D:\models\yolov8s.pt
```

Η ίδια εκκίνηση χωρίς το bat. Το `--frames-folder` δεν χρειάζεται: το `project` μέσα στο `annotool_live.json` είναι και το όνομα του φακέλου με τα jpg, π.χ. `part8_reduced_20261017_RLWC_MensEnglandvTonga_Live_Seven_1930-cluster_7`.

```bat
python anno_live\live_trainer.py --sync-folder C:\Users\jimts\Documents\projects\live_sync --frames-root D:\downloads --work-dir C:\Users\jimts\Documents\projects\live_work --base-weights C:\Users\jimts\Documents\projects\yolov8s.pt --device 0
```

Ένας μόνο κύκλος και έξοδος:

```bat
python anno_live\live_trainer.py --sync-folder C:\Users\jimts\Documents\projects\live_sync --frames-root D:\downloads --work-dir C:\Users\jimts\Documents\projects\live_work --base-weights C:\Users\jimts\Documents\projects\yolov8s.pt --device 0 --once
```

`--frames-root` επαναλαμβάνεται αν τα projects είναι σε παραπάνω από έναν δίσκο. `--frames-folder` παραμένει, και αν το δώσεις κερδίζει την αναζήτηση. `--sync-folder` είναι ο φάκελος που διαλέγεις στο **Ζωντανά**. `--work-dir` είναι για datasets και runs, έξω από το repo και έξω από τον φάκελο sync. `--base-weights` είναι αρχείο στο δίσκο. Αν το αρχείο λείπει, το script σταματάει· δεν το κατεβάζει.

Στην RTX 5070 Laptop 8GB: `--device 0`, AMP κλειστό (το default), `--batch 4`. Αν η μνήμη το σηκώνει, δοκίμασε `--batch 8`.

## Τι κάνει κάθε κύκλος

1. Περιμένει reviewed καρέ. Ο πρώτος κύκλος ξεκινάει στα `--min-reviewed` (40). Οι επόμενοι κάθε `--every` (30) καινούργια reviewed από το πλήθος τη στιγμή που άνοιξε ο προηγούμενος κύκλος.
2. Dataset μόνο από reviewed. Κλάση είναι `brand|tpoint`. Ένα κουτί ανά instance (`hits` δεν πολλαπλασιάζει το κουτί). Reviewed χωρίς κουτί = αρνητικό. Καρέ που δεν είναι ούτε στο `reviewed` ούτε στα `images` δεν μπαίνουν ως αρνητικά.
3. Τα κουτιά είναι σε συντεταγμένες καμβά (`width`/`height` του annotool, π.χ. 1141×642). Πριν τη κανονικοποίηση YOLO μεταφέρονται στο μέγεθος του αρχείου jpg.
4. Η λίστα κλάσεων μένει σταθερή ανάμεσα σε κύκλους (οι καινούργιες μπαίνουν στο τέλος). Ο πρώτος κύκλος και κάθε κύκλος με καινούργια κλάση ξεκινάει από τα base weights. Αλλιώς γίνεται fine-tune από το προηγούμενο `best.pt`.
5. Μετά την εκπαίδευση ξαναδιαβάζει το live αρχείο. Προβλέπει τα επόμενα `--lookahead` (150) καρέ που δεν είναι reviewed και δεν έχουν κουτιά, ξεκινώντας `--predict-margin` (20) καρέ μετά το τρέχον `currentImage`, γιατί αυτά τα προλαβαίνει όσο τρέχει το μοντέλο.
6. Οι καινούργιες προβλέψεις συγχωνεύονται με τις παλιές. Καρέ πίσω του, reviewed, ή με δικά του κουτιά, φεύγουν. Καρέ μπροστά του που αυτός ο γύρος δεν τα ξαναείδε κρατάνε τις παλιές προτάσεις. Όπου έτρεξε το καινούργιο μοντέλο, κερδίζει εκείνο, ακόμη κι αν δεν βρήκε τίποτα.

Προεπιλογές για κύκλο λίγων λεπτών στην 5070 όταν μαζευτούν μερικές εκατοντάδες ή χιλιάδες καρέ: `--epochs 20` από την αρχή, `--finetune-epochs 8` μετά, `--imgsz 640`, `--batch 4`, `--workers 0` στα Windows (2 αλλού), AMP off, `conf 0.25`, `iou 0.5`, agnostic NMS. Οι πρώτοι κύκλοι με ~40 καρέ τελειώνουν γρηγορότερα. Εκπαίδευση από τα base weights: SGD, `lr0=0.01`. Fine-tune: AdamW, `lr0=0.001`. Το ultralytics αγνοεί το `lr0` όταν ο optimizer είναι `auto`, οπότε ο trainer τον ορίζει ρητά.

Άλλα flags: `--patience` (default 100, οπότε οι σύντομοι κύκλοι δεν κόβονται νωρίς), `--val-fraction` (default 0.1, σταθερό ανά καρέ), `--poll-seconds` (default 5), `--lr0`, `--amp` για να ανάψεις το AMP.

Στον φάκελο sync γράφει μόνο:

- `annotool_predictions.json`
- `live_trainer_status.json`

Για atomic εγγραφή εμφανίζεται για μια στιγμή ένα `.<όνομα>.<pid>.tmp` δίπλα τους και μετά γίνεται replace. Κάθε project έχει δικό του υποφάκελο `<work-dir>\<project>\` με `state.json`, `best.pt`, dataset και runs. Αν το `project` στο live αρχείο αλλάξει, ο trainer βρίσκει τον καινούργιο φάκελο καρέ και φορτώνει το μοντέλο εκείνου του project· δεν ανακατεύει κλάσεις ούτε βάρη. Η αναζήτηση αποθηκεύεται στο `<work-dir>\frames_cache.json` και δεν ξανατρέχει σε κάθε poll. Αν ο φάκελος δεν βρεθεί, το `last_error` λέει το project και τα roots, το `state` μένει `idle`, και δεν ξεκινάει κύκλος. Προβλέψεις που γράφτηκαν για άλλο project σβήνονται, γιατί τα stems (`00001`…) επαναλαμβάνονται από ματς σε ματς. Αν σβήσεις τον υποφάκελο ενός project, η λίστα κλάσεων και ο κύκλος εκείνου του project ξεκινούν από την αρχή.

## `live_trainer_status.json`

Το annotool το δείχνει όπως είναι. `schema` είναι 1. Όλα τα κλειδιά υπάρχουν πάντα· ό,τι δεν είναι γνωστό ακόμη είναι `null`.

| Πεδίο | Τιμή |
| --- | --- |
| `schema` | `1` |
| `state` | `idle`, `training`, ή `predicting` |
| `project` | Το `project` του live αρχείου. `null` πριν διαβαστεί |
| `frames_folder` | Ο φάκελος jpg που χρησιμοποιείται (από `--frames-folder` ή από την αναζήτηση). `null` αν δεν βρέθηκε |
| `cycle` | Ολοκληρωμένοι κύκλοι· όσο τρέχει εκπαίδευση είναι ο κύκλος που είναι ανοιχτός |
| `reviewed` | Πλήθος μοναδικών ονομάτων στο `reviewed` |
| `reviewed_since_last_cycle` | Πόσα reviewed μαζεύτηκαν μετά το snapshot του τελευταίου κύκλου |
| `next_cycle_at` | Κατώφλι. Ο επόμενος κύκλος ανοίγει όταν το `reviewed` φτάσει αυτόν τον αριθμό, όχι ώρα |
| `predicted_frames` | Πόσα καρέ έχουν κουτιά μέσα στο τρέχον `annotool_predictions.json` |
| `predicted_from` | Πρώτο καρέ του αρχείου προβλέψεων, στη σειρά των frames (stem, ή `folder/stem`) |
| `predicted_to` | Τελευταίο καρέ του ίδιου αρχείου |
| `classes` | Σταθερή λίστα `brand\|tpoint`, με τη σειρά των indices |
| `last_map50` | mAP50 του καλύτερου epoch του τελευταίου κύκλου (το υψηλότερο mAP50-95). Κατά την εκπαίδευση ενημερώνεται σε κάθε epoch |
| `epoch` | Epoch που μόλις τελείωσε, από 1. `0` πριν τελειώσει το πρώτο. `null` αν δεν έχει τρέξει κύκλος |
| `epochs` | Πόσα epoch έχει αυτός ο κύκλος |
| `updated_at` | ISO-8601 UTC, αλλάζει σε κάθε εγγραφή |
| `last_error` | Σφάλμα του τελευταίου κύκλου, ή ότι ο φάκελος καρέ δεν βρέθηκε (με το όνομα του project και τα roots). Αλλιώς `null` |
| `current_image` | Το `currentImage` του live αρχείου |
| `weights` | Το `best.pt` που χρησιμοποιείται για προβλέψεις |
| `message` | Σύντομο ελληνικό κείμενο για την οθόνη |
| `started_at` | Πότε άνοιξε αυτή η διαδικασία |
| `device` | Τι δόθηκε στο `--device`, ή `auto` |
| `from_base` | `true` αν ο τελευταίος κύκλος ξεκίνησε από τα base weights |
| `train_images` | Καρέ train του τελευταίου dataset |
| `val_images` | Καρέ val του τελευταίου dataset |

Παράδειγμα όσο περιμένει τον πρώτο κύκλο:

```json
{
  "schema": 1,
  "state": "idle",
  "project": "part8_reduced_20261017_RLWC_MensEnglandvTonga_Live_Seven_1930-cluster_7",
  "frames_folder": "D:\\downloads\\season\\part8_reduced_20261017_RLWC_MensEnglandvTonga_Live_Seven_1930-cluster_7",
  "cycle": 0,
  "reviewed": 12,
  "reviewed_since_last_cycle": 12,
  "next_cycle_at": 40,
  "predicted_frames": 0,
  "predicted_from": null,
  "predicted_to": null,
  "classes": [],
  "last_map50": null,
  "epoch": null,
  "epochs": null,
  "updated_at": "2026-11-14T18:00:00+00:00",
  "last_error": null,
  "current_image": "00048",
  "weights": null,
  "message": "Αναμονή · 12/40 reviewed",
  "started_at": "2026-11-14T17:50:00+00:00",
  "device": "0",
  "from_base": null,
  "train_images": null,
  "val_images": null
}
```

Το `epoch` / `epochs` έρχονται από callback του ultralytics (`on_fit_epoch_end`) σε κάθε epoch.

## `annotool_predictions.json`

Ίδιο σχήμα με το export του annotool / το `predict_to_json.py`: `project`, `imageNum`, `prefs`, `images`, `currentImage`, `presets`, `Annotator`. Κάθε καρέ έχει `imageName`, `imageIndex`, `width`, `height`, `annotations`, `exifdata`. Κάθε κουτί έχει `startPoint`, `diagPoint`, `group`, `brand`, `tpoint`, `hits` (πάντα 1), `confidence`. Ένα κουτί ανά instance, χωρίς συγχώνευση ίδιου `brand|tpoint`. Οι συντεταγμένες είναι στον καμβά του live αρχείου για αυτό το καρέ, αλλιώς στο πιο συχνό `width`/`height`.

## Δοκιμή

Χωρίς εκπαίδευση:

```bat
python anno_live\test_live_trainer.py
```

Ένας μικρός κύκλος σε CPU, με τοπικό `yolov8n.pt`:

```bat
python anno_live\test_live_trainer.py --train --weights D:\models\yolov8n.pt
```

## Σημειώσεις

Τα `anno2026/scripts/predict_to_json.py`, `convert_to_yolo.py`, `train.py` και τα `anno_video/NEW_PROJECT_RUNBOOK.md` / `annotation_playbook.md` δεν υπάρχουν σε αυτό το checkout, οπότε ο κώδικας δεν τα κάνει import. Ακολουθεί το συμβόλαιό τους: κλάσεις `brand|tpoint`, μετατροπή καμβά → αρχείο όπως το `LogoDetection/annoToYOLO.py`, `conf 0.25`, `iou 0.5`, agnostic NMS, AMP κλειστό.

Ο κύκλος δοκιμάστηκε εδώ σε CPU με `yolov8n` και συνθετικά jpg, όχι στην RTX 5070. Το `best.pt` αντιγράφεται στο `<work-dir>\<project>\best.pt`. Αν η εκπαίδευση τελειώσει και οι προβλέψεις αποτύχουν, η επόμενη εκκίνηση συνεχίζει από τις προβλέψεις χωρίς να ξαναεκπαιδεύσει τον ίδιο κύκλο. Η πρώτη εκκίνηση του ultralytics μπορεί να κατεβάσει μία φορά το `Arial.ttf` για plots, ακόμη και με plots κλειστά· τα βάρη δεν κατεβαίνουν.
