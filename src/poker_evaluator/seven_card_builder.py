"""Vectorized exhaustive dictionary builder, bounded-memory and resumable."""
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations_with_replacement
import json
from math import comb
from pathlib import Path
import platform
from random import Random
from time import perf_counter

import numpy as np

from .cards import Card
from .evaluate7 import evaluate7
from .rank_table import load_rank_table, rank_seven_cards
from .seven_card_dictionary import (HAND_COUNT, DATA_FILENAME, MANIFEST_FILENAME,
    SevenCardRankDictionary, file_sha256, index_cards, hand_index, CATEGORY_NAMES)

FORMAT = "poker-seven-card-colex-u16le-v1"
EXPECTED_CATEGORIES = (23294460, 58627800, 31433400, 6461620, 6180020,
                       4047644, 3473184, 224848, 41584)
CHOOSE = np.array([[comb(n, k) if n >= k else 0 for k in range(8)] for n in range(53)], dtype=np.int64)


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temp.replace(path)


def unrank_batch(start, stop):
    """Inverse combinadic, returns increasing physical card IDs for every index."""
    remaining = np.arange(start, stop, dtype=np.int64)
    ids = np.empty((stop-start, 7), dtype=np.uint8)
    for k in range(7, 0, -1):
        values = np.searchsorted(CHOOSE[:, k], remaining, side="right") - 1
        ids[:, k-1] = values
        remaining -= CHOOSE[values, k]
    return ids


def rank_key(ranks):
    return sum(1 << (4*r) for r in ranks)


def prepare_tables():
    """Only 49,205 rank multisets; evaluate these through the ORIGINAL evaluator.

    Round-robin suits guarantee no flush and no duplicate card, preserving all
    non-flush possibilities. Actual flushes are handled independently by suit mask.
    """
    ordered = sorted(load_rank_table(), reverse=True)
    rank_map = {value: i+1 for i, value in enumerate(ordered)}
    keys, ranks = [], []
    for values in combinations_with_replacement(range(13), 7):
        if max(Counter(values).values()) > 4:
            continue
        cards = [Card(r+2, i % 4) for i, r in enumerate(values)]
        keys.append(rank_key(values))
        ranks.append(rank_map[evaluate7(cards)])
    order = np.argsort(np.asarray(keys, dtype=np.uint64))
    keys = np.asarray(keys, dtype=np.uint64)[order]
    ranks = np.asarray(ranks, dtype=np.uint16)[order]
    flush = np.full(8192, 7463, dtype=np.uint16)
    for mask in range(8192):
        if not 5 <= mask.bit_count() <= 7:
            continue
        values = [i+2 for i in range(12, -1, -1) if mask & (1 << i)]
        high = next((h for h in range(14, 5-1, -1)
                     if all(r in values for r in range(h-4, h+1))), None)
        if high is None and {14, 2, 3, 4, 5}.issubset(values):
            high = 5
        value = (8, high) if high is not None else (5, *values[:5])
        flush[mask] = rank_map[value]
    return keys, ranks, flush, ordered


