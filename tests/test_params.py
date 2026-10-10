"""Parameter validation and coercion to command-line strings."""

from __future__ import annotations

import pytest

from pardesline.catalog import Method, Parameter
from pardesline.errors import ParameterError


def P(**kw) -> Parameter:
    kw.setdefault("name", "x")
    kw.setdefault("default", None)
    return Parameter(**kw)


def test_float():
    p = P(type="float", min=0.0, max=1.0)
    assert p.coerce(0.5) == "0.5"
    assert p.coerce(1) == "1.0"
    assert p.coerce("0.25") == "0.25"
    with pytest.raises(ParameterError, match="above the maximum"):
        p.coerce(1.5)
    with pytest.raises(ParameterError, match="below the minimum"):
        p.coerce(-1)
    with pytest.raises(ParameterError, match="got a bool"):
        p.coerce(True)
    with pytest.raises(ParameterError, match="expected a float"):
        p.coerce("abc")


def test_int():
    p = P(type="int", min=1, max=10)
    assert p.coerce(3) == "3"
    assert p.coerce(3.0) == "3"
    assert p.coerce("7") == "7"
    with pytest.raises(ParameterError, match="expected an int"):
        p.coerce(2.5)
    with pytest.raises(ParameterError, match="above the maximum"):
        p.coerce(11)


def test_bool():
    p = P(type="bool")
    assert p.coerce(True) == "true"
    assert p.coerce(False) == "false"
    assert p.coerce("yes") == "true"
    assert p.coerce("0") == "false"
    assert p.coerce(1) == "true"
    with pytest.raises(ParameterError, match="expected true/false"):
        p.coerce("maybe")


def test_enum_is_case_insensitive_and_normalised():
    p = P(type="enum", options=("GEOMETRY", "MOMENTS"))
    assert p.coerce("geometry") == "GEOMETRY"
    with pytest.raises(ParameterError, match="is not one of"):
        p.coerce("CENTER")


def test_list_and_string():
    assert P(type="list").coerce([4, 2, 1]) == "4,2,1"
    assert P(type="list").coerce("4,2,1") == "4,2,1"
    assert P(type="string").coerce("Normals") == "Normals"
    with pytest.raises(ParameterError, match="expected text"):
        P(type="string").coerce(["a"])


def test_method_validate_unknown_and_suggestion():
    m = Method(
        id="m",
        name="M",
        module_id="mod",
        script="m.py",
        output_extension=".ply",
        parameters=(
            P(name="voxel_size", type="float", default=0.02),
            P(name="nb_neighbors", type="int", default=20),
        ),
    )
    assert m.validate({"voxel_size": 0.1}) == {"voxel_size": "0.1"}
    assert m.validate(None) == {}
    assert m.validate({"voxel_size": None}) == {}
    with pytest.raises(ParameterError, match=r"voxel_sise -> voxel_size\?"):
        m.validate({"voxel_sise": 0.1})
    with pytest.raises(ParameterError, match="Accepted: voxel_size, nb_neighbors"):
        m.validate({"depth": 9})


def test_method_without_parameters():
    m = Method(id="m", name="M", module_id="mod", script="m.py", output_extension=".ply")
    with pytest.raises(ParameterError, match="takes no parameters"):
        m.validate({"depth": 9})
