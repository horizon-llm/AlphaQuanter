import argparse
import json
import logging
import os
import pickle
import re
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import tiktoken
import zstandard
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

log = logging.getLogger("bot")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Filter and organize Reddit posts by stock ticker relevance"
    )
    parser.add_argument(
        "--year", type=int, required=True, help="Year of the Reddit data (e.g., 2024)"
    )
    parser.add_argument(
        "--month", type=int, required=True, help="Month of the Reddit data (1-12)"
    )
    parser.add_argument(
        "--ticker", type=str, required=True, help="Stock ticker symbol (e.g., MSFT)"
    )
    parser.add_argument(
        "--input-path",
        type=str,
        required=True,
        help="Path to input .zst file (e.g., RS_2024-03.zst)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Path to output JSON file (default: reddit_filtered_{TICKER}_{YEAR}{MONTH:02d}.json)",
    )
    parser.add_argument(
        "--top-per-day",
        type=int,
        default=10,
        help="Number of top posts to keep per day (default: 10)",
    )
    parser.add_argument(
        "--base-threshold",
        type=float,
        default=0.5,
        help="Base semantic similarity threshold (default: 0.5)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.05,
        help="Margin for generic similarity (default: 0.05)",
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
        help="List of subreddits to filter",
    )

    return parser.parse_args()


ALIASES = {
    "GOOGL": [r"Google", r"Alphabet"],
    "MSFT": [r"Microsoft"],
    "META": [r"Meta Platforms?", r"Facebook", r"Instagram", r"WhatsApp", r"Oculus"],
    "NVDA": [r"NVIDIA"],
    "TSLA": [r"Tesla"],
}

EVAL_TEMPLATES = {
    "GOOGL": [
        "This post evaluates GOOGL stock: Alphabet fundamentals, ads, cloud, AI impact on share price.",
        "Earnings/guidance analysis for Google with implications for GOOGL stock.",
        "Investment recommendation on GOOGL with risk/reward assessment.",
    ],
    "MSFT": [
        "Evaluating MSFT stock: Azure growth, AI, Copilot, margins, and valuation.",
        "Earnings analysis for Microsoft and expected impact on MSFT price.",
        "Buy/sell/hold view on MSFT with thesis and risks.",
    ],
    "META": [
        "Evaluating META stock: ads, Reels, family apps, Reality Labs burn, and valuation.",
        "Earnings/guidance discussion for Meta Platforms and impact on META shares.",
        "Investment view on META with catalysts and risks.",
    ],
    "NVDA": [
        "Evaluating NVDA stock: datacenter demand, GPUs, supply, pricing, and valuation.",
        "NVIDIA earnings/gross margin outlook and expected impact on NVDA stock.",
        "Buy/sell/hold thesis on NVDA with near-term catalysts.",
    ],
    "TSLA": [
        "Evaluating TSLA stock: deliveries, margins, FSD progress, energy, and valuation.",
        "Tesla earnings/guidance discussion and implications for TSLA price.",
        "Investment view on TSLA with catalysts, risks, and time horizon.",
    ],
}

GENERIC_TEMPLATES = [
    "Casually mentioning many tickers in a list without evaluating any single one.",
    "General statement about wishing to have invested in multiple companies.",
    "Talking broadly about tech stocks without specific analysis or valuation.",
]

INVESTMENT_CUES = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\bhold\b",
    r"\bthesis\b",
    r"\bvaluation\b",
    r"\bprice target\b",
    r"\bearnings\b",
    r"\bguidance\b",
    r"\brevenue\b",
    r"\bmargin\b",
    r"\bEPS\b",
    r"\bforecast\b",
    r"\bDCF\b",
    r"\bundervalued\b",
    r"\bovervalued\b",
    r"\bPE\b",
    r"\bP\/E\b",
    r"\bshort\b",
    r"\blong\b",
    r"\bcatalyst\b",
    r"\brisk\b",
    r"\bupgrade\b",
    r"\bdowngrade\b",
]

CUE_BOOST = 0.02
REQUIRE_POSITIVE = True


def read_and_decode(
    reader, chunk_size, max_window_size, previous_chunk=None, bytes_read=0
):
    """Read and decode zstandard compressed data."""
    chunk = reader.read(chunk_size)
    bytes_read += chunk_size
    if previous_chunk is not None:
        chunk = previous_chunk + chunk
    try:
        return chunk.decode()
    except UnicodeDecodeError:
        if bytes_read > max_window_size:
            raise UnicodeError(
                f"Unable to decode frame after reading {bytes_read:,} bytes"
            )
        log.info(f"Decoding error with {bytes_read:,} bytes, reading another chunk")
        return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)


