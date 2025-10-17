import json
import os
import pickle
from datetime import datetime, timedelta

import pandas as pd
import tiktoken
from dateutil.relativedelta import relativedelta
from langchain_core.tools import tool
from recipe.langgraph_agent.react_agent_loop import ReactAgentLoop
from stockstats import wrap

DATA_PATH = "/path/to/collected_data/"


def get_data_in_range(ticker, start_date, end_date):
    with open(
        f"{DATA_PATH}fundamental_metrics/insider_transactions/{ticker}.pkl",
        "rb",
    ) as f:
        data = pickle.load(f)
    filtered_data = {}
    for key, value in data.items():
        if start_date <= key <= end_date and len(value) > 0:
            filtered_data[key] = value
    return filtered_data


@tool(parse_docstring=True)
def get_insider_transactions(symbol: str, curr_date: str, look_back_days: int):
    """
    Retrieve the company's insider transactions

    Args:
        symbol: ticker symbol of the company
        curr_date: current date you are trading at, yyyy-mm-dd
        look_back_days: How many days to look back, default is 7, it must not exceed 30.
    """
    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = date_obj - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    data = get_data_in_range(symbol, before, curr_date)

    if len(data) == 0:
        return ""

    result_str = ""

    seen_dicts = []
    for date, senti_list in data.items():
        for entry in senti_list:
            if entry not in seen_dicts:
                result_str += f"### Transaction Date: {entry['transaction_date']}, {entry['executive']} ({entry['executive_title']})\nType: {entry['security_type']}\nShares: {entry['shares']} ({'Acquisition' if entry['acquisition_or_disposal'] == 'A' else 'Disposal'})\n\n"
                seen_dicts.append(entry)

    return (
        f"## {symbol} insider transactions from {before} to {curr_date}:\n" + result_str
    )


@tool(parse_docstring=True)
def get_balance_sheet(symbol: str, freq: str, curr_date: str):
    """
    Retrieve the company's balance sheet

    Args:
        symbol: ticker symbol of the company
        freq: annual / quarterly
        curr_date: current date you are trading at, yyyy-mm-dd
    """
    with open(
        f"{DATA_PATH}fundamental_metrics/balance_sheet/{symbol}-{freq}.pkl",
        "rb",
    ) as f:
        df = pickle.load(f)

    df.columns = pd.to_datetime(df.columns)
    curr_date_dt = pd.to_datetime(curr_date)

    valid_dates = [col for col in df.columns if col <= curr_date_dt]
    if not valid_dates:
        raise ValueError("No balance sheet found!")
    else:
        closest_date = max(valid_dates)
    latest_balance_sheet = df[closest_date]
    latest_balance_sheet = latest_balance_sheet.dropna()
    return (
        f"## {freq} balance sheet for {symbol} released on {closest_date.date()}: \n"
        + str(latest_balance_sheet)
    )


@tool(parse_docstring=True)
def get_cashflow(symbol: str, freq: str, curr_date: str):
    """
    Retrieve the company's cash flow

    Args:
        symbol: ticker symbol of the company
        freq: annual / quarterly
        curr_date: current date you are trading at, yyyy-mm-dd
    """
    with open(
        f"{DATA_PATH}fundamental_metrics/cash_flow/{symbol}-{freq}.pkl",
        "rb",
    ) as f:
        df = pickle.load(f)

    df.columns = pd.to_datetime(df.columns)
    curr_date_dt = pd.to_datetime(curr_date)

    valid_dates = [col for col in df.columns if col <= curr_date_dt]
    if not valid_dates:
        raise ValueError("No cash flow found!")
    else:
        closest_date = max(valid_dates)
    latest_cash_flow = df[closest_date]
    latest_cash_flow = latest_cash_flow.dropna()

    return (
        f"## {freq} cash flow statement for {symbol} released on {closest_date.date()}: \n"
        + str(latest_cash_flow)
    )


