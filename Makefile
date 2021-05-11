VIRTUAL_ENV ?= env

all: $(VIRTUAL_ENV)

.PHONY: help
# target: help - Display callable targets
help:
	@egrep "^# target:" [Mm]akefile

.PHONY: clean
# target: clean - Display callable targets
clean:
	@rm -rf example/proto/*.py
	@rm -rf tests/proto/*.py
	@rm -rf build/ dist/ docs/_build *.egg-info
	@find $(CURDIR) -name "*.py[co]" -delete
	@find $(CURDIR) -name "*.orig" -delete
	@find $(CURDIR)/$(MODULE) -name "__pycache__" | xargs rm -rf

# ==============
#  Bump version
# ==============

.PHONY: release
VERSION?=minor
# target: release - Bump version
release: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/bump2version $(VERSION)
	@git checkout master
	@git merge develop
	@git checkout develop
	@git push origin develop master
	@git push --tags

.PHONY: minor
minor: release

.PHONY: patch
patch:
	make release VERSION=patch

.PHONY: major
major:
	make release VERSION=major

# =============
#  Development
# =============

$(VIRTUAL_ENV): setup.cfg
	@[ -d $(VIRTUAL_ENV) ] || python -m venv $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pip install -e .[tests,build,example]
	@touch $(VIRTUAL_ENV)

.PHONY: test t
# target: test - Runs tests
test t: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/pytest tests

.PHONY: mypy
mypy: $(VIRTUAL_ENV)
	@$(VIRTUAL_ENV)/bin/mypy muffin_grpc

.PHONY: example
example: build $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/uvicorn --reload example:app

.PHONY: example-grpc
example-grpc: $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/muffin example:app --aiolib=asyncio grpc_server --build-proto

.PHONY: build
build: $(VIRTUAL_ENV) clean
	$(VIRTUAL_ENV)/bin/muffin example:app grpc_build