def read_lines_zst(file_name):
    """Read lines from zstandard compressed file."""
    with open(file_name, "rb") as file_handle:
        buffer = ""
        reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(
            file_handle
        )
        while True:
            chunk = read_and_decode(reader, 2**27, (2**29) * 2)
            if not chunk:
                break
            lines = (buffer + chunk).split("\n")
            for line in lines[:-1]:
                yield line, file_handle.tell()
            buffer = lines[-1]
        reader.close()


def load_reddit_data_from_zst(file_path, subreddits, year, month):
    """Load and filter Reddit data from zst file."""
    file_size = os.stat(file_path).st_size
    data = defaultdict(list)

    bad_lines = useful = file_lines = 0
    last_created_str = "--"
    prev_bytes = 0

    pbar = tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Loading zst file",
    )

    all_lines = read_lines_zst(file_path)

    for line, file_bytes_processed in all_lines:
        try:
            obj = json.loads(line)
            created = datetime.utcfromtimestamp(int(obj["created_utc"]))
            last_created_str = created.strftime("%Y-%m-%d %H:%M:%S")

            if created.year == year and created.month == month:
                if obj.get("subreddit") in subreddits:
                    data[obj["subreddit"]].append(obj)
                    useful += 1
        except (KeyError, json.JSONDecodeError):
            bad_lines += 1
        finally:
            file_lines += 1
            delta = file_bytes_processed - prev_bytes
            if delta > 0:
                pbar.update(delta)
                prev_bytes = file_bytes_processed
            if file_lines % 100000 == 0:
                pbar.set_postfix_str(
                    f"{last_created_str} | lines:{file_lines:,} "
                    f"| bad:{bad_lines:,} | useful:{useful:,}"
                )

    pbar.close()
    log.info(f"Complete: {file_lines:,} lines | {bad_lines:,} bad | {useful:,} useful")

    for key in data.keys():
        log.info(f"{key}: {len(data[key])} posts")

    return data


def compile_patterns(ticker):
    """Compile regex patterns for ticker matching."""
    cashtag = re.compile(rf"(?<![A-Za-z0-9_])\${ticker}\b", re.IGNORECASE)
    pure = re.compile(rf"\b{ticker}\b", re.IGNORECASE)
    alias_res = [
        re.compile(rf"\b{a}\b", re.IGNORECASE) for a in ALIASES.get(ticker, [])
    ]
    return {"cashtag": cashtag, "ticker": pure, "aliases": alias_res}


def text_of(obj):
    """Extract text content from Reddit post object."""
    return f"{obj.get('title','')} {obj.get('selftext','')}".strip()


def passes_keyword_prefilter(patterns, text):
    """Check if text contains ticker or aliases."""
    if patterns["cashtag"].search(text) or patterns["ticker"].search(text):
        return True
    for ar in patterns["aliases"]:
        if ar.search(text):
            return True
    return False


def semantic_score(text_emb, anchors):
    """Calculate maximum cosine similarity with anchor embeddings."""
    sims = util.cos_sim(text_emb, anchors)
    return float(sims.max())


def created_ts(obj):
    """Extract creation timestamp from object."""
    try:
        return int(obj.get("created_utc", 0))
    except Exception:
        return 0


def is_in_year_month(utc_ts, year, month):
    """Check if timestamp is in specified year and month."""
    dt = datetime.fromtimestamp(utc_ts, tz=timezone.utc)
    return dt.year == year and dt.month == month


def obj_key_of(obj, txt):
    """Generate unique key for deduplication."""
    return obj.get("id") or hash(txt)


def compute_rank_score(s, base_threshold, margin):
    """Calculate ranking score based on semantic similarity."""
    boost = CUE_BOOST if s["has_cue"] else 0.0
    boundary = max(base_threshold - boost, s["gen"] + margin)
    return s["eval"] - boundary


def day_key_utc(ts):
    """Convert timestamp to YYYY-MM-DD date string."""
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")


def dedup_key(obj):
    """Generate deduplication key from object."""
    return obj.get("id") or hash(f"{obj.get('title','')} {obj.get('selftext','')}")


def organize_by_date(posts):
    """Organize posts by date and sort by upvotes."""
    posts_by_date = defaultdict(list)

    for obj in posts:
        ts = created_ts(obj)
        date_str = day_key_utc(ts)
        posts_by_date[date_str].append(obj)

    result = {}
    for date, date_posts in sorted(posts_by_date.items()):
        sorted_posts = sorted(date_posts, key=lambda x: x.get("ups", 0), reverse=True)
        result[date] = sorted_posts

    return result


