# Thin wrapper for Mac/Linux; tasks.py holds the real commands (works on Windows too).
PY ?= python

.PHONY: setup data report-weather report-physics simulate train validate assumptions test app api
setup data report-weather report-physics simulate train validate assumptions test app api:
	$(PY) tasks.py $@
