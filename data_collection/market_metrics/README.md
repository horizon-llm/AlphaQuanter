# Market Data Collection

Python scripts for fetching stock market data and technical indicators.

## Scripts

### 1. get_market_data.py
Fetches historical OHLCV data from Yahoo Finance.

### 2. get_technical_indicators.py
Fetches and computes technical indicators using Alpha Vantage API.

## Requirements

```bash
# For market data
pip install yfinance

# For technical indicators
pip install requests pandas numpy
```

## Usage

### Market Data

```bash
python get_market_data.py --ticker <TICKER> --start-date <YYYYMMDD> --end-date <YYYYMMDD> [--output <PATH>]
```

**Output columns:** Date, Open, High, Low, Close, Adj Close, Volume

**Default filename:** `market_{ticker}_{start_date}_{end_date}.csv`

### Technical Indicators

```bash
python get_technical_indicators.py --ticker <TICKER> --start-date <YYYYMMDD> --end-date <YYYYMMDD> [--api-key <KEY>] [--output <PATH>]
```

**API-based indicators:** SMA20, EMA10, RSI, STOCH, CCI, BBANDS, ATR, OBV

**Computed indicators:** VWMA20, CMF, MACD, MACDS, MACDH

**Default filename:** `technical_indicators_{ticker}_{start_date}_{end_date}.csv`

## Arguments

### Common Arguments (Both Scripts)

- `--ticker`: Stock ticker symbol (required)
- `--start-date`: Start date in YYYYMMDD format (required)
- `--end-date`: End date in YYYYMMDD format (required)
- `--output`: Output file path (optional)

### Technical Indicators Only

- `--api-key`: Alpha Vantage API key (optional if environment variable is set)

## API Key Configuration (Technical Indicators)

**Option 1: Command line**
```bash
python get_technical_indicators.py --ticker MSFT --start-date 20220101 --end-date 20230630 --api-key YOUR_KEY
```

**Option 2: Environment variable**
```bash
export ALPHA_VANTAGE_API=YOUR_KEY
python get_technical_indicators.py --ticker MSFT --start-date 20220101 --end-date 20230630
```

Get your free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

## Examples

### Fetch Market Data

```bash
# Basic usage
python get_market_data.py --ticker MSFT --start-date 20250101 --end-date 20250630

# Custom output
python get_market_data.py --ticker TSLA --start-date 20250101 --end-date 20250630 --output price_volumn/TSLA.csv
```

### Fetch Technical Indicators

```bash
# With environment variable
export ALPHA_VANTAGE_API=YOUR_KEY
python get_technical_indicators.py --ticker MSFT --start-date 20220101 --end-date 20230630

# With API key in command
python get_technical_indicators.py --ticker TSLA --start-date 20220101 --end-date 20230630 --api-key YOUR_KEY

# Custom output path
python get_technical_indicators.py --ticker MSFT --start-date 20220101 --end-date 20230630 --output technical_indicators/MSFT.csv
```

## Output Format

### Market Data CSV

| Column | Description |
|--------|-------------|
| Date | Trading date (YYYY-MM-DD) |
| Open | Opening price (2 decimals) |
| High | Highest price (2 decimals) |
| Low | Lowest price (2 decimals) |
| Close | Closing price (2 decimals) |
| Adj Close | Adjusted closing price (2 decimals) |
| Volume | Trading volume (integer) |

### Technical Indicators CSV

| Column | Description |
|--------|-------------|
| Date | Trading date (YYYY-MM-DD) |
| SMA20 | Simple Moving Average (20) |
| EMA10 | Exponential Moving Average (10) |
| RSI | Relative Strength Index (14) |
| STOCH_SLOWK, STOCH_SLOWD | Stochastic Oscillator |
| CCI | Commodity Channel Index (21) |
| BBANDS_MID, BBANDS_UPPER, BBANDS_LOWER | Bollinger Bands (20) |
| ATR | Average True Range (14) |
| OBV | On-Balance Volume |
| VWMA20 | Volume Weighted Moving Average (20) |
| CMF | Chaikin Money Flow (21) |
| MACD, MACDS, MACDH | MACD indicators (12-26-9) |

All numeric values formatted to 6 decimal places.