# **PRD.md — Dynamic HTML Brochure Generator (No-JS Output)**

**Doc owner:** Witness Alchemist

**Version:** 1.0 (one-shot PRD)

**Status:** Draft for build

**Last updated:** 2025-08-18

---

## **1) Summary**

Build a deterministic **Python** brochure generator that composes a **luxury-grade, print-ready HTML + CSS** catalogue from a **products.json** file (and later Excel). Output must contain **zero JavaScript** while preserving a premium visual layout (cover, contents, per-category hero, product grid cards). The system will be run on demand (CLI/CI) whenever the product set changes, producing a zipped artifact (HTML, CSS, assets) and optionally a PDF via a headless renderer (out of scope for MVP code, documented for ops).

---

## **2) Goals & Non-Goals**

### **Goals**

1. **Deterministic generation:** Given **products.json**, produce identical brochure output (idempotent).
2. **Luxury visual:** Modern, editorial look: cover section, contents list, category sections, hero (optional), grid product cards, refined print CSS.
3. **Data parsing:** Robustly extract **specs (key:value)** and **features (bullets)** from noisy concatenated strings in input.
4. **Zero-JS brochure:** Output strictly HTML + CSS (no external fonts by default; safe fallbacks).
5. **Easy selection:** Include/exclude products by model or status without editing templates.
6. **Single-command build:** Simple CLI for local/CI use.
7. **Extensibility hooks:** Clear points to add i18n, comparison spreads, and Excel input later.

### **Non-Goals (MVP)**

* No interactive elements in the output (no toggles, no filters).
* No live hosting or CMS editor.
* No in-browser rendering controls or variable fonts loading.
* i18n and comparison spreads are **deferred** to later phases.

---

## **3) Success Metrics**

* **Rendering fidelity:** 1:1 with reference layout principles; passes stakeholder visual review.
* **Robustness:** Handles ≥1,000 SKUs without formatting breaks; no orphan headings; no broken anchors.
* **No-JS compliance:** Lighthouse shows 0 JS bytes; static assets only.
* **Time to generate:** ≤10s for 1k SKUs on a standard CI runner.
* **Zero blocking errors on malformed product rows:** invalid entries are logged & skipped; build still succeeds.

---

## **4) Primary Users & Personas**

* **Marketing Ops:** runs builds when offerings change; needs consistent output for web/PDF.
* **Sales:** requests quick, curated selections to send with quotes.
* **Design Lead:** enforces typography and layout polish; approves themes.
* **Partner/Reseller:** downloads static brochure for their locale (later i18n).

---

## **5) User Stories (MVP)**

1. **As Marketing Ops, I run **brochure build --src products.json** and get **/out/index.html** + **/out/catalog.css**.**
2. As Sales, I build only a subset by SKU: **brochure build --include IPB195,T772**.
3. As Design Lead, I swap brand tokens (colors, spacing) in one file to restyle the entire brochure.
4. As Marketing Ops, I get graceful placeholders when images are missing—no layout collapse.

---

## **6) Scope of MVP**

