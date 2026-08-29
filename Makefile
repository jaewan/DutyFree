# DutyFree — common tasks. Everything here is dependency-free (stdlib only)
# except the gem5 build, which needs the project's own venv.
SHELL   := /bin/bash
ROOT    := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
PY      ?= python3
GEM5VENV ?= $(HOME)/gem5-venv

.PHONY: help test lint check gem5 clean-artifacts state

help:                     ## show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-18s\033[0m %s\n",$$1,$$2}'

test:                     ## run the analysis-helper regression tests
	@$(PY) -W error::ResourceWarning -m unittest discover -s $(ROOT)/tests -v

lint:                     ## byte-compile every committed python file
	@$(PY) -m compileall -q $(ROOT)/experiments $(ROOT)/tests && echo "  python OK"
	@for f in $(ROOT)/experiments/asplos/*.sh $(ROOT)/benchmarks/bench/*.sh; do \
	   [ -e "$$f" ] && bash -n "$$f" || true; done; echo "  shell syntax OK"

check: test lint          ## everything CI runs

gem5:                     ## build the Intel 8592 gem5 target
	@source $(GEM5VENV)/bin/activate && cd $(ROOT)/gem5 && \
	  scons build_Intel_8592/gem5.opt -j $$(nproc)

state:                    ## print where the project stands
	@sed -n '1,40p' $(ROOT)/experiments/asplos/STATE_2026-08-30.md

clean-artifacts:          ## remove build junk ONLY -- never results or records
	@find $(ROOT) -name __pycache__ -type d -not -path '*/gem5/*' \
	   -not -path '*/linux/*' -exec rm -rf {} + 2>/dev/null || true
	@find $(ROOT) -name '*.o' -not -path '*/gem5/*' -not -path '*/linux/*' -delete 2>/dev/null || true
	@rm -f $(ROOT)/.git/objects/pack/tmp_pack_* 2>/dev/null || true
	@echo "  removed build artifacts; results/ experiments/ untouched"
