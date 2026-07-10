# WRC Template Matching System

## Στόχος
Template matching για WRC logo detection με focus στο bottom-left corner (broadcast overlay).

## Δομή Φακέλων

### Νέα Δομή (Προτεινόμενη):

```
template_matching/
├── templates/
│   ├── Ford Logos/
│   │   └── TVGI/
│   │       ├── ford_colored_leaderboard.png
│   │       ├── ford_white_leaderboard.png
│   │       └── ford_driver.png
│   ├── WRC Logos/
│   │   └── TVGI/
│   │       └── wrc_logo_basic.png
│   ├── Toyota Logos/
│   │   └── TVGI/
│   │       └── toyota_leaderboard.png
│   └── SKODA Logos/
│       └── TVGI/
│           └── skoda_leaderboard.png
├── output/            # Annotated results
├── wrc_template_matcher.py  # Main script
├── brand_mapping.txt  # Optional (fallback only)
└── README.md          # This file
```

**Πώς λειτουργεί:**
- **Brand:** Εξάγεται από folder name (π.χ. "Ford Logos" → "Ford")
- **Location:** Εξάγεται από subfolder name (π.χ. "TVGI")
- **Δεν χρειάζεται `brand_mapping.txt`** - όλα προέρχονται από τη δομή των φακέλων

### Παλιά Δομή (ακόμα υποστηρίζεται):

```
template_matching/
├── templates/          # Template images (flat structure)
├── output/            # Annotated results
├── wrc_template_matcher.py  # Main script
└── README.md          # This file
```

## Templates που χρειάζεσαι

### WRC Logo Templates

#### 1. WRC Logo - Basic (ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ)
**File:** `wrc_logo_basic.png` ή `wrc_logo_basic.jpg`
- **Τι να κάνεις:**
  - Κάνε screenshot του WRC logo από broadcast overlay (bottom-left corner)
  - Crop μόνο το WRC logo (χωρίς FIA logo δίπλα)
  - **ΣΥΝΙΣΤΑΤΑΙ: Κράτα το background** (όχι transparent) - το dark background βοηθάει στο matching
  - **Μέγεθος:** 50-200 pixels width (όσο πιο μεγάλο, τόσο καλύτερο)
  - **Format:** PNG με background color ή JPG

**Σημαντικό για Transparency:**
- **Non-transparent (με background):** ✅ **Προτιμήται** - πιο αξιόπιστο matching
  - Το background color βοηθάει το OpenCV να match-άρει καλύτερα
  - Για broadcast overlays (WRC στο bottom-left), συνήθως έχουν dark background
  - Κράτα το background όπως φαίνεται στο broadcast
- **Transparent:** ⚠️ Μπορεί να δουλεύει, αλλά λιγότερο αξιόπιστο
  - Το OpenCV συνήθως αγνοεί το alpha channel
  - Χρησιμοποιήσε το μόνο αν το logo έχει varying backgrounds

#### 2. WRC + FIA Logo Together (ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ)
**File:** `wrc_fia_together.png`
- **Τι να κάνεις:**
  - Screenshot του WRC logo μαζί με FIA logo (όπως φαίνεται στο broadcast)
  - Αυτό βοηθάει για περιπτώσεις που τα δύο logos είναι μαζί
  - **Μέγεθος:** 100-300 pixels width

---

### Car Manufacturer Logo Templates (Ford, Toyota, Skoda, Lancia, Hyundai)

Για να πιάσεις τα logos των car manufacturers, χρειάζεσαι templates από **διαφορετικές πηγές** γιατί τα logos εμφανίζονται σε διαφορετικά contexts:

#### A. Leaderboard Logos (ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ)
**Πού είναι:** Top-left overlay, δίπλα στα ονόματα των οδηγών

**Παραδείγματα filenames:**
- `ford_leaderboard.png`
- `toyota_leaderboard.png`
- `skoda_leaderboard.png`
- `lancia_leaderboard.png`
- `hyundai_leaderboard.png`

**Τι να κάνεις:**
1. Pause το video όταν βλέπεις το leaderboard (top-left)
2. Zoom στο logo δίπλα στο όνομα του οδηγού (π.χ. "JÜR" με Ford logo)
3. Screenshot μόνο το logo (χωρίς το όνομα)
4. Crop tight - μόνο το logo, minimal background
5. **Μέγεθος:** 20-60 pixels width (μικρά logos)
6. **Format:** PNG