* **Input:** **products.json** (schema below).
* **Layouts:** *Category Hero* (optional, single product) +  *Product Grid* .
* **Theming:** One “luxury dark” theme via CSS tokens; print CSS included.
* **Output:**/out/index.html**, **/out/catalog.css**, **/out/assets/*** (if images supplied).**
* **Interfaces:** CLI commands; basic logs.
* **Docs:** README with run instructions; sample JSON.

---

## **7) Input Data Model**

### **7.1 Product JSON (raw)**

Each element resembles:

```
{
  "id": "uuid-or-similar",
  "name": "AC Hard-wire Video Doorbell",
  "model": "IPB195",
  "category": "Video Door Bell",
  "supplier": "Vendor X",
  "status": "published",
  "images": ["path-or-url.png"],
  "specifications": {
    "specifications": "Image sensor: 2MP CMOS | Lens: 100° fixed focus | Video: 1920x1080 | Features: IR night vision, two-way audio",
    "features": "Siren | Motion detection"
  },
  "price": 0,
  "currency": "USD"
}
```

**Notes**

* Many real rows mix **specs** and **features** in **specifications.specifications**. The parser must split by pipe/commas, detect **key: value** pairs for specs, and treat the rest as features.
* **status** may contain non-status prose; treat such content as a **note** and default status to **published**.

### **7.2 Normalized Product (internal)**

After parsing/deduplication by **model**:

```
{
  "product_name": "AC Hard-wire Video Doorbell",
  "model": "IPB195",
  "category": "Video Door Bell",
  "features": ["IR night vision", "Two-way audio", "Siren"],
  "specs": {"Image sensor":"2MP CMOS","Lens":"100° fixed focus","Video":"1920x1080"},
  "note": null,
  "image": "assets/IPB195.png"
}
```

---

## **8) Layout System**

### **8.1 Page Structure**

* **Cover**: title + subtitle + soft gradients; no hero image required.
* **Contents**: list of categories with anchors.
* **Category Section** **:**
* **Optional Hero Card**: chosen by rule (specific models) or heuristic (most specs ≥6).
* **Product Grid**: responsive cards, 2–4 per row (CSS only).
* **Footer Note**: generation stamp.

### **8.2 Components**

* **Product Card**
  * Media area (image or SVG placeholder)
  * Title + Model code badge
  * Key–value spec table
  * Features line (comma-separated)
  * Subtle footer row (category label)
* **Hero Card**
  * Two-column emphasis; larger media; same table & features.

### **8.3 Layout Rules (MVP)**

* Pick hero per category by:
  1. **Rule file**layout_rules.json**: **"hero_models": ["IPB195","IPB215"]
  2. Else heuristic: product with highest spec count (≥6).

---

## **9) Visual & Typography**

* **Design language:** editorial luxury; soft gradients; subtle inner glow; dark panels with crisp separators.
* **Tokens:** background, card, line, ink, muted, accent, spacing scale, border radius.
* **Typography:** system fonts (Inter fallback via OS). Later: optional brand font via CSS @font-face (still no JS).
* **Print CSS:** **@page { size: A4; margin: 18mm }**, avoid breaks inside cards (**break-inside: avoid**), contents set to 2 columns when printing.

---

## **10) Non-Functional Requirements**

* **Performance:** 1k SKUs renders in ≤10s.
* **Reliability:** Build does not fail on malformed rows; logs warn & continue.
* **Portability:** Python 3.10+; no external native deps for MVP.
* **Security:** No remote fetch in generation; treat image paths as local or already vetted URLs.
* **Compliance:** Output uses semantic HTML; alt text for images from product name.

---

## **11) System Architecture**

```
CLI (Python)
  ├── Loader: read products.json
  ├── Normalizer: dedupe by model, parse specs/features, coerce fields
  ├── Grouper: category → [products], select hero
  ├── Renderer: Jinja2 → HTML, copy CSS, copy assets
  └── Artifact: /out/index.html, /out/catalog.css, /out/assets/*
```

* **Templating:** Jinja2 partials
  * **catalog.html.j2** (cover, contents, sections)
  * product_card.html**, **hero_card.html
* **No JS** embedded or linked.

---

## **12) CLI & Configuration**

### **12.1 Commands**

```
brochure build --src products.json --out out
brochure build --src products.json --out out --include IPB195,T772
brochure build --src products.json --out out --rules layout_rules.json
```

### **12.2 Flags**

* **--src** (required): path to JSON
* **--out** (default: **out/**)
* **--include** (optional): CSV list of models to include
* --rules** (optional): path to **layout_rules.json
* **--theme** (future): choose style token set

### **12.3 Exit codes**

* **0** success
* **1** unrecoverable (bad JSON, template missing)

---

## **13) Parsing Algorithm (MVP)**

1. **Split** **specifications.specifications** by **|** (and normalize **||**), then for each segment:
   * **If it contains **:** → **key:value** → **specs[key]=value
   * Else → append to **features**
2. If **specifications.features** present, split by **|**/**,**/**;** and merge into **features**.
3. **Clean** duplicates, trim punctuation; skip **"Not Selected"**.
4. **Status**: if value not in {published, draft, archived, to be ordered, not selected, ''}**, treat it as ****note**; set status=published**.**
5. **Deduplicate by model** (first instance wins).
6. **Group** by category.
7. **Hero pick** by rule list or spec-count heuristic.

---

## **14) Error Handling & Edge Cases**

* Missing **model**: log **WARN: missing model**, include using generated key, but never use for hero.
* **Missing **category**: default **"Uncategorized"**.**
* Empty **specs** & **features**: still render card (only name/model/table header hidden).
* Extremely long values: truncate visually via CSS **overflow-wrap: anywhere;**.
* Duplicate models across categories: first occurrence wins; subsequent dropped with warning listing both categories.

---

## **15) Directory Layout**

```
project/
  brochure/
    templates/
      catalog.html.j2
      product_card.html
      hero_card.html
    styles/
      catalog.css
    cli.py
    parser.py
    renderer.py
    __init__.py
  examples/
    products.json
    layout_rules.json
  out/
    index.html
    catalog.css
    assets/
```

---

## **16) Testing Strategy**

* **Unit tests:** parser (segment splitting, spec detection, de-dup), hero selection logic, include filter.
* **Golden tests:** snapshot HTML for small catalogs to detect unintended visual changes (DOM assertions).
* **Load test:** 1k–5k products random synthetic data.
* **Accessibility lint:** headings order, alt text present, contrast tokens verified.
* **No-JS check:** assert no **`<script>`** tag in output.

---

## **17) Release & Deployment**

* **Packaging:** **pipx**-installable CLI (**pyproject.toml**).
* **CI:** GitHub Actions
  * Lint + tests
  * **Build artifacts (**/out**) from **examples/products.json
  * Optionally upload artifact to release
