# Recut Tracker Reference Guide

---

## QUICK START - Resume Session

**Read this section first when resuming work on this project.**

### Project Location
```
/Users/modobrew/Documents/Claude-Projects-2026/Recut_Tracker/
```

### Current Project Status: MVP COMPLETE (Feb 2026)
- Data structure analyzed and documented
- Roles identified (5 total)
- Error code mappings established
- All 5 role specifications complete:
  - Cutting Manager (A) - cutting errors, recuts by material/SKU
  - Sewing Manager (B) - repairs, SMO performance, detection location
  - Production Manager (C) - holistic view, department breakdown
  - QC Manager (D) - detection effectiveness (Sewing vs QC)
  - Operations Director (E) - strategic view, trends, investment priorities
- Data loader built and tested
- Streamlit dashboard built with all 5 role views

### To Run Locally
```bash
cd /Users/modobrew/Documents/Claude-Projects-2026/Recut_Tracker
streamlit run app.py
```
Then open browser to: http://localhost:8501

### To Stop Local Dashboard
Press `Ctrl+C` in the terminal, or:
```bash
pkill -f "streamlit run"
```

### Key Files
| File | Purpose |
|------|---------|
| `Recut_Tracker_Reference.md` | This file - project documentation |
| `Roles.md` | ONE Tracker role spec (reference for pattern) |
| `ONE_Tracker_Reference.md` | ONE Tracker full reference (similar project) |
| `Rework_Tracker_JAN26.xlsm` | Source data file |
| `requirements.txt` | Python dependencies |
| `app.py` | Main Streamlit dashboard application |
| `utils/data_loader.py` | Excel parsing, data cleaning, Error Source classification |
| `utils/sku_utils.py` | Parent SKU rollup logic |
| `utils/metrics.py` | KPI calculations for all 5 roles |

### Related Project
This project follows the pattern established by the **ONE Tracker Dashboard**:
- Location: `/Users/modobrew/Documents/Claude-Projects-2026/ONE_Tracker/`
- Live App: https://one-tracker-dashboard.streamlit.app
- GitHub: https://github.com/modobrew/ONE-Tracker-Dashboard

---

## Overview

The Recut Tracker is a tool for tracking rework events - repairs, recuts, and fails that occur during production. It helps identify problem areas by SKU, operator, material, and error type.

**Goal:** Build a Streamlit dashboard (similar to ONE Tracker) that allows users to:
1. Upload the Rework Tracker Excel file
2. Select a role-based view
3. View KPIs and insights relevant to their role
4. Identify problem areas and actionable items

---

## Data Source

**File:** `Rework_Tracker_JAN26.xlsm`

### Sheets
| Sheet | Purpose | Ignore? |
|-------|---------|---------|
| Reference Lists | Data validation dropdowns | Yes |
| 2025 Sewing Repairs | Order-level repair tracking | No |
| Recut List | Individual recut piece tracking | No |

**Note:** "2025 Sewing Repairs" contains 2026 data as well. The Date column determines when the event occurred.

---

## Sheet 1: 2025 Sewing Repairs

**Purpose:** Tracks repairs at the production order level.

**Row count:** ~1,605 records

**Date range:** April 2024 - Present (ongoing)

### Columns (Use These)
| # | Column | Data Type | Description |
|---|--------|-----------|-------------|
| 0 | Date | Date | When repair occurred |
| 1 | Repair Discovered | Text | Where found: SEWING or QC |
| 2 | SKU-Colorway-Size | Text | Product identifier |
| 3 | PR# | Text | Production order number (e.g., PR14875) |
| 4 | Total Qty | Integer | Total units in order |
| 5 | Repair Qty | Integer | Units repaired |
| 6 | Repair Time (min) | Integer | Time spent on repair (minutes) |
| 7 | % Repaired | Decimal | Repair Qty / Total Qty |
| 8 | Reason for Repair | Text | Free text description |
| 9 | Recut Qty | Integer | Units requiring recut |
| 10 | Reason for Recut | Text | Free text description |
| 11 | Fail Qty | Integer | Units that failed/scrapped |
| 12 | Reason for Fail | Text | Free text description |
| 13 | Reason Code | Text | Standardized error code (see Error Codes) |
| 14 | Manager | Text | Sewing manager name |
| 15 | SMO/PA | Text | Sewing Machine Operator or Production Assistant |
| 16 | CMO | Text | Cutting Machine Operator (when cutting-related) |

