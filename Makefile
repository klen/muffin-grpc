VIRTUAL_ENV ?= .venv

# =============
#  Development
# =============

$(VIRTUAL_ENV): poetry.lock
	@[ -d $(VIRTUAL_ENV) ] || python -m venv $(VIRTUAL_ENV)
	@poetry install --with tests,dev
	@poetry run pre-commit install --hook-type pre-push
	@touch $(VIRTUAL_ENV)

.PHONY: test t
# target: test - Runs tests
test t: $(VIRTUAL_ENV)
	@poetry run pytest tests

.PHONY: mypy
mypy: $(VIRTUAL_ENV)
	@poetry run mypy muffin_grpc

.PHONY: example
example: build $(VIRTUAL_ENV)
	@poetry run uvicorn --reload example:app

.PHONY: example-grpc
example-grpc: $(VIRTUAL_ENV)
	@poetry run muffin example:app --aiolib=asyncio grpc_server --build-proto

.PHONY: build
build: $(VIRTUAL_ENV) clean
	@poetry run muffin example:app grpc_build

# ==============
#  Bump version
# ==============

.PHONY: release
VPART ?= minor
# target: release - Bump version
release: $(VIRTUAL_ENV)
	@git checkout develop
	@git pull
	@git checkout master
	@git pull
	@git merge develop
	@poetry version $(VPART)
	@git commit -am "Bump version: `poetry version -s`"
	@git tag `poetry version -s`
	@git checkout develop
	@git merge master
	@git push origin develop master
	@git push --tags

.PHONY: minor
minor: release

.PHONY: patch
patch:
	make release VPART=patch

.PHONY: major
major:
	make release VPART=major
