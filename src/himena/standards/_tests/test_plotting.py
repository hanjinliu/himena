import pytest
from himena.standards import plotting as hplt

def test_subplots():
    row = hplt.row(2)
    row[0].plot([0, 1, 2], [3, 0, -2])
    row[1].scatter([0, 1, 2], [3, 0, -2])
    with pytest.raises(IndexError):
        row[2]

    col = hplt.column(2)
    col[0].plot([0, 1, 2], [3, 0, -2])
    col[1].scatter([0, 1, 2], [3, 0, -2])
    with pytest.raises(IndexError):
        col[2]