def main():
    args = parse_arguments()

    YEAR = args.year
    MONTH = args.month
    TICKER = args.ticker
    N_TOP_PER_DAY = args.top_per_day
    BASE_THRESHOLD = args.base_threshold
    MARGIN = args.margin

    if args.output_path:
        OUTPUT_PATH = args.output_path
    else:
        OUTPUT_PATH = f"reddit_filtered_{TICKER}_{YEAR}{MONTH:02d}.json"

    log.info(f"Loading Reddit data from {args.input_path}...")
    data = load_reddit_data_from_zst(args.input_path, args.subreddits, YEAR, MONTH)

    log.info(f"Initializing model and patterns for {TICKER}...")
    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
    model = SentenceTransformer(MODEL_NAME)
    enc = tiktoken.get_encoding("cl100k_base")

    INVESTMENT_RE = re.compile("|".join(INVESTMENT_CUES), re.IGNORECASE)
    patterns = compile_patterns(TICKER)

    if TICKER not in EVAL_TEMPLATES:
        log.warning(f"No evaluation templates for {TICKER}, using generic approach")
        EVAL_EMB = model.encode(GENERIC_TEMPLATES, normalize_embeddings=True)
    else:
        EVAL_EMB = model.encode(EVAL_TEMPLATES[TICKER], normalize_embeddings=True)

    GENERIC_EMB = model.encode(GENERIC_TEMPLATES, normalize_embeddings=True)

    log.info("Processing posts...")
    scores = {}

    for subreddit, posts in data.items():
        log.info(f"Processing {subreddit}: {len(posts)} posts")
        for obj in tqdm(posts, desc=f"Analyzing {subreddit}"):
            txt = text_of(obj)
            if not txt:
                continue
            if (obj.get("selftext") or "").strip().lower() in {
                "[removed]",
                "[deleted]",
            }:
                continue

            ts = created_ts(obj)
            if not is_in_year_month(ts, YEAR, MONTH):
                continue

            elen = len(enc.encode(txt))
            if elen < 10 or elen > 1000:
                continue

            if not passes_keyword_prefilter(patterns, txt):
                continue

            key = obj_key_of(obj, txt)

            text_emb = model.encode([txt], normalize_embeddings=True)
            gen_sim = semantic_score(text_emb, GENERIC_EMB)
            eval_sim = semantic_score(text_emb, EVAL_EMB)
            has_cue = bool(INVESTMENT_RE.search(txt))

            scores[key] = {
                "eval": eval_sim,
                "gen": gen_sim,
                "has_cue": has_cue,
                "obj": obj,
            }

    log.info(f"Filtering and ranking posts...")
    cands_by_day = defaultdict(list)

    for key, s in scores.items():
        txt = text_of(s["obj"])
        elen = len(enc.encode(txt))
        if elen > 500:
            continue

        ts = created_ts(s["obj"])
        if not is_in_year_month(ts, YEAR, MONTH):
            continue

        day = day_key_utc(ts)
        sc = compute_rank_score(s, BASE_THRESHOLD, MARGIN)
        cands_by_day[day].append((sc, ts, key, s["obj"]))

    log.info(f"Selecting top {N_TOP_PER_DAY} posts per day...")
    all_posts = []
    seen = set()

    for day, cands in cands_by_day.items():
        cands.sort(key=lambda x: (x[0], x[1]), reverse=True)

        picked = []
        for sc, ts, key, obj in cands:
            if REQUIRE_POSITIVE and sc <= 0:
                continue
            dk = dedup_key(obj)
            if dk in seen:
                continue
            seen.add(dk)
            picked.append(obj)
            if len(picked) >= N_TOP_PER_DAY:
                break

        all_posts.extend(picked)

    log.info(f"Total posts selected: {len(all_posts)}")

    organized_posts = organize_by_date(all_posts)

    log.info(f"\nPosts organized by date:")
    for date, posts in sorted(organized_posts.items()):
        log.info(f"  {date}: {len(posts)} posts")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(organized_posts, f, indent=4, ensure_ascii=False)

    log.info(f"\nData saved to {OUTPUT_PATH}")
    log.info(f"Total dates: {len(organized_posts)}")
    log.info(f"Total posts: {sum(len(posts) for posts in organized_posts.values())}")


if __name__ == "__main__":
    main()
