"""Tests for the shared analysis helpers (stdlib unittest -- no dependencies).

Each test encodes a failure this project actually committed. That is the
selection criterion: a regression test per real mistake, so the same class of
error cannot recur silently. Run with:  make test
"""
import math, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "experiments", "lib"))
from dutyfree import stats, gem5, resctrl  # noqa: E402


class TestStats(unittest.TestCase):
    def test_quantile_matches_hand_computed(self):
        v = [1, 2, 3, 4]
        self.assertEqual(stats.quantile(v, 0.0), 1)
        self.assertEqual(stats.quantile(v, 1.0), 4)
        self.assertAlmostEqual(stats.quantile(v, 0.5), 2.5)

    def test_quantile_rejects_empty_and_bad_p(self):
        self.assertRaises(ValueError, stats.quantile, [], 0.5)
        self.assertRaises(ValueError, stats.quantile, [1], 1.5)

    def test_summary_sd_is_nan_for_one_sample_not_an_exception(self):
        s = stats.summary([42.0])
        self.assertEqual(s["n"], 1)
        self.assertTrue(math.isnan(s["sd"]))

    def test_alternates_detects_period_2(self):
        """2026-08-30: a period-2 alternation was reported as bimodality;
        median and IQR are the wrong summaries for an alternating signal."""
        self.assertTrue(stats.alternates([41, 19, 43, 19, 41, 19]))
        self.assertFalse(stats.alternates([36.0, 35.9, 37.0, 36.3, 36.8, 35.4]))

    def test_uniform_flags_a_checker_that_never_varies(self):
        """A verification result identical across every record is more likely a
        broken checker than a real finding."""
        self.assertTrue(stats.uniform(["?", "?", "?", "?"]))
        self.assertFalse(stats.uniform([True, True, False]))

    def test_load_jsonl_raises_on_malformed_rather_than_dropping(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.jsonl")
            with open(p, "w") as fh: fh.write('{"a":1}\n\nnot json\n')
            with self.assertRaises(ValueError) as e:
                stats.load_jsonl(p)
            self.assertIn("x.jsonl:3", str(e.exception))


class TestResctrl(unittest.TestCase):
    def test_mask_equal_compares_values_not_text(self):
        """2026-08-30: the kernel normalises '00ff'->'ff'; a string compare
        false-alarmed on 24 of 36 valid records."""
        self.assertTrue(resctrl.mask_equal("00ff", "ff"))
        self.assertTrue(resctrl.mask_equal("0001", "1"))
        self.assertFalse(resctrl.mask_equal("00ff", "0f"))
        self.assertFalse(resctrl.mask_equal(None, "ff"))

    def test_schemata_parses_indented_lines(self):
        """2026-08-30: schemata lines are INDENTED on this kernel, so
        startswith('L3:') never matched and every record recorded '?'."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "schemata"), "w") as fh:
                fh.write("    MB:0=2048;1=2048\n      L3:0=00ff;1=ffff\n")
            self.assertEqual(resctrl.schemata_l3(d), "00ff")
            self.assertTrue(resctrl.mask_equal(resctrl.schemata_l3(d), "ff"))


class TestGem5(unittest.TestCase):
    def test_completed_rejects_a_truncated_run(self):
        """F12: a criterion a crashed run can satisfy."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out"); os.mkdir(out)
            with open(out + ".log", "w") as fh: fh.write("warn: something\n")
            ok, why = gem5.completed(out)
            self.assertFalse(ok)
            self.assertIn("Exiting", why)

    def test_completed_accepts_a_finished_run(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out"); os.mkdir(out)
            with open(out + ".log", "w") as fh:
                fh.write("Exiting @ tick 123 because m5_exit\nDONE_0 x\n")
            self.assertTrue(gem5.completed(out)[0])

    def test_realized_size_comes_from_the_log_not_the_name(self):
        """F9, five instances: report the realized size, never the requested."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "t3.0"); os.mkdir(out)
            with open(out + ".log", "w") as fh:
                fh.write("fused: stream 16.00 MB, table requested 3.00 MB, "
                         "REALIZED 2.00 MB (262144 elements)\n")
            self.assertEqual(gem5.realized_table_mb(out), 2.00)

    def test_read_stats_and_config(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out"); os.mkdir(out)
            with open(os.path.join(out, "stats.txt"), "w") as fh:
                fh.write("simTicks 1234 # comment\nsystem.cpu0.numCycles 99\n")
            s = gem5.read_stats(out)
            self.assertEqual(s["simTicks"], 1234)
            self.assertEqual(s["system.cpu0.numCycles"], 99)
            with open(os.path.join(out, "config.ini"), "w") as fh:
                fh.write("[system.cpu0]\ntype=BaseO3CPU\ncmd=/bin/victim 2650 3000000\n")
            self.assertEqual(gem5.config_value(out, "system.cpu0", "type"), "BaseO3CPU")
            self.assertFalse(gem5.declared_streaming(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestArchiveReproducesPublished(unittest.TestCase):
    """The committed archive must reproduce the committed outcome documents.

    This is the campaign-level regression guard: if either the archive or a
    published number drifts, this fails here rather than in review.
    """
    def test_head_to_head_recoveries(self):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        data = os.path.join(root, "experiments", "asplos", "data", "gem5")
        if not os.path.isdir(data):
            self.skipTest("archive not present")
        import collections, re, statistics as st
        published = {"hh": {"h2": 88.51, "cat4": 89.47, "cat10": 88.62},
                     "fh": {"h2": 90.61, "cat4": 89.47, "cat10": 91.04}}
        for pref, want in published.items():
            path = os.path.join(data, f"{pref}_runs.jsonl")
            if not os.path.exists(path):
                self.skipTest(f"{pref} archive absent")
            g = collections.defaultdict(list)
            for r in stats.load_jsonl(path):
                m = re.match(rf"{pref}_(\w+?)_s\d", r["run"])
                if m and r.get("completed") and r.get("cyc_per_access"):
                    g[m.group(1)].append(r["cyc_per_access"])
            q = st.mean(g["qui"]); tw = st.mean(g["wb"]) / q
            for arm, exp in want.items():
                got = 100 * (tw - st.mean(g[arm]) / q) / (tw - 1)
                self.assertAlmostEqual(got, exp, delta=0.02,
                                       msg=f"{pref}/{arm}: archive {got:.2f} vs published {exp}")
