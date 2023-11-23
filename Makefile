SHELL=/bin/bash
PYTHON=python3.11
PYTHON_ENV=env/$(shell hostname)/$(PYTHON)

.PHONY: milan build clean fullclean \
	application chromium headless-chromium firefox headless-firefox


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

frontend: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	python -m milan.frontend.server --port=8080

application: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/demo-application.py $(args)

chromium: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/test-script.py --browser=chromium $(args)

headless-chromium: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/test-script.py --browser=chromium --headless $(args)

firefox: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/test-script.py --browser=firefox $(args)

headless-firefox: | $(PYTHON_ENV)
	. $(PYTHON_ENV)/bin/activate && \
	$(PYTHON) scripts/test-script.py --browser=firefox --headless $(args)
