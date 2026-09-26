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
	make pkg-install

sync-deps: pkg-install ## Install/update dev dependency group
	$(PIP) install --group dev

format:
	$(PYTHON) -m black plugins packages out
	$(PYTHON) -m isort plugins packages out

c4d-test:
	@cls
	@echo "Running C4D tests..."
	@set "JB_ENV=test" && \
	set "g_additionalModulePath=$(C4D_PLUGIN_PATH)" && \
	"$(C4D_PYTHON)" "$(CURDIR)/tests/integration/test_flows.py" || exit /B 0

blend-run:
	@echo "Running Blender..."
	@set "BLENDER_USER_SCRIPTS=$(ROOT_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(ADDON_NAME)

blend-dev-run: ## Run Blender with the development addon (editable sources)
	@echo "Running Blender (dev)..."
	@set "BLENDER_USER_SCRIPTS=$(ROOT_DEV_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(DEV_ADDON_NAME)


blend-test:
	@cls
	@echo "Running Blender tests..."
	@set "JB_ENV=test" && \
	set "BLENDER_USER_SCRIPTS=$(ROOT_ADDONS_PATH)" && \
	"$(BLENDER_PATH)" --addons $(ADDON_NAME) --python "$(CURDIR)/tests/integration/test_flows.py" || exit /B 0
