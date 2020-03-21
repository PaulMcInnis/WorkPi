"""https://raw.githubusercontent.com/Mekire/rounded-rects-pygame/master/roundrects/roundrects.py"""
import pygame as pg
from pygame import gfxdraw


def round_rect(surface, rect, color, rad=20, border=0, inside=(0, 0, 0, 0)):
    """
    Draw a rect with rounded corners to surface.  Argument rad can be specified
    to adjust curvature of edges (given in pixels).  An optional border
    width can also be supplied; if not provided the rect will be filled.
    Both the color and optional interior color (the inside argument) support
    alpha.
    """
    def _render_region(image, rect, color, rad):
        """Helper function for round_rect."""
        corners = rect.inflate(-2 * rad, -2 * rad)
        for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
            pg.draw.circle(image, color, getattr(corners, attribute), rad)
        image.fill(color, rect.inflate(-2 * rad, 0))
        image.fill(color, rect.inflate(0, -2 * rad))

    rect = pg.Rect(rect)
    zeroed_rect = rect.copy()
    zeroed_rect.topleft = 0, 0
    image = pg.Surface(rect.size).convert_alpha()
    image.fill((0, 0, 0, 0))
    _render_region(image, zeroed_rect, color, rad)
    if border:
        zeroed_rect.inflate_ip(-2 * border, -2 * border)
        _render_region(image, zeroed_rect, inside, rad)
    surface.blit(image, rect)
