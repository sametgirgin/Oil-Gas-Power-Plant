# Oil & Gas Power Plants Explorer

Streamlit app to explore the Global Oil and Gas Plant Tracker data. It plots plants on a capacity-scaled bubble map and provides sidebar filters (Country, Status, Fuel, Hydrogen capable?, Region, Technology, CHP), plus a glossary tab that shows local markdown and images.

## Quick start
- Install deps: `pip install -r requirements.txt`
- Run: `streamlit run app.py`
- Data: the app reads `Global-Oil-and-Gas-Plant-Tracker-GOGPT-February-2024-v4.xlsx` (Gas & Oil Units sheet). Edits to the file are picked up automatically.

## Files
- `app.py` — Streamlit app.
- `requirements.txt` — Python dependencies.
- `glossary.md` — Markdown rendered in the Glossary tab (images like `tech.png` and `chp.png` are shown if present).
- `logo.png` — Shown next to the app title.
