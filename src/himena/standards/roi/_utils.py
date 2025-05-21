from __future__ import annotations

import math
import numpy as np
from numpy.typing import NDArray


def polygon_mask(
    shape: tuple[int, int], vertices: NDArray[np.number]
) -> NDArray[np.bool_]:
    """Create a binary mask of a polygon.

    Parameters
    ----------
    shape : tuple[int, int]
        Shape of the mask.
    vertices : np.ndarray
        Nx2 array of the vertices of the polygon.

    Returns
    -------
    mask : np.ndarray
        Binary mask of the polygon.
    """
    x, y = np.indices(shape)
    points = np.vstack((x.ravel(), y.ravel())).T
    mask = points_in_poly(points, vertices).reshape(shape)
    return mask


# This function is copied from https://github.com/napari/napari/blob/main/napari/layers/shapes/_shapes_utils.py
def points_in_poly(points: NDArray[np.number], vertices: NDArray[np.number]):
    """Tests points for being inside a polygon using the ray casting algorithm

    Parameters
    ----------
    points : np.ndarray
        Mx2 array of points to be tested
    vertices : np.ndarray
        Nx2 array of the vertices of the polygon.

    Returns
    -------
    inside : np.ndarray
        Length M boolean array with `True` for points inside the polygon
    """
    n_verts = len(vertices)
    inside = np.zeros(len(points), dtype=bool)
    j = n_verts - 1
    for i in range(n_verts):
        # Determine if a horizontal ray emanating from the point crosses the
        # line defined by vertices i-1 and vertices i.
        cond_1 = np.logical_and(
            vertices[i, 1] <= points[:, 1], points[:, 1] < vertices[j, 1]
        )
        cond_2 = np.logical_and(
            vertices[j, 1] <= points[:, 1], points[:, 1] < vertices[i, 1]
        )
        cond_3 = np.logical_or(cond_1, cond_2)
        d = vertices[j] - vertices[i]
        # Prevents floating point imprecision from generating false positives
        tolerance = 1e-12
        d = np.where(abs(d) < tolerance, 0, d)
        if d[1] == 0:
            # If y vertices are aligned avoid division by zero
            cond_4 = d[0] * (points[:, 1] - vertices[i, 1]) > 0
        else:
            cond_4 = points[:, 0] < (
                d[0] * (points[:, 1] - vertices[i, 1]) / d[1] + vertices[i, 0]
            )
        cond_5 = np.logical_and(cond_3, cond_4)
        inside[cond_5] = 1 - inside[cond_5]
        j = i

    # If the number of crossings is even then the point is outside the polygon,
    # if the number of crossings is odd then the point is inside the polygon

    return inside


def eccentricity(a: float, b: float) -> float:
    a, b = sorted([a, b])
    if b == 0:
        return 0.0
    return math.sqrt(1 - a**2 / b**2)
