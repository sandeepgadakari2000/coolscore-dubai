"""Window shading by balconies (overhangs) and neighbouring towers (obstruction).

Geometry is 2-D (infinitely long overhang and obstruction parallel to the
facade), the standard simplification for facade studies:

- An overhang of depth ``d`` at the window head shades a height
  ``d * tan(profile angle)`` of a window of height ``h`` from the beam.
- A neighbouring tower subtends a horizon angle ``eps`` above the window;
  beam is blocked when the sun's profile angle is below ``eps``.
- Diffuse sky light on a vertical window is reduced by both: from a point a
  distance ``y`` below the overhang, the visible sky spans elevations
  ``eps .. atan(y/d)``, i.e. a fraction ``sin(atan(y/d)) - sin(eps)`` of an
  unobstructed vertical surface's sky view.
"""

from __future__ import annotations

import numpy as np


def obstruction_angle_deg(height_m, distance_m, z_m):
    """Horizon angle (deg) of a neighbouring tower seen from height ``z_m``."""
    rise = np.clip(np.asarray(height_m, dtype=float) - np.asarray(z_m, dtype=float), 0.0, None)
    return np.degrees(np.arctan2(rise, np.asarray(distance_m, dtype=float)))


def diffuse_window_factor(depth_m, window_h_m, eps_deg, n: int = 24):
    """Share of unobstructed sky-diffuse reaching a window under an overhang and obstruction."""
    d = np.atleast_1d(np.asarray(depth_m, dtype=float))
    h = np.atleast_1d(np.asarray(window_h_m, dtype=float))
    sin_eps = np.sin(np.radians(np.atleast_1d(np.asarray(eps_deg, dtype=float))))
    frac = (np.arange(n) + 0.5) / n                      # midpoints down the window
    y = frac[None, :] * h[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        sin_psi = np.where(d[:, None] > 0, y / np.sqrt(y**2 + d[:, None] ** 2), 1.0)
    return np.clip(sin_psi - sin_eps[:, None], 0.0, None).mean(axis=1)


def beam_window_factor(tan_profile, depth_m, window_h_m, width_fraction, tan_eps):
    """Unshaded share of beam irradiance on a window (one hour, vectorised over units).

    ``tan_profile`` is NaN when the sun is behind the facade (no beam anyway).
    """
    tp = np.nan_to_num(np.asarray(tan_profile, dtype=float), nan=-1.0)
    visible = tp > tan_eps
    with np.errstate(divide="ignore", invalid="ignore"):
        shaded = np.clip(depth_m * np.clip(tp, 0.0, None) / window_h_m, 0.0, 1.0)
    return visible * (1.0 - width_fraction * shaded)
