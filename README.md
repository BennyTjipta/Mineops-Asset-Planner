# MineOps Asset Planner

**C++17 maintenance-scheduling CLI + Python-generated interactive HTML dashboard.**
This is a small software engineering portfolio project set in a fictional equipment-maintenance environment. It demonstrates practical programming, structured data handling, basic data validation, test automation and presenting results clearly. **The dataset is entirely synthetic**. it does not come from a real mine or employer. The project is a learning prototype, **not** a safety-critical maintenance system.

## Explore the project immediately
Open [`demo/dashboard.html`](demo/dashboard.html) in any browser. The dashboard works offline, includes a searchable equipment table and a status filter, and requires no account or external services.

The C++ program processes a sample 12-asset CSV register, calculates due dates, flags overdue/due-soon items, and exports a report. The Python script turns that report into a single offline HTML file.

### Features
- **C++ command-line interface:** list assets; view maintenance summary; list due-soon items; add equipment; record a completed service; export CSV.
- **Data validation:** checks ISO dates, leap years, positive service intervals, nonnegative usage and duplicate IDs.
- **Maintenance assessment:** calculates days and usage-hours remaining, using configurable thresholds in `src/main.cpp`.
- **Python report generator:** creates a responsive, filterable, self-contained HTML dashboard.
- **Automated tests:** covers CLI commands, file updates, duplicate IDs, invalid dates, CSV escaping and dashboard HTML escaping.
- **No third-party dependencies** beyond a C++17 compiler, CMake and Python 3.9+.

## Quick start

### 1. Compile
```bash
cmake -S . -B build
cmake --build build
```

**Windows:** Install [CMake](https://cmake.org/download/) and a C++ compiler such as the Microsoft Visual C++ Build Tools. Open the project's folder in PowerShell. Depending on your generator, the executable may be `build\\Debug\\assetops.exe` rather than `build\\assetops.exe`. The examples below use `./build/assetops` (Linux/macOS); replace it with the correct `.exe` path on Windows.

### 2. Run the CLI
From the repository root:

```bash
./build/assetops summary --as-of 2026-11-19
./build/assetops list --as-of 2026-11-19
./build/assetops due --within 14 --as-of 2026-11-19
```

For repeatable demonstrations, the program defaults to 2026-11-19 if `--as-of` is omitted. In actual use, pass the date you want to assess. A day is overdue when its deadline has **passed** (`days remaining < 0`); it is due soon at **14 days or less**. Asset usage follows the same convention: overdue below zero, due soon at **50 operating hours or less**.

### 3. Export a report and build the dashboard
Create a `reports` directory, then run:

```bash
./build/assetops export --output reports/maintenance_report.csv --as-of 2026-11-19
python dashboard.py --input reports/maintenance_report.csv --output reports/dashboard.html --as-of 2026-11-19
```

Open `reports/dashboard.html` in a browser. The generator produces plain HTML with embedded CSS and JavaScript, so it also works without internet access.

> The `reports/` directory is excluded from version control because generated reports are replaceable. A ready-made report and dashboard are included under `demo/`.

### 4. Create/update records (on a copy of the CSV)
```bash
# Make a working copy of the provided sample data before editing it.
cp data/assets.csv my_assets.csv

./build/assetops add --file my_assets.csv --id A013 --name "Pump, West" --category Water --last-serviced 2026-11-01 --interval-days 60 --hours-used 25 --hour-limit 200
./build/assetops service A013 --date 2026-11-19 --file my_assets.csv
```

Windows PowerShell copy equivalent: `Copy-Item data/assets.csv my_assets.csv`.

### 5. Run the test suite
```bash
python -m unittest discover -s tests -v
```

Run this after compiling the C++ application. These tests use only Python's standard library.

## Project structure
```text
mineops_asset_planner/
├── CMakeLists.txt            # C++17 build configuration
├── src/main.cpp             # Asset modelling, CLI and maintenance logic
├── dashboard.py             # CSV → self-contained HTML report
├── data/assets.csv          # Synthetic sample equipment data
├── demo/dashboard.html      # Ready-to-open dashboard
├── demo/maintenance_report.csv
├── tests/test_cli.py        # CLI integration tests
├── tests/test_dashboard.py  # Dashboard output tests
├── LICENSE
└── README.md
```

## Assumptions and limits
1. Service is due when either the calendar interval or the hours-since-service limit reaches its threshold. At exactly the due date/hour limit, status is `DUE_SOON`, not `OVERDUE`; this is a simple demonstration convention.
2. Usage hours are manually entered in the sample CSV. There is no live IoT equipment integration.
3. The `service` command sets hours-since-service to zero and updates the last-serviced date, but does not capture maintenance technician signatures or audit history.
4. Dates are handled as calendar dates, without time zones or shift times.
5. The CSV file is a learning-oriented persistence layer. A real deployment should use transactions, concurrency controls, access control, logging and proper asset-maintenance policies.

## What I learned / discussion prompts
If showing this project to an employer, be able to explain:

- Why date checks and duplicate-ID validation matter for data integrity.
- How the two independent maintenance triggers (time and usage) affect priority.
- How the CLI, CSV and Python report components are separated.
- How the integration tests prevent regressions.
- What would change for production: a database, structured audit logs, user authentication and a proper scheduler.
