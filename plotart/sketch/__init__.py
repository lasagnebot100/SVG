"""plotart.sketch – a p5.js/Processing-like creative coding API in Python.

    from plotart.sketch import run_sketch, execute, render_svg, render_png, to_plotter
"""
from .color import PALETTES, Color, Gradient
from .core import Sketch
from .export import render_png, to_plotter
from .render_svg import render_svg
from .runner import api_reference, execute, list_examples, run_sketch

__all__ = ["Sketch", "Color", "Gradient", "PALETTES", "run_sketch", "execute", "render_svg",
           "render_png", "to_plotter", "api_reference", "list_examples"]
