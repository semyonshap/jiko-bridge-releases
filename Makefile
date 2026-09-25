SYSTEM := $(if $(filter Windows_NT,$(OS)),Windows,$(shell uname -s))

ifeq ($(SYSTEM),Windows)
    include MakeWin.mk
else ifeq ($(SYSTEM),Darwin)
    -include MakeMac.mk
else
    -include MakeLinux.mk
endif

.PHONY: help venv blend-test c4d-test

include MakePkg.mk

help: ## Show this help message
	@awk '/^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, substr($$0, index($$0, "##")+3)}' $(MAKEFILE_LIST)

venv:
	python -m venv venv
	$(PYTHON) -m pip install --group dev
	$(PIP) install -r requirements.txt

sync-deps: ## Install/update dev dependency group
	$(PIP) install --group dev

format:
	$(PYTHON) -m black plugins packages
	$(PYTHON) -m isort plugins packages

lint:
	make blend-lint
	make pkg-lint
	make diff-all

typecheck:
	make blend-typecheck
	make pkg-typecheck

c4d-test:
	@cls
	@echo "Running C4D tests..."
	@set "JB_ENV=test" && \
	set "g_additionalModulePath=$(C4D_PLUGIN_PATH)" && \
	"$(C4D_PYTHON)" "$(CURDIR)/tests/integration/test_flows.py" || exit /B 0

blend:
	make blend-lint
	make blend-typecheck
	make blend-test

blend-run:
	@echo "Running Blender..."
	@set "BLENDER_USER_SCRIPTS=$(ROOT_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(ADDON_NAME)

blend-lint:
	$(PYTHON) -m pylint --rcfile=pyproject.toml plugins/blender/addons/$(ADDON_NAME) tests/integration

blend-typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/blender/addons/$(ADDON_NAME) tests/integration


blend-test:
	@cls
	@echo "Running Blender tests..."
	@set "JB_ENV=test" && \
	set "BLENDER_USER_SCRIPTS=$(ROOT_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(ADDON_NAME) --python "$(CURDIR)/tests/integration/test_flows.py" || exit /B 0
