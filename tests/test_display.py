import pytest
from src.utils.display import convert_coordinates


def test_convert_valid():
    assert convert_coordinates("A1") == (0, 0)
    assert convert_coordinates("C4") == (2, 3)
    assert convert_coordinates("B2") == (1, 1)


def test_convert_invalid_bounds():
    with pytest.raises(ValueError):
        convert_coordinates("D1")  # ligne D n'existe pas
    with pytest.raises(ValueError):
        convert_coordinates("A5")  # colonne 5 n'existe pas


def test_convert_lowercase():
    assert convert_coordinates("a1") == (0, 0)
    assert convert_coordinates("c4") == (2, 3)
    with pytest.raises(ValueError):
        convert_coordinates("1A")  # format inverse invalide
