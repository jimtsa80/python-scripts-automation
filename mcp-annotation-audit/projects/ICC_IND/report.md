# Annotation Audit Report – ICC_IND

**Project:** ICC_IND · **Expected brands:** 2026_ICC_T20 · **Κανόνες:** audit_rules.md

*Duration ανά αγώνα με merge Part1+Part2 (IND v ENG = ένας αγώνας).*

---

## 1) Brands / Locations που λείπουν

- **Brands από expected που δεν εμφανίζονται στο sheet:** Κανένα (όλα τα 14 από το 2026_ICC_T20.txt εμφανίζονται· εφαρμογή audit_rules).
- **Γραμμές με κενό Brand:** 0.

---

## 2) Μεγάλες αποκλίσεις (Brand · Location)

Μόνο συνδυασμοί με **μεγάλο Δ** (max − min duration ανά αγώνα). Ταξινόμηση κατά φθίνουσα Δ.

| Brand | Location | IND v USA | IND v NAM | IND v PAK | IND v NLD | IND v SA | IND v WI | IND v ENG | Δ (sec) |
|-------|----------|-----------|-----------|-----------|-----------|----------|----------|-----------|---------|
| Adidas | Playing Kit - Arm | 3252 | 3882 | 3090 | 2291 | 2863 | 3706 | **1680** | **2202** |
| Apollo Tyres | Playing Kit - Arm | 1741 | 1962 | 1458 | 1186 | 1349 | 1745 | **822** | **1140** |
| Emirates | Umpire Jersey Back | 538 | 150 | 667 | 549 | 400 | 925 | **163** | **775** |
| DP World | Boundary Rope | 1005 | 741 | 566 | 605 | 957 | 852 | **259** | **746** |
| DP World | Grass Sign - End of Wicket | 744 | 626 | 415 | 298 | 434 | 786 | **139** | **647** |
| Emirates | Umpire Jersey Back - Fly Better | 207 | 139 | 658 | 246 | 2 | — | — | **656** |
| Hyundai | Grass Sign - End of Wicket | 767 | 625 | 433 | 362 | 348 | 688 | **124** | **643** |
| Emirates | Boundary Rope | 861 | 812 | 660 | 767 | 808 | 858 | **299** | **562** |
| **Adidas** | **Playing Kit - Pants** | 356 | 314 | 360 | 356 | 290 | 555 | **22** | **533** |

**Προτεραιότητα review:** Adidas · Playing Kit - Arm (ENG πολύ χαμηλό), Apollo · Playing Kit - Arm, Emirates · Umpire Jersey Back, DP World · Boundary Rope, **Adidas · Playing Kit - Pants** (ENG 22 vs WI 555).
