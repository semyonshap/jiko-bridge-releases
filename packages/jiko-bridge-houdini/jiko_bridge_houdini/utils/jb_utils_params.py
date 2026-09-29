from typing import Optional

import hou
from jiko_bridge_client import AssetFile, AssetModel
from jiko_bridge_houdini.jb_types import ASSETS_PARM
from jiko_bridge_houdini.jb_utils import absolute_path


def parm_of(node: hou.OpNode, template: str, *numbers: int) -> Optional[hou.Parm]:
    """Parameter of one multiparm instance: every ``#`` takes the next number."""
    for number in numbers:
        template = template.replace("#", str(number), 1)
    return node.parm(template)


def multiparm_numbers(node: hou.OpNode, template: str, *numbers: int) -> list[int]:
    """Instance numbers of a multiparm, as they appear in its parameter names."""
    count = parm_of(node, template, *numbers)
    if count is None:
        return []
    offset = _instance_offset(count)
    return [offset + index for index in range(count.evalAsInt())]


def parm_text(node: hou.OpNode, template: str, *numbers: int) -> str:
    """String value of one multiparm parameter, empty when it is absent."""
    parm = parm_of(node, template, *numbers)
    return parm.evalAsString() if parm is not None else ""


def set_parm_text(
    node: hou.OpNode, template: str, value: Optional[str], *numbers: int
) -> None:
    """Write a string into one multiparm parameter, skipping an absent one."""
    parm = parm_of(node, template, *numbers)
    text = "" if value is None else str(value)
    if parm is not None and parm.evalAsString() != text:
        parm.set(text)


def set_multiparm_count(node: hou.OpNode, template: str, count: int, *numbers: int) -> None:
    """Set how many instances a multiparm holds, skipping an absent parameter."""
    parm = parm_of(node, template, *numbers)
    if parm is not None and parm.evalAsInt() != count:
        parm.set(count)


def set_parm_flag(node: hou.OpNode, template: str, value: bool, *numbers: int) -> None:
    """Write a toggle into one multiparm parameter, skipping an absent one."""
    parm = parm_of(node, template, *numbers)
    if parm is not None and bool(parm.evalAsInt()) != value:
        parm.set(int(value))


def node_assets(node: hou.OpNode) -> list[AssetModel]:
    """Every asset entry of the node, in parameter order."""
    return [
        AssetModel(
            vault_name=parm_text(node, "vault_name#", number) or None,
            pack_name=parm_text(node, "pack_name#", number) or None,
            asset_name=parm_text(node, "asset_name#", number) or None,
            files=[
                AssetFile(
                    filepath=parm_text(node, "filepath#_#", number, item) or None,
                    asset_type=parm_text(node, "asset_type#_#", number, item) or None,
                    bridge_type=parm_text(node, "bridge_type#_#", number, item) or None,
                )
                for item in multiparm_numbers(node, "num_files#", number)
            ],
        )
        for number in multiparm_numbers(node, ASSETS_PARM)
    ]


def asset_cache_file(node: hou.OpNode, asset: AssetModel) -> Optional[str]:
    """Cache layer path stored in the entry of one asset, None when it has no entry."""
    names = (asset.vault_name, asset.pack_name, asset.asset_name)
    number = _find_entry(node, names)
    return absolute_path(parm_text(node, "cache_file#", number)) if number is not None else None


def store_asset(node: hou.OpNode, asset: AssetModel, enable: bool = False) -> None:
    """Write the asset the Bridge returned into its entry, creating the entry.

    The enable flag seeds only a newly created entry, so a switch the user has
    set by hand survives the next import.
    """
    names = (asset.vault_name, asset.pack_name, asset.asset_name)
    number = _find_entry(node, names)
    if number is None:
        number = _add_entry(node)
        set_parm_flag(node, "enable#", enable, number)
    for template, value in zip(("vault_name#", "pack_name#", "asset_name#"), names):
        set_parm_text(node, template, value, number)
    set_parm_text(
        node,
        "cache_file#",
        f'`chs("cache_path")`/`chs("vault_name{number}")`'
        f'/`chs("pack_name{number}")`__`chs("asset_name{number}")`'
        f'/usd/`chs("asset_name{number}")`.usd',
        number,
    )
    set_multiparm_count(node, "num_files#", len(asset.files), number)
    for item, file in zip(multiparm_numbers(node, "num_files#", number), asset.files):
        for template, value in zip(
            ("filepath#_#", "asset_type#_#", "bridge_type#_#"),
            (file.filepath, file.asset_type, file.bridge_type),
        ):
            set_parm_text(node, template, value, number, item)


def _instance_offset(count: hou.Parm) -> int:
    """Offset between the instance indices and the numbers used in parameter names."""
    return count.multiParmStartOffset() or 1


def _find_entry(
    node: hou.OpNode, names: tuple[Optional[str], Optional[str], Optional[str]]
) -> Optional[int]:
    """Number of the entry holding the asset; a hand-filled entry has no vault name."""
    for number, stored in zip(multiparm_numbers(node, ASSETS_PARM), node_assets(node)):
        if (stored.vault_name, stored.pack_name, stored.asset_name) == names:
            return number
        if not stored.vault_name and (stored.pack_name, stored.asset_name) == names[1:]:
            return number
    return None


def _add_entry(node: hou.OpNode) -> int:
    """Append an empty asset entry and return the number of its parameters."""
    count = node.parm(ASSETS_PARM)
    if count is None:
        raise hou.NodeError("The asset parameter is missing. Rebuild the HDA.")
    number = _instance_offset(count) + count.evalAsInt()
    count.set(count.evalAsInt() + 1)
    return number
