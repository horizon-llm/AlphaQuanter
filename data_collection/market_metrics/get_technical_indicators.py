#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import time
from datetime import date, datetime

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://www.alphavantage.co/query"


def parse_date(date_str):
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYYMMDD")


def build_url(params):
    return f"{BASE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())


def check_response(data):
    if "Error Message" in data:
        raise RuntimeError(f"API Error: {data['Error Message']}")
    if "Note" in data:
        raise RuntimeError(f"API Note: {data['Note']}")


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
            check_response(data)
            return data
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(backoff**attempt)

    raise RuntimeError(f"Failed after {retries} attempts: {last_error}")


def fetch_indicator(api_key, ticker, function, params):
    all_params = {"function": function, "symbol": ticker, "apikey": api_key, **params}
    url = build_url(all_params)
    return fetch_with_retry(url)


def fetch_sma20(api_key, ticker):
    data = fetch_indicator(
        api_key,
        ticker,
        "SMA",
        {
            "interval": "daily",
            "time_period": "20",
            "series_type": "close",
            "outputsize": "full",
        },
    )
    return data.get("Technical Analysis: SMA", {})


def fetch_ema10(api_key, ticker):
    data = fetch_indicator(
        api_key,
        ticker,
        "EMA",
        {
            "interval": "daily",
            "time_period": "10",
            "series_type": "close",
            "outputsize": "full",
        },
    )
    return data.get("Technical Analysis: EMA", {})


def fetch_rsi14(api_key, ticker):
    data = fetch_indicator(
        api_key,
        ticker,
        "RSI",
        {
            "interval": "daily",
            "time_period": "14",
            "series_type": "close",
            "outputsize": "full",
        },
    )
    return data.get("Technical Analysis: RSI", {})


def fetch_stoch(api_key, ticker):
    data = fetch_indicator(
        api_key, ticker, "STOCH", {"interval": "daily", "fastkperiod": "14"}
    )
    return data.get("Technical Analysis: STOCH", {})


def fetch_cci20(api_key, ticker):
    data = fetch_indicator(
        api_key,
        ticker,
        "CCI",
        {"interval": "daily", "time_period": "20", "outputsize": "full"},
    )
    return data.get("Technical Analysis: CCI", {})


def fetch_bbands20(api_key, ticker):
    data = fetch_indicator(
        api_key,
        ticker,
        "BBANDS",
        {
            "interval": "daily",
            "time_period": "20",
            "series_type": "close",
            "nbdevup": "2",
            "nbdevdn": "2",
            "outputsize": "full",
        },
    )
    return data.get("Technical Analysis: BBANDS", {})


def fetch_atr14(api_key, ticker):
    data = fetch_indicator(
        api_key,
        ticker,
        "ATR",
        {"interval": "daily", "time_period": "14", "outputsize": "full"},
    )
    return data.get("Technical Analysis: ATR", {})


def fetch_obv(api_key, ticker):
    data = fetch_indicator(
        api_key, ticker, "OBV", {"interval": "daily", "outputsize": "full"}
    )
    return data.get("Technical Analysis: OBV", {})


def fetch_daily_prices(api_key, ticker):
    data = fetch_indicator(api_key, ticker, "TIME_SERIES_DAILY", {"outputsize": "full"})

    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        raise RuntimeError("Daily time series data not found")

    df = pd.DataFrame.from_dict(time_series, orient="index")
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)

    column_mapping = {
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume",
    }

    df.columns = [c.strip() for c in df.columns]

    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)

    if not set(["open", "high", "low", "close", "volume"]).issubset(df.columns):
        col_map = {}
        for col in df.columns:
            if "open" in col.lower():
                col_map[col] = "open"
            elif "high" in col.lower():
                col_map[col] = "high"
            elif "low" in col.lower():
                col_map[col] = "low"
            elif "close" in col.lower():
                col_map[col] = "close"
            elif "volume" in col.lower():
                col_map[col] = "volume"
        df.rename(columns=col_map, inplace=True)

    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df


def compute_vwma20(df):
    return (df["close"] * df["volume"]).rolling(20).sum() / df["volume"].rolling(
        20
    ).sum()


