PKG_PATHS := $(patsubst %/pyproject.toml,%,$(wildcard packages/*/pyproject.toml))

-include $(wildcard packages/*/package.mk)

PKG_PACKAGE_TARGETS := $(foreach mk,$(wildcard packages/*/package.mk),package-$(notdir $(dir $(mk))))

.PHONY: pkg pkg-lint pkg-typecheck pkg-package pkg-package-c4d pkg-package-blend $(PKG_PACKAGE_TARGETS)

pkg: ## Lint and typecheck every package in packages/
	make pkg-lint
	make pkg-typecheck

pkg-lint: ## Lint every package in packages/
	$(PYTHON) -m pylint --rcfile=pyproject.toml $(PKG_PATHS)

pkg-typecheck: ## Typecheck every package in packages/
	$(PYTHON) -m mypy --config-file=pyproject.toml --python-version=3.11 $(PKG_PATHS)

pkg-package-c4d: ## Bundle the Cinema 4D plugin into plugins/cinema4d/jiko_bridge_c4d.pyp
	$(PYTHON) packages/jiko-bundler/bundle.py packages/jiko-bridge-c4d/jiko_bridge_c4d/entry.py \
		-I packages/jiko-bridge-c4d \
		-I packages/jiko-bridge-client \
		--external c4d \
		--external maxon \
		-o plugins/cinema4d/jiko_bridge_c4d.pyp

pkg-package-blend: ## Bundle the Blender addon into plugins/blender/addons/jiko_bridge_blend/__init__.py
	$(PYTHON) packages/jiko-bundler/bundle.py packages/jiko-bridge-blend/jiko_bridge_blend/entry.py \
		-I packages/jiko-bridge-blend \
		-I packages/jiko-bridge-client \
		--external bpy \
		--external bmesh \
		--external mathutils \
		--external addon_utils \
		-o plugins/blender/addons/jiko_bridge_blend/__init__.py

pkg-package: pkg-package-c4d pkg-package-blend $(PKG_PACKAGE_TARGETS) ## Bundle distributable artifacts for every plugin
