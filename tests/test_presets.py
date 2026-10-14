"""Preset shapes: the three Moviola renderings, pinned as filter chains."""

from __future__ import annotations

import pytest

from moviola_protocol_mcp.presets import get_preset, list_presets


def test_standard_preset_seats_black_ntsc_j_and_keeps_eight_bit_grey() -> None:
    chain = get_preset("standard").filter_chain()
    assert "fps=10" in chain
    assert "in_range=limited:out_range=full" in chain
    assert "format=gray" in chain
    assert "greyedge" in chain
    assert get_preset("standard").palette_colors == 8
    assert get_preset("standard").filter_chain(fps=15).startswith("fps=15")


def test_intersect_preset_overcalculates_grey_then_thresholds_to_one_bit() -> None:
    preset = get_preset("intersect")
    chain = preset.filter_chain()
    assert "curves=all='0/0 0.30/0.02 0.5/0.5 0.70/0.98 1/1'" in chain
    assert "lut=y='if(gt(val,128),255,0)'" in chain
    assert chain.index("curves") < chain.index("lut")
    assert preset.one_bit is True
    assert preset.palette_colors == 2


def test_torch_preset_runs_five_fps_and_resizes_to_360_or_480() -> None:
    preset = get_preset("torch")
    assert "fps=5" in preset.filter_chain()
    assert "scale=-2:'min(360,ih)'" in preset.filter_chain()
    assert "scale=-2:'min(480,ih)'" in preset.filter_chain(height=480)
    assert preset.one_bit is True


def test_preset_aliases_a_b_c_resolve_and_unknown_names_are_refused_by_name() -> None:
    assert get_preset("A").name == "standard"
    assert get_preset("b").name == "intersect"
    assert get_preset("C").name == "torch"
    assert get_preset("none").name == "passthrough"
    with pytest.raises(ValueError, match="unknown preset 'banana'"):
        get_preset("banana")


def test_list_presets_describes_all_four_renderings() -> None:
    names = [entry["name"] for entry in list_presets()]
    assert names == ["standard", "intersect", "torch", "passthrough"]
