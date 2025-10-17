import json
import pickle
import os
import pandas as pd

# Define default data path
DATA_PATH = "/path/to/collected_data/"

def topkl(json_path, pkl_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    with open(pkl_path, "wb") as f:
        pickle.dump(data, f)

    print(f"Saved pickle to {pkl_path}")


def topkl2(csv_path, pkl_path):
    data = pd.read_csv(
        csv_path,
        sep=",",
        index_col=0,
    )
    with open(pkl_path, "wb") as f:
        pickle.dump(data, f)

    print(f"Saved pickle to {pkl_path}")


def topkl3(csv_path, pkl_path):
    data = pd.read_csv(csv_path)
    with open(pkl_path, "wb") as f:
        pickle.dump(data, f)

    print(f"Saved pickle to {pkl_path}")

if __name__ == "__main__":
    for ticker in ["GOOGL", "MSFT", "META", "TSLA", "NVDA"]:
        PREFIX = f"{DATA_PATH}fundamental_metrics/insider_transactions/"
        topkl(f"{PREFIX}{ticker}.json", f"{PREFIX}{ticker}.pkl")
        PREFIX = f"{DATA_PATH}fundamental_metrics/dividends/"
        topkl(f"{PREFIX}{ticker}.json", f"{PREFIX}{ticker}.pkl")
        PREFIX = f"{DATA_PATH}event_sentiment_metrics/reddit/"
        topkl(f"{PREFIX}{ticker}.json", f"{PREFIX}{ticker}.pkl")
        PREFIX = f"{DATA_PATH}event_sentiment_metrics/alpha_vantage/"
        topkl(f"{PREFIX}{ticker}.json", f"{PREFIX}{ticker}.pkl")

        for freq in ["annual", "quarterly"]:
            csv_path = f"{DATA_PATH}fundamental_metrics/balance_sheet/{ticker}-{freq}.csv"
            pkl_path = f"{DATA_PATH}fundamental_metrics/balance_sheet/{ticker}-{freq}.pkl"
            topkl2(csv_path, pkl_path)
        
        
        for freq in ["annual", "quarterly"]:
            csv_path = f"{DATA_PATH}fundamental_metrics/cash_flow/{ticker}-{freq}.csv"
            pkl_path = f"{DATA_PATH}fundamental_metrics/cash_flow/{ticker}-{freq}.pkl"
            topkl2(csv_path, pkl_path)
        
        csv_path = f"{DATA_PATH}fundamental_metrics/earnings_estimates/{ticker}.csv"
        pkl_path = f"{DATA_PATH}fundamental_metrics/earnings_estimates/{ticker}.pkl"
        topkl2(csv_path, pkl_path)

        for freq in ["annual", "quarterly"]:
            csv_path = f"{DATA_PATH}fundamental_metrics/income_statements/{ticker}-{freq}.csv"
            pkl_path = f"{DATA_PATH}fundamental_metrics/income_statements/{ticker}-{freq}.pkl"
            topkl2(csv_path, pkl_path)
        
        PREFIX = f"{DATA_PATH}market_metrics/price_volumn/"
        topkl3(f"{PREFIX}{ticker}.csv", f"{PREFIX}{ticker}.pkl")

        PREFIX = f"{DATA_PATH}market_metrics/technical_indicators/"
        topkl3(f"{PREFIX}{ticker}.csv", f"{PREFIX}{ticker}.pkl")

    topkl3(f"{DATA_PATH}economic_sector_metrics/economic_sector_metrics.csv", f"{DATA_PATH}economic_sector_metrics/economic_sector_metrics.pkl")