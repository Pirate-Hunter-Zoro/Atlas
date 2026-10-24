#!/usr/bin/env python3
"""P0 tests 8b/9 + section B: single-stream speed, TTFT with a realistic agent
preamble, and a concurrency sweep against an OpenAI-shaped endpoint."""
import argparse, asyncio, json, os, statistics, time
import aiohttp
from transformers import AutoTokenizer


def build_preamble(tok, target_tokens):
    """A filler system prompt of ~target_tokens tokens, shaped like a tool catalogue."""
    unit = ("You have access to a tool named read_file which takes a single parameter "
            "path, a string naming a file relative to the repository root, and returns "
            "the file's contents as text. Prefer it over guessing. ")
    ids = tok(unit, add_special_tokens=False)["input_ids"]
    reps = max(1, target_tokens // max(1, len(ids)))
    text = unit * reps
    ids = tok(text, add_special_tokens=False)["input_ids"][:target_tokens]
    return tok.decode(ids)


async def one_request(sess, url, model, key, system, prompt, max_tokens):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.0, "stream": True,
        "stream_options": {"include_usage": True},
    }
    hdr = {"Content-Type": "application/json"}
    if key:
        hdr["Authorization"] = f"Bearer {key}"
    t0 = time.perf_counter()
    ttft = None
    n_out = 0
    usage = None
    async with sess.post(url, json=body, headers=hdr) as r:
        r.raise_for_status()
        async for raw in r.content:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices", []):
                piece = ch.get("delta", {}).get("content")
                if piece:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    n_out += 1
    t1 = time.perf_counter()
    if usage and usage.get("completion_tokens"):
        n_out = usage["completion_tokens"]
    decode_s = (t1 - t0) - (ttft or 0.0)
    return {
        "ttft_s": ttft, "total_s": t1 - t0, "out_tokens": n_out,
        "decode_tok_s": (n_out / decode_s) if decode_s > 0 and n_out else None,
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
    }


async def sweep(url, model, key, system, prompt, max_tokens, levels, out):
    results = {}
    conn = aiohttp.TCPConnector(limit=64)
    timeout = aiohttp.ClientTimeout(total=1800)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as sess:
        # warm the prefix cache and the CUDA graphs
        await one_request(sess, url, model, key, system, "Say OK.", 8)
        for c in levels:
            t0 = time.perf_counter()
            rs = await asyncio.gather(*[
                one_request(sess, url, model, key, system, prompt, max_tokens)
                for _ in range(c)])
            wall = time.perf_counter() - t0
            per = [r["decode_tok_s"] for r in rs if r["decode_tok_s"]]
            ttfts = [r["ttft_s"] for r in rs if r["ttft_s"]]
            tot_out = sum(r["out_tokens"] for r in rs)
            results[c] = {
                "concurrency": c,
                "per_session_tok_s_median": statistics.median(per) if per else None,
                "per_session_tok_s_min": min(per) if per else None,
                "aggregate_tok_s": tot_out / wall if wall else None,
                "ttft_s_median": statistics.median(ttfts) if ttfts else None,
                "ttft_s_max": max(ttfts) if ttfts else None,
                "wall_s": wall,
                "out_tokens_total": tot_out,
                "prompt_tokens": rs[0].get("prompt_tokens"),
            }
            print(json.dumps(results[c]), flush=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--api-key", default=os.environ.get("FLEET_API_KEY", ""))
    ap.add_argument("--preamble-tokens", type=int, default=15000)
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--levels", default="1,2,4,6,8")
    ap.add_argument("--out", default="bench_tier1.json")
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.tokenizer)
    system = build_preamble(tok, a.preamble_tokens)
    prompt = ("Write a Python function that merges two sorted lists of integers into "
              "one sorted list without using sorted(). Explain your reasoning briefly, "
              "then give the function.")
    levels = [int(x) for x in a.levels.split(",")]
    asyncio.run(sweep(a.base_url + "/chat/completions", a.model, a.api_key,
                      system, prompt, a.max_tokens, levels, a.out))


if __name__ == "__main__":
    main()
