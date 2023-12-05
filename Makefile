SHELL=/bin/bash
PYTHON=python3.11
PYTHON_ENV=env/$(shell hostname)/$(PYTHON)
DOC_ROOT=doc

.PHONY: milan build clean fullclean \
	application chromium headless-chromium firefox headless-firefox demos


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
	MILAN_CI_TEST=1 tox $(args)

frontend: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	python -m milan.frontend.server --port=8080

# browser #####################################################################
install-browser: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	playwright install $(args)

chromium: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/run-browser.py --browser=chromium $(args)

headless-chromium: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/run-browser.py --browser=chromium --headless $(args)

firefox: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/run-browser.py --browser=firefox $(args)

headless-firefox: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/run-browser.py --browser=firefox --headless $(args)

# demos #######################################################################
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
