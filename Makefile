# Определение ОС
SYSTEM := $(if $(filter Windows_NT,$(OS)),Windows,$(shell uname -s))

# Подключаем нужный конфиг в зависимости от системы
ifeq ($(SYSTEM),Windows)
    include MakeWin.mk
else ifeq ($(SYSTEM),Darwin)
    -include MakeMac.mk
else
    -include MakeLinux.mk
endif

.PHONY: help venv pkg pkg-lint pkg-typecheck pkg-install blend-test c4d-test

# Все пакеты в packages/: каталоги, рядом с которыми лежит pyproject.toml
PKG_PATHS := $(patsubst %/pyproject.toml,%,$(wildcard packages/*/pyproject.toml))

help: ## Show this help message
	@awk '/^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, substr($$0, index($$0, "##")+3)}' $(MAKEFILE_LIST)

venv:
	python -m venv venv
	$(PYTHON) -m pip install --group dev
	$(PIP) install -r requirements.txt

sync-deps: ## Install/update dev dependency group
	$(PIP) install --group dev

pkg: ## Lint and typecheck every package in packages/
	make pkg-lint
	make pkg-typecheck

pkg-lint: ## Lint every package in packages/
	$(PYTHON) -m pylint --rcfile=pyproject.toml $(PKG_PATHS)

pkg-typecheck: pkg-install ## Typecheck every package in packages/
	$(PYTHON) -m mypy --config-file=pyproject.toml --python-version=3.11 $(PKG_PATHS)

pkg-install: ## Install every package in packages/ into the venv (editable)
	$(PIP) install $(foreach pkg,$(PKG_PATHS),-e $(pkg))

diff:
	code --diff "$(C4D_PLUGIN_PATH)/src/jb_protocols.py" "$(BLENDER_PLUGIN_PATH)/src/jb_protocols.py"

diff-all:
	@$(PYTHON) scripts/check_diff.py "$(C4D_PLUGIN_PATH)" "$(BLENDER_PLUGIN_PATH)"

lint:
	make c4d-lint
	make blend-lint
	make pkg-lint
	make diff-all

typecheck:
	make c4d-typecheck
	make blend-typecheck
	make pkg-typecheck

c4d:
	make c4d-lint
	make c4d-typecheck
	make c4d-test

c4d-lint:
	$(PYTHON) -m pylint --rcfile=pyproject.toml plugins/cinema4d tests/integration

c4d-typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml plugins/cinema4d tests/integration

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
