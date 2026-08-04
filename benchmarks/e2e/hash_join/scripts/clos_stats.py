"""Shared stats helpers for the CLOS-split experiment scripts.

CI is a percentile bootstrap of the MEDIAN (not a normal-approximation CI of
the mean), so the reported interval brackets the same statistic being
reported as the point estimate. With a normal-approx CI on the mean, a
skewed sample can print a median that falls outside its own "95% CI".
"""
import random
import statistics


def median_ci95(vals, seed=1234, boots=2000):
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(vals)
    boot_medians = []
    for _ in range(boots):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        boot_medians.append(statistics.median(sample))
    boot_medians.sort()
    lo_idx = int(0.025 * boots)
    hi_idx = int(0.975 * boots) - 1
    return (boot_medians[lo_idx], boot_medians[hi_idx])


def cov(vals):
    if len(vals) < 2:
        return float("nan")
    mean = statistics.mean(vals)
    if mean == 0:
        return float("nan")
    return statistics.stdev(vals) / mean


def summarize_metric(vals):
    lo, hi = median_ci95(vals)
    return {
        "median": statistics.median(vals),
        "cov": cov(vals),
        "ci95_lo": lo,
        "ci95_hi": hi,
        "n": len(vals),
    }
