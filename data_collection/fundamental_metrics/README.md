# Fundamental Data Collection

A unified Python script to fetch various types of fundamental data from Alpha Vantage API.

## Supported Data Types

### JSON Output
- **dividends** - Dividend declarations grouped by date
- **insider-transactions** - Insider transaction records grouped by date

### CSV Output
- **earnings-estimates** - Earnings estimates with dates as columns
- **balance-sheet** - Balance sheet statements (requires --annual or --quarterly)
- **income-statement** - Income statements (requires --annual or --quarterly)
- **cash-flow** - Cash flow statements (requires --annual or --quarterly)

## Requirements

```bash
pip install requests pandas
```

## Usage

```bash
python get_fundamental_data.py <DATA_TYPE> --ticker <TICKER> --start-date <YYYYMMDD> --end-date <YYYYMMDD> [OPTIONS]
```

## Arguments

### Required Arguments

- `data_type`: Type of data (positional argument, see choices above)
- `--ticker`: Stock ticker symbol
- `--start-date`: Start date in YYYYMMDD format
- `--end-date`: End date in YYYYMMDD format

### Optional Arguments

- `--api-key`: Alpha Vantage API key (or use `ALPHA_VANTAGE_API` env var)
- `--output`: Output file path (auto-generated if not specified)
- `--annual`: Fetch annual reports (financial statements only)
- `--quarterly`: Fetch quarterly reports (financial statements only)

## API Key Configuration

**Option 1: Environment variable**
```bash
export ALPHA_VANTAGE_API=YOUR_API_KEY
```

**Option 2: Command line argument**
```bash
python get_fundamental_data.py <DATA_TYPE> --ticker MSFT --start-date 20220101 --end-date 20230630 --api-key YOUR_KEY
```

Get your free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key).

## Output File Naming

If `--output` is not specified, files are automatically named:

**JSON outputs:**
- `dividends_{ticker}_{start_date}_{end_date}.json`
- `insider_transactions_{ticker}_{start_date}_{end_date}.json`

**CSV outputs:**
- `earnings_estimates_{ticker}_{start_date}_{end_date}.csv`
- `balance_sheet_{ticker}_{start_date}_{end_date}.csv`
- `income_statement_{ticker}_{start_date}_{end_date}.csv`
- `cash_flow_{ticker}_{start_date}_{end_date}.csv`

## Examples

### Dividends
```bash
export ALPHA_VANTAGE_API=YOUR_KEY
python get_fundamental_data.py dividends --ticker MSFT --start-date 20220101 --end-date 20230630
```

Output: `dividends_MSFT_20220101_20230630.json`

### Insider Transactions
```bash
python get_fundamental_data.py insider-transactions --ticker TSLA --start-date 20220101 --end-date 20230630 --api-key YOUR_KEY
```

Output: `insider_transactions_TSLA_20220101_20230630.json`

### Earnings Estimates
```bash
python get_fundamental_data.py earnings-estimates --ticker NVDA --start-date 20220101 --end-date 20230630
```

Output: `earnings_estimates_NVDA_20220101_20230630.csv`

### Financial Statements (Annual)
```bash
python get_fundamental_data.py balance-sheet --ticker MSFT --start-date 20220101 --end-date 20230630 --annual

python get_fundamental_data.py income-statement --ticker TSLA --start-date 20220101 --end-date 20230630 --annual

python get_fundamental_data.py cash-flow --ticker NVDA --start-date 20220101 --end-date 20230630 --annual
```

### Financial Statements (Quarterly)
```bash
python get_fundamental_data.py balance-sheet --ticker MSFT --start-date 20220101 --end-date 20230630 --quarterly

python get_fundamental_data.py income-statement --ticker TSLA --start-date 20220101 --end-date 20230630 --quarterly
```

### Custom Output Path
```bash
python get_fundamental_data.py dividends --ticker MSFT --start-date 20220101 --end-date 20230630 --output data/msft_divs.json
```
