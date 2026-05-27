from calculator import add

def test_add():
    # Intentionally failing: 2+2 is 4, but we expect 5
    assert add(2, 2) == 5