### Columns (Ignore)
- Column 17 (Column1) and all Unnamed columns after - empty/unused

### Repair Discovered Values
- `SEWING` - Defect found during sewing process
- `QC` - Defect found at Quality Control inspection

### Manager Names (normalize case)
- Yolanda, Humberto, Louisa, Chris, Bryce, Izzy, McKade

### SMO Name Formatting
SMO names are normalized to format: **First Initial + Last Name** (e.g., JSmith)
- First letter capitalized (initial)
- Second letter capitalized (start of last name)
- Rest of name lowercase
- Examples: `JSMITH` → `JSmith`, `jfernandez` → `JFernandez`, `MANGELA` → `MAngela`

---

## Sheet 2: Recut List

**Purpose:** Tracks individual pieces that needed to be recut.

**Row count:** ~6,054 records

**Date range:** March 2025 - Present (ongoing)

### Columns (Use These)
| Column | Data Type | Description |
|--------|-----------|-------------|
| CODE | Text | Error code indicating responsibility |
| SKU | Text | Product identifier |
| Material | Text | Material type used (e.g., FB-SQ-CMA) |
| Cut/Length | Text | What part was cut (e.g., Flap, Front, Molle) |
| QTY | Integer | Pieces needing recut |
| Operator/Order# | Text | Sewing operator name (who caused error) |
| Order# | Text | Order number |
| Document_No | Text | PR number (links to Sewing Repairs PR#) |
| PA | Text | Production Assistant who handled it |
| Time | Time | Time of entry |
| Date | Date | Date of entry |
| Due Date | Date | Order due date |
| On list | Boolean | Is it on the recut list? |
| Done | Boolean | Has it been completed? |
| scrap? | Boolean | Was it scrapped? |
| RECUT? | Boolean | Was it recut? |
| FAILED? | Boolean | Did it fail? |
| QTY Failed | Integer | Quantity that failed |
| Date Scrapped | Date | When scrapped (if applicable) |

### Columns (Ignore)
- Column 20+ (Column17, Column18, etc. and all Unnamed) - empty/unused

### Data Quality Notes
- **Case inconsistencies in names:** Normalize during data loading
  - PA examples: WILL/Will/will, MCKADE/McKade/mckade, CODY/Cody/cody
  - Operator examples: YOLANDA/Yolanda, ANGELA/Angela
- **Boolean column garbage:** Some rows have invalid values (*, \, backticks, etc.) - treat as False

---

## Error Codes & Error Source Classification

**IMPORTANT:** "Error Source" is the standardized classification used in the dashboard. Error codes from both sheets are mapped to these categories.

### Error Source Categories

| Error Source | Description | Equipment Types |
|--------------|-------------|-----------------|
| Cutting Operator Error | Human error in cutting department | - |
| Sewing Operator Error | Human error in sewing department | - |
| Cutting Machine Error | Equipment malfunction in cutting | Hot cut, Laser, Cold cut, Die clicker/Gerber |
| Sewing Machine Error | Equipment malfunction in sewing | Sewing machine, AMS |
| Other Machine Error | Other equipment issues | - |
| Material Defect | Raw material issues | - |
| Other | Miscellaneous/uncategorized | - |

### Sewing Repairs - Reason Code Mapping

| Code | Error Source | Error Type |
|------|--------------|------------|
| A1A | Cutting Operator Error | Cutting Error |
| A1B | Cutting Operator Error | Marking Error |
| A1C | Cutting Operator Error | Kitting Error |
| A1D | Cutting Operator Error | Other Error |
| A2A | Sewing Operator Error | Sewing Error |
| A2D | Sewing Operator Error | Other Error |
| A1 | Cutting Machine Error | Laser |
| B1C | Cutting Machine Error | Hot Cut |
| B1E | Cutting Machine Error | Laser |
| A | Sewing Machine Error | Sewing |
| B2 | Sewing Machine Error | Sewing |
| B3 | Other Machine Error | Other |
| C1 | Material Defect | Skipped Picks |
| C2 | Material Defect | Out of Spec |
| C3 | Material Defect | Other |

**Older format codes (also present):**
- S1-S8: Sewing Operator Error (various sewing errors)

### Recut List - CODE Column Mapping

| Code | Error Source | Description |
|------|--------------|-------------|
| A | Sewing Operator Error | Sewing operator error |
| A: SMO Error | Sewing Operator Error | Sewing Machine Operator error |
| B | Cutting Operator Error | Wrong material cut |
| C | Cutting Operator Error | Marking error |
| F | Cutting Operator Error | Material cut too short |
| L | Cutting Machine Error | Laser error |
| AMS | Sewing Machine Error | AMS error |
| A* | Other Machine Error | Machine error |
| D | Material Defect | Material defect |
| E | Other | Missing pieces |
| P | Other | Production Assistant error |

---

## Role Responsibility Mapping

### Cutting Manager (CM) - NEW ROLE
**Focus:** Cutting-related errors and recuts

**Relevant Error Sources:**
- Cutting Operator Error: Human errors (wrong material, marking, kitting, cut too short)
- Cutting Machine Error: Equipment issues (Hot cut, Laser, Cold cut, Die clicker/Gerber)

**Key Questions:**
- How many pieces needed recut due to cutting errors?
- Which CMOs have the most errors?
- Which materials/SKUs have the most cutting issues?
- What are the most common cutting error types?

### Sewing Manager
**Focus:** Sewing-related errors and repairs

**Relevant Error Sources:**
- Sewing Operator Error: Human errors from SMOs
- Sewing Machine Error: Equipment issues (Sewing machine, AMS)

**Key Questions:**
- Which SMOs have the most repairs?
- Which SKUs cause the most sewing issues?
- How much repair time is being consumed?
- What are the most common sewing error types?

### Production Manager
**Focus:** Overall rework impact on production

**Relevant Data:** All records from both sheets, all Error Source categories

**Key Questions:**
- Total repairs, recuts, fails?
- Impact on throughput (repair time)?
- Problem SKUs driving the most rework?
- Error Source breakdown (operator vs machine vs material)?

### QC Manager
**Focus:** Where defects are being caught (detection location)

**Relevant Data:** Sewing Repairs where Repair Discovered = QC or SEWING

**Note:** "Caught at Sewing vs QC" refers to where repairs/issues were **discovered**, not where fails occurred.

**Key Questions:**
- What's being caught at QC vs Sewing?
- Are defects escaping to QC that should be caught earlier?
- Which inspectors/SKUs have the most QC-caught issues?

### Operations Director
**Focus:** High-level metrics and trends

**Relevant Data:** Aggregated metrics from both sheets

**Key Questions:**
- Overall rework load (proxy for cost of quality)?
- Month-over-month trends?
- Which Error Sources need investment/training?

---

## Role View Specifications

### A) Cutting Manager View

**Purpose:** Monitor cutting department errors, identify problem materials/SKUs, and reduce recuts.

#### Data Sources

| Source | Filter | What it provides |
|--------|--------|------------------|
| Recut List | CODE in (B, C, F) | Individual recut pieces, Material, Cut/Length |
| Sewing Repairs | Reason Code starts with A1 | Order-level data, Recut Qty, Fail Qty, CMO (when populated) |

**Note:** CMO responsible for cutting errors must be determined by cross-referencing PR# and Material SKU with external document.

#### A1) Summary Metric Cards

| Metric | Source | Calculation |
|--------|--------|-------------|
| Total Recut Pieces | Recut List (B/C/F) | Sum of QTY |
| Total Cutting Incidents | Sewing Repairs (A1x) | Count of records |
| Recut Qty (from Repairs) | Sewing Repairs (A1x) | Sum of Recut Qty |
| Fail Qty (from Cutting) | Sewing Repairs (A1x) | Sum of Fail Qty |
| Cutting Errors | Both | Count where A1A or B |
| Marking Errors | Both | Count where A1B or C |
| Kitting Errors | Sewing Repairs | Count where A1C |

#### A2) Key Insights (auto-generated bullets)

Generate 3-5 bullets using these rules (show only bullets that trigger):

- "{X} recut pieces this period from cutting-related errors."
- If marking errors > cutting errors: "Marking errors exceed cutting errors - review marking process."
- If one material > 20% of recuts: "Material {X} accounts for {Y}% of recuts - investigate."
- If kitting errors > 0: "{N} kitting errors recorded - verify kitting procedures."
- Trend comparison: "Recuts trending {up/down} {X}% vs prior period."

#### A3) Charts

1. **Recut Pieces Over Time** - Line or bar chart by week/month
2. **Error Type Breakdown** - Pie or bar chart (Cutting vs Marking vs Kitting vs Other)
3. **Top 10 Materials by Recut Count** - Horizontal bar chart

#### A4) Tables

1. **Recuts by Material**
   - Columns: Material, Total Recut Pieces, Cutting Errors, Marking Errors, Cut Too Short
   - Source: Recut List (B/C/F codes)
   - Sort by: Total Recut Pieces (descending)

2. **Recuts by Parent SKU (Finished Good)**
   - Columns: Parent SKU, Total Recut Pieces, Materials Affected (list)
   - Source: Recut List (B/C/F codes) with SKU rolled up to Parent
   - Sort by: Total Recut Pieces (descending)

3. **Cutting Incidents by Error Type**
   - Columns: Error Type, Count, Recut Qty, Fail Qty
   - Source: Sewing Repairs (A1x codes)
   - Rows: Cutting Error (A1A), Marking Error (A1B), Kitting Error (A1C), Other (A1D)

4. **Cutting Incident Detail**
   - Columns: Date, PR#, SKU, Recut Qty, Fail Qty, Reason Code, CMO, Reason for Recut
   - Source: Sewing Repairs (A1x codes)
   - Sort by: Date (descending)

---

### B) Sewing Manager View

**Purpose:** Monitor sewing department repairs, identify problem SKUs, track SMO performance, and improve inline detection.

#### Data Sources

| Source | Filter | What it provides |
|--------|--------|------------------|
| Sewing Repairs | All records; A2x/S codes for sewing-specific errors | Repair Qty, Repair Time, Recut Qty, Fail Qty, SMO, Reason Code |
| Recut List | CODE in (A, "A: SMO Error") | Recuts caused by sewing operator errors |

#### B1) Summary Metric Cards

| Metric | Source | Calculation |
|--------|--------|-------------|
| Total Repairs | Sewing Repairs | Sum of Repair Qty |
| Total Repair Time (min) | Sewing Repairs | Sum of Repair Time (min) |
| Avg Time per Repair | Sewing Repairs | Total Repair Time (min) / Total Repairs |
| Total Recuts (Sewing Errors) | Recut List (A codes) | Sum of QTY |
| Total Fails | Sewing Repairs | Sum of Fail Qty |
| % Caught at Sewing | Sewing Repairs | (Count where Repair Discovered = SEWING / Total Count) × 100 |
| % Caught at QC | Sewing Repairs | (Count where Repair Discovered = QC / Total Count) × 100 |
| Sewing Error Incidents | Sewing Repairs (A2x/S codes) | Count of records |

#### B2) Key Insights (auto-generated bullets)

Generate 3-5 bullets using these rules (show only bullets that trigger):

- "{X} total repairs consuming {Y} minutes ({Z} hours) of repair time."
- If % Caught at QC > % Caught at Sewing: "More issues caught at QC ({X}%) than Sewing ({Y}%) - improve inline detection."
- If % Caught at Sewing > 60%: "Good inline detection - {X}% of issues caught at Sewing before QC."
- If one SKU > 15% of repairs: "SKU {X} accounts for {Y}% of repairs - review work instructions or training."
- Trend comparison: "Repairs trending {up/down} {X}% vs prior period."
- If avg repair time > threshold: "Average repair time is {X} min - investigate high-effort repairs."

#### B3) Charts

1. **Repairs Over Time** - Line or bar chart by week/month
2. **Detection Location** - Pie chart (% Caught at Sewing vs % Caught at QC)
3. **Top 10 SKUs by Repair Qty** - Horizontal bar chart

#### B4) Tables

1. **Top SKUs by Repair Qty**
   - Columns: Parent SKU, Repair Qty, Total Repair Time (min), Fail Qty, Recut Qty
   - Source: Sewing Repairs (all records, rolled up by Parent SKU)
   - Sort by: Repair Qty (descending)

2. **Top SKUs by Repair Time**
   - Columns: Parent SKU, Total Repair Time (min), Repair Qty, Avg Time per Repair
   - Source: Sewing Repairs (all records, rolled up by Parent SKU)
   - Sort by: Total Repair Time (descending)

3. **Repairs by Error Type**
   - Columns: Reason Code, Count, Repair Qty, Total Repair Time (min), Fail Qty
   - Source: Sewing Repairs (A2x and S codes only)
   - Shows breakdown of sewing-specific error types

4. **SMO Performance**
   - Columns: SMO, Repair Qty, Total Repair Time (min), Avg Time per Repair, Fail Qty, Parent SKUs Repaired
   - Source: Sewing Repairs (SMO/PA column)
   - Sort by: Repair Qty (descending)
   - Note: Normalize SMO names for accurate aggregation (format: JSmith - first initial + last name)

5. **Recuts from Sewing Errors**
   - Columns: Parent SKU, Recut Pieces, Materials Affected
   - Source: Recut List (A codes)
   - Sort by: Recut Pieces (descending)

---

### C) Production Manager View

**Purpose:** Monitor overall rework impact on production, identify problem SKUs, and understand where issues originate across departments.

#### Data Sources

| Source | Filter | What it provides |
|--------|--------|------------------|
| Sewing Repairs | All records | Repair Qty, Repair Time, Recut Qty, Fail Qty, by SKU/department |
| Recut List | All records | Individual recut pieces, by error type/department |

#### C1) Summary Metric Cards

| Metric | Source | Calculation |
|--------|--------|-------------|
| Total Rework Events | Both | Sewing Repairs count + Recut List count |
| Total Repairs | Sewing Repairs | Sum of Repair Qty |
| Total Repair Time (min) | Sewing Repairs | Sum of Repair Time (min) |
| Total Recut Pieces | Recut List | Sum of QTY |
| Total Fails | Sewing Repairs | Sum of Fail Qty |
| % Cutting Operator Errors | Both | (Cutting Operator Error incidents / Total incidents) × 100 |
| % Sewing Operator Errors | Both | (Sewing Operator Error incidents / Total incidents) × 100 |
| % Cutting Machine Errors | Both | (Cutting Machine Error incidents / Total incidents) × 100 |
| % Sewing Machine Errors | Both | (Sewing Machine Error incidents / Total incidents) × 100 |
| % Other Machine Errors | Both | (Other Machine Error incidents / Total incidents) × 100 |
| % Total Machine Errors | Both | (All machine error incidents / Total incidents) × 100 |
| % Material Defects | Both | (Material Defect incidents / Total incidents) × 100 |

**Error Source Classification:** See "Error Codes & Error Source Classification" section above.

#### C2) Key Insights (auto-generated bullets)

Generate 3-5 bullets using these rules (show only bullets that trigger):

- "{X} total rework events consuming {Y} hours of repair time this period."
- If one Error Source > 40%: "{X}% of issues originate from {Error Source} - coordinate with relevant Manager."
- If one SKU > 10% of rework: "SKU {X} accounts for {Y}% of all rework - prioritize for review."
- Trend comparison: "Rework trending {up/down} {X}% vs prior period."
- If fails > 0: "{X} units failed/scrapped this period - monitor material loss."

#### C3) Charts

1. **Rework Over Time** - Line chart showing Repairs, Recuts, Fails trends (separate lines or stacked)
2. **Error Source Breakdown** - Pie chart (Cutting Operator vs Sewing Operator vs Cutting Machine vs Sewing Machine vs Other Machine vs Material vs Other)
3. **Top 10 SKUs by Total Rework** - Horizontal bar (combined Repairs + Recuts + Fails)

#### C4) Tables

1. **Top Problem SKUs (by Repair Qty)**
   - Columns: Parent SKU, Repair Qty, Total Repair Time (min), Recut Qty, Fail Qty, Total Rework
   - Source: Sewing Repairs (rolled up by Parent SKU)
   - Sort by: Repair Qty (descending)

2. **Top Problem SKUs (by Recut Pieces)**
   - Columns: Parent SKU, Recut Pieces, Top Error Types
   - Source: Recut List (rolled up by Parent SKU)
   - Sort by: Recut Pieces (descending)

3. **Rework by Error Source**
   - Columns: Error Source, Incidents, Pct of Total
   - Rows: Cutting Operator Error, Sewing Operator Error, Cutting Machine Error, Sewing Machine Error, Other Machine Error, Material Defect, Other
   - Shows where rework is originating for cross-functional discussions

4. **Recent Incidents**
   - Columns: Date, PR#, SKU, Repair Qty, Recut Qty, Fail Qty, Reason Code, Total Repair Time (min)
   - Source: Sewing Repairs
   - Sort by: Date (descending)
   - Limit: Most recent 20-50 records

---

### D) QC Manager View

**Purpose:** Monitor detection effectiveness - identify what's escaping to QC that should have been caught at Sewing, and improve inline detection.

#### Data Sources

| Source | Filter | What it provides |
|--------|--------|------------------|
| Sewing Repairs | All records; key field is Repair Discovered (SEWING vs QC) | Detection location, what QC is catching |
| Recut List | Not used | No detection location data |

**Target:** ≥70% of issues caught at Sewing = good inline detection

#### D1) Summary Metric Cards

| Metric | Source | Calculation |
|--------|--------|-------------|
| Total Issues | Sewing Repairs | Count of records |
| Caught at Sewing | Sewing Repairs | Count where Repair Discovered = SEWING |
| Caught at QC | Sewing Repairs | Count where Repair Discovered = QC |
| % Caught at Sewing | Sewing Repairs | (Sewing count / Total count) × 100 |
| % Caught at QC | Sewing Repairs | (QC count / Total count) × 100 |
| Repairs from QC-Caught | Sewing Repairs | Sum of Repair Qty where Repair Discovered = QC |
| Fails from QC-Caught | Sewing Repairs | Sum of Fail Qty where Repair Discovered = QC |

#### D2) Key Insights (auto-generated bullets)

Generate 3-5 bullets using these rules (show only bullets that trigger):

- If % at Sewing ≥ 70%: "✅ Strong inline detection - {X}% of issues caught at Sewing before reaching QC."
- If % at QC > 50%: "⚠️ More than half of issues caught at QC ({X}%) - inline detection needs improvement."
- If % at QC between 30-50%: "{X}% of issues caught at QC - room for improvement in inline detection."
- If specific SKU has > 60% QC catch rate: "SKU {X} has {Y}% of issues caught at QC - review sewing checkpoints for this product."
- Trend comparison: "QC catch rate trending {up/down} vs prior period."

#### D3) Charts

1. **Detection Location Over Time** - Stacked bar or line chart (Sewing vs QC by week/month)
2. **Detection Split** - Pie chart (% Caught at Sewing vs % Caught at QC)
3. **Top 10 SKUs Caught at QC** - Horizontal bar chart

#### D4) Tables

1. **SKUs with Poor Inline Detection**
   - Columns: Parent SKU, Total Issues, Caught at QC, Caught at Sewing, % Caught at QC
   - Filter: Only SKUs where % Caught at QC > 50%
   - Sort by: Caught at QC count (descending)
   - Purpose: Identifies SKUs where too many defects escape to QC

2. **Error Types by Detection Location**
   - Columns: Reason Code, Total, Caught at Sewing, Caught at QC, % at QC
   - Sort by: Total (descending)
   - Purpose: Shows which error types are most commonly caught at QC vs Sewing

3. **Detection Summary by SKU**
   - Columns: Parent SKU, Total Issues, Caught at Sewing, Caught at QC, % at Sewing, % at QC
   - Sort by: Total Issues (descending)

4. **QC-Caught Issue Detail**
   - Columns: Date, PR#, SKU, Repair Qty, Fail Qty, Reason Code, Reason for Repair
   - Filter: Repair Discovered = QC
   - Sort by: Date (descending)
   - Limit: Most recent 20-50 records

---

### E) Operations Director View

**Purpose:** 30,000 ft strategic view - high-level metrics, trends, and where to invest (training, tooling, process, R&D).

#### Data Sources

| Source | Filter | What it provides |
|--------|--------|------------------|
| Sewing Repairs | All records | Aggregated metrics, trends |
| Recut List | All records | Recut volume |

#### E1) Summary Metric Cards

| Metric | Source | Calculation | Display |
|--------|--------|-------------|---------|
| Total Rework Events | Both | Sewing Repairs count + Recut List count | With MoM comparison (↑/↓ %) |
| Total Repair Time (hrs) | Sewing Repairs | Sum of Repair Time / 60 | With MoM comparison |
| Total Recut Pieces | Recut List | Sum of QTY | With MoM comparison |
| Total Fails | Sewing Repairs | Sum of Fail Qty | With MoM comparison |
| Top Problem SKU | Both | SKU with highest combined rework | SKU name displayed |
| Primary Error Source | Both | Error Source category with highest % of issues | Error Source name + % |

**Note:** Show hours (not minutes) for strategic view. Include month-over-month comparisons in cards.

#### E2) Key Insights (auto-generated bullets)

Generate 3-5 bullets using these rules (show only bullets that trigger):

- "{X} total rework events consuming {Y} hours of labor this period."
- "Primary error source: {Error Source} ({X}% of issues) - coordinate with relevant Manager."
- "Top investment priority: SKU {X} with {Y} rework events."
- Trend comparison: "Rework {up/down} {X}% vs prior period."
- If one Error Source trending up > 10%: "{Error Source} trending up {X}% - review process/training investment."
- If repair hours high: "{X} hours of repair time = approximately {Y} FTE days consumed by rework."

#### E3) Charts

1. **Monthly Rework Trend** - Line chart showing rework events over time (12-month view if available)
2. **Monthly Repair Time Trend** - Line chart showing hours consumed per month
3. **Error Source Breakdown** - Pie chart (Cutting Operator vs Sewing Operator vs Cutting Machine vs Sewing Machine vs Other Machine vs Material vs Other)

#### E4) Tables

1. **SKU Investment Priority List**
   - Columns: Parent SKU, Repairs, Recuts, Fails, Total Rework, Repair Time (hrs), Primary Error Type
   - Source: Both sheets combined, rolled up by Parent SKU
   - Sort by: Total Rework (descending)
   - Limit: Top 10-15 SKUs
   - Purpose: Which SKUs need investment (training, work instructions, R&D design review)

2. **Top 5 Primary Error Types**
   - Callout showing the top 5 error types (Reason Codes) by incident count
   - Purpose: Quick visibility into most common failure modes

3. **Error Source Summary**
   - Columns: Error Source, Incidents, % of Total
   - Rows: Cutting Operator Error, Sewing Operator Error, Cutting Machine Error, Sewing Machine Error, Other Machine Error, Material Defect, Other
   - Purpose: Where to focus cross-functional investment and resources

---

## Acronyms

| Acronym | Meaning |
|---------|---------|
| SMO | Sewing Machine Operator |
| PA | Production Assistant |
| CMO | Cutting Machine Operator |
| PR# | Production Order Number |
| QC | Quality Control |
| AMS | (TBD - automated machine system?) |

---

## Data Relationships

### Sheet Linkage
- `PR#` (Sewing Repairs) ↔ `Document_No` (Recut List)
- A repair may require a recut, linking records across both sheets

### Parent SKU Rollup
- Same logic as ONE Tracker should apply
- Strip color codes to analyze at product family level
- Color codes: BK, CB, MC, MA, MB, MT, RG, WD, WG, TB, TD, TJ, RD, ML, NG, NP, RT
- CR is a product prefix, NOT a color code

---

## Tech Stack (Planned)

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | Streamlit | Matches ONE Tracker, fast development |
| Data Processing | Pandas | Excel handling, aggregations |
| Visualization | Plotly | Interactive charts |
| Hosting | Streamlit Community Cloud | Free, easy deployment |

---

## Development Phases (Planned)

### Phase 1: Data Foundation
- [x] Build data loader for both sheets
- [x] Normalize names (case consistency, SMO JSmith format)
- [x] Handle data quality issues (boolean columns)
- [x] Implement Parent SKU rollup
- [x] Error Source classification from error codes (7 categories)
- [ ] Link sheets via PR#/Document_No (deferred - not critical for MVP)

### Phase 2: Define Metrics
- [x] Cutting Manager KPIs and tables
- [x] Sewing Manager KPIs and tables
- [x] Production Manager KPIs and tables
- [x] QC Manager KPIs and tables
- [x] Operations Director KPIs and tables

### Phase 3: Build Dashboard
- [x] File upload
- [x] Role selector (5 roles)
- [x] Date/month filters (with presets)
- [x] Summary metric cards
- [x] Tables per role
- [x] Charts per role (pie, line, bar)
- [x] Auto-generated insights

### Phase 4: Polish & Deploy
- [ ] Styling
- [ ] Testing with real data
- [ ] Deploy to Streamlit Cloud
- [ ] Documentation

---

## Next Steps

1. ~~**Define metrics** - Work through KPIs, tables, charts, and insights for each role~~ ✅ COMPLETE
2. **Build data loader** - Parse both sheets, normalize names, handle data quality
3. **Build dashboard** - Streamlit app following ONE Tracker structure
4. **Test & refine** - Validate metrics with real data, adjust thresholds
5. **Deploy** - Push to Streamlit Community Cloud

---

## Notes / Decisions Log

| Date | Decision |
|------|----------|
| 2026-02-04 | Ignore columns 17+ in Sewing Repairs, 20+ in Recut List |
| 2026-02-04 | Normalize case inconsistencies in operator/PA names |
| 2026-02-04 | Cutting Manager focuses on A1x codes (Sewing Repairs) and B/C/F codes (Recut List) |
| 2026-02-04 | Sheets can be linked via PR#/Document_No |
| 2026-02-05 | Cutting Manager spec finalized - metrics, tables, charts, insights defined |
| 2026-02-05 | CM error types: Cutting (A1A/B), Marking (A1B/C), Kitting (A1C), Cut Too Short (F), Other (A1D) |
| 2026-02-05 | Recuts by Parent SKU table should include Materials Affected column |
| 2026-02-05 | CMO table deferred - can add later if tracking method updated |
| 2026-02-05 | Sewing Manager spec finalized - includes SMO performance table |
| 2026-02-05 | SM cares about detection location (Sewing vs QC) for inline accountability |
| 2026-02-05 | SM needs both total repair time AND average time per repair |
| 2026-02-05 | Production Manager spec finalized - holistic view across both sheets |
| 2026-02-05 | PM sees combined total rework AND broken out by area (repairs, recuts, fails) |
| 2026-02-05 | PM uses department breakdown for cross-functional discussions |
| 2026-02-05 | PM does not need Manager-level visibility |
| 2026-02-05 | Targets to be set after evaluating current state |
| 2026-02-05 | QC Manager spec finalized - focused on detection location (Sewing vs QC) |
| 2026-02-05 | QC target: ≥70% caught at Sewing = good inline detection |
| 2026-02-05 | QC cares about which error types are caught at QC vs Sewing |
| 2026-02-05 | QC view is basic for this tracker - Recut List not used (no detection location) |
| 2026-02-05 | Operations Director spec finalized - 30,000 ft strategic view |
| 2026-02-05 | OD uses hours (not minutes) for repair time - more strategic |
| 2026-02-05 | OD metric cards include month-over-month comparisons (↑/↓ %) |
| 2026-02-05 | SKU Investment Priority List framing approved for OD |
| 2026-02-05 | Data loader built and tested - 1,600 Sewing Repairs + 5,038 Recut List records |
| 2026-02-05 | Error Source classification working from error codes |
| 2026-02-05 | Parent SKU rollup working (same logic as ONE Tracker) |
| 2026-02-05 | Baseline metrics: 68.4% caught at Sewing (below 70% target), 551 hrs repair time |
| 2026-02-05 | Dashboard MVP complete with all 5 role views |
| 2026-02-05 | Refactored "Department" to "Error Source" for clearer terminology |
| 2026-02-05 | Split Machine Error into 3 categories: Cutting Machine Error, Sewing Machine Error, Other Machine Error |
| 2026-02-05 | Cutting machines: Hot cut, Laser, Cold cut, Die clicker/Gerber |
| 2026-02-05 | Sewing machines: Sewing machine, AMS |
| 2026-02-05 | SMO name formatting: first initial + last name (JSmith format) |
| 2026-02-05 | Renamed Repair_Time_Min to Total_Repair_Time_Min throughout |
| 2026-02-05 | Added Parent_SKUs_Repaired column to SMO Performance table |
| 2026-02-05 | "Caught at Sewing vs QC" refers to where repairs were DISCOVERED, not fails |
| 2026-02-05 | Added Top 5 Primary Error Types callout for Operations Director view |
| 2026-02-05 | Baseline error distribution: Sewing Operator Error 45.7%, Other 21.7%, Other Machine Error 13.0%, Material Defect 7.8%, Cutting Operator Error 5.9%, Sewing Machine Error 2.8%, Cutting Machine Error 2.7% |

---
