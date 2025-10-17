import argparse
import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests

BASE_URL = "https://www.alphavantage.co/query"

MACRO_INDICATORS = {
    "treasury-yield": {
        "function": "TREASURY_YIELD",
        "params": {"interval": "monthly", "maturity": "10year"},
    },
    "federal-funds-rate": {
        "function": "FEDERAL_FUNDS_RATE",
        "params": {"interval": "monthly"},
    },
    "cpi": {"function": "CPI", "params": {"interval": "monthly"}},
    "wti": {"function": "WTI", "params": {"interval": "monthly"}},
    "copper": {"function": "COPPER", "params": {"interval": "monthly"}},
}


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYYMMDD")


def fetch_with_retry(url, retries=6, backoff=2.0):
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()

            if isinstance(data, dict):
                if "Note" in data:
                    raise RuntimeError(f"API Note: {data['Note']}")
                if "Error Message" in data:
                    raise RuntimeError(f"API Error: {data['Error Message']}")

            return data
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(backoff**attempt)

    raise RuntimeError(f"Failed after {retries} attempts: {last_error}")


def fetch_indicator(api_key, indicator_name, config):
    params = {"function": config["function"], "apikey": api_key, **config["params"]}

    url = BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    data = fetch_with_retry(url)

    if "data" not in data:
        raise RuntimeError(f"No data found for {indicator_name}")

    return data["data"]


def process_indicator(data, indicator_name):
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.set_index("date").sort_index()
    df.rename(columns={"value": indicator_name.replace("-", "_")}, inplace=True)
    return df


def filter_by_date_range(df, start_date, end_date):
    mask = (df.index >= start_date) & (df.index <= end_date)
    return df[mask]


def merge_indicators(dfs, start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date, freq="MS")
    result = pd.DataFrame(index=date_range)

    for df in dfs:
        result = result.join(df, how="left")

    result = result.sort_index(ascending=False)
    return result


def save_to_csv(df, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    df.to_csv(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start-date", required=True, help="Start date in YYYYMMDD format"
    )
    parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD format")
    parser.add_argument(
        "--api-key", help="Alpha Vantage API key (or use ALPHA_VANTAGE_API env var)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: macro_data_{start_date}_{end_date}.csv)",
    )

    args = parser.parse_args()

    try:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if start_date > end_date:
        print("Error: start-date must be before or equal to end-date", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key or os.getenv("ALPHA_VANTAGE_API")
    if not api_key:
        print(
            "Error: API key required via --api-key or ALPHA_VANTAGE_API environment variable",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = args.output
    if not output_path:
        output_path = f"macro_data_{args.start_date}_{args.end_date}.csv"

    try:
        print("Fetching macroeconomic indicators...")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print()

        dfs = []
        for indicator_name, config in MACRO_INDICATORS.items():
            print(f"Fetching {indicator_name}...")
            raw_data = fetch_indicator(api_key, indicator_name, config)
            df = process_indicator(raw_data, indicator_name)
            df_filtered = filter_by_date_range(df, start_date, end_date)
            dfs.append(df_filtered)
            print(f"  Retrieved {len(df_filtered)} records")

        print("\nMerging indicators...")
        result = merge_indicators(dfs, start_date, end_date)

        output_file = save_to_csv(result, output_path)
        print(f"\nSuccessfully saved: {output_file}")
        print(f"Total rows: {len(result)}")
        print(f"Columns: {', '.join(result.columns)}")

        print("\nData preview:")
        print(result.head())

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
