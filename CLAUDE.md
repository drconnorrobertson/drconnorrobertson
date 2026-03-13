# CLAUDE.md

## Repository Overview

This repo contains the **STR Deal Finder** — a Python application that continuously monitors Zillow for short-term rental investment properties. It also serves as the GitHub profile repo for drconnorrobertson (README.md appears on the profile page).

## Structure

```
.
├── README.md                     # GitHub profile page
├── CLAUDE.md                     # Instructions for AI assistants
├── requirements.txt              # Python dependencies
├── config/
│   └── settings.yaml             # Markets, API keys, financial assumptions
├── src/
│   ├── main.py                   # Entry point — scan-analyze-notify loop
│   ├── models.py                 # Data classes (Property, Deal, etc.)
│   ├── zillow_client.py          # Zillow RapidAPI integration
│   ├── revenue_estimator.py      # STR revenue estimation (Mashvisor + heuristics)
│   ├── financial_analyzer.py     # Full underwriting engine
│   ├── permit_checker.py         # STR permit feasibility lookup
│   └── notifier.py               # Terminal output + CSV export
├── data/
│   └── str_regulations.json      # STR permit rules by city/county
├── tests/
│   ├── test_financial_analyzer.py
│   └── test_revenue_estimator.py
└── output/                       # Generated CSVs (gitignored)
```

## Commands

- **Run the app**: `python -m src.main --config config/settings.yaml`
- **Dry run (once, no loop)**: `python -m src.main --dry-run`
- **Run tests**: `python -m pytest tests/ -v`
- **Install deps**: `pip install -r requirements.txt`

## Key Conventions

- **Config-driven**: All financial assumptions, markets, and thresholds are in `config/settings.yaml`
- **API keys go in settings.yaml** (not committed with real keys — use `YOUR_RAPIDAPI_KEY` placeholder)
- Financial calculations are the most critical module — always add/update tests when changing `financial_analyzer.py`
- Revenue estimation uses a tiered fallback: Mashvisor API -> market heuristic table
- STR regulations are stored in `data/str_regulations.json` — update when adding new markets

## Financial Model

- 10% down, 90% loan at configurable interest rate
- Cash-on-cash = (Annual Revenue - All Expenses) / Total Cash Invested
- Total Cash Invested = Down Payment + Closing Costs (3%) + Improvements + Furnishing
- All 14 expense categories tracked (mortgage, tax, insurance, HOA, property mgmt, utilities, maintenance, cleaning, platform fees, supplies, permit, accounting, furniture reserve, landscaping)
