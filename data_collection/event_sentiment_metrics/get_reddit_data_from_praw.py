import argparse
import json
import os
import time
from collections import defaultdict
from datetime import datetime

import praw
import requests
from tqdm import tqdm


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch Reddit posts for a specific stock ticker within a date range"
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
        "--client-id",
        type=str,
        default=None,
        help="Reddit API client ID (or set REDDIT_CLIENT_ID env var). See: https://github.com/reddit-archive/reddit/wiki/OAuth2",
    )
    parser.add_argument(
        "--client-secret",
        type=str,
        default=None,
        help="Reddit API client secret (or set REDDIT_CLIENT_SECRET env var). See: https://github.com/reddit-archive/reddit/wiki/OAuth2",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: reddit_{ticker}_{startdate}_{enddate}.json)",
    )
    parser.add_argument(
        "--subreddits",
        type=str,
        nargs="+",
        default=[
            "StockMarket",
            "wallstreetbets",
            "unusual_whales",
            "technology",
            "stocks",
            "WallStreetbetsELITE",
            "options",
            "TheRaceTo10Million",
            "ValueInvesting",
            "Daytrading",
            "investing",
        ],
        help="List of subreddits to search",
    )

    return parser.parse_args()


def parse_date(date_str):
    """Parse date string in YYYYMMDD format to datetime object."""
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYYMMDD format.")


def initialize_reddit_client(client_id, client_secret):
    """Initialize Reddit API client using PRAW."""
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="Reddit Stock Data Crawler",
    )


def fetch_post_json(permalink):
    """Fetch post data in JSON format from Reddit."""
    json_url = f"https://www.reddit.com{permalink.rstrip('/')}.json"

    try:
        response = requests.get(json_url, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code == 200:
            data = response.json()
            return data[0]["data"]["children"][0]["data"]
        else:
            print(f"Failed to fetch {json_url}: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error fetching {json_url}: {e}")
        return None


def search_subreddit_for_ticker(
    reddit, subreddit_name, ticker, start_date, end_date, seen_ids
):
    """Search a subreddit for posts mentioning the ticker within date range."""
    subreddit = reddit.subreddit(subreddit_name)
    print(f"Start searching: {subreddit_name}")

    last_submission = None
    posts_collected = []

    while True:
        print(">> Start searching ...")

        search_results = subreddit.search(
            ticker,
            time_filter="year",
            limit=500,
            params={"after": last_submission.fullname if last_submission else None},
        )

        new_results_found = False
        posts_fetched_count = 0

        for submission in search_results:
            if submission.id in seen_ids:
                continue

            seen_ids.add(submission.id)
            new_results_found = True

            post_time = datetime.fromtimestamp(submission.created_utc)

            if start_date <= post_time <= end_date:
                if not (
                    submission.url.endswith(".jpg")
                    or submission.url.endswith(".gif")
                    or submission.url.endswith(".png")
                ):

                    post_data = fetch_post_json(submission.permalink)

                    if post_data:
                        posts_collected.append(post_data)
                        posts_fetched_count += 1

                    time.sleep(0.5)

            last_submission = submission

        print(f">> Fetched {posts_fetched_count} posts from this batch")

        if not new_results_found:
            print("No new results, moving to next subreddit")
            break

        time.sleep(2)

    print(f"END: {subreddit_name}")
    return posts_collected


def organize_posts_by_date(posts):
    """Organize posts by date and sort by upvotes."""
    posts_by_date = defaultdict(list)

    for post in posts:
        created_utc = post.get("created_utc")
        if created_utc:
            post_date = datetime.fromtimestamp(created_utc).strftime("%Y-%m-%d")
            posts_by_date[post_date].append(post)

    organized_posts = {}
    for date, date_posts in sorted(posts_by_date.items()):
        sorted_posts = sorted(date_posts, key=lambda x: x.get("ups", 0), reverse=True)
        organized_posts[date] = sorted_posts

    return organized_posts


def main():
    args = parse_arguments()

    client_id = args.client_id or os.environ.get("REDDIT_CLIENT_ID")
    client_secret = args.client_secret or os.environ.get("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: Reddit API credentials not provided.")
        print("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables")
        print("or use --client-id and --client-secret arguments")
        print("See: https://github.com/reddit-archive/reddit/wiki/OAuth2")
        return

    try:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date).replace(hour=23, minute=59, second=59)
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        return

    if args.output:
        output_path = args.output
    else:
        output_path = f"reddit_{args.ticker}_{args.start_date}_{args.end_date}.json"

    reddit = initialize_reddit_client(client_id, client_secret)

    seen_ids = set()
    all_posts = []

    for subreddit_name in tqdm(args.subreddits):
        posts = search_subreddit_for_ticker(
            reddit, subreddit_name, args.ticker, start_date, end_date, seen_ids
        )
        all_posts.extend(posts)

    print(f"\nTotal posts fetched: {len(all_posts)}")

    organized_posts = organize_posts_by_date(all_posts)

    print(f"\nPosts organized by date:")
    for date, posts in sorted(organized_posts.items()):
        print(f"  {date}: {len(posts)} posts")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(organized_posts, f, indent=4, ensure_ascii=False)

    print(f"\nData saved to {output_path}")
    print(f"Total dates: {len(organized_posts)}")
    print(f"Total posts: {sum(len(posts) for posts in organized_posts.values())}")


if __name__ == "__main__":
    main()