**Παράδειγμα:**
- Βλέπεις "JÜR" με μικρό Ford logo → Screenshot μόνο το Ford logo
- Βλέπεις "ROS" με Lancia logo → Screenshot μόνο το Lancia logo

---

#### B. Driver Info Panel Logos (ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ)
**Πού είναι:** Bottom-right overlay, στο driver info panel

**Παραδείγματα filenames:**
- `ford_driver_panel.png`
- `toyota_driver_panel.png`
- `skoda_driver_panel.png`

**Τι να κάνεις:**
1. Pause όταν βλέπεις driver info panel (bottom-right)
2. Screenshot το logo που φαίνεται εκεί (π.χ. Ford logo δίπλα στο "JOSHUA MCERLEAN")
3. Crop μόνο το logo
4. **Μέγεθος:** 50-150 pixels width (μεσαία logos)
5. **Format:** PNG

---

#### C. Car Body Logos (ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ)
**Πού είναι:** Στο car body (doors, hood, side panels)

**Παραδείγματα filenames:**
- `ford_car_door.png` - Ford logo στο door
- `ford_car_hood.png` - Ford logo στο hood/bonnet
- `toyota_car_side.png` - Toyota logo στο side panel
- `skoda_car_door.png` - Skoda logo στο door
- `hyundai_car_side.png` - Hyundai logo στο side

**Τι να κάνεις:**
1. Pause όταν βλέπεις το car με καθαρό logo
2. Zoom στο logo στο car body
3. Screenshot μόνο το logo (αν είναι δυνατό, crop tight)
4. Προσπάθησε να έχεις clean logo (χωρίς πολύ distortion από car shape)
5. **Μέγεθος:** 80-250 pixels width (μεγάλα logos)
6. **Format:** PNG ή JPG

**Tips:**
- Αν το logo είναι distorted από car angle, κάνε template από straight-on view
- **Κράτα το background** από car livery (non-transparent) - βοηθάει στο matching
- Αν το logo έχει consistent background color, κράτα το
- Αν το logo έχει varying backgrounds, μπορείς να δοκιμάσεις transparent, αλλά non-transparent είναι πιο αξιόπιστο

---

#### D. Multiple Size Variants (Optional αλλά Recommended)

Για κάθε brand, μπορείς να έχεις:
- **Small:** `{brand}_small.png` (20-50 pixels) - για leaderboard
- **Medium:** `{brand}_medium.png` (50-150 pixels) - για driver panel
- **Large:** `{brand}_large.png` (150-300 pixels) - για car body

**Παράδειγμα:**
- `ford_small.png` - μικρό Ford logo
- `ford_medium.png` - μεσαίο Ford logo
- `ford_large.png` - μεγάλο Ford logo

---

### Recommended Template Structure

```
templates/
├── wrc_logo_basic.png
├── wrc_fia_together.png
│
├── ford_leaderboard.png          # Ford από leaderboard
├── ford_driver_panel.png         # Ford από driver panel
├── ford_car_door.png            # Ford από car door
│
├── toyota_leaderboard.png       # Toyota από leaderboard
├── toyota_car_side.png         # Toyota από car side
│
├── skoda_leaderboard.png        # Skoda από leaderboard
├── skoda_car_door.png          # Skoda από car door
│
├── lancia_leaderboard.png       # Lancia από leaderboard
│
└── hyundai_car_side.png        # Hyundai από car side
```

## Πώς να πάρεις τα Templates - Step by Step

### Για WRC Logo:

#### Μέθοδος 1: Screenshot από Broadcast
1. Άνοιξε ένα frame που έχει WRC logo στο bottom-left
2. Κάνε zoom στο logo (200-300%)
3. Κάνε screenshot μόνο του logo
4. Crop το logo (αφαίρεσε περιττό background)
5. Αποθήκευσε ως PNG

---

### Για Car Manufacturer Logos (Ford, Toyota, Skoda, κτλ):

#### Step 1: Leaderboard Logos (Top-Left Overlay)

**Παράδειγμα για Ford:**
1. Βρες frame με leaderboard στο top-left
2. Βρες το Ford logo δίπλα σε όνομα οδηγού (π.χ. "JÜR" με Ford logo)
3. Zoom στο logo (300-500%)
4. Screenshot μόνο το Ford logo (χωρίς το "JÜR" text)
5. Crop tight - μόνο το logo
6. Αποθήκευσε ως `ford_leaderboard.png`

**Επαναλάβετε για:**
- Toyota (δίπλα σε "ROS" ή άλλο όνομα)
- Skoda (δίπλα σε "DAP" ή άλλο όνομα)
- Lancia (δίπλα σε "ROS" ή "GRY")
- Hyundai (αν υπάρχει στο leaderboard)

---

#### Step 2: Driver Panel Logos (Bottom-Right Overlay)

**Παράδειγμα για Ford:**
1. Βρες frame με driver info panel (bottom-right)
2. Βρες το Ford logo δίπλα στο driver name (π.χ. "JOSHUA MCERLEAN")
3. Zoom στο logo (200-300%)
4. Screenshot μόνο το Ford logo
5. Crop tight
6. Αποθήκευσε ως `ford_driver_panel.png`

---

#### Step 3: Car Body Logos

**Παράδειγμα για Ford:**
1. Βρες frame όπου φαίνεται το car με καθαρό logo
2. Zoom στο logo στο car body (door, hood, ή side panel)
3. Screenshot το logo
4. Crop tight (αν είναι δυνατό, μόνο το logo)
5. Αν το logo έχει background color από car livery, κράτα το
6. Αποθήκευσε ως `ford_car_door.png` ή `ford_car_hood.png`

**Επαναλάβετε για:**
- Toyota (στο Yaris Rally1)
- Skoda (στο Fabia Rally2)
- Hyundai (στο i20 N Rally1)
- Lancia (στο Delta Integrale ή άλλο model)

---

#### Step 4: Multiple Angles (Optional)

Αν το logo φαίνεται σε διαφορετικές γωνίες:
- `ford_car_door_straight.png` - straight-on view
- `ford_car_door_angle.png` - angled view

---

### Tips για καλύτερα Templates:

✅ **Κάνε:**
- **High contrast** - logo να ξεχωρίζει από background
- **Clean edges** - no blur, no compression artifacts
- **Keep background** - non-transparent templates match-άρουν καλύτερα
- **Tight crop** - minimal background αλλά κράτα το background color
- **Multiple sources** - leaderboard + car body + driver panel
- **Multiple sizes** - small, medium, large variants

❌ **Μην κάνεις:**
- **Transparent templates** (αν μπορείς να το αποφύγεις) - non-transparent είναι πιο αξιόπιστο
- Templates με πολύ background (αλλά κράτα λίγο background)
- Templates που είναι blurry
- Templates που είναι πολύ distorted
- Templates που είναι πολύ μεγάλα (over 500px) - resize πρώτα

### Transparency: Transparent vs Non-Transparent

**Non-Transparent (με background):** ✅ **ΠΡΟΤΙΜΗΤΕΟ**
- **Γιατί:** Το OpenCV template matching λειτουργεί καλύτερα με solid backgrounds
- **Πότε:** Όταν το logo έχει consistent background στο broadcast
- **Παράδειγμα:** WRC logo με dark background στο bottom-left overlay

**Transparent:** ⚠️ **Μόνο αν χρειάζεται**
- **Γιατί:** Το OpenCV συνήθως αγνοεί το alpha channel, οπότε δεν βοηθάει πολύ
- **Πότε:** Αν το logo έχει varying backgrounds και δεν μπορείς να κρατήσεις consistent background
- **Παράδειγμα:** Car logo που εμφανίζεται σε διαφορετικά car liveries

**Σύσταση:** 
- **Κράτα το background** όπως φαίνεται στο broadcast
- Αν το logo έχει dark background στο broadcast, κράτα το dark background στο template
- Αν το logo έχει light background, κράτα το light background
- **Μην κάνεις transparent** εκτός αν είναι απολύτως απαραίτητο

## Tips για καλά Templates

✅ **Κάνε:**
- High contrast (logo vs background)
- Clean edges (no compression artifacts)
- Multiple sizes (small, medium, large)
- Multiple variations (solo, with FIA)

❌ **Μην κάνεις:**
- Templates με πολύ noise
- Templates που είναι blurry
- Templates που είναι πολύ μεγάλα (over 500px)
- Templates με πολύ background

## Expected Template Sizes

Για 1920x1080 broadcast frames:

### WRC Logo:
- **Small:** 40-80 pixels width
- **Medium:** 80-150 pixels width  
- **Large:** 150-250 pixels width

### Car Manufacturer Logos:

**Leaderboard (top-left overlay):**
- **Size:** 20-60 pixels width
- **Examples:** `ford_leaderboard.png`, `toyota_leaderboard.png`

**Driver Panel (bottom-right overlay):**
- **Size:** 50-150 pixels width
- **Examples:** `ford_driver_panel.png`, `toyota_driver_panel.png`

**Car Body (doors, hood, side panels):**
- **Size:** 80-250 pixels width
- **Examples:** `ford_car_door.png`, `toyota_car_side.png`

---

## Complete Example Template List

Ακολουθεί ένα πλήρες example list με όλα τα templates που μπορείς να έχεις:

```
templates/
│
├── WRC Logos
│   ├── wrc_logo_basic.png
│   ├── wrc_fia_together.png
│   ├── wrc_logo_small.png
│   └── wrc_logo_large.png
│
├── Ford Logos
│   ├── ford_leaderboard.png          # 20-60px - από leaderboard
│   ├── ford_driver_panel.png         # 50-150px - από driver panel
│   ├── ford_car_door.png            # 80-250px - από car door
│   └── ford_car_hood.png            # 80-250px - από car hood
│
├── Toyota Logos
│   ├── toyota_leaderboard.png        # 20-60px
│   ├── toyota_driver_panel.png       # 50-150px
│   └── toyota_car_side.png          # 80-250px
│
├── Skoda Logos
│   ├── skoda_leaderboard.png         # 20-60px
│   ├── skoda_driver_panel.png        # 50-150px
│   └── skoda_car_door.png           # 80-250px
│
├── Lancia Logos
│   ├── lancia_leaderboard.png        # 20-60px
│   └── lancia_car_side.png          # 80-250px
│
└── Hyundai Logos
    ├── hyundai_leaderboard.png       # 20-60px
    └── hyundai_car_side.png         # 80-250px
```

**Σημείωση:** Δεν χρειάζεσαι όλα τα templates. Ξεκίνα με:
1. **WRC:** `wrc_logo_basic.png` (υποχρεωτικό)
2. **Ford:** `ford_leaderboard.png` + `ford_driver_panel.png` (αν υπάρχουν)
3. **Toyota:** `toyota_leaderboard.png` (αν υπάρχει)
4. Προσθήκη περισσότερων καθώς τα βρίσκεις

## Folder Structure Organization (Προτεινόμενη)

### Νέα Δομή: Brand/Location Subfolders

**Πλεονεκτήματα:**
- ✅ **Αυτόματη brand/location detection** - δεν χρειάζεται `brand_mapping.txt`
- ✅ **Καλύτερη οργάνωση** - όλα τα templates για ένα brand σε ένα folder
- ✅ **Εύκολη διαχείριση** - προσθήκη νέων templates απλά copy-paste

**Δομή:**
```
templates/
├── Ford Logos/
│   └── TVGI/
│       ├── ford_colored_leaderboard.png
│       ├── ford_white_leaderboard.png
│       └── ford_driver.png
├── WRC Logos/
│   └── TVGI/
│       └── wrc_logo_basic.png
├── Toyota Logos/
│   └── TVGI/
│       └── toyota_leaderboard.png
└── SKODA Logos/
    └── TVGI/
        └── skoda_leaderboard.png
```

**Πώς λειτουργεί:**
1. **Brand:** Εξάγεται από folder name (π.χ. "Ford Logos" → "Ford")
2. **Location:** Εξάγεται από subfolder name (π.χ. "TVGI")
3. **Grouping:** Όλα τα templates στο ίδιο `{Brand} Logos/{Location}/` folder ομαδοποιούνται
4. **Hits:** Μετράει αυτόματα πόσες detections βρέθηκαν για κάθε (brand, location)

**Παράδειγμα:**
- `templates/Ford Logos/TVGI/ford_colored_leaderboard.png` → Brand: "Ford", Location: "TVGI"
- `templates/Ford Logos/TVGI/ford_white_leaderboard.png` → Brand: "Ford", Location: "TVGI"
- Αν βρει και τα δύο → 1 annotation με `hits: 2`

---

## Brand Mapping Configuration (Optional - Fallback Only)

Το `brand_mapping.txt` είναι **optional** και χρησιμοποιείται μόνο ως fallback:
- Αν το template είναι στο root `templates/` folder (παλιά δομή)
- Αν το location subfolder δεν υπάρχει

**Format:**
```
# Brand:Location
WRC:TVGI
Ford:TVGI
```

**Σημείωση:** Με τη νέα folder structure, **δεν χρειάζεσαι** `brand_mapping.txt`!

## Βελτίωση εικόνων και σήμανση περιοχής

### 1. Πώς βελτιώνουμε τις εικόνες (preprocessing)

Πριν το template matching, εφαρμόζουμε στα frames **contrast enhancement** και **unsharp masking** ώστε τα logos να match-άρουν καλύτερα:

- **Contrast:** `cv2.convertScaleAbs(image, alpha=1.2, beta=10)` — αύξηση αντίθεσης.
- **Sharpening:** Gaussian blur + `addWeighted` (unsharp mask) — το ίδιο εφαρμόζεται και στα templates ώστε εικόνα και template να είναι στο ίδιο “style”.

Αυτό γίνεται **αυτόματα** μέσα στη λειτουργία detection (όχι σε ξεχωριστό βήμα). Τα templates φορτώνονται και preprocess-άρονται με την ίδια λογική κατά το `load_templates()`.

### 2. Πώς σημαδεύουμε την περιοχή που κοιτάμε (visualize zones)

Για να δεις **ακριβώς ποια ζώνη** ψάχνει το script (π.χ. bottom-right για ICC):

- **`--visualize-zones`**  
  Για κάθε εικόνα που επεξεργάζεσαι, αποθηκεύει μια εικόνα με **ορατά ορθογώνια** πάνω στις ζώνες (bottom_left, bottom_right, κ.λπ.). Κάθε ζώνη έχει χρώμα και label (π.χ. `bottom_right` σε μπλε).

  Παράδειγμα:
  ```bash
  python wrc_template_matcher.py <image_folder> --visualize-zones
  python icc_template_matcher.py <image_folder> --visualize-zones
  ```
  Τα αρχεία οπτικοποίησης πηγαίνουν στο `output/` (WRC) ή `icc_output/` (ICC), με names τύπου `zones_<filename>.png`.

- **`--annotate`**  
  Σημαδεύει τις **detections**: πράσινα bounding boxes με label (brand + confidence), π.χ. `Emirates 0.85`. Δεν σχεδιάζει τις ζώνες, μόνο τα findings.

**Σύνοψη:**
- **Ζώνη που κοιτάς:** `--visualize-zones` → εικόνες με σημαδεμένες ζώνες (όπου ψάχνει).
- **Τι βρήκε:** `--annotate` → εικόνες με πράσινα boxes στα detected logos.

Μπορείς να βάλεις και τα δύο: `--visualize-zones --annotate` για ζώνες + detections.

## Next Steps

1. **Βάλε τα templates** στον φάκελο `templates/` (WRC) ή `icc_templates/` (ICC)
2. **(Optional) Δημιούργησε `brand_mapping.txt`** για custom brand→location mapping
3. **Τρέξε το script:**  
   - WRC: `python wrc_template_matcher.py <image_folder>`  
   - ICC (bottom-right, π.χ. Emirates): `python icc_template_matcher.py <image_folder>`
4. **Ελέγξε τα results** στο `output/` (WRC) ή `icc_output/` (ICC)
5. **Ζώνες:** πρόσθεσε `--visualize-zones` για να δεις τις περιοχές· `--annotate` για τα detection boxes


python .\preprocess_for_template_matching.py F:\downloads\batch11\ --temporal-median-all
python .\wrc_template_matcher.py F:\downloads\batch9\ --WRConly 
python .\wrc_template_matcher.py F:\downloads\batch11\

PS F:\cursor\python-scripts-automation\csv2xls> python .\json_to_csv_UPDATED.py F:\cursor\python-scripts-automation\template_matching\output

F:\cursor\python-scripts-automation\csv2xls\csvs => edw pane