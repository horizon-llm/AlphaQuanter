# Data Collection

A comprehensive collection of Python scripts for fetching market data, fundamental data, macroeconomic indicators, and sentiment analysis from news and social media.

## Overview

This suite provides tools to gather complete stock market data across multiple dimensions:

- **Market Data**: Historical OHLCV price data and 15+ computed trading indicators
- **Fundamental Data**: Financial statements, earnings, dividends, insider transactions
- **Macroeconomic Data**: Treasury yields, Fed rates, CPI, commodities
- **Sentiment Data**: News articles and Reddit posts analysis

## Quick Start

### Installation

```bash
# Core dependencies
pip install yfinance requests pandas numpy

# For Reddit (PRAW method)
pip install praw tqdm

# For Reddit (Dump method)
pip install sentence-transformers zstandard tiktoken tqdm
```

### API Keys

Get free API keys from:
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key (for technical, fundamental, macro data, and news)
- **Reddit API**: https://www.reddit.com/prefs/apps (for Reddit PRAW method)

```bash
export ALPHA_VANTAGE_API=YOUR_KEY
export REDDIT_CLIENT_ID=YOUR_ID
export REDDIT_CLIENT_SECRET=YOUR_SECRET
```

## Scripts Overview

### Market & Technical Data

**get_market_data.py** - Historical OHLCV data from Yahoo Finance
```bash
python get_market_data.py --ticker MSFT --start-date 20220901 --end-date 20250630 --output price_volumn/MSFT.csv
```

**get_technical_indicators.py** - 15+ technical indicators (SMA, EMA, RSI, MACD, etc.)
```bash
python get_technical_indicators.py --ticker MSFT --start-date 20220901 --end-date 20250630 --output technical_indicators/MSFT.csv
```

### Fundamental Data

**get_fundamental_data.py** - Financial statements, dividends, insider transactions, earnings
```bash
# Dividends
python get_fundamental_data.py dividends --ticker MSFT --start-date 20220901 --end-date 20250630 --output dividends/MSFT.json

# Financial statements (annual or quarterly)
python get_fundamental_data.py balance-sheet --ticker MSFT --start-date 20220901 --end-date 20250630 --annual --output balance_sheet/MSFT-annual.csv

# Insider transactions
python get_fundamental_data.py insider-transactions --ticker MSFT --start-date 20220901 --end-date 20250630 --output insider_transactions/MSFT.json
```

### Macroeconomic Data

**get_macro_data.py** - Treasury yields, Fed rates, CPI, commodities
```bash
python get_macro_data.py --start-date 20220901 --end-date 20250630 --output economic_sector_metrics.csv
```

### Sentiment Data

**get_news_data.py** - News articles with sentiment scores
```bash
python get_news_data.py --ticker MSFT --start-date 20220901 --end-date 20250630 --output alpha_vantage/MSFT.josn
```

**get_reddit_data_from_praw.py** - Recent Reddit posts (live API)
```bash
python get_reddit_data_from_praw.py --ticker MSFT --start-date 20220901 --end-date 20250630 --output reddit/MSFT.json
```

## Output Formats

- **CSV**: Market data, technical indicators, fundamental data, macro data
- **JSON**: News sentiment, Reddit posts (organized by date)

All outputs use consistent naming: `{type}_{ticker}_{start_date}_{end_date}.{ext}`

## Common Arguments

**Required for most scripts:**
- `--ticker`: Stock ticker symbol
- `--start-date`: Start date (YYYYMMDD)
- `--end-date`: End date (YYYYMMDD)

**Optional:**
- `--api-key`: API key (or use environment variables)
- `--output`: Custom output path

## Data Sources

- **Yahoo Finance**: Market OHLCV data (free, no API key)
- **Alpha Vantage**: Technical indicators, fundamentals, macro data, news (free API key)
- **Reddit API**: Recent posts via PRAW (free API credentials)
- **Reddit Dumps**: Historical archives from Academic Torrents (no API needed)
