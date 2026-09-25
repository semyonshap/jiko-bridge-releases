PKG_PATHS := $(patsubst %/pyproject.toml,%,$(wildcard packages/*/pyproject.toml))

-include $(wildcard packages/*/package.mk)

PKG_PACKAGE_TARGETS := $(foreach mk,$(wildcard packages/*/package.mk),package-$(notdir $(dir $(mk))))

.PHONY: pkg pkg-lint pkg-typecheck pkg-install pkg-build pkg-package pkg-package-c4d $(PKG_PACKAGE_TARGETS)

pkg: ## Lint and typecheck every package in packages/
	make pkg-lint
	make pkg-typecheck

pkg-lint: ## Lint every package in packages/
	$(PYTHON) -m pylint --rcfile=pyproject.toml $(PKG_PATHS)

pkg-typecheck: pkg-install ## Typecheck every package in packages/
	$(PYTHON) -m mypy --config-file=pyproject.toml --python-version=3.11 $(PKG_PATHS)

pkg-install: ## Install every package in packages/ into the venv (editable)
	$(PIP) install $(foreach pkg,$(PKG_PATHS),-e $(pkg))

# Сборка идёт по одному пакету за вызов: у каждого свой pyproject.toml, а
# python -m build принимает ровно один каталог.
define PKG_BUILD_RULE
.PHONY: pkg-build-$(notdir $(1))
pkg-build-$(notdir $(1)):
	$(PYTHON) -m build $(1)
endef

PKG_BUILD_TARGETS := $(foreach pkg,$(PKG_PATHS),pkg-build-$(notdir $(pkg)))

$(foreach pkg,$(PKG_PATHS),$(eval $(call PKG_BUILD_RULE,$(pkg))))

pkg-build: $(PKG_BUILD_TARGETS) ## Build sdist + wheel for every package

pkg-package-c4d: ## Bundle the Cinema 4D plugin into plugins/cinema4d/jiko_bridge_c4d.pyp
	$(PYTHON) packages/jiko-bundler/bundle.py packages/jiko-bridge-c4d/jiko_bridge_c4d/entry.py -I packages/jiko-bridge-c4d -I packages/jiko-bridge-client --external c4d --external maxon -o plugins/cinema4d/jiko_bridge_c4d.pyp

pkg-package: pkg-build pkg-package-c4d $(PKG_PACKAGE_TARGETS) ## Build distributable artifacts for every package
