.PHONY: api web demo test check-web check-demo check

PYTHON ?= .venv/bin/python

api:
	PYTHONPATH=backend/src $(PYTHON) -m sgtrace_app

web:
	npm --prefix frontend run dev

demo:
	npm --prefix product-demo run start

test:
	$(PYTHON) -m pytest -q

check-web:
	npm --prefix frontend test
	npm --prefix frontend run build

check-demo:
	npm --prefix product-demo test
	npm --prefix product-demo run build

check: test check-web check-demo
