# DutyFree benchmarks — top-level Makefile
#
# Targets:
#   make build        — build all C benchmark binaries
#   make figures      — regenerate paper figures from bundled data/
#   make reproduce    — reproduce measurements (requires EMR + SPR hardware + root)
#   make check        — verify environment and binary sanity
#   make clean        — remove built binaries and generated figures

PYTHON    ?= python3
BENCH_DIR  = bench
FIG_DIR    = figures

.PHONY: all build figures reproduce check clean

all: build figures

# ── build ─────────────────────────────────────────────────────────────────────
build:
	$(MAKE) -C $(BENCH_DIR)

# ── figures (from bundled data) ───────────────────────────────────────────────
figures: _pip_check
	@mkdir -p $(FIG_DIR)
	$(PYTHON) analysis/plot_wss.py     --data-dir data/ --out $(FIG_DIR)/
	$(PYTHON) analysis/plot_cat_mba.py --data-dir data/ --out $(FIG_DIR)/
	@echo ""
	@echo "Figures written to $(FIG_DIR)/"

_pip_check:
	@$(PYTHON) -c "import matplotlib, numpy" 2>/dev/null || \
	  (echo "Missing Python deps. Run: pip install -r analysis/requirements.txt" && exit 1)

# ── reproduce (requires hardware) ────────────────────────────────────────────
reproduce: build check
	@echo ""
	@echo "=== EMR WSS sweep ==="
	$(PYTHON) experiments/wss_sweep.py --platform emr --sweep all --out-dir experiments/results/emr/
	@echo ""
	@echo "=== SPR WSS sweep (if on SPR, else skip) ==="
	@echo "  python3 experiments/wss_sweep.py --platform spr --sweep all"
	@echo ""
	@echo "=== CAT/MBA experiment (EMR, requires root + resctrl) ==="
	@echo "  sudo bash experiments/cat_mba_driver.sh"

# ── check ─────────────────────────────────────────────────────────────────────
check:
	@echo "=== Checking binaries ==="
	@for b in bench/victim/pointer_chase_nocap bench/aggressor/stream_wb \
	           bench/aggressor/forced_turnover; do \
	  if [ -f "$$b" ]; then echo "  OK  $$b"; \
	  else echo "  MISSING $$b — run: make build" && exit 1; fi; \
	done
	@echo "=== Checking data files ==="
	@for f in data/emr_cxl8.csv data/emr_local4.csv \
	           data/catmba_s2_cxl8_baseline.csv data/catmba_s3_cat_3ways.csv; do \
	  if [ -f "$$f" ]; then echo "  OK  $$f"; \
	  else echo "  MISSING $$f"; fi; \
	done
	@echo "=== Checking Python deps ==="
	@$(PYTHON) -c "import matplotlib; import numpy; print('  OK  matplotlib', matplotlib.__version__, '  numpy', numpy.__version__)"
	@echo "=== Check complete ==="

# ── clean ─────────────────────────────────────────────────────────────────────
clean:
	$(MAKE) -C $(BENCH_DIR) clean
	rm -rf $(FIG_DIR)
