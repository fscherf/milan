SHELL=/bin/bash
PYTHON=python3.11
PYTHON_ENV=env
DOC_ROOT=doc

.PHONY: milan build clean fullclean \
	test ci-test frontend2\
	playwright-install playwright-browser \
	browser demos

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

# tests #######################################################################
test: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	tox $(args)

ci-test: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	MILAN_CI_TEST=1 tox -e py38,py39,py310,py311 $(args)

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

# milan #######################################################################
browser: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/run-browser.py $(args)

demos: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	rm $(DOC_ROOT)/*.gif && \
	$(PYTHON) scripts/run-browser.py \
		--browser=chromium \
		--headless \
		--run-form-demo \
		--capture=$(DOC_ROOT)/form-demo.gif && \
	$(PYTHON) scripts/run-browser.py \
		--browser=chromium \
		--headless \
		--run-multi-window-demo \
		--capture=$(DOC_ROOT)/multi-window-demo.gif
