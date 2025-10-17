import argparse
import json
import os
from collections import defaultdict
from datetime import datetime

import requests


def get_url(ticker, start_date, end_date, api_key):
    """Construct API URL for fetching news sentiment data."""
    return (
        f"https://www.alphavantage.co/query?"
        f"function=NEWS_SENTIMENT&tickers={ticker}&apikey={api_key}"
        f"&time_from={start_date}&time_to={end_date}&limit=1000"
    )


def fetch_news_data(url):
    """Fetch news data from API."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed with status code: {response.status_code}")
        return None


def deduplicate_by_url(data_list):
    """Remove duplicate entries by URL."""
    seen_urls = set()
    result = []
    for item in data_list:
        url = item.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            result.append(item)

    return result


def format_date(date_str, time_suffix):
    """Format date string by removing T and time parts, then adding specified suffix."""
    # Remove 'T' and everything after it if present
    base_date = date_str.split("T")[0]
    return f"{base_date}{time_suffix}"


def get_ticker_relevance_score(news_item, ticker):
    """Get relevance score for a specific ticker from news item."""
    ticker_sentiment = news_item.get("ticker_sentiment", [])
    for sentiment in ticker_sentiment:
        if sentiment.get("ticker") == ticker:
            return float(sentiment.get("relevance_score", 0))
    return 0.0


def organize_news_by_date(news_list, ticker):
    """
    Organize news by date and sort by ticker relevance score.
    Returns a dict where keys are dates (YYYY-MM-DD) and values are lists of news.
    """
    news_by_date = defaultdict(list)

    for news_item in news_list:
        time_published = news_item.get("time_published", "")
        if len(time_published) >= 8:
            date_str = time_published[:8]
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            news_by_date[formatted_date].append(news_item)

    sorted_news_by_date = {}
    for date, news_items in sorted(news_by_date.items()):
        sorted_news = sorted(
            news_items,
            key=lambda x: get_ticker_relevance_score(x, ticker),
            reverse=True,
        )
        sorted_news_by_date[date] = sorted_news

    return sorted_news_by_date


def main():
    """Main function to fetch and save news data."""
    parser = argparse.ArgumentParser(
        description="Fetch news sentiment data from Alpha Vantage API"
    )
    parser.add_argument(
        "--ticker", type=str, required=True, help="Stock ticker symbol (e.g., MSFT)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date in YYYYMMDD format (e.g., 20250101)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date in YYYYMMDD format (e.g., 20250110)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Alpha Vantage API key (overrides environment variable)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: news_{ticker}_{startdate}_{enddate}.json)",
    )

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ALPHA_VANTAGE_API")
    if not api_key:
        print(
            "Error: API key not provided. Set ALPHA_VANTAGE_API environment variable or use --api-key argument"
        )
        return

    start_date = format_date(args.start_date, "T0000")
    end_date = format_date(args.end_date, "T2359")
    ticker = args.ticker

    base_start_date = args.start_date.split("T")[0]
    base_end_date = args.end_date.split("T")[0]

    if args.output:
        output_path = args.output
    else:
        output_path = f"news_{ticker}_{base_start_date}_{base_end_date}.json"

    url = get_url(ticker, start_date, end_date, api_key)
    print(f"Initial URL: {url}")

    data = fetch_news_data(url)
    if not data or "feed" not in data:
        print("Failed to fetch initial data")
        return

    all_data = []
    all_data.extend(data["feed"])
    print(f"Initial size: {len(all_data)}")

    while True:
        try:
            new_end_date = data["feed"][-1]["time_published"][:-2]

            url = get_url(ticker, start_date, new_end_date, api_key)
            data = fetch_news_data(url)

            if not data or "feed" not in data:
                break

            print(f"First article: {data['feed'][0]['time_published']}")
            print(f"Last article: {data['feed'][-1]['time_published']}")

            if data["feed"][-1]["time_published"] == all_data[-1]["time_published"]:
                print("Reached duplicate data, stopping pagination")
                break

            all_data.extend(data["feed"])
            print(f"Total size: {len(all_data)}")

        except Exception as e:
            print(f"Error occurred: {e}")
            break

    cleaned_data = deduplicate_by_url(all_data)
    print(f"After deduplication: {len(cleaned_data)} unique articles")

    organized_data = organize_news_by_date(cleaned_data, ticker)

    print(f"\nNews organized by date:")
    for date, news_items in sorted(organized_data.items()):
        print(f"  {date}: {len(news_items)} articles")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(organized_data, f, indent=4, ensure_ascii=False)

    print(f"\nData saved to {output_path}")
    print(f"Total dates: {len(organized_data)}")
    print(f"Total articles: {sum(len(items) for items in organized_data.values())}")


if __name__ == "__main__":
    main()