@tool(parse_docstring=True)
def get_earnings_estimate(symbol: str, curr_date: str):
    """
    Retrieve the company's earnings estimate

    Args:
        symbol: ticker symbol of the company
        curr_date: current date you are trading at, yyyy-mm-dd
    """
    with open(
        f"{DATA_PATH}fundamental_metrics/earnings_estimates/{symbol}.pkl",
        "rb",
    ) as f:
        df = pickle.load(f)

    df.columns = pd.to_datetime(df.columns)
    curr_date_dt = pd.to_datetime(curr_date)

    valid_dates = [col for col in df.columns if col <= curr_date_dt]
    if not valid_dates:
        raise ValueError("No earnings estimate found!")
    else:
        closest_date = max(valid_dates)
    latest_ee = df[closest_date]
    latest_ee = latest_ee.dropna()
    return (
        f"## earnings estimate for {symbol} released on {closest_date.date()}: \n"
        + str(latest_ee)
    )


@tool(parse_docstring=True)
def get_dividends(symbol: str, curr_date: str):
    """
    Retrieve the company's dividends

    Args:
        symbol: ticker symbol of the company
        curr_date: current date you are trading at, yyyy-mm-dd
    """
    with open(
        f"{DATA_PATH}fundamental_metrics/dividends/{symbol}.pkl",
        "rb",
    ) as f:
        data = pickle.load(f)

    valid_dates = [col for col in data.keys() if col <= curr_date]
    if not valid_dates:
        return f"## No recent dividend information could be found for {symbol}."
    else:
        closest_date = max(valid_dates)
    amount = data[closest_date]

    return f"## The most recent declared dividend date for {symbol} is {closest_date}, with an amount of {amount}."


@tool(parse_docstring=True)
def get_income_statements(symbol: str, freq: str, curr_date: str):
    """
    Retrieve the company's income statements

    Args:
        symbol: ticker symbol of the company
        freq: annual / quarterly
        curr_date: current date you are trading at, yyyy-mm-dd
    """
    with open(
        f"{DATA_PATH}fundamental_metrics/income_statements/{symbol}-{freq}.pkl",
        "rb",
    ) as f:
        df = pickle.load(f)

    df.columns = pd.to_datetime(df.columns)
    curr_date_dt = pd.to_datetime(curr_date)

    valid_dates = [col for col in df.columns if col <= curr_date_dt]
    if not valid_dates:
        raise ValueError("No cash flow found!")
    else:
        closest_date = max(valid_dates)
    latest_income = df[closest_date]
    latest_income = latest_income.dropna()
    return (
        f"## {freq} income statement for {symbol} released on {closest_date.date()}: \n"
        + str(latest_income)
    )


def get_macro_indicators_window(indicator, curr_date, look_back_months):
    best_ind_params = {
        "treasury_yield": (
            "Treasury Yield: The return on investment for U.S. government bonds of various maturities (e.g., 2-year, 10-year). "
        ),
        "federal_funds_rate": (
            "Federal Funds Rate: The benchmark interest rate set by the Federal Reserve for overnight lending between banks. "
        ),
        "cpi": (
            "Consumer Price Index (CPI): Measures the average change over time in prices paid by consumers for a basket of goods and services. "
        ),
        "wti": (
            "West Texas Intermediate (WTI) Crude Oil Price: Benchmark price for U.S. crude oil. "
        ),
        "copper": ("Copper Price: A global benchmark for industrial metal demand. "),
    }

    if indicator not in best_ind_params:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(best_ind_params.keys())}"
        )

    end_date = curr_date
    curr_date = datetime.strptime(curr_date, "%Y-%m-%d")
    path = f"{DATA_PATH}economic_sector_metrics/economic_sector_metrics.pkl"
    with open(
        path,
        "rb",
    ) as f:
        data = pickle.load(f)
    if data.columns[0] != "date":
        data = data.rename(columns={data.columns[0]: "Date"})
    data["Date"] = pd.to_datetime(data["Date"])

    dates_in_df = data["Date"].astype(str).str[:10]

    out = data[data["Date"] <= curr_date].head(look_back_months).reset_index(drop=True)

    out = out[["Date", indicator]]
    ind_string = ""
    for i in range(out.shape[0]):
        ind_string += (
            f"{out['Date'].iloc[i].strftime('%Y-%m-%d')}: {out[indicator].iloc[i]}\n"
        )

    result_str = (
        f"## {indicator} values for the {look_back_months} months prior to {end_date}:\n\n"
        + ind_string
        + "\n\n"
        + best_ind_params.get(indicator, "No description available.")
    )

    return result_str


