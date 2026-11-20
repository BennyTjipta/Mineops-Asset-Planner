# Publish MineOps Asset Planner to GitHub — applicant instructions

**The link does not exist until you create the repository.** The source is an AI-assisted portfolio learning prototype using synthetic mining-equipment records. You should run, understand and improve it before submitting it as evidence of your skills.

## 1. Learn and test the project

1. Extract the project ZIP to a folder on your computer.
2. Read `README.md` and inspect `src/main.cpp` (maintenance logic), `dashboard.py` (report generation), and `tests/` (automated checks).
3. Build the CLI: `cmake -S . -B build` then `cmake --build build`. You need a C++17 compiler and CMake. On Windows you may need Visual Studio Build Tools; the executable may appear under `build\Debug\assetops.exe`.
4. Run a command, for example `assetops summary --as-of 2026-11-19`. The exact executable path depends on your OS/build.
5. Run `python -m unittest discover -s tests -v` from the project root. The provided version passed eight tests in the preparation environment, but verify it on your own computer.
6. Make an improvement of your own, such as another test, a clearer error message or a dashboard tweak. Re-run tests.

## 2. Publish it

1. Visit https://github.com and sign in.
2. Create a **public** repository named `mineops-asset-planner`. Do not auto-create a second README or license.
3. Use **Add file → Upload files** and select the *contents of the extracted project folder* (or use Git commands). Keep the directory structure: `src/`, `tests/`, `demo/`, `data/`. Do not upload compiled `build/`, `__pycache__/`, or personal data.
4. Commit with a message such as `Publish initial AI-assisted maintenance-planner prototype`.
5. Open the public repository in an incognito browser window and verify that README.md, source code, sample data and tests are accessible.
6. Copy the true URL, for example `https://github.com/YOUR-USERNAME/mineops-asset-planner` (replace YOUR-USERNAME!).
7. Paste the URL into the Valiant Gold field asking for **“a link to anything you've built (GitHub or similar)”**. Do not paste the ZIP download link or the placeholder.

## 3. Describe it accurately

> MineOps Asset Planner — AI-assisted C++17 maintenance-scheduling learning prototype with a CSV-based CLI, synthetic asset dataset, Python-generated offline HTML dashboard, and automated tests.

Be able to explain how deadlines and usage thresholds are calculated, how records are validated, and which parts you have reviewed and modified. Avoid presenting it as a completed university assignment, commercial deployment or independently authored code.
