.PHONY: test smoke run clean

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

smoke:
	PYTHONPATH=src python3 -m rfdi.cli run --config configs/experiments/core.json

run: test smoke

clean:
	@echo "No destructive clean target: caches are fingerprinted and preserved."
