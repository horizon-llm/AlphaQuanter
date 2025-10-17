# Macroeconomic Data Fetcher

A Python script to fetch and combine macroeconomic indicators from Alpha Vantage API.

## Indicators Fetched

- **Treasury Yield** - 10-year U.S. Treasury yield (monthly)
- **Federal Funds Rate** - U.S. Federal Funds effective rate (monthly)
- **CPI** - Consumer Price Index (monthly)
- **WTI** - West Texas Intermediate crude oil prices (monthly)
- **Copper** - Copper commodity prices (monthly)

## Requirements

```bash
pip install requests pandas
```

## Usage

```bash
python get_macro_data.py --start-date <YYYYMMDD> --end-date <YYYYMMDD> [OPTIONS]
```

## Arguments

### Required Arguments

- `--start-date`: Start date in YYYYMMDD format
- `--end-date`: End date in YYYYMMDD format

### Optional Arguments

- `--api-key`: Alpha Vantage API key (or use `ALPHA_VANTAGE_API` env var)
- `--output`: Output file path (default: `macro_data_{start_date}_{end_date}.csv`)

## API Key Configuration

**Option 1: Environment variable**
```bash
export ALPHA_VANTAGE_API=YOUR_API_KEY
python get_macro_data.py --start-date 20220101 --end-date 20250630
```

**Option 2: Command line argument**
```bash
python get_macro_data.py --start-date 20220101 --end-date 20250630 --api-key YOUR_API_KEY
```

Get your free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

## Output File Naming

If `--output` is not specified, the file will be automatically named:
```
macro_data_{start_date}_{end_date}.csv
```

Examples:
- `macro_data_20220101_20250630.csv`
- `macro_data_20200101_20241231.csv`

## Examples

**Basic usage**
```bash
export ALPHA_VANTAGE_API=YOUR_KEY
python get_macro_data.py --start-date 20220101 --end-date 20250630
```

**With API key argument**
```bash
python get_macro_data.py --start-date 20220101 --end-date 20250630 --api-key YOUR_KEY
```

**Custom output path**
```bash
python get_macro_data.py --start-date 20220101 --end-date 20250630 --output data/economic_indicators.csv
```

## Output Format

The script generates a CSV file with dates as index and indicators as columns:

```csv
date,treasury_yield,federal_funds_rate,cpi,wti,copper
...
```

**Features:**
- Dates sorted in descending order (most recent first)
- All indicators aligned to month start dates
- Missing values left as NaN if data unavailable
- All five indicators merged into single table

