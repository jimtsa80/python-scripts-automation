# Annotation Audit Report – ICC_Rest

**Project:** ICC_Rest · **Expected brands:** 2026_ICC_T20 · **Κανόνες:** audit_rules.md (Adidas/Apollo μόνο IND · Asics/Radar μόνο AUS και μόνο ρουχά · alcohol αγνοούνται σε muslim-country).

Duration ανά αγώνα με **merge Part1+Part2**. Tab: ICC_Rest.

---

## 1) Brands / Locations που λείπουν

- **Brands από expected (.txt) που δεν εμφανίζονται στο sheet:** **Κανένα** (όλα τα 14 expected brands εμφανίζονται).
- **Γραμμές με κενό Brand:** 0

*(Εφαρμογή audit_rules: Adidas/Apollo μόνο σε αγώνες με Ινδία· Asics/Radar μόνο σε AUS και ρουχά· alcohol αγνοούνται σε αγώνες με μουσουλμανική χώρα.)*

---

## 2) Μεγάλες αποκλίσεις (Brand · Location)

Δ (sec) = max − min duration ανά αγώνα. Στήλες = αγώνες από το sheet **ICC_Rest** (χωρίς Ινδία). Ταξινόμηση κατά φθίνουσα Δ. Κενό (–) = δεν εμφανίζεται στο match.

| Brand | Location | SCO v WI | ENG v NEP | ITA v SCO | OMA v ZIM | CAN v SA | NAM v NLD | NZ v UAE | PAK v USA | ENG v WI | AUS v ZIM | Δ (sec) |
|-------|----------|----------|-----------|-----------|-----------|----------|-----------|----------|-----------|----------|-----------|---------|
| Coca Cola | Media Backdrop | 55 | – | 115 | 120 | 108 | 22 | 93 | 112 | 329 | 1 | 328 |
| Emirates | Grass Sign - End of Wicket | 218 | 287 | 413 | 208 | 282 | 265 | 109 | 225 | 268 | 244 | 304 |
| Emirates | Media Backdrop | 55 | – | 115 | 120 | 127 | 83 | 101 | 112 | 358 | 79 | 303 |
| Aramco | Media Backdrop | 55 | – | 115 | 120 | 108 | 83 | 93 | 112 | 329 | 79 | 274 |
| DP World | Media Backdrop | 55 | – | 115 | 120 | 108 | 61 | 101 | 112 | 329 | 79 | 274 |
| Google | Media Backdrop | 55 | – | 115 | 120 | 108 | 61 | 101 | 112 | 329 | 79 | 274 |
| Hyundai | Media Backdrop | 55 | – | 115 | 120 | 108 | 83 | 101 | 112 | 329 | 79 | 274 |
| Sobha | Media Backdrop | 55 | – | 115 | 120 | 108 | 83 | 101 | 112 | 329 | 79 | 274 |
| Aramco | Grass Sign - End of Wicket | 220 | 278 | 413 | 250 | 213 | 143 | 253 | 313 | 273 | 228 | 270 |
| Hyundai | Grass Sign - End of Wicket | 224 | 244 | 412 | 188 | 258 | 149 | 210 | 195 | 181 | 228 | 263 |
| Emirates | Umpire Jersey Back | 123 | 113 | 372 | 142 | 165 | 157 | 158 | 171 | 203 | 206 | 259 |
| Emirates | Stumps | 9 | 20 | 22 | 25 | 27 | 262 | 9 | 17 | 23 | 98 | 253 |
| Aramco | Stumps | 12 | 21 | 21 | 23 | 31 | 252 | 2 | 15 | 23 | 91 | 250 |
| Marriott | Media Backdrop | 55 | – | 115 | 120 | 108 | 62 | 101 | – | 291 | 79 | 236 |
| Budweiser | Media Backdrop | 55 | – | 101 | – | 87 | 72 | 92 | – | 291 | – | 236 |
| Aramco | Boundary Rope | 302 | 206 | 356 | 361 | 393 | 310 | 161 | 292 | 333 | 311 | 232 |
| DP World | Grass Sign - End of Wicket | 223 | 246 | 401 | 263 | 225 | 202 | 196 | 313 | 181 | 206 | 220 |
| Hyundai | Dugout - Seats | 128 | 173 | 91 | 83 | 81 | 115 | 75 | 195 | 117 | 288 | 213 |
| Hyundai | Boundary Rope | 140 | 129 | 142 | 128 | 332 | 281 | 145 | 288 | 270 | 253 | 204 |
| Marriott | Grass Sign - Square of Wicket | 25 | 12 | 51 | 33 | 68 | 39 | 8 | 212 | 49 | 47 | 204 |
| DP World | Boundary Rope | 285 | 226 | 337 | 376 | 349 | 308 | 174 | 332 | 362 | 342 | 202 |
| Google | Grass Sign - Square of Wicket | 17 | 23 | 35 | 63 | 59 | 62 | 55 | 217 | 136 | 42 | 200 |
| Sobha | Grass Sign - Square of Wicket | 26 | 18 | 36 | 75 | 156 | 36 | – | 212 | 40 | 57 | 194 |
| Coca Cola | Grass Sign - Square of Wicket | 15 | 32 | 36 | 41 | 156 | 29 | 9 | 201 | 127 | 43 | 192 |
| Emirates | Boundary Rope | 242 | 257 | 330 | 316 | 396 | 341 | 208 | 310 | 339 | 319 | 188 |

**Προτεραιότητα review:** (1) **Coca Cola · Media Backdrop** — Δ 328 s (ENG v WI 329 vs AUS v ZIM 1): έλεγχος AUS v ZIM. (2) **Emirates · Grass Sign - End of Wicket** και **Media Backdrop** — μεγάλη διακύμανση. (3) **Media Backdrop** πολλών brands (Aramco, DP World, Google, Hyundai, Sobha) — ίδιο pattern 55/115/120 σε πολλούς αγώνες, υψηλό στο ENG v WI· consistency. (4) **Emirates / Aramco · Stumps** — NAM v NLD πολύ υψηλό (252–262 s) vs υπόλοιπους· έλεγχος. (5) **Grass Sign - Square of Wicket** (Marriott, Google, Sobha, Coca Cola) — PAK v USA ξεχωρίζει (201–212 s).

---

## 3) Τι να ξανακοιτάξεις και σε ποιο αρχείο (ξεφεύγουν από τον ΜΟ)

Όλα αναφέρονται στο **sheet ICC_Rest**. Άνοιξε το tab **ICC_Rest** και ψάξε τη γραμμή που αντιστοιχεί στον αγώνα (File) και στο Brand · Location. Ο ΜΟ είναι ο μέσος όρος duration για αυτό το (Brand, Location) στους αγώνες όπου εμφανίζεται.

- **Coca Cola · Media Backdrop**  
  Ξεφεύγει **χαμηλά** στο **AUS v ZIM** (1 s· ΜΟ ≈ 131 s). Αξίζει να ανοίξεις το αρχείο/αγώνα **AUS v ZIM** και να ελέγξεις αν το Media Backdrop της Coca Cola έχει under-annotation. Επίσης **υψηλά** στο **ENG v WI** (329 s) — αν οι υπόλοιποι αγώνες είναι σωστοί, έλεγχος αν στο ENG v WI υπάρχει διπλό ή διαφορετικό scope.

- **Emirates · Grass Sign - End of Wicket**  
  Ξεφεύγει **χαμηλά** στο **NZ v UAE** (109 s· ΜΟ ≈ 252 s) — άνοιξε **NZ v UAE**. Επίσης **υψηλά** στο **ITA v SCO** (413 s) — άνοιξε **ITA v SCO** αν θες να δεις αν πραγματικά έχει περισσότερο exposure.

- **Emirates · Media Backdrop**  
  Ξεφεύγει **υψηλά** στο **ENG v WI** (358 s· ΜΟ ≈ 127 s) — άνοιξε **ENG v WI**. Επίσης χαμηλά στο SCO v WI (55 s) και σε άλλα — αν το ENG v WI είναι το σωστό baseline, τότε re-check τα χαμηλά.

- **Aramco / DP World / Google / Hyundai / Sobha · Media Backdrop**  
  Κοινό pattern: πολλοί αγώνες ~55–120 s, ενώ **ENG v WI** πάνω από 320 s (ΜΟ γύρω στο 120–130 s). Άνοιξε **ENG v WI** και σύγκρινε με έναν αγώνα π.χ. SCO v WI ή ITA v SCO· αν το ENG v WI είναι σωστό, τότε στα άλλα μπορεί να λείπει duration.

- **Emirates · Umpire Jersey Back**  
  Ξεφεύγει **υψηλά** στο **ITA v SCO** (372 s· ΜΟ ≈ 201 s) — άνοιξε **ITA v SCO**.

- **Emirates · Stumps**  
  Ξεφεύγει **υψηλά** στο **NAM v NLD** (262 s· ΜΟ ≈ 55 s) — άνοιξε **NAM v NLD** και re-check αν το Stumps της Emirates έχει πραγματικά τόσο περισσότερο ή αν υπάρχει διπλό counting.

- **Aramco · Stumps**  
  Ίδιο: **υψηλά** στο **NAM v NLD** (252 s· ΜΟ ≈ 54 s) — άνοιξε **NAM v NLD**.

- **Hyundai · Dugout - Seats**  
  Ξεφεύγει **υψηλά** στο **AUS v ZIM** (288 s· ΜΟ ≈ 147 s) — άνοιξε **AUS v ZIM**.

- **Hyundai · Boundary Rope**  
  Ξεφεύγει **υψηλά** στο **CAN v SA** (332 s· ΜΟ ≈ 219 s) — άνοιξε **CAN v SA**.

- **Marriott · Grass Sign - Square of Wicket**  
  Ξεφεύγει **υψηλά** στο **PAK v USA** (212 s· ΜΟ ≈ 59 s) — άνοιξε **PAK v USA**.

- **Google / Sobha / Coca Cola · Grass Sign - Square of Wicket**  
  Ξεφεύγουν **υψηλά** στο **PAK v USA** (201–217 s)· ΜΟ γύρω στο 50–70 s. Άνοιξε **PAK v USA** και έλεγξε αν το Grass Sign - Square of Wicket για αυτά τα brands έχει σωστό duration.

**Σύνοψη αρχείων που αξίζει να ανοίξεις πρώτα:**  
**AUS v ZIM** (Coca Cola Media Backdrop πολύ χαμηλά, Hyundai Dugout - Seats υψηλά), **ENG v WI** (Media Backdrop πολλών brands πολύ υψηλά), **NAM v NLD** (Emirates/Aramco Stumps πολύ υψηλά), **PAK v USA** (Grass Sign - Square of Wicket πολλών brands υψηλά), **ITA v SCO** (Emirates Grass Sign και Umpire Jersey Back υψηλά), **NZ v UAE** (Emirates Grass Sign χαμηλά).
