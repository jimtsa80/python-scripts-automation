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
python anno_live\live_trainer.py --sync-folder C:\Users\jimts\Documents\projects\live_sync --frames-root D:\downloads --work-dir C:\Users\jimts\Documents\projects\live_work --base-weights C:\Users\jimts\Documents\projects\yolov8s.pt --device 0 --batch 4 --workers 2 --gpu-mem-fraction 0.7 --min-free-vram-mb 1536
```

Ένας μόνο κύκλος και έξοδος:

```bat
python anno_live\live_trainer.py --sync-folder C:\Users\jimts\Documents\projects\live_sync --frames-root D:\downloads --work-dir C:\Users\jimts\Documents\projects\live_work --base-weights C:\Users\jimts\Documents\projects\yolov8s.pt --device 0 --once
```

`--frames-root` επαναλαμβάνεται αν τα projects είναι σε παραπάνω από έναν δίσκο. `--frames-folder` παραμένει, και αν το δώσεις κερδίζει την αναζήτηση. `--sync-folder` είναι ο φάκελος που διαλέγεις στο **Ζωντανά**. `--work-dir` είναι για datasets και runs, έξω από το repo και έξω από τον φάκελο sync. `--base-weights` είναι αρχείο στο δίσκο. Αν το αρχείο λείπει, το script σταματάει· δεν το κατεβάζει.

Η αναζήτηση δεν διαβάζει όλο το `D:\downloads`. Πρώτα κοιτάει το συνηθισμένο μονοπάτι `<root>\batchNN\<match>\reduced_<match>\<project>` (ο φάκελος του project έχει jpg μέσα του). Αλλιώς περπατάει μέχρι `--frames-max-depth` (default 6), σταματάει στον πρώτο φάκελο με ακριβώς αυτό το όνομα και jpg απευθείας μέσα του, και δεν μπαίνει σε φακέλους που είναι ήδη frames (πολλά jpg). Πριν ξεκινήσει, το status γίνεται `searching` με μήνυμα `Αναζήτηση φακέλου frames για <project>…`. Το αποτέλεσμα γράφεται στο `<work-dir>\frames_cache.json`· η επόμενη εκκίνηση το διαβάζει και δεν ξαναψάχνει.

Στην RTX 5070 Laptop 8GB, με τον browser ανοιχτό για annotation: `--device 0`, AMP κλειστό (το default), `--batch 4`, `--workers 2`, `--gpu-mem-fraction 0.7` (το process δεν παίρνει πάνω από ~70% της VRAM), `--min-free-vram-mb 1536` (αν η ελεύθερη VRAM είναι από κάτω, περιμένει πριν από train ή predict). Το `cache` μένει κλειστό, ώστε οι εικόνες να μην φορτώνονται όλες στη RAM. Στα Windows η διεργασία πέφτει σε below-normal priority (psutil, αλλιώς `SetPriorityClass`). Αν η κάρτα γεμίσει (`CUDA out of memory`, και όταν τρέχει άλλο GPU job), αδειάζει την cache, περιμένει `--oom-wait` δευτερόλεπτα (default 45), ξαναδοκιμάζει με το μισό batch (μέχρι 1) και μετά με `--workers 0`. Το `--imgsz` δεν αλλάζει. Το `state` γίνεται `waiting_gpu` και το `last_error` καθαρίζει μόλις ο επόμενος κύκλος ή οι προβλέψεις πετύχουν.

## Τι κάνει κάθε κύκλος

1. Περιμένει reviewed καρέ. Ο πρώτος κύκλος ξεκινάει στα `--min-reviewed` (40). Οι επόμενοι κάθε `--every` (30) καινούργια reviewed από το πλήθος τη στιγμή που άνοιξε ο προηγούμενος κύκλος.
2. Dataset από τα reviewed καρέ όλης της οικογένειας, όχι μόνο του τρέχοντος project. Κλάση είναι `brand|tpoint`. Ένα κουτί ανά instance (`hits` δεν πολλαπλασιάζει το κουτί). Reviewed χωρίς κουτί = αρνητικό. Καρέ που δεν είναι ούτε στο `reviewed` ούτε στα `images` δεν μπαίνουν ως αρνητικά. Το `rejected` του live αρχείου (`imageName` → λίστα `{brand, tpoint, x, y, width, height, confidence}` σε pixels καμβά, ίδια αρχή με το `startPoint`) είναι hard negatives: αν το καρέ είναι και reviewed, μπαίνει στο dataset (άδειο label αν δεν έχει δικά του κουτιά) και επαναλαμβάνεται 3 φορές στο train. Απόρριψη σε καρέ που δεν είναι reviewed αγνοείται. Το πλήθος μοναδικών τέτοιων καρέ γράφεται στο `hard_negative_frames`.
3. Τα κουτιά είναι σε συντεταγμένες καμβά (`width`/`height` του annotool, π.χ. 1141×642). Πριν τη κανονικοποίηση YOLO μεταφέρονται στο μέγεθος του αρχείου jpg.
4. Η λίστα κλάσεων της οικογένειας μένει σταθερή (οι καινούργιες μπαίνουν στο τέλος, τα ids δεν αλλάζουν και καμία παλιά κλάση δεν σβήνεται). Η οικογένεια είναι το `modelFamily` του live αρχείου, αλλιώς το πρώτο `prefs.groups` (π.χ. `2026 RLWC`), αλλιώς `default`. Η βιβλιοθήκη είναι `<work-dir>\models\<οικογένεια>\`: `best.pt`, το προηγούμενο `best_prev.pt`, `meta.json` (κλάσεις και per-class mAP) και `dataset.json` με τα reviewed labels κάθε project της οικογένειας (φάκελος καρέ, work dir, κουτιά). Κάθε κύκλος εκπαιδεύεται στην ένωση αυτών των project. Πάνω από `--max-family-images` (default 1500) κρατάει πρόσφατα καρέ και μερίδιο από κάθε κλάση, ώστε να χωράει στην 8GB. Καινούργιο project σε οικογένεια που έχει ήδη μοντέλο: προβλέψεις αμέσως σε όλα τα μη-reviewed καρέ (από το πρώτο καρέ, πριν από εκπαίδευση), μετά κύκλοι βελτίωσης από το `best.pt` της οικογένειας (λίγα epochs), ακόμη κι αν ο κύκλος δεν είναι ο πρώτος. Αν το `best.pt` της οικογένειας αλλάξει, ένα project ξαναπαίρνει προβλέψεις όταν το αποθηκευμένο αποτύπωμα (mtime, μέγεθος, sha1) είναι παλιότερο· δεν χρειάζεται χειροκίνητο `state.json`. Καινούργια οικογένεια ξεκινάει από τα `--base-weights`. Μετά από κάθε επιτυχημένο κύκλο το `best.pt` της οικογένειας αντικαθίσταται, εκτός αν λείπει κλάση που η οικογένεια ήδη ήξερε. Χαμηλότερο mAP50 δεν κρατάει το παλιό αρχείο. Το `modelChoice` είναι `continue` (προεπιλογή), `new` (από τα base weights, χωρίς το παλιό μοντέλο), ή `from:<οικογένεια>`. Το `--init-weights` χρησιμοποιείται μόνο στον πρώτο κύκλο όταν η επιλογή είναι `continue` και η οικογένεια δεν έχει ακόμη μοντέλο. Αν κανένα project της οικογένειας δεν έχει κουτί λογότυπου, ο κύκλος δεν ξεκινάει: το status μένει `idle` με μήνυμα `Αναμονή · δεν υπάρχουν κουτιά λογότυπου στην οικογένεια` και χωρίς `last_error`.
5. Μετά την εκπαίδευση ξαναδιαβάζει το live αρχείο. Προβλέπει τα επόμενα `--lookahead` (150) καρέ που δεν είναι reviewed και δεν έχουν κουτιά, ξεκινώντας `--predict-margin` (20) καρέ μετά το τρέχον `currentImage`, γιατί αυτά τα προλαβαίνει όσο τρέχει το μοντέλο.
6. Οι καινούργιες προβλέψεις συγχωνεύονται με τις παλιές. Καρέ πίσω του, reviewed, ή με δικά του κουτιά, φεύγουν. Καρέ μπροστά του που αυτός ο γύρος δεν τα ξαναείδε κρατάνε τις παλιές προτάσεις. Όπου έτρεξε το καινούργιο μοντέλο, κερδίζει εκείνο, ακόμη κι αν δεν βρήκε τίποτα.

Προεπιλογές για κύκλο λίγων λεπτών στην 5070 όταν μαζευτούν μερικές εκατοντάδες ή χιλιάδες καρέ, χωρίς να κολλάει ο browser: `--epochs 20` από την αρχή, `--finetune-epochs 8` μετά, `--imgsz 640`, `--batch 4`, `--workers 2`, `--gpu-mem-fraction 0.7`, `--min-free-vram-mb 1536`, `--oom-wait 45`, AMP off, `cache` κλειστό, `conf 0.25`, `iou 0.3`, agnostic NMS. Μετά το NMS, `--contain` (default 0.6) πετάει το κουτί με το μικρότερο confidence όταν η τομή καλύπτει τουλάχιστον αυτό το ποσοστό της επιφάνειας του μικρότερου κουτιού, ανεξάρτητα από κλάση. Έτσι δύο προβλέψεις που πέφτουν η μία πάνω στην άλλη στο ίδιο καρέ μένουν μία, η πιο σίγουρη. `--contain 0` κλείνει αυτό το πέρασμα. Οι πρώτοι κύκλοι με ~40 καρέ τελειώνουν γρηγορότερα. Εκπαίδευση από τα base weights: SGD, `lr0=0.01`. Fine-tune: AdamW, `lr0=0.001`. Το ultralytics αγνοεί το `lr0` όταν ο optimizer είναι `auto`, οπότε ο trainer τον ορίζει ρητά.

Άλλα flags: `--init-weights` (τοπικό `.pt` για τον πρώτο κύκλο νέου project), `--frames-max-depth` (default 6), `--patience` (default 100, οπότε οι σύντομοι κύκλοι δεν κόβονται νωρίς), `--val-fraction` (default 0.1, σταθερό ανά καρέ), `--max-family-images` (default 1500), `--poll-seconds` (default 5), `--lr0`, `--amp` για να ανάψεις το AMP, `--gpu-mem-fraction` (default 0.7, `0` για χωρίς όριο), `--min-free-vram-mb` (default 1536, `0` για να μην περιμένει), `--oom-wait` (default 45 δευτερόλεπτα). `--workers 0` μένει διαθέσιμο αν ο dataloader στα Windows κολλήσει.

Στον φάκελο sync γράφει μόνο:

- `annotool_predictions.json`
- `live_trainer_status.json`

Για atomic εγγραφή εμφανίζεται για μια στιγμή ένα `.<όνομα>.<pid>.tmp` δίπλα τους και μετά γίνεται replace. Κάθε project έχει δικό του υποφάκελο `<work-dir>\<project>\` με `state.json`, `best.pt`, dataset και runs. Η κοινή βιβλιοθήκη οικογενειών είναι `<work-dir>\models\<οικογένεια>\best.pt` και αλλάζει project χωρίς επανεκκίνηση, μαζί με τον φάκελο καρέ. Αν το `project` στο live αρχείο αλλάξει, ο trainer βρίσκει τον καινούργιο φάκελο καρέ. Projects της ίδιας οικογένειας μοιράζονται το `best.pt` και τη λίστα κλάσεων. Άλλη οικογένεια δεν ανακατεύει κλάσεις ούτε βάρη. Η αναζήτηση αποθηκεύεται στο `<work-dir>\frames_cache.json` και η επόμενη εκκίνηση το βρίσκει αμέσως. Αν ο φάκελος δεν βρεθεί, το `last_error` λέει το project και τα roots, το `state` μένει `idle`, και δεν ξεκινάει κύκλος. Προβλέψεις που γράφτηκαν για άλλο project σβήνονται, γιατί τα stems (`00001`…) επαναλαμβάνονται από ματς σε ματς. Αν σβήσεις τον υποφάκελο ενός project, η λίστα κλάσεων και ο κύκλος εκείνου του project ξεκινούν από την αρχή.

## `live_trainer_status.json`

Το annotool το δείχνει όπως είναι. `schema` είναι 1. Όλα τα κλειδιά υπάρχουν πάντα· ό,τι δεν είναι γνωστό ακόμη είναι `null`.

| Πεδίο | Τιμή |
| --- | --- |
| `schema` | `1` |
| `state` | `searching`, `idle`, `training`, `predicting`, ή `waiting_gpu`. `searching` είναι η αναζήτηση του φακέλου καρέ. `waiting_gpu` είναι αναμονή για ελεύθερη VRAM ή επανάληψη μετά από CUDA out of memory |
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
| `last_error` | Σφάλμα του τελευταίου κύκλου, CUDA out of memory όσο περιμένει επανάληψη, ή ότι ο φάκελος καρέ δεν βρέθηκε (με το όνομα του project και τα roots). Γίνεται `null` μόλις ένας επόμενος κύκλος ή οι προβλέψεις πετύχουν. Η απλή αναμονή για ελεύθερη VRAM δεν γράφει εδώ σφάλμα |
| `current_image` | Το `currentImage` του live αρχείου |
| `weights` | Το `best.pt` που χρησιμοποιείται για προβλέψεις |
| `message` | Σύντομο ελληνικό κείμενο για την οθόνη |
| `started_at` | Πότε άνοιξε αυτή η διαδικασία |
| `device` | Τι δόθηκε στο `--device`, ή `auto` |
| `from_base` | `true` αν ο τελευταίος κύκλος δεν έκανε fine-tune το `best.pt` αυτού του project (base ή `--init-weights`) |
| `train_images` | Αρχεία train του τελευταίου dataset, μαζί με τις επαναλήψεις των hard negatives |
| `val_images` | Καρέ val του τελευταίου dataset |
| `hard_negative_frames` | Μοναδικά reviewed καρέ με απόρριψη στο τελευταίο dataset. `0` αν δεν υπάρχουν |
| `model_family` | Οικογένεια μοντέλου (`modelFamily`, αλλιώς το πρώτο group, αλλιώς `default`). `null` πριν διαβαστεί το live αρχείο |
| `model_mode` | `συνέχεια` αν το project ξεκινάει από μοντέλο της οικογένειας, `νέο` αν ξεκινάει από τα base weights. `null` αν δεν έχει δεθεί ακόμη |
| `per_class_map50` | AP50 ανά κλάση στον καλύτερο epoch του τελευταίου κύκλου, `{ "brand\|tpoint": 0.42 }`. `{}` πριν από κύκλο |

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
  "message": "Αναμονή · 12/40 reviewed · 2026 RLWC · συνέχεια",
  "started_at": "2026-11-14T17:50:00+00:00",
  "device": "0",
  "from_base": null,
  "train_images": null,
  "val_images": null,
  "hard_negative_frames": 0,
  "model_family": "2026 RLWC",
  "model_mode": "συνέχεια",
  "per_class_map50": {}
}
```

Το `epoch` / `epochs` έρχονται από callback του ultralytics (`on_fit_epoch_end`) σε κάθε epoch.

## `annotool_predictions.json`

Ίδιο σχήμα με το export του annotool / το `predict_to_json.py`: `project`, `imageNum`, `prefs`, `images`, `currentImage`, `presets`, `Annotator`. Το `project` είναι το `project` του live αρχείου· το εργαλείο αγνοεί προβλέψεις άλλου project. Κάθε καρέ έχει `imageName`, `imageIndex`, `width`, `height`, `annotations`, `exifdata`. Κάθε κουτί έχει `startPoint`, `diagPoint`, `group`, `brand`, `tpoint`, `hits` (πάντα 1), `confidence`. Ένα κουτί ανά instance, χωρίς συγχώνευση ίδιου `brand|tpoint`. Οι συντεταγμένες είναι στον καμβά του live αρχείου για αυτό το καρέ, αλλιώς στο πιο συχνό `width`/`height`.

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

Τα `anno2026/scripts/predict_to_json.py`, `convert_to_yolo.py`, `train.py` και τα `anno_video/NEW_PROJECT_RUNBOOK.md` / `annotation_playbook.md` δεν υπάρχουν σε αυτό το checkout, οπότε ο κώδικας δεν τα κάνει import. Ακολουθεί το συμβόλαιό τους: κλάσεις `brand|tpoint`, μετατροπή καμβά → αρχείο όπως το `LogoDetection/annoToYOLO.py`, `conf 0.25`, `iou 0.3`, agnostic NMS, μετά φίλτρο `--contain 0.6`, AMP κλειστό.

Ο κύκλος δοκιμάστηκε εδώ σε CPU με `yolov8n` και συνθετικά jpg, όχι στην RTX 5070. Το `best.pt` αντιγράφεται στο `<work-dir>\<project>\best.pt`. Αν η εκπαίδευση τελειώσει και οι προβλέψεις αποτύχουν, η επόμενη εκκίνηση συνεχίζει από τις προβλέψεις χωρίς να ξαναεκπαιδεύσει τον ίδιο κύκλο. Η πρώτη εκκίνηση του ultralytics μπορεί να κατεβάσει μία φορά το `Arial.ttf` για plots, ακόμη και με plots κλειστά· τα βάρη δεν κατεβαίνουν.