def fetch_reddit(date, max_limit, query):
    all_content = []
    enc = tiktoken.encoding_for_model("gpt-4o")
    with open(
        f"{DATA_PATH}event_sentiment_metrics/reddit/NEW_{query}.json",
        "r",
    ) as f:
        data = json.load(f)
    for parsed_line in data.get(date, []):
        post = {
            "date": date,
            "content": parsed_line["content"],
            "upvotes": parsed_line.get("ups", 0),
        }
        all_content.append(post)
    all_content.sort(key=lambda x: x["upvotes"], reverse=True)
    selected_content = []
    total_tokens = 0
    total_nums = 0
    for idx, ii in enumerate(all_content):
        length = len(enc.encode(ii["content"]))
        if total_tokens + length <= 1000 and total_nums < max_limit:
            selected_content.append(ii)
            total_tokens += length
            total_nums += 1

    return selected_content


def get_data_in_range_alphav(ticker, start_date, end_date):
    with open(
        f"{DATA_PATH}event_sentiment_metrics/alpha_vantage/{ticker}.pkl",
        "rb",
    ) as f:
        data = pickle.load(f)
    filtered_data = {}
    for key, value in data.items():
        if start_date <= key <= end_date and len(value) > 0:
            filtered_data[key] = value
    return filtered_data


def get_reddit(ticker, curr_date):
    start_date = curr_date
    look_back_days = 2
    max_limit_per_day = 5

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    posts = []
    curr_date = datetime.strptime(before, "%Y-%m-%d")

    total_iterations = (start_date - curr_date).days + 1

    while curr_date <= start_date:
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        fetch_result = fetch_reddit(curr_date_str, max_limit_per_day, ticker)
        posts.extend(fetch_result)
        curr_date += relativedelta(days=1)

    if len(posts) == 0:
        return ""

    news_str = ""
    for post in posts:
        news_str += f"{post['date']}: {post['content']}\n\n"

    return f"##{ticker} Reddit, from {before} to {start_date}:\n\n{news_str}"


def get_alphav_news(ticker, curr_date):
    look_back_days = 2
    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    result = get_data_in_range_alphav(ticker, before, curr_date)

    if len(result) == 0:
        return ""

    combined_result = ""
    for day, data in sorted(result.items()):
        if len(data) == 0:
            continue
        # print(day, len(data))
        data = data[:10]  # return the 10-most relevant news for each day
        for entry in data:
            score = float(entry["ticker_sentiment"][0]["ticker_sentiment_score"])
            label = entry["ticker_sentiment"][0]["ticker_sentiment_label"]
            current_news = (
                f"{day} [Sentiment score = {score:.2f}, {label}] " + entry["title"]
            )
            combined_result += current_news + "\n"

    return (
        f"## {ticker} News, from {before} to {curr_date}:\n"
        + "Interpret the sentiment score x: values near 0 are Neutral, larger positive values indicate increasingly Bullish, and larger negative values indicate increasingly Bearish.\n"
        + str(combined_result)
    )


def get_stockstats_indicator(symbol, indicator, curr_date):
    curr_date = datetime.strptime(curr_date, "%Y-%m-%d")
    curr_date = curr_date.strftime("%Y-%m-%d")
    try:
        path = f"{DATA_PATH}market_metrics/technical_indicators/{symbol}.pkl"
        with open(
            path,
            "rb",
        ) as f:
            data = pickle.load(f)

        df = wrap(data)
        if indicator == "MACD":
            indicator = ["MACD", "MACDS", "MACDH"]
        elif indicator == "BBANDS":
            indicator = ["BBANDS_MID", "BBANDS_UPPER", "BBANDS_LOWER"]
        elif indicator == "STOCH":
            indicator = ["STOCH_SLOWK", "STOCH_SLOWD"]
        matching_rows = df[df["Date"].str.startswith(curr_date)]
        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            if isinstance(indicator, list):
                if indicator[0] == "BBANDS_MID":
                    return f"(Middle={indicator_value[0]:.02f},Upper={indicator_value[1]:.02f},Lower={indicator_value[2]:.02f})"
                if indicator[0] == "STOCH_SLOWK":
                    return f"(SlowK={indicator_value[0]:.02f},SlowD={indicator_value[1]:.02f})"
                if indicator[0] == "MACD":
                    return f"(MACD={indicator_value[0]:.02f},Signal={indicator_value[1]:.02f},Histogram={indicator_value[2]:.02f})"
            return f"{float(indicator_value):.2f}"
        else:
            return "N/A: Not a trading day (weekend or holiday)"
    except Exception as e:
        print(
            f"Error getting stockstats indicator data for indicator {indicator} on {curr_date}: {e}"
        )
        return ""


