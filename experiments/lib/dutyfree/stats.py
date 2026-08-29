"""Statistics helpers. Deliberately small and deliberately tested."""
from __future__ import annotations
import json, math, statistics as _st
from typing import Iterable, Sequence


def load_jsonl(path: str) -> list[dict]:
    """Read a JSONL file, skipping blank lines. Raises on malformed JSON rather
    than silently dropping a record -- a silently dropped record is how a run
    with dead arms looks identical to a complete one."""
    out = []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{n}: malformed JSON: {e}") from None
    return out


def quantile(values: Sequence[float], p: float) -> float:
    """Linear-interpolation quantile. p in [0,1]."""
    if not values:
        raise ValueError("quantile of an empty sequence")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must be in [0,1], got {p}")
    v = sorted(values)
    if len(v) == 1:
        return float(v[0])
    i = (len(v) - 1) * p
    lo = int(math.floor(i))
    hi = min(lo + 1, len(v) - 1)
    return float(v[lo] + (v[hi] - v[lo]) * (i - lo))


def iqr(values: Sequence[float]) -> float:
    return quantile(values, 0.75) - quantile(values, 0.25)


def summary(values: Sequence[float]) -> dict:
    """median/mean/sd/iqr/n in one call, sd=nan for n<2 rather than raising."""
    v = list(values)
    if not v:
        raise ValueError("summary of an empty sequence")
    return dict(n=len(v), mean=_st.mean(v), median=_st.median(v),
                sd=_st.stdev(v) if len(v) > 1 else float("nan"),
                iqr=iqr(v) if len(v) > 1 else 0.0,
                min=min(v), max=max(v))


def alternates(values: Sequence[float], ratio: float = 1.25) -> bool:
    """True if odd- and even-indexed medians differ by more than `ratio`.

    Exists because a period-2 alternation was mistaken for bimodality on
    2026-08-30: median and IQR are the wrong summaries for an alternating
    signal, and nothing in the harness noticed.
    """
    if len(values) < 4:
        return False
    odd = [v for i, v in enumerate(values) if i % 2 == 0]
    even = [v for i, v in enumerate(values) if i % 2 == 1]
    if not odd or not even:
        return False
    a, b = _st.median(odd), _st.median(even)
    if min(a, b) == 0:
        return False
    r = max(a, b) / min(a, b)
    return r > ratio


def uniform(values: Iterable) -> bool:
    """True if every value is identical.

    A verification check whose result is uniform across all records is more
    likely broken than the thing it tests. Call this on check outputs.
    """
    v = list(values)
    return len(v) > 1 and all(x == v[0] for x in v)
