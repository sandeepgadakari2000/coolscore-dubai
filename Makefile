# Thin wrapper for Mac/Linux; tasks.py holds the real commands (works on Windows too).
PY ?= python

.PHONY: setup data report-weather report-physics simulate train validate assumptions climate test app api launch
setup data report-weather report-physics simulate train validate assumptions climate test app api launch:
	$(PY) tasks.py $@
