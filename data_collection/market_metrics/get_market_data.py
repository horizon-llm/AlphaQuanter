import argparse
from datetime import datetime, timedelta

import yfinance as yf


def main():
    parser = argparse.ArgumentParser(description="Fetch stock historical data")
    parser.add_argument(
        "--ticker", type=str, required=True, help="Stock ticker symbol, e.g., MSFT"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date in yyyymmdd format, e.g., 20250101",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date in yyyymmdd format, e.g., 20250630",
    )
    parser.add_argument(
        "--output", type=str, required=False, help="Output CSV filename (optional)"
    )

    args = parser.parse_args()

    try:
        start_date = datetime.strptime(args.start_date, "%Y%m%d").strftime("%Y-%m-%d")
        # Add one day to end_date
        end_date_obj = datetime.strptime(args.end_date, "%Y%m%d") + timedelta(days=1)
        end_date = end_date_obj.strftime("%Y-%m-%d")
    except ValueError:
        print("Error: Invalid date format. Please use yyyymmdd format, e.g., 20250101")
        return

    print(f"Fetching data for {args.ticker} from {start_date} to {args.end_date}...")
    stock = yf.Ticker(args.ticker)
    df = stock.history(start=start_date, end=end_date, auto_adjust=False)

    df = df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]]

    df.index = df.index.strftime("%Y-%m-%d")
    df.index.name = "Date"

    price_columns = ["Open", "High", "Low", "Close", "Adj Close"]
    df[price_columns] = df[price_columns].round(2)

    if args.output:
        output_file = args.output
    else:
        output_file = f"market_{args.ticker}_{args.start_date}_{args.end_date}.csv"

    df.to_csv(output_file)

    print(f"Data saved to {output_file}")
    print(f"\nData preview:")
    print(df.head())
    print(f"\nTotal records: {len(df)}")


if __name__ == "__main__":
    main()