def get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days):
    best_ind_params = {
        # Trend Indicator
        "SMA20": (
            "SMA 20: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
        ),
        "EMA10": (
            "EMA 10: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
        ),
        "VWMA20": (
            "VWMA 20: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
        ),
        # Momentum Indicators
        "RSI": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
        ),
        "STOCH": (
            "STOCH: Compares a security’s closing price to its price range over a set period, "
            "plotted as SlowK and its moving average SlowD. "
            "Usage: Monitor SlowK–SlowD crossovers and apply typical 80/20 thresholds to spot potential overbought or oversold conditions. "
        ),
        "CCI": (
            "CCI: Measures the deviation of price from its statistical average. "
            "Usage: Apply ±100 levels to spot potential overbought/oversold zones or trend reversals. "
        ),
        # Volatility Indicators
        "BBANDS": (
            "Bollinger Bands: Consist of a Middle Band (typically a 20-period SMA) and Upper/Lower Bands set "
            "at ±2 standard deviations from the middle. "
            "Usage: The middle band serves as a dynamic benchmark for price, the upper band highlights potential overbought or breakout zones, "
            "and the lower band signals possible oversold conditions. "
        ),
        "ATR": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
        ),
        # Volume-Based Indicators
        "OBV": (
            "OBV: Cumulative volume indicator that adds volume on up days and subtracts on down days. "
            "Usage: Track OBV trends to confirm price movements or spot divergences that may precede reversals. "
        ),
        "CMF": (
            "CMF: Measures buying and selling pressure based on price and volume over a set period. "
            "Usage: Positive values suggest accumulation, negative values indicate distribution; watch for shifts across the zero line. "
        ),
        # Hybrid
        "MACD": (
            "MACD: Momentum indicator composed of the MACD line (difference between two EMAs), "
            "the Signal line (EMA of the MACD line), and the Histogram (gap between MACD and Signal). "
            "Usage: Identify trend changes through MACD–Signal crossovers, gauge momentum strength via Histogram size, "
            "and watch for divergence between MACD and price as early reversal signals. "
        ),
    }

    if indicator not in best_ind_params:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(best_ind_params.keys())}"
        )
    end_date = curr_date
    curr_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date - relativedelta(days=look_back_days)

    path = f"{DATA_PATH}market_metrics/price_volumn/{symbol}.pkl"

    with open(
        path,
        "rb",
    ) as f:
        data = pickle.load(f)

    data["Date"] = pd.to_datetime(data["Date"], utc=True)
    dates_in_df = data["Date"].astype(str).str[:10]
    values = []
    while curr_date >= before:
        if curr_date.strftime("%Y-%m-%d") in dates_in_df.values:
            indicator_value = get_stockstats_indicator(
                symbol, indicator, curr_date.strftime("%Y-%m-%d")
            )
            values.append(f"{indicator_value}")
        curr_date = curr_date - relativedelta(days=1)

    ind_string = "→".join(values[::-1])
    result_str = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {end_date}:\n\n"
        + ind_string
        + "\n\n"
        + best_ind_params.get(indicator, "No description available.")
    )

    return result_str


