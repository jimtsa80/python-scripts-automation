# MCP Annotation Audit Server

MCP server για να συνδέεσαι στο Google Spreadsheet με annotation αποτελέσματα και να κάνεις audit μέσα από το Cursor: inconsistencies, missing brands, reports και ερωτήσεις στα δεδομένα.

**Στρατηγική:** Λίγα βασικά tools (schema, summary, get_data, value_counts, inconsistencies_by_group, find_inconsistencies, find_missing_brands, query, κ.λπ.). Ο AI συνδυάζει τα tools ανά ερώτηση αντί να προστίθενται νέα ειδικά tools για κάθε ερώτηση.

## Τι κάνει

- **Schema**: Δείχνει τις στήλες του sheet.
- **Summary**: Πλήθος γραμμών, headers, sample row.
- **Inconsistencies**: Ίδια λογική τιμή με διαφορετική γραφή (π.χ. "Dunlop" vs "dunlop" vs "Dunlop ") → ομαδοποίηση variants.
- **Missing brands**: Γραμμές με κενό brand + (προαιρετικά) expected brands που δεν εμφανίζονται. Τα expected φορτώνονται από τον **φάκελο του project** (ή legacy `brands_db/`).
- **Audit report**: Ένα πλήρες report (markdown) με inconsistencies και sample missing brands.
- **Query**: Φίλτρο σε column (π.χ. όλα όπου Brand = "Dunlop").
- **Get data**: Εξαγωγή δεδομένων (max_rows, προαιρετικά μόνο συγκεκριμένες στήλες). **Value counts** και **inconsistencies by group** για να απαντάς ερωτήσεις συνδυάζοντας κλήσεις.

## Δομή: γενικές οδηγίες (ρίζα) + ανά project

- **Ρίζα repo:** **`INSTRUCTIONS.md`** — γενικές οδηγίες για **όλα τα projects**: μορφή report (brands που λείπουν από .txt, brands/locations/brand·location με αποκλίσεις, προτεραιότητα από brands με περισσότερο duration), merge Part1/Part2, χρήση MCP tools χωρίς scripts. Το tool **`annotation_get_instructions`** επιστρέφει αυτές τις γενικές οδηγίες μαζί με τα project-specific.

- **Ανά project:** **`projects/<όνομα_tab>/`** — π.χ. `projects/ICC_IND/`
  - **`audit_rules.md`** — κανόνες audit (team-specific brands, alcohol σε muslim-country, κ.λπ.)
  - **`instructions.txt`** — μόνο project-specific (ποιο .txt για expected brands, Part1/Part2 για αυτό το project, κ.λπ.)
  - **`*.txt`** — expected brands (γραμμές `#Brand Name`)