* **Ops (optional):** Headless Chrome/Playwright step to render PDF from **index.html** (env-specific, not in MVP code).

---

## **18) Risks & Mitigations**

* **Inconsistent input formatting** → robust parser & warnings; add “strict mode” for later.
* **Design drift** with future categories → keep template partials isolated; tokens only for color/spacing.
* **Image quality variance** → enforce min dimensions via QA checklist; placeholder SVG to keep rhythm.

---

## **19) Roadmap**

**MVP (Week 1–2)**

* Parser + normalizer
* Jinja templates (cover, hero, grid)
* Luxury CSS theme + print CSS
* CLI + basic tests
* Docs + example data

**Phase 1.1**

* Excel ingestion (pandas), SKU manifest, ordering per category
* Multiple themes (dark/light)

**Phase 2 (Deferred)**

* i18n (EN/FR)
* Comparison spreads
* Brand font integration (self-hosted)
* PDF export job in CI

---

## **20) Acceptance Criteria (MVP)**

* **Given a valid **products.json**, **brochure build** creates **/out/index.html** + **/out/catalog.css** with:**
  * Cover + contents anchors for each category.
  * For every category: optional hero + grid cards.
  * Each card shows name, model, spec table (if any), features line (if any).
  * No **`<script>`** tags or inline JS in output.
  * Print test produces readable A4 with no broken cards across pages.
* Parser handles mixed spec/feature strings and emits warnings, not crashes.
* Building with **--include** restricts to those models only.

---

## **21) Open Questions**

* Do we need deterministic category ordering (config file) vs. alpha by default?
* Will we ship brand fonts (license) or keep system fonts until Phase 2?
* Image sourcing: local only or permit CDN URLs (with copy or leave external)?

---

## **22) Glossary**

* **Hero Card:** Prominent, larger card placed at the top of a category.
* **Grid Card:** Standard product tile with media, specs, features.
* **No-JS Output:** The final brochure must contain no JavaScript resources or tags.
* **Idempotent Build:** Same input → identical output.

---

## **23) Appendix**

### **23.1 Example** ****

### **layout_rules.json**

### ** (optional for hero)**

```
{
  "rules": [
    {"match": {"category": "Video Door Bell"}, "hero_models": ["IPB195","IPB215"]}
  ]
}
```

### **23.2 Example CLI Usage**

```
# Build full brochure
brochure build --src ./products.json --out ./out

# Build selected SKUs
brochure build --src ./products.json --include IPB195,T772 --out ./out
```

### **23.3 CSS Tokens (extract)**

```
:root{
  --bg:#0b0d12; --panel:#0f1218; --card:#131722;
  --ink:#e9eefb; --muted:#9fb0c9; --line:#212735;
  --accent:#78c3ff; --glow:rgba(120,195,255,.08);
}
```

---

**End of PRD**
