import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

import pandas as pd
import requests

BASE_URL = "https://www.alphavantage.co/query"

STATEMENT_TYPES = {
    "balance-sheet": "BALANCE_SHEET",
    "income-statement": "INCOME_STATEMENT",
    "cash-flow": "CASH_FLOW",
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


def save_output(data, output_path, is_dataframe=False):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if is_dataframe:
        data.to_csv(output_path, index=True)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    return output_path


# ========== DIVIDENDS ==========
def fetch_dividends(api_key, ticker, start_date, end_date):
    url = f"{BASE_URL}?function=DIVIDENDS&symbol={ticker}&apikey={api_key}"
    data = fetch_with_retry(url)

    if not data or "data" not in data:
        raise RuntimeError("Invalid or empty dividend data")

    result = {}
    for item in data["data"]:
        key = item.get("declaration_date", "")
        try:
            key_date = datetime.strptime(key, "%Y-%m-%d")
        except ValueError:
            continue

        if start_date <= key_date <= end_date:
            result[key] = float(item["amount"])

    return result


# ========== INSIDER TRANSACTIONS ==========
def fetch_insider_transactions(api_key, ticker, start_date, end_date):
    url = f"{BASE_URL}?function=INSIDER_TRANSACTIONS&symbol={ticker}&apikey={api_key}"
    data = fetch_with_retry(url)

    if "data" not in data:
        raise RuntimeError("No insider transaction data found")

    grouped = defaultdict(list)
    for item in data["data"]:
        date_str = item.get("transaction_date", "")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if start_date <= date_obj <= end_date:
            grouped[date_str].append(item)

    return dict(grouped)


# ========== EARNINGS ESTIMATES ==========
def fetch_earnings_estimates(api_key, ticker, start_date, end_date):
    url = f"{BASE_URL}?function=EARNINGS_ESTIMATES&symbol={ticker}&apikey={api_key}"
    data = fetch_with_retry(url)

    if "estimates" not in data:
        raise RuntimeError("No estimates found in response")

    estimates = data["estimates"]
    if not estimates:
        raise RuntimeError("Estimates list is empty")

    # Convert list of dicts to DataFrame
    df = pd.DataFrame(estimates)

    # Parse date column
    df["date"] = pd.to_datetime(df["date"])

    # Filter by date range
    mask = (df["date"] >= pd.Timestamp(start_date)) & (
        df["date"] <= pd.Timestamp(end_date)
    )
    df_filtered = df[mask]

    if df_filtered.empty:
        return pd.DataFrame()

    # Sort by date
    df_filtered = df_filtered.sort_values("date")

    # Set date as index and transpose
    df_filtered = df_filtered.set_index("date")
    df_T = df_filtered.T

    # Format date columns as strings
    df_T.columns = df_T.columns.strftime("%Y-%m-%d")

    return df_T


# ========== FINANCIAL STATEMENTS ==========
def fetch_financial_statement(
    api_key, ticker, function_name, report_type, start_date, end_date
):
    url = f"{BASE_URL}?function={function_name}&symbol={ticker}&apikey={api_key}"
    data = fetch_with_retry(url)

    if not isinstance(data, dict):
        raise RuntimeError("Invalid response format")

    if report_type == "annual":
        key = "annualReports"
    elif report_type == "quarterly":
        key = "quarterlyReports"
    else:
        raise ValueError(f"Invalid report type: {report_type}")

    if key not in data:
        raise RuntimeError(f"No {key} found in response")

    reports = data[key]
    filtered = []

    for report in reports:
        fiscal_date_str = report.get("fiscalDateEnding", "")
        if not fiscal_date_str:
            continue

        try:
            fiscal_date = datetime.strptime(fiscal_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if start_date <= fiscal_date <= end_date:
            filtered.append(report)

    df = pd.DataFrame(filtered)
    if not df.empty and "fiscalDateEnding" in df.columns:
        df = df.sort_values("fiscalDateEnding")

    df_filtered = df.set_index("fiscalDateEnding")
    df_T = df_filtered.T

    return df_T


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "data_type",
        choices=[
            "dividends",
            "insider-transactions",
            "earnings-estimates",
            "balance-sheet",
            "income-statement",
            "cash-flow",
        ],
        help="Type of fundamental data to fetch",
    )
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol")
    parser.add_argument(
        "--start-date", required=True, help="Start date in YYYYMMDD format"
    )
    parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD format")
    parser.add_argument(
        "--api-key", help="Alpha Vantage API key (or use ALPHA_VANTAGE_API env var)"
    )
    parser.add_argument(
        "--output", help="Output file path (auto-generated if not specified)"
    )

    report_group = parser.add_mutually_exclusive_group()
    report_group.add_argument(
        "--annual",
        action="store_true",
        help="Fetch annual reports (financial statements only)",
    )
    report_group.add_argument(
        "--quarterly",
        action="store_true",
        help="Fetch quarterly reports (financial statements only)",
    )

    args = parser.parse_args()

    ticker = args.ticker.strip().upper()
    data_type = args.data_type

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

    # Check for --annual or --quarterly requirement for financial statements
    if data_type in STATEMENT_TYPES:
        if not args.annual and not args.quarterly:
            print(
                f"Error: {data_type} requires either --annual or --quarterly flag",
                file=sys.stderr,
            )
            sys.exit(1)
        report_type = "annual" if args.annual else "quarterly"
    else:
        if args.annual or args.quarterly:
            print(
                f"Warning: --annual/--quarterly flags are ignored for {data_type}",
                file=sys.stderr,
            )
        report_type = None

    # Generate default output path
    output_path = args.output
    if not output_path:
        data_name = data_type.replace("-", "_")
        if data_type in STATEMENT_TYPES:
            output_path = f"{data_name}_{ticker}_{args.start_date}_{args.end_date}.csv"
        elif data_type == "earnings-estimates":
            output_path = f"{data_name}_{ticker}_{args.start_date}_{args.end_date}.csv"
        else:
            output_path = f"{data_name}_{ticker}_{args.start_date}_{args.end_date}.json"

    try:
        print(f"Fetching {data_type.replace('-', ' ')} for {ticker}...")
        print(f"Date range: {start_date.date()} to {end_date.date()}")

        # Fetch data based on type
        if data_type == "dividends":
            result = fetch_dividends(api_key, ticker, start_date, end_date)
            is_df = False
            print(f"Total records: {len(result)}")

        elif data_type == "insider-transactions":
            result = fetch_insider_transactions(api_key, ticker, start_date, end_date)
            is_df = False
            total_transactions = sum(len(items) for items in result.values())
            print(f"Total dates: {len(result)}")
            print(f"Total transactions: {total_transactions}")

        elif data_type == "earnings-estimates":
            result = fetch_earnings_estimates(api_key, ticker, start_date, end_date)
            is_df = True
            if result.empty:
                print(
                    "Warning: No data found in the specified date range",
                    file=sys.stderr,
                )
            else:
                print(f"Columns (dates): {len(result.columns)}")
                print(f"Rows (metrics): {len(result)}")

        elif data_type in STATEMENT_TYPES:
            function_name = STATEMENT_TYPES[data_type]
            result = fetch_financial_statement(
                api_key, ticker, function_name, report_type, start_date, end_date
            )
            is_df = True
            print(f"Total reports: {len(result)}")

        else:
            raise ValueError(f"Unknown data type: {data_type}")

        # Save output
        output_file = save_output(result, output_path, is_df)
        print(f"Successfully saved: {output_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
