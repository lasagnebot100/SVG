"""Algorithm toolkit for generative art – registered as sketch functions on import.

growth.py      differential growth, DLA, space colonization
simulation.py  Verlet physics, boids, cellular automata, reaction–diffusion
patterns.py    wave function collapse, Truchet, Delaunay, TSP art, contours,
               evenly spaced streamlines, L-systems, circle packing

Everything is pure Python (numpy/scipy are used for speed when available) and
deterministic: functions that need randomness use the sketch's seeded generator.
"""
from . import growth, patterns, simulation  # noqa: F401  (registers the tools)
