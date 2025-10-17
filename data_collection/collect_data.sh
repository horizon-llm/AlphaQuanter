#!/bin/bash

# Configuration
TICKER="MSFT"
OUTPUT_DIR="../collected_data"
START_DATE="20220901"
END_DATE="20250630"

# Create output directories
DIRS=(
	"market_metrics/price_volumn"
	"market_metrics/technical_indicators"
	"event_sentiment_metrics/alpha_vantage"
	"event_sentiment_metrics/reddit"
	"fundamental_metrics/balance_sheet"
	"fundamental_metrics/cash_flow"
	"fundamental_metrics/income_statements"
	"fundamental_metrics/dividends"
	"fundamental_metrics/earnings_estimates"
	"fundamental_metrics/insider_transactions"
	"economic_sector_metrics"
)

for dir in "${DIRS[@]}"; do
	mkdir -p ${OUTPUT_DIR}/${dir}
done

echo "=========================================="
echo "Running data collection for ${TICKER}"
echo "Date range: ${START_DATE} - ${END_DATE}"
echo "Output directory: ${OUTPUT_DIR}"
echo "=========================================="

# 1. Market Data
echo "[1/11] Fetching market data..."
python get_market_data.py \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/market_metrics/price_volumn/${TICKER}.csv

# 2. Market Data - Technical Indicators
echo "[2/11] Fetching technical indicators..."
python get_technical_indicators.py \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/market_metrics/technical_indicators/${TICKER}.csv

# 3. Fundamental Data - Balance Sheet
echo "[3/11] Fetching balance sheet (annual & quarterly)..."
python get_fundamental_data.py balance-sheet \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--annual \
	--output ${OUTPUT_DIR}/fundamental_metrics/balance_sheet/${TICKER}-annual.csv

python get_fundamental_data.py balance-sheet \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--quarterly \
	--output ${OUTPUT_DIR}/fundamental_metrics/balance_sheet/${TICKER}-quarterly.csv

# 4. Fundamental Data - Cash Flow
echo "[4/11] Fetching cash flow (annual & quarterly)..."
python get_fundamental_data.py cash-flow \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--annual \
	--output ${OUTPUT_DIR}/fundamental_metrics/cash_flow/${TICKER}-annual.csv

python get_fundamental_data.py cash-flow \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--quarterly \
	--output ${OUTPUT_DIR}/fundamental_metrics/cash_flow/${TICKER}-quarterly.csv

# 5. Fundamental Data - Income Statement
echo "[5/11] Fetching income statement (annual & quarterly)..."
python get_fundamental_data.py income-statement \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--annual \
	--output ${OUTPUT_DIR}/fundamental_metrics/income_statements/${TICKER}-annual.csv

python get_fundamental_data.py income-statement \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--quarterly \
	--output ${OUTPUT_DIR}/fundamental_metrics/income_statements/${TICKER}-quarterly.csv

# 6. Fundamental Data - Dividends
echo "[6/11] Fetching dividends..."
python get_fundamental_data.py dividends \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/fundamental_metrics/dividends/${TICKER}.json

# 7. Fundamental Data - Earnings Estimates
echo "[7/11] Fetching earnings estimates..."
python get_fundamental_data.py earnings-estimates \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/fundamental_metrics/earnings_estimates/${TICKER}.csv

# 8. Fundamental Data - Insider Transactions
echo "[8/11] Fetching insider transactions..."
python get_fundamental_data.py insider-transactions \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/fundamental_metrics/insider_transactions/${TICKER}.json

# 9. Macro Data
echo "[9/11] Fetching macro data..."
python get_macro_data.py \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/economic_sector_metrics/economic_sector_metrics.csv

# 10. News Data
echo "[10/11] Fetching news sentiment data..."
python get_news_data.py \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/event_sentiment_metrics/alpha_vantage/${TICKER}.json

# 11. Reddit Data (PRAW method)
echo "[11/11] Fetching Reddit data (PRAW)..."
python get_reddit_data_from_praw.py \
	--ticker ${TICKER} \
	--start-date ${START_DATE} \
	--end-date ${END_DATE} \
	--output ${OUTPUT_DIR}/event_sentiment_metrics/reddit/${TICKER}.json

echo "=========================================="
echo "Data collection completed!"
echo "All files saved to: ${OUTPUT_DIR}"
echo "=========================================="