**Results spreadsheet:** [Google Sheet](https://docs.google.com/spreadsheets/d/1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU/edit) — το ID είναι το default στο config. Το **tab επιλέγεται πάντα από το όνομα του project**: π.χ. `ANNOTATION_PROJECT=ICC_IND` → worksheet **ICC_IND**. Τα αρχεία (expected brands, audit_rules) διαβάζονται από **`projects/ICC_IND/`**. Έτσι αλλάζεις project αλλάζοντας μόνο τη μεταβλητή (ή το env στο MCP config).

## Κανόνες audit (context)

Στον φάκελο του project: **`audit_rules.md`** (ή χρήση του tool **`annotation_get_instructions`**). Team-specific brands (Ινδία: Adidas, Apollo Tyres · Αυστραλία: Asics, Radar Tyres) και αγνόηση alcohol brands σε αγώνες με μουσουλμανική χώρα.

## Προαπαιτούμενα

1. **Python 3.10+**
2. **Google Cloud project** με ενεργό **Google Sheets API** (και προαιρετικά Google Drive API).
3. **Service account** και JSON key (ήδη υπάρχουν στο project):
   - Τα credentials είναι στο **`resultsChecker_new/client_secret.json`** (ίδιο Google project με Sheets + Drive API).
   - **Κοινή χρήση** του spreadsheet με το **service account email** από το JSON ως Viewer (ή Editor αν χρειάζεσαι εγγραφή).

## Εγκατάσταση

**Με uv:**
```bash
cd mcp-annotation-audit
uv sync
```

**Με pip:**
```bash
cd mcp-annotation-audit
pip install mcp gspread google-auth
pip install -e .
```
(Το `-e .` εγκαθιστά το package σε editable mode ώστε να τρέχει `python -m mcp_annotation_audit` από οπουδήποτε.)

## Ρύθμιση

Ο server διαβάζει τις ακόλουθες **μεταβλητές περιβάλλοντος**:

| Μεταβλητή | Περιγραφή | Παράδειγμα |
|-----------|-----------|------------|
| `ANNOTATION_SPREADSHEET_ID` | ID του Google Sheet (από το URL). **Default:** results spreadsheet· μπορείς να το αφήσεις κενό | `1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU` |
| **`ANNOTATION_PROJECT`** | **Όνομα project = όνομα tab = όνομα φακέλου** (π.χ. `ICC_IND`). Όταν οριστεί, τα δεδομένα διαβάζονται από αυτό το tab και τα αρχεία από `projects/ICC_IND/` | `ICC_IND` |
| **`ANNOTATION_PROJECT_ROOT`** | **Ρίζα του repo** (φάκελος που περιέχει `src/` και `projects/`). Όταν το MCP τρέχει από άλλο path (π.χ. Cursor MCP), όρισε αυτό ώστε να βρίσκονται τα `projects/<name>/*.txt` και `audit_rules.md` | `F:\cursor\python-scripts-automation\mcp-annotation-audit` |
| `ANNOTATION_SHEET_NAME_OR_GID` | Όνομα sheet ή gid. **Χρησιμοποιείται μόνο αν δεν οριστεί ANNOTATION_PROJECT.** Κενό = πρώτο sheet | `94046938` ή `Sheet1` |
| `GSPREAD_CREDENTIALS` | Πλήρης διαδρομή στο JSON του service account | `F:\cursor\python-scripts-automation\resultsChecker_new\client_secret.json` |

Στο project χρησιμοποιούνται ήδη τα credentials από **`resultsChecker_new/client_secret.json`**. Άστο κενό μόνο αν θες να χρησιμοποιήσεις το default του gspread: `~/.config/gspread/service_account.json`.

### Παράδειγμα (Windows PowerShell) — με project

```powershell
$env:ANNOTATION_SPREADSHEET_ID = "1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU"
$env:ANNOTATION_PROJECT = "ICC_IND"   # tab name = folder name under projects/
$env:GSPREAD_CREDENTIALS = "F:\cursor\python-scripts-automation\resultsChecker_new\client_secret.json"
```

Χωρίς project (legacy): άσε κενό το `ANNOTATION_PROJECT` και βάλε `ANNOTATION_SHEET_NAME_OR_GID` αν χρειάζεσαι συγκεκριμένο sheet.

## Εκτέλεση (δοκιμή)

```bash
# Από το root του repo
cd mcp-annotation-audit
uv run python -m mcp_annotation_audit
```

Ο server τρέχει με stdio transport· το Cursor θα το καλεί αυτόματα όταν το προσθέσεις σαν MCP server.

## Προσθήκη στο Cursor

1. Άνοιξε **Cursor Settings** (Ctrl+,) → **MCP** (ή **Features** → **MCP**).
2. Πρόσθεσε νέο server. Συνήθως η config είναι σε JSON, π.χ.:

```json
{
  "mcpServers": {
    "annotation-audit": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "f:/cursor/python-scripts-automation/mcp-annotation-audit",
        "python",
        "-m",
        "mcp_annotation_audit"
      ],
      "env": {
        "ANNOTATION_SPREADSHEET_ID": "1MA5KmcDq4ZsxXH5dWlIz7Tp3r0A9ajcI8VyJkBFtyrU",
        "ANNOTATION_PROJECT": "ICC_IND",
        "GSPREAD_CREDENTIALS": "F:/cursor/python-scripts-automation/resultsChecker_new/client_secret.json"
      }
    }
  }
}
```

- Αν χρησιμοποιείς **pip**: εγκατέστησε πρώτα με `pip install -e .` από το `mcp-annotation-audit`. Στη config χρησιμοποίησε:
  `"command": "python", "args": ["-m", "mcp_annotation_audit"]` και στο `env` πρόσθεσε τις μεταβλητές. Μπορείς να βάλεις και `"cwd": "f:/cursor/python-scripts-automation/mcp-annotation-audit"` αν το package δεν είναι global.

3. Αποθήκευσε και κάνε restart Cursor (αν χρειάζεται). Μετά μπορείς να ρωτάς π.χ.:
   - “Πόσες γραμμές έχει το annotation sheet;”
   - “Βρες inconsistencies στα brands”
   - “Ποια brands λείπουν για ICC;” (με `brands_file=2026_ICC_T20`)
   - “Ένα audit report για το annotation sheet”

## Brands και οδηγίες ανά project

- **Με `ANNOTATION_PROJECT`**: Ο server ψάχνει στο **`projects/<ANNOTATION_PROJECT>/`**. Εκεί μπορείς να βάλεις:
  - **`instructions.txt`** — οδηγίες (το tool **`annotation_get_instructions`** τις επιστρέφει).
  - **`audit_rules.md`** — κανόνες audit (επιστρέφονται κι αυτά από **`annotation_get_instructions`**).
  - **`*.txt`** — expected brands (ίδιο format: γραμμές `#Brand Name`). Το **`annotation_list_brands_files`** δείχνει τα διαθέσιμα· στο **`annotation_find_missing_brands`** περνάς `brands_file="2026_ICC_T20"` (όνομα χωρίς .txt).
- **Χωρίς project (legacy)**: Τα brands διαβάζονται από **`mcp-annotation-audit/brands_db/`**.

## Tools που εκθέτει (για το AI)

- `annotation_get_schema` – headers του sheet
- `annotation_get_summary` – σύνοψη (row count, sample)
- **`annotation_get_instructions`** – οδηγίες και audit rules από τον φάκελο του project (`instructions.txt`, `audit_rules.md`)
- `annotation_list_brands_files` – λίστα .txt αρχείων στο project folder (ή brands_db/)
- `annotation_find_inconsistencies` – ομάδες variants (key_columns προαιρετικό)
- `annotation_find_missing_brands` – κενά brands + expected που δεν υπάρχουν (expected_brands ή brands_file, π.χ. brands_file="2026_ICC_T20")
- `annotation_audit_report` – πλήρες audit report (markdown)
- `annotation_query` – filter_column + filter_value
- `annotation_get_data` – δεδομένα (max_rows, προαιρετικά columns για μικρότερο payload)
- `annotation_value_counts` – πλήθος ανά τιμή στήλης (π.χ. top brands)
- `annotation_inconsistencies_by_group` – ανά group (π.χ. Brand) inconsistencies σε άλλη στήλη (π.χ. Location)
- `annotation_get_expected_brands` – επιστρέφει τη λίστα expected brands από ένα brands_db αρχείο (για να την συνδυάζει ο LLM με get_data και να κάνει ο ίδιος grouping/sύγκριση ανά αγώνα κ.λπ.).

Ο **LLM** κάνει τη δουλειά: συνδυάζει τα tools (π.χ. get_expected_brands + get_data με columns File,Brand), ομαδοποιεί ανά αγώνα (Part1/Part2 → ίδιο match), και υπολογίζει missing/minimal. Δεν προστίθενται νέα ειδικά tools για κάθε ερώτηση.

## Troubleshooting

- **SpreadsheetNotFound / 404**: Κάνε share το sheet με το service account email.
- **Permission denied**: Ενεργοποίησε Google Sheets API (και αν χρειάζεται Drive API) στο project.
- **ANNOTATION_SPREADSHEET_ID missing**: Πρόσθεσε τη μεταβλητή στο `env` του MCP config στο Cursor.
