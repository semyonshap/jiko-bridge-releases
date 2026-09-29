"""Solo workflow shared by every Jiko Bridge DCC plugin."""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Generic, List, cast

from ..contracts import (
    JbContainerT,
    JbMaterialT,
    JbMatrixT,
    JbObjectT,
    JbSceneABC,
    JbSettingsABC,
    JbSourceT,
)
from ..logger import get_logger


class JbAssetSoloABC(ABC, Generic[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]):
    """Base class for the solo command holding the shared solo workflow.

    The workflow picks the containers to isolate, keeps the history on the
    settings, and leaves only the DCC-specific visibility work to
    ``_apply_solo``.
    """

    scene_class: type[JbSceneABC[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]]
    settings_class: type[JbSettingsABC[JbSourceT, JbContainerT]]

    history_size = 5

    def __init__(self, source: JbSourceT):
        self.source = source
        self.scene = self.scene_class(source)

    @property
    def logger(self) -> Logger:
        """Logger of the concrete plugin module, so log lines stay traceable."""
        return get_logger(type(self).__module__)

    def solo(self) -> None:
        """Isolate the selection, or the previous selection when it is empty."""
        containers = self._solo_selection()
        if containers:
            self._apply_solo(containers)

    def _solo_selection(self) -> list[JbContainerT]:
        objects = cast(List[JbObjectT], self.scene.get_selection())
        combine = self.scene.get_containers_from_instances(
            objects
        ) + self.scene.get_containers_from_objects(objects)
        settings = self.settings_class(self.source)
        if combine:
            self._remember(settings, combine)
            return combine
        return self._forget(settings)

    def _remember(
        self, settings: JbSettingsABC[JbSourceT, JbContainerT], containers: list[JbContainerT]
    ) -> None:
        """Push a selection onto the history, ignoring a repeat of the newest entry."""
        entries = settings.load_solo()
        if entries and set(entries[0]) == set(containers):
            return
        settings.save_solo([containers, *entries][: self.history_size])

    def _forget(self, settings: JbSettingsABC[JbSourceT, JbContainerT]) -> list[JbContainerT]:
        """Drop the newest entry and return the one before it."""
        entries = settings.load_solo()
        if len(entries) < 2:
            return []
        settings.save_solo(entries[1:])
        return entries[1]

    @abstractmethod
    def _apply_solo(self, containers: list[JbContainerT]) -> None:
        """Show the given containers and hide everything else."""
