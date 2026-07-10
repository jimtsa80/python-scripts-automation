# Κανόνες audit – brands ανά context

Χρησιμοποιούνται ώστε να **μην** θεωρούνται λάθος/outlier/missing brands που λείπουν λόγω χώρας ή θρησκείας.

---

## 1. Team-specific brands (μόνο όταν παίζει η χώρα)

| Χώρα    | Brands              | Σημείωση |
|---------|---------------------|----------|
| **Ινδία**  | Adidas, Apollo Tyres | Να λαμβάνονται υπόψη **μόνο** σε αγώνες με Ινδία. Σε άλλους αγώνες (π.χ. AUS v ENG) να μην τα ελέγχουμε ως missing/outlier. |
| **Αυστραλία** | Asics, Radar Tyres | Να λαμβάνονται υπόψη **μόνο** σε αγώνες με Αυστραλία. Σε άλλους αγώνες να μην τα ελέγχουμε. |

---

## 2. Αγώνες με μουσουλμανική χώρα – alcohol brands

Όταν παίζει **μουσουλμανική χώρα** (π.χ. Pakistan, UAE, κ.λπ.), **να μην ελέγχουμε** brands που σχετίζονται με αλκοόλ· δεν υπάρχουν στο broadcast.

- **Alcohol-related brands** (παράδειγμα): Budweiser, Royal Stag. (Η λίστα μπορεί να επεκταθεί.)
- Παράδειγμα: σε IND v PAK να μην θεωρούμε missing/outlier τα alcohol brands.
- Σε αγώνες χωρίς μουσουλμανική χώρα, τα alcohol brands ελέγχονται κανονικά.

---

## Χρήση

- Σε αναλύσεις **missing / minimal duration**: να φιλτράρουμε expected brands ανά αγώνα (team-specific + alcohol σε muslim-country matches).
- Σε **outliers**: να μην flagάρουμε ως outlier τα Adidas/Apollo Tyres σε μη-IND αγώνες, και Asics/Radar Tyres σε μη-AUS αγώνες· και να αγνοούμε alcohol brands σε αγώνες με μουσουλμανική χώρα.
