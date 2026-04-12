# AE Cost Segregation Report Generator

This repository contains the AE Cost Seg report generation tool. It produces cost segregation study reports for commercial and residential rental properties.

## Running a Cost Seg Report

To generate a report, create a property JSON file and run:

```bash
python run_report.py <property_file.json> [--years N] [--output-dir DIR]
```

Or use the Python API directly:

```python
from cost_seg.report import generate_report

property_data = {
    "property_name": "My Building",
    "property_type": "office",        # office, retail, restaurant, warehouse, manufacturing, medical, hotel, apartment, multifamily
    "cost_basis": 2500000,             # Total depreciable cost (exclude land)
    "placed_in_service": "2026-01-15", # YYYY-MM-DD
    "tax_rate": 0.37,                  # Combined federal+state rate
    "land_value": 400000,              # Optional
    "address": "123 Main St",          # Optional
}

filepath, report_text = generate_report(property_data, output_dir="reports", years=10)
```

## Property JSON Format

Required fields:
- `property_name` - Name or identifier for the property
- `property_type` - One of: office, retail, restaurant, warehouse, manufacturing, medical, hotel, apartment, multifamily
- `cost_basis` - Total depreciable cost basis (excluding land)
- `placed_in_service` - Date placed in service (YYYY-MM-DD format)

Optional fields:
- `address` - Property address
- `land_value` - Value of land (excluded from depreciation)
- `tax_rate` - Combined tax rate for savings estimate (default: 0.37)
- `allocations` - Custom dict of asset class percentages (e.g. `{"5-year": 0.10, "7-year": 0.06, ...}`)
- `components` - Detailed list of components with category and cost

## Output

Reports are saved to the `reports/` directory as both:
- `.txt` - Formatted text report
- `.json` - Machine-readable summary data

## Project Structure

- `cost_seg/` - Core library
  - `classifications.py` - IRS asset categories and default allocation percentages
  - `depreciation.py` - MACRS depreciation calculation engine
  - `report.py` - Report generation and formatting
- `examples/` - Sample property files
- `reports/` - Generated report output
- `run_report.py` - CLI entry point
