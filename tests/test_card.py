from src.models.card import Card


def test_card_init():
    card = Card(5)
    assert card.value == 5
    assert card.visible is False


def test_card_str_hidden():
    card = Card(7)
    assert str(card) == "X"


def test_card_str_visible():
    card = Card(7)
    card.visible = True
    assert str(card) == "7"