def compute_cmf21(df):
    hl_range = df["high"] - df["low"]
    mfm = np.where(
        hl_range == 0,
        0.0,
        ((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl_range,
    )
    mfv = mfm * df["volume"]
    return (
        pd.Series(mfv, index=df.index).rolling(21).sum()
        / df["volume"].rolling(21).sum()
    )


def compute_macd(df):
    ema_fast = df["close"].ewm(span=12, adjust=False).mean()
    ema_slow = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist


def compute_manual_indicators(df):
    result = pd.DataFrame(index=df.index)
    result["VWMA20"] = compute_vwma20(df)
    result["CMF"] = compute_cmf21(df)
    result["MACD"], result["MACDS"], result["MACDH"] = compute_macd(df)
    return result


def get_common_dates(data_dicts):
    date_sets = [set(d.keys()) for d in data_dicts if d]
    if not date_sets:
        return set()

    common = date_sets[0]
    for date_set in date_sets[1:]:
        common &= date_set
    return common


def filter_date_range(dates, start_date, end_date):
    filtered = []
    for date_str in dates:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if start_date <= d <= end_date:
                filtered.append(date_str)
        except ValueError:
            continue
    return sorted(filtered)


def format_value(value):
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.6f}"


def build_row(date_str, indicators, manual_dict):
    row = [
        date_str,
        indicators["sma"][date_str].get("SMA"),
        indicators["ema"][date_str].get("EMA"),
        indicators["rsi"][date_str].get("RSI"),
        indicators["stoch"][date_str].get("SlowK"),
        indicators["stoch"][date_str].get("SlowD"),
        indicators["cci"][date_str].get("CCI"),
        indicators["bbands"][date_str].get("Real Middle Band"),
        indicators["bbands"][date_str].get("Real Upper Band"),
        indicators["bbands"][date_str].get("Real Lower Band"),
        indicators["atr"][date_str].get("ATR"),
        indicators["obv"][date_str].get("OBV"),
        manual_dict[date_str].get("VWMA20"),
        manual_dict[date_str].get("CMF"),
        manual_dict[date_str].get("MACD"),
        manual_dict[date_str].get("MACDS"),
        manual_dict[date_str].get("MACDH"),
    ]

    return [row[0]] + [format_value(v) for v in row[1:]]


def write_csv(rows, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    headers = [
        "Date",
        "SMA20",
        "EMA10",
        "RSI",
        "STOCH_SLOWK",
        "STOCH_SLOWD",
        "CCI",
        "BBANDS_MID",
        "BBANDS_UPPER",
        "BBANDS_LOWER",
        "ATR",
        "OBV",
        "VWMA20",
        "CMF",
        "MACD",
        "MACDS",
        "MACDH",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return output_path


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--ticker", required=True, help="Stock ticker symbol")
    parser.add_argument(
        "--start-date", required=True, help="Start date (YYYYMMDD or YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", required=True, help="End date (YYYYMMDD or YYYY-MM-DD)"
    )
    parser.add_argument(
        "--api-key", help="Alpha Vantage API key (or use ALPHA_VANTAGE_API env var)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: technical_indicators_{ticker}_{start_date}_{end_date}.csv)",
    )

    args = parser.parse_args()

    ticker = args.ticker.strip().upper()

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
        output_path = f"technical_indicators_{ticker}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"

    try:
        print(f"Fetching technical indicators for {ticker}...")
        print(f"Date range: {start_date} to {end_date}")

        print("Fetching API indicators...")
        indicators = {
            "sma": fetch_sma20(api_key, ticker),
            "ema": fetch_ema10(api_key, ticker),
            "rsi": fetch_rsi14(api_key, ticker),
            "stoch": fetch_stoch(api_key, ticker),
            "cci": fetch_cci20(api_key, ticker),
            "bbands": fetch_bbands20(api_key, ticker),
            "atr": fetch_atr14(api_key, ticker),
            "obv": fetch_obv(api_key, ticker),
        }

        print("Computing manual indicators...")
        df = fetch_daily_prices(api_key, ticker)
        manual_df = compute_manual_indicators(df)

        manual_dict = {
            ts.strftime("%Y-%m-%d"): {
                "VWMA20": row["VWMA20"],
                "CMF": row["CMF"],
                "MACD": row["MACD"],
                "MACDS": row["MACDS"],
                "MACDH": row["MACDH"],
            }
            for ts, row in manual_df.iterrows()
        }

        print("Finding common dates...")
        all_data = list(indicators.values()) + [manual_dict]
        common_dates = get_common_dates(all_data)
        filtered_dates = filter_date_range(common_dates, start_date, end_date)

        if not filtered_dates:
            print("Warning: No data found in the specified date range", file=sys.stderr)
            sys.exit(0)

        print(f"Building CSV with {len(filtered_dates)} rows...")
        rows = []
        for date_str in filtered_dates:
            try:
                row = build_row(date_str, indicators, manual_dict)
                rows.append(row)
            except Exception as e:
                print(
                    f"Warning: Skipping date {date_str} due to error: {e}",
                    file=sys.stderr,
                )
                continue

        output_file = write_csv(rows, output_path)
        print(f"Successfully saved: {output_file}")
        print(f"Total records: {len(rows)}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
