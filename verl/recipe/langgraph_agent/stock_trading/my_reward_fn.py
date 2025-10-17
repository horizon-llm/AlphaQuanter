import json
import os
import re
import uuid
from collections import Counter

import numpy as np
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")


def extract_answers(text: str):
    # return re.findall(r"####\s*(BUY|SELL|HOLD)", text)
    matches = re.findall(
        r"<answer>\s*(BUY|SELL|HOLD)\s*</answer>", text, flags=re.IGNORECASE
    )
    return matches[-1].lower() if matches else ""


def count_duplicate_calls(calls: list[dict]):
    calls_as_str = [json.dumps(c, sort_keys=True) for c in calls]
    counter = Counter(calls_as_str)

    duplicates = [v for k, v in counter.items() if v > 1]

    return sum(duplicates) - len(duplicates)


def count_diff_calls(calls: list[dict]):
    calls_as_str = [c.get("name", "") for c in calls]
    return list(set(calls_as_str))


def count_calls(calls: list[dict]):
    calls_as_str = [c.get("name", "") for c in calls]
    return len(calls_as_str)


def extract_tool_calls_simple(text: str):
    pattern = r"<tool_call>(.*?)</tool_call>"
    blocks = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    reward = 0
    out = []
    for blk in blocks:
        blk_stripped = blk.strip()
        try:
            maybe = json.loads(blk_stripped)
            if isinstance(maybe, list):
                tool_list = [o for o in maybe if isinstance(o, dict)]
                reward -= len(tool_list) ** 2 / 10
                out.extend(tool_list)
                continue
        except Exception:
            pass

        for line in blk.splitlines():
            line = line.strip()
            if not line or not line.startswith("{") or not line.endswith("}"):
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                pass
    return out, reward


def random_fn(data_source, solution_str, ground_truth, extra_info=None):
    import random

    return random.uniform(-1, 1)


def score_response(text: str):
    global enc
    match = re.search(r"^(.*?)<tool_call>", text, re.S)

    score = 0
    if match:
        before_tool = match.group(1)
        length = len(enc.encode(before_tool))
        if "<think>" in before_tool and "</think>" in before_tool:
            score += 0.005
        if length >= 200 and length <= 600:
            score += 0.1
        else:
            score += 0.05 - 0.01 * (length - 200) * (length - 600) / 30000
    else:
        score += 0.001

    pattern = r"\nassistant\n(.*?)<tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)

    results = []
    cnt = 0
    for idx, m in enumerate(matches, 1):
        if m.strip():
            results.append((idx, "Good (+1)", m.strip()[:60] + "..."))
            length = len(enc.encode(m.strip()))
            if "<think>" in m and "</think>" in m:
                score += 0.005
            if length >= 200 and length <= 600:
                score += 0.1
            else:
                score += 0.05 - 0.01 * (length - 200) * (length - 600) / 30000
            cnt += 1
        else:
            results.append((idx, "Bad (-1)", "[Empty]"))
            score += 0.001
            cnt += 1

    return score, results


def new_reward_fn(data_source, solution_str, ground_truth, extra_info=None):
    action = extract_answers(solution_str).lower()
    r = float(ground_truth)

    result_reward = 0
    format_reward = 0
    tool_reward = 0

    THRESHOLD = 1.5
    if abs(r) <= THRESHOLD:
        label = "hold"
    elif r > 0:
        label = "buy"
    elif r < 0:
        label = "sell"

    if not action in ["buy", "sell", "hold"]:
        format_reward -= 1.0
        result_reward = -1.0
    else:
        if r > THRESHOLD:
            if action == "buy":
                result_reward = 1
            elif action == "hold":
                result_reward = -0.75
            else:
                result_reward = -1
        elif abs(r) <= THRESHOLD:
            if action == "hold":
                result_reward = 1
            elif action == "buy":
                result_reward = -0.5
            else:
                result_reward = -0.5
        else:
            if action == "sell":
                result_reward = 1
            elif action == "hold":
                result_reward = -0.75
            else:
                result_reward = -1
    try:
        res_score, _ = score_response(solution_str)
        format_reward += res_score

        valid_analysis = 0

    except Exception as e:
        print(e)
        format_reward = 0

    try:
        calls, tool_reward = extract_tool_calls_simple(solution_str)
        for j in calls:
            arg_date = None
            try:
                arg_date = j["arguments"]["curr_date"]
            except Exception as e:
                tool_reward -= 0.1
                continue
            if arg_date > extra_info["date"]:
                result_reward = -1
                tool_reward -= 50.0

        dup_calls = count_duplicate_calls(calls)
        num_calls = count_calls(calls)

        tool_reward -= dup_calls * 0.05
        if num_calls <= 4 or num_calls > 8:
            tool_reward -= abs(num_calls - extra_info["expected_tool_calls"]) * 1
        calls = count_diff_calls(calls)
        if not "get_market_data" in calls:
            tool_reward -= 0.1

        if not "get_stock_indicators" in calls:
            tool_reward -= 0.1
    except Exception as e:
        tool_reward -= 0.1

    return {
        "score": 5 * result_reward + format_reward + tool_reward,
        "result_score": result_reward,
        "format_score": format_reward,
        "tool_score": tool_reward,
        "acc": float(action == label),
    }


if __name__ == "__main__":
    pass
