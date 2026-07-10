# Κανόνες audit – ICCR_Rest (γήπεδο – άλλες ομάδες εκτός Ινδίας)

Οι κανόνες εφαρμόζονται ώστε να **μην** θεωρούνται λάθος/outlier/missing brands που λείπουν λόγω χώρας, θρησκείας ή τύπου location.

---

## 1. Team-specific brands

| Χώρα | Brands | Σημείωση |
|------|--------|----------|
| **Ινδία** | Adidas, Apollo Tyres | Ίδιο με ICC_IND: να λαμβάνονται υπόψη **μόνο** σε αγώνες με Ινδία. Σε άλλους αγώνες (π.χ. AUS v ENG) να μην τα ελέγχουμε ως missing/outlier. |
| **Αυστραλία** | Asics, Radar Tyres | Να λαμβάνονται υπόψη **μόνο στα ρουχά της Αυστραλίας**: δηλαδή σε αγώνες με Αυστραλία και **μόνο** σε locations που είναι ρουχά (Playing Kit - Arm/Cap/Pants, Spectator Apparel, Bib, Training Apparel, Umpire Jersey, Kids Clothing, κ.λπ.). Σε μη-AUS αγώνες ή σε μη-ρουχά locations να μην ελέγχουμε Asics/Radar Tyres. |

---

## 2. Αγώνες με μουσουλμανική χώρα – alcohol brands

**Ίδιο με ICC_IND:** Όταν παίζει **μουσουλμανική χώρα** (π.χ. Pakistan, UAE), **να μην ελέγχουμε** brands που σχετίζονται με αλκοόλ.

- **Alcohol-related brands:** Budweiser, Royal Stag (η λίστα μπορεί να επεκταθεί).
- Σε αγώνες χωρίς μουσουλμανική χώρα, τα alcohol brands ελέγχονται κανονικά.

---

## 3. Context project – γήπεδο (άλλες ομάδες)

Αυτό το project (**ICCR_Rest**) αφορά **γήπεδο όταν παίζουν οι άλλες ομάδες** (εκτός Ινδίας). Τα data στο tab **ICCR_Rest** μπορεί να τα setάρεις/χρησιμοποιείς με αυτό το context (αγώνες χωρίς IND, ή focus σε AUS/ENG/κλπ.).

---

## Χρήση

- **Missing / minimal duration:** φιλτράρισε expected brands ανά αγώνα (Adidas/Apollo μόνο σε IND· Asics/Radar μόνο σε AUS και μόνο σε locations ρουχών· alcohol αγνοούνται σε muslim-country matches).
- **Outliers:** μην flagάρεις Adidas/Apollo σε μη-IND αγώνες· Asics/Radar σε μη-AUS αγώνες ή σε μη-ρουχά· alcohol brands σε αγώνες με μουσουλμανική χώρα.