@tool(parse_docstring=True)
def get_market_data(symbol: str, curr_date: str, look_back_days: int) -> str:
    """
    Retrieve the stock price data for a given ticker symbol for the specified ticker symbol in the specified date range

    Args:
        symbol: Ticker symbol of the company, e.g. AAPL
        curr_date: The current trading date you are trading on, yyyy-mm-dd
        look_back_days: How many days to look back, default is 14, it must not exceed 30.
    """
    path = f"{DATA_PATH}market_metrics/price_volumn/{symbol}.pkl"
    with open(
        path,
        "rb",
    ) as f:
        df = pickle.load(f)

    end_date = curr_date
    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    prev_date = date_obj - timedelta(days=look_back_days)
    start_date = prev_date.strftime("%Y-%m-%d")

    mask = df["Date"].str[:10].between(start_date, end_date)
    return df.loc[mask].reset_index(drop=True)


@tool(parse_docstring=True)
def get_stock_indicators(
    symbol: str, indicator: str, curr_date: str, look_back_days: int
) -> str:
    """
    Retrieve stock stats indicators for a given ticker symbol

    Args:
        symbol: Ticker symbol of the company, e.g. AAPL
        indicator: Technical indicator to get the analysis and report of. Option include: SMA20, EMA10, VWMA20, RSI, STOCH, CCI, BBANDS, ATR, OBV, CMF, MACD
        curr_date: The current trading date you are trading on, YYYY-mm-dd
        look_back_days: How many days to look back, default is 14, it must not exceed 30.
    """

    indicators = [i.strip() for i in indicator.split(",")]

    indicators = [",".join(indicators)]

    results = []

    for indicator in indicators:
        results.append(
            get_stock_stats_indicators_window(
                symbol, indicator, curr_date, look_back_days
            )
        )

    return "\n".join(results)


@tool(parse_docstring=True)
def get_news_data(symbol: str, curr_date: str) -> str:
    """
    Retrieve recent news updates on a given stock within 3 days

    Args:
        symbol: Ticker symbol of the company, e.g. AAPL
        curr_date: The current trading date you are trading on, YYYY-mm-dd
    """

    alphav_news_results = get_alphav_news(symbol, curr_date)
    return alphav_news_results


@tool(parse_docstring=True)
def get_reddit_data(symbol: str, curr_date: str) -> str:
    """
    Retrieve recent reddit updates on a given stock within 3 days

    Args:
        symbol: Ticker symbol of the company, e.g. AAPL
        curr_date: The current trading date you are trading on, YYYY-mm-dd
    """

    reddit_results = get_reddit(symbol, curr_date)

    return reddit_results


@tool(parse_docstring=True)
def get_macro_indicators(curr_date: str, look_back_months: int):
    """
    Retrieve macro indicators report

    Args:
        curr_date: The current trading date you are trading on, YYYY-mm-dd
        look_back_months: How many months to look back, default is 6, it must not exceed 12.
    """
    results = []
    for indicator in [
        "treasury_yield",
        "federal_funds_rate",
        "cpi",
        "wti",
        "copper",
    ]:
        results.append(
            get_macro_indicators_window(indicator, curr_date, look_back_months)
        )
    return "\n".join(results)


def get_fundamental_data(symbol: str, freq: str, curr_date: str):
    """
    Retrieve the company's fundamental data

    Args:
        symbol: ticker symbol of the company
        freq: reporting frequency of the company's financial history: annual / quarterly
        curr_date: current date you are trading at, yyyy-mm-dd
    """
    results = []
    results.append(get_balance_sheet(symbol, freq, curr_date))
    results.append(get_cashflow(symbol, freq, curr_date))
    results.append(get_income_statements(symbol, freq, curr_date))
    results.append(get_insider_transactions(symbol, curr_date, 7))
    results.append(get_dividends(symbol, curr_date))
    results.append(get_earnings_estimate(symbol, curr_date))
    return "\n".join(results)


class TraderReactAgentLoop(ReactAgentLoop):
    @classmethod
    def init_class(cls, config, tokenizer, **kwargs):
        cls.tools = [
            get_market_data,
            get_stock_indicators,
            get_news_data,
            get_reddit_data,
            get_macro_indicators,
            get_balance_sheet,
            get_cashflow,
            get_income_statements,
            get_insider_transactions,
            get_dividends,
            get_earnings_estimate,
        ]
        super().init_class(config, tokenizer)


if __name__ == "__main__":
    pass
