#!/usr/bin/env python3
"""CLI entry point for generating AE Cost Segregation reports.

Usage:
    python run_report.py examples/sample_property.json
    python run_report.py property.json --years 15 --output-dir my_reports
"""

import argparse
import sys

from cost_seg.report import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="AE Cost Segregation Report Generator"
    )
    parser.add_argument(
        "property_file",
        help="Path to property JSON file",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years for depreciation schedule (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory for reports (default: reports)",
    )

    args = parser.parse_args()

    try:
        filepath, report_text = generate_report(
            args.property_file,
            output_dir=args.output_dir,
            years=args.years,
        )
        print(report_text)
        print(f"\nReport saved to: {filepath}")
    except FileNotFoundError:
        print(f"Error: Property file not found: {args.property_file}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field in property data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
