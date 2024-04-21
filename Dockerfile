FROM ubuntu:focal

ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHON_VERSIONS="3.7 3.8 3.9 3.10 3.11 3.12"
ARG PYTHON_VERSION="3.11"

# setup /milan
RUN mkdir /milan

COPY ./milan /milan/milan
COPY ./bin /milan/bin
COPY ./pyproject.toml /milan/pyproject.toml

# Ubuntu dependencies
RUN apt update && \
	apt-get install -y software-properties-common && \
	add-apt-repository ppa:deadsnakes/ppa && \
	apt update && \
	for version in ${PYTHON_VERSIONS}; do \
		apt install -y \
			python${version} \
			python${version}-dev \
			python${version}-venv && \
		python${version} -m ensurepip --upgrade \
	; done

# python dependencies
RUN python${PYTHON_VERSION} -m pip install /milan[docker]

# setup playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN python${PYTHON_VERSION} -m playwright install-deps
RUN python${PYTHON_VERSION} -m playwright install

RUN chmod -R 777 /ms-playwright

# setup user
RUN adduser milan
RUN chown -R milan:milan /milan

USER milan
