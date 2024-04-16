SHELL=/bin/bash
PYTHON=python3.11
PYTHON_ENV=env
DOC_ROOT=doc

.PHONY: milan build clean fullclean shell \
	dist _release \
	test ci-test frontend demos \
	playwright-install playwright-browser

all: browser

# docker ######################################################################
milan:
	docker compose run --service-ports milan $(args)

build:
	docker compose build --no-cache

# python ######################################################################
clean:
	rm -rf $(PYTHON_ENV)

fullclean:
	rm -rf env

$(PYTHON_ENV): pyproject.toml
	rm -rf $(PYTHON_ENV) && \
	$(PYTHON) -m venv $(PYTHON_ENV) && \
	. $(PYTHON_ENV)/bin/activate && \
	pip install pip --upgrade && \
	pip install -e .[dev]

shell: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	rlpython $(args)

# packaging ###################################################################
dist: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	rm -rf dist *.egg-info && \
	$(PYTHON) -m build

_release: dist
	. $(PYTHON_ENV)/bin/activate && \
	twine upload --config-file ~/.pypirc.fscherf dist/*

# tests #######################################################################
test:
	docker compose run milan tox $(args)

ci-test:
	docker compose run milan MILAN_CI_TEST=1 tox -e py38,py39,py310,py311 $(args)

demos:
	$(MAKE) test args="-- -k demos"

frontend: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	python -m milan.frontend.server --port=8080

# playwright ##################################################################
playwright-install: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	playwright install $(args)

playwright-browser: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/run-playwright.py