def evaluate_batch(ids, tables):
    keys, nonflush, flush, _ = tables
    rank_ids = (ids // 4).astype(np.uint64)
    key = np.left_shift(np.uint64(1), 4*rank_ids).sum(axis=1, dtype=np.uint64)
    positions = np.searchsorted(keys, key)
    result = nonflush[positions].copy()
    suits = ids % 4
    for suit in range(4):
        selected = np.flatnonzero((suits == suit).sum(axis=1) >= 5)
        if not len(selected):
            continue
        masks = np.bitwise_or.reduce(np.where(suits[selected] == suit,
            np.left_shift(np.uint64(1), rank_ids[selected]), np.uint64(0)), axis=1)
        result[selected] = np.minimum(result[selected], flush[masks])
    return result


def verify(directory, *, oracle_samples=10000, seed=20261028, _allow_pending=False):
    directory = Path(directory)
    if type(oracle_samples) is not int or not 0 <= oracle_samples <= HAND_COUNT:
        raise ValueError("Invalid oracle sample count")
    manifest = json.loads((directory / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("hand_count") != HAND_COUNT:
        raise ValueError("Invalid dictionary manifest")
    if not manifest.get("complete") and not _allow_pending:
        raise ValueError("Dictionary has not completed verification")
    if (directory / DATA_FILENAME).stat().st_size != HAND_COUNT*2:
        raise ValueError("Unexpected data size")
    if file_sha256(directory / DATA_FILENAME) != manifest["sha256"]:
        raise ValueError("Dictionary checksum mismatch")
    ordered = tuple(tuple(v) for v in manifest["rank_values"])
    if ordered != tuple(sorted(load_rank_table(), reverse=True)):
        raise ValueError("Rank definitions differ from existing evaluator")
    counts = np.zeros(9, dtype=np.int64)
    distinct = np.zeros(7463, dtype=np.bool_)
    category = np.array([0] + [v[0] for v in ordered], dtype=np.uint8)
    raw = np.memmap(directory / DATA_FILENAME, dtype="<u2", mode="r")
    try:
        for start in range(0, HAND_COUNT, 1_000_000):
            values = np.asarray(raw[start:start+1_000_000])
            if np.any((values < 1) | (values > 7462)):
                raise ValueError("Invalid rank found in full scan")
            counts += np.bincount(category[values], minlength=9)
            distinct[values] = True
        if tuple(counts) != EXPECTED_CATEGORIES:
            raise ValueError(f"Category frequencies disagree: {counts.tolist()}")
        rng = Random(seed)
        indices = [0, HAND_COUNT-1] + rng.sample(range(HAND_COUNT), oracle_samples)
        for index in indices:
            cards = index_cards(index)
            if hand_index(cards) != index or int(raw[index]) != rank_seven_cards(list(cards)):
                raise ValueError(f"Oracle mismatch at index {index}")
        return dict(complete_scan=True, hand_count=HAND_COUNT, distinct_ranks=int(distinct.sum()),
                    category_counts=dict(zip(CATEGORY_NAMES, map(int, counts))),
                    oracle_checks=len(indices), oracle_seed=seed, sha256=manifest["sha256"],
                    verified_at=datetime.now(timezone.utc).isoformat())
    finally:
        del values
        del raw


def build(directory, *, chunk_size=250000, oracle_samples=10000, seed=20261028):
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("Positive chunk size required")
    if not isinstance(oracle_samples, int) or not 0 <= oracle_samples <= HAND_COUNT:
        raise ValueError("Invalid oracle sample count")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / DATA_FILENAME
    manifest_path = directory / MANIFEST_FILENAME
    if final.exists() and manifest_path.exists():
        report = verify(directory, oracle_samples=oracle_samples, seed=seed, _allow_pending=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["complete"] = True
        atomic_json(manifest_path, manifest)
        atomic_json(directory / "verification.json", report)
        return report
    partial = directory / (DATA_FILENAME + ".partial")
    progress_path = directory / "build_progress.json"
    if final.exists():
        raise ValueError("Data exists without a completed manifest; preserve it and choose another directory")
    started = perf_counter()
    print("Preparing 49,205 rank patterns using existing evaluate7...", flush=True)
    tables = prepare_tables()
    start = 0
    if partial.exists():
        progress = json.loads(progress_path.read_text())
        if (progress.get("format") != FORMAT or progress.get("rank_values") != [list(v) for v in tables[3]]
                or partial.stat().st_size != HAND_COUNT * 2):
            raise ValueError("Incompatible partial dictionary")
        start = progress["completed"]
        if type(start) is not int or not 0 <= start <= HAND_COUNT:
            raise ValueError("Invalid resume offset")
        mode = "r+"
    else:
        mode = "w+"
    raw = np.memmap(partial, dtype="<u2", mode=mode, shape=(HAND_COUNT,))
    progress = dict(format=FORMAT, rank_values=tables[3], completed=start)
    atomic_json(progress_path, progress)
    try:
        for begin in range(start, HAND_COUNT, chunk_size):
            end = min(begin+chunk_size, HAND_COUNT)
            raw[begin:end] = evaluate_batch(unrank_batch(begin, end), tables)
            raw.flush()
            progress["completed"] = end
            atomic_json(progress_path, progress)
            if begin == start or end == HAND_COUNT or end // 5_000_000 != begin // 5_000_000:
                print(f"{end:,}/{HAND_COUNT:,} ({100*end/HAND_COUNT:.1f}%) elapsed={perf_counter()-started:.1f}s", flush=True)
    finally:
        del raw
    partial.replace(final)
    manifest = dict(format=FORMAT, complete=False, hand_count=HAND_COUNT,
                    bytes=HAND_COUNT*2, card_encoding="4*(rank-2)+suit; suits=s,c,h,d",
                    index="sum(C(sorted_card_id[i],i+1) for i in range(7))",
                    rank_order="1=strongest;7462=weakest", rank_values=tables[3],
                    sha256=file_sha256(final), python=platform.python_version(), numpy=np.__version__,
                    built_at=datetime.now(timezone.utc).isoformat(), build_seconds=perf_counter()-started)
    atomic_json(manifest_path, manifest)
    print("Full-table scan and independent original-evaluator checks...", flush=True)
    report = verify(directory, oracle_samples=oracle_samples, seed=seed, _allow_pending=True)
    manifest["complete"] = True
    atomic_json(manifest_path, manifest)
    atomic_json(directory / "verification.json", report)
    return report
