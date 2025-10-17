# Event Sentiment Data Collection

Python scripts for fetching news and Reddit data related to stock sentiment analysis.

## Scripts

### 1. News Data
**get_news_data.py** - Fetches news sentiment data from Alpha Vantage API.

### 2. Reddit Data (Two Methods)

**get_reddit_data_from_praw.py** - Fetches recent Reddit posts via live API (PRAW).

**get_reddit_data_from_dump.py** - Processes historical Reddit dumps with AI semantic filtering.

## Requirements

```bash
# News data
pip install requests

# Reddit (PRAW method)
pip install praw requests tqdm

# Reddit (Dump method)
pip install sentence-transformers zstandard numpy tiktoken tqdm
```

## Usage

### News Data

```bash
python get_news_data.py --ticker <TICKER> --start-date <YYYYMMDD> --end-date <YYYYMMDD> [--api-key <KEY>] [--output <PATH>]
```

**Default filename:** `news_{ticker}_{start_date}_{end_date}.json`

### Reddit Data - PRAW Method

```bash
python get_reddit_data_from_praw.py --ticker <TICKER> --start-date <YYYYMMDD> --end-date <YYYYMMDD> [--client-id <ID>] [--client-secret <SECRET>] [--output <PATH>]
```

**Default filename:** `reddit_{ticker}_{start_date}_{end_date}.json`

### Reddit Data - Dump Method

```bash
python get_reddit_data_from_dump.py --year <YYYY> --month <MM> --ticker <TICKER> --input-path <PATH_TO_ZST> [--output-path <PATH>]
```

**Default filename:** `reddit_filtered_{ticker}_{year}{month}.json`

## Arguments

### News Data

**Required:**
- `--ticker`: Stock ticker symbol
- `--start-date`: Start date (YYYYMMDD)
- `--end-date`: End date (YYYYMMDD)

**Optional:**
- `--api-key`: Alpha Vantage API key (or use `ALPHA_VANTAGE_API` env var)
- `--output`: Output JSON file path

### Reddit PRAW Method

**Required:**
- `--ticker`: Stock ticker symbol
- `--start-date`: Start date (YYYYMMDD)
- `--end-date`: End date (YYYYMMDD)

**Optional:**
- `--client-id`: Reddit API client ID (or use `REDDIT_CLIENT_ID` env var)
- `--client-secret`: Reddit API client secret (or use `REDDIT_CLIENT_SECRET` env var)
- `--output`: Output JSON file path
- `--subreddits`: Custom list of subreddits to search

### Reddit Dump Method

**Required:**
- `--year`: Year to process (e.g., 2024)
- `--month`: Month to process (1-12)
- `--ticker`: Stock ticker symbol
- `--input-path`: Path to Reddit dump .zst file

**Optional:**
- `--output-path`: Output JSON file path
- `--top-per-day`: Number of top posts per day (default: 10)
- `--base-threshold`: Semantic similarity threshold (default: 0.55)
- `--subreddits`: Custom list of subreddits to filter

## API Setup

### News Data (Alpha Vantage)
Get your free API key at https://www.alphavantage.co/support/#api-key

```bash
export ALPHA_VANTAGE_API=YOUR_KEY
```

### Reddit PRAW Method
1. Create app at https://www.reddit.com/prefs/apps
2. Select "script" type
3. Note your client_id and client_secret

```bash
export REDDIT_CLIENT_ID=YOUR_CLIENT_ID
export REDDIT_CLIENT_SECRET=YOUR_CLIENT_SECRET
```

### Reddit Dump Method
No API required. Download dumps from https://academictorrents.com/details/56aa49f9653ba545f48df2e33679f014d2829c10

## Examples

### News Data
```bash
# With environment variable
export ALPHA_VANTAGE_API=YOUR_KEY
python get_news_data.py --ticker MSFT --start-date 20230101 --end-date 20231231

# With API key argument
python get_news_data.py --ticker TSLA --start-date 20240101 --end-date 20240630 --api-key YOUR_KEY --output news/tsla.json
```

### Reddit PRAW
```bash
# With environment variables
export REDDIT_CLIENT_ID=YOUR_ID
export REDDIT_CLIENT_SECRET=YOUR_SECRET
python get_reddit_data_from_praw.py --ticker MSFT --start-date 20250101 --end-date 20250131

# With credentials as arguments
python get_reddit_data_from_praw.py --ticker TSLA --start-date 20250201 --end-date 20250228 \
  --client-id YOUR_ID --client-secret YOUR_SECRET
```

### Reddit Dump
```bash
# Basic usage
python get_reddit_data_from_dump.py --year 2024 --month 3 --ticker NVDA \
  --input-path RS_2024-03.zst

# With custom parameters
python get_reddit_data_from_dump.py --year 2024 --month 12 --ticker MSFT \
  --input-path /data/RS_2024-12.zst \
  --output-path results/msft_dec.json \
  --top-per-day 20 --base-threshold 0.6
```

## Output Format

All scripts output JSON files organized by date (YYYY-MM-DD):

### News Data
```json
{
    "2025-01-01": [
        {
            "title": "Article title",
            "url": "https://...",
            "time_published": "20250101T143000",
            "summary": "Summary...",
            "overall_sentiment_score": 0.125,
            "ticker_sentiment": [...]
        }
    ]
}
```

### Reddit Data (Both Methods)
```json
{
    "2025-01-01": [
        {
            "title": "Post title",
            "author": "username",
            "created_utc": 1704067200.0,
            "ups": 1500,
            "score": 1450,
            "num_comments": 234,
            "selftext": "Post content...",
            "subreddit": "wallstreetbets"
        }
    ]
}
```

**Features:**
- Articles/posts grouped by date
- Sorted by relevance (news) or upvotes (Reddit)
- Automatic deduplication
- Complete metadata included

## Method Comparison

### Reddit PRAW
- **Source:** Live Reddit API
- **Best for:** Recent data (past ~1 year)
- **Features:** Real-time search, targeted queries
- **Rate limits:** Reddit API throttling
- **Speed:** Fast for targeted searches

### Reddit Dump
- **Source:** Historical archives (.zst files, 5-15GB)
- **Best for:** Historical analysis, research
- **Features:** AI semantic filtering, complete monthly data
- **Rate limits:** None
- **Speed:** 15-30 min per month
- **Quality:** Investment-focused posts only

## Default Subreddits (Reddit Methods)

Both Reddit scripts search these subreddits by default:
- StockMarket, wallstreetbets, unusual_whales, technology, stocks, WallStreetbetsELITE, options, TheRaceTo10Million, ValueInvesting, Daytrading, investing