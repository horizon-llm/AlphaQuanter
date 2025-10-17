"""
Create dataset for Trader
"""

import argparse
import os
import random

import numpy as np
import pandas as pd

TOOL_NUM = 8


def generate_ticker(ticker, start_date="2022-09-01", end_date="2024-03-31"):
    DATA_PATH = "/path/to/collected_data/"
    df = pd.read_csv(
        os.path.join(DATA_PATH, "market_metrics", "price_volumn", f"{ticker}.csv"),
        parse_dates=["Date"],
    )
    price_col = "Adj Close"
    next_t = 8
    price = df[price_col]
    ret_cols = []
    for k in range(2, next_t + 1):
        col = f"r_+{k}"
        df[col] = price.shift(-k) / price.shift(-1) - 1.0
        ret_cols.append(col)
    mask = (df["Date"] >= pd.Timestamp(start_date)) & (
        df["Date"] <= pd.Timestamp(end_date)
    )
    out = df.loc[mask, ["Date", price_col] + ret_cols].copy()
    lam = 0.8
    out["ticker"] = ticker
    raw_w = np.array([lam ** (k - 1) for k in range(2, next_t + 1)], dtype=float)
    w = 100 * raw_w / raw_w.sum()

    out["fwd_ret_ewm_h1_to_h7"] = out[ret_cols].to_numpy() @ w
    return out


def generate_ticker_rl_data(split):
    rl_dataset = {
        "prompt": [],
        "data_source": [],
        "ability": [],
        "reward_model": [],
        "extra_info": [],
        "agent_name": [],
    }
    if split == "train":
        dfs = []
        for ticker in ["GOOGL", "MSFT", "NVDA", "META", "TSLA"]:
            df = generate_ticker(ticker, "2022-09-01", "2024-03-31")
            dfs.append(df)
        df = pd.concat(dfs, axis=0, ignore_index=True)
    elif split == "test":
        dfs = []
        for ticker in ["GOOGL", "MSFT", "NVDA", "META", "TSLA"]:
            df = generate_ticker(ticker, "2024-05-15", "2024-11-14")
            dfs.append(df)
        df = pd.concat(dfs, axis=0, ignore_index=True)
    else:
        raise NotImplementedError

    for idx in range(df.shape[0]):
        current_date = df["Date"].iloc[idx].strftime("%Y-%m-%d")
        current_ticker = df["ticker"].iloc[idx]
        sys_prompt = f"""You are a professional trading strategy analyst. Your goal is to generate a well-reasoned final trade decision (BUY/SELL/HOLD) for a given stock and date through systematic, evidence-based exploration using all available tools. At most {TOOL_NUM} tool calls.
r
You have access to the following tools — use them intentionally and iteratively to test hypotheses and deepen your analysis:

- [MUST] get_market_data (historical OHLCV)
- [MUST] get_stock_indicators (trend indicators(SMA20, EMA10, VWMA20), momentum (RSI, STOCH, CCI), volatility (BBANDS, ATR), and volume-based (OBV, CMF), and hybrid(MACD))
- [OPTIONAL] get_news_data
- [OPTIONAL] get_reddit_data
- [OPTIONAL] get_macro_indicators
- [OPTIONAL] get_balance_sheet
- [OPTIONAL] get_cashflow
- [OPTIONAL] get_income_statements
- [OPTIONAL] get_insider_transactions
- [OPTIONAL] get_dividends
- [OPTIONAL] get_earnings_estimate

GUIDELINES:
## Think Like an Analyst, Not a Script.
Approach the problem creatively. There is no single fixed workflow. Use your reasoning to form hypotheses, then leverage tools flexibly to explore, validate, or refute your ideas. Be curious and iterative.

## Start with a High-Level Hypothesis.
Begin by outlining your initial perspective and what you aim to investigate. This isn’t a rigid plan—it’s a starting point. You’re encouraged to adapt as new evidence emerges.

## Plan, Execute, Then Analyze in the format: <think> ... </think>
- First, Briefly Plan: Before calling any tool, briefly state your current hypothesis or what you aim to learn with the next step.
- Then, Call One Tool: Execute only one tool call per step. You must wait for and receive the result before proceeding.
- Finally, Analyze and Adapt: Interpret the result. Does it confirm your hypothesis? Does it reveal something new? Use this insight to refine your next step.

## One Step at a Time.
You are strictly permitted to make only one tool call at a time. The subsequent analysis and planning must be based on the returned result before any further tool is called. This ensures a deliberate and evidence-driven investigative process.

## Conclude with a Decision.
After synthesizing all evidence, provide a clear and justified trade recommendation in the format:
<answer>BUY | SELL | HOLD</answer>

- Current date: {current_date}
- Target stock ticker: {current_ticker}"""
        prompt_with_template = [
            {
                "role": "system",
                "content": sys_prompt,
            },
            {
                "role": "human",
                "content": f"""Write your thinking process between <think> and </think>. DO NOT STOP until you print the final decision between <answer> and </answer>.""",
            },
        ]
        rl_dataset["prompt"].append(prompt_with_template)
        rl_dataset["data_source"].append("TradingAgent")
        rl_dataset["ability"].append("other")
        rl_dataset["extra_info"].append(
            {
                "index": idx,
                "date": current_date,
                "split": split,
                "expected_tool_calls": TOOL_NUM,
            }
        )
        rl_dataset["reward_model"].append(
            {"style": "rule", "ground_truth": df["fwd_ret_ewm_h1_to_h7"].iloc[idx]}
        )
        rl_dataset["agent_name"].append("trader")

    rl_dataset = pd.DataFrame(data=rl_dataset)
    return rl_dataset


if __name__ == "__main__":
    train_dataset = generate_ticker_rl_data("train")
    test_dataset = generate_ticker_rl_data("test")
    print(f"train_data size : {train_dataset.shape}")
    print(f"test_data  size : {test_dataset.shape}")
    output_dir = f"data/dataset/"
    os.makedirs(output_dir, exist_ok=True)
    train_dataset.to_parquet(os.path.join(output_dir, "train.parquet"))
    test_dataset.to_parquet(os.path.join(output_dir, "test.parquet"))
