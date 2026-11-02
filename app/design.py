"""Deterministic, non-generative garment editing proof of concept.

Geometry is fixed: edit operations recolor a reference shirt and draw patterns.
This is an image-based design preview, NOT a fabric simulator or a photorealistic
AI renderer. Image generation is intentionally not claimed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / 'assets' / 'reference_shirt.jpg'
COLOR_NAMES = {
    'teal': '#317e79', 'greenish blue': '#317e79', 'greenish-blue': '#317e79',
    'forest green': '#316954', 'green': '#347d62', 'blue': '#346d96',
    'navy': '#1c3050', 'deep blue': '#233b63', 'black': '#17191c',
    'white': '#ffffff', 'cream': '#e8d9bc', 'olive': '#70794e',
    'maroon': '#633848', 'grey': '#707a81', 'gray': '#707a81',
    'brown': '#6f4c39',
}

@dataclass
class Design:
    base_color: str = '#317e79'
    line_color: str = '#17191c'
    pattern: str = 'micro-check'
    check_spacing: int = 9
    collar: str = 'point'
    sleeves: str = 'full'
    occasion: str = 'Everyday / versatile'
    preferred_style: str = 'Understated'
    budget: str = 'Not specified'
    notes: str = ''

    def asdict(self):
        return asdict(self)

    @classmethod
    def from_payload(cls, values: dict):
        allowed = set(cls.__dataclass_fields__)
        cleaned = {k: v for k, v in values.items() if k in allowed}
        obj = cls(**cleaned)
        for attr in ('base_color', 'line_color'):
            val = getattr(obj, attr)
            if not isinstance(val, str) or re.fullmatch(r'#[0-9a-fA-F]{6}', val) is None:
                raise ValueError(f'{attr} must be a six-digit hexadecimal color')
        if obj.pattern not in ('micro-check', 'window-check', 'solid', 'pinstripe'):
            raise ValueError('Unsupported pattern')
        if not isinstance(obj.check_spacing, int) or not 5 <= obj.check_spacing <= 36:
            raise ValueError('Check spacing must be between 5 and 36 pixels')
        if obj.collar not in ('point', 'spread') or obj.sleeves not in ('full', 'rolled'):
            raise ValueError('Unsupported collar or sleeve specification')
        for field in ('occasion', 'preferred_style', 'budget', 'notes'):
            if not isinstance(getattr(obj, field), str) or len(getattr(obj, field)) > 400:
                raise ValueError(f'Invalid {field}')
        return obj


def hexrgb(color: str):
    return np.array([int(color[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def render_design(design: Design, quality: int = 93) -> bytes:
    """Preserve source garment geometry, recolor fabric, and overlay selected line pattern."""
    source = Image.open(REFERENCE).convert('RGB')
    original = np.asarray(source, dtype=np.float32)
    # A conservative chromatic mask; dark buttons and grey background aren't recolored.
    r, g, b = original[..., 0], original[..., 1], original[..., 2]
    raw_mask = (g > r * 1.22) & (b > r * 1.22) & (g > 43) & (b > 46) & (r < 150) & (g < 205)
    mask = np.asarray(Image.fromarray((raw_mask * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.72)), dtype=np.float32) / 255.
    smooth = np.asarray(source.filter(ImageFilter.GaussianBlur(2.15)), dtype=np.float32)
    # Normalize by luminance of reference cloth to keep photographic lighting and folds.
    lum = (smooth[..., 0] * .2126 + smooth[..., 1] * .7152 + smooth[..., 2] * .0722)
    light = np.clip(lum / 99., .43, 1.75)
    target = hexrgb(design.base_color)
    recolored = np.clip(target[None, None, :] * light[..., None], 0, 255)
    blended = original * (1 - mask[..., None]) + recolored * mask[..., None]
    if design.pattern != 'solid':
        ys, xs = np.indices(raw_mask.shape)
        spacing = design.check_spacing
        thickness = 1 if spacing < 16 else 2
        if design.pattern == 'pinstripe':
            grid = (xs % spacing < thickness)
        elif design.pattern == 'window-check':
            grid = (xs % (spacing * 2) < thickness) | (ys % (spacing * 2) < thickness)
        else:
            grid = (xs % spacing < thickness) | (ys % spacing < thickness)
        line_opacity = np.where(grid, .68 if design.pattern == 'micro-check' else .6, 0) * mask
        lines = hexrgb(design.line_color)[None, None, :]
        blended = blended * (1 - line_opacity[..., None]) + lines * line_opacity[..., None]
    output = Image.fromarray(np.uint8(np.clip(blended, 0, 255)), 'RGB')
    stream = BytesIO()
    output.save(stream, format='JPEG', quality=quality, optimize=True)
    return stream.getvalue()


def parse_edit(command: str, design: Design):
    """Conservative command parser. Never pretend to support arbitrary AI image edits."""
    txt = re.sub(r'\s+', ' ', command.strip().lower())
    if not txt or len(txt) > 600:
        return design, [], 'Please describe a short change.'
    updates: dict[str, object] = {}
    if re.search(r'\b(no checks?|plain|solid|remove (?:the )?(?:checks?|stripes?))\b', txt):
        updates['pattern'] = 'solid'
    elif re.search(r'\b(pinstripe|pin stripe|vertical stripes?)\b', txt):
        updates['pattern'] = 'pinstripe'
    elif re.search(r'\b(window ?checks?|large checks?)\b', txt):
        updates['pattern'] = 'window-check'
    elif re.search(r'\b(micro.?checks?|fine checks?|add checks?|switch to checks?)\b', txt):
        updates['pattern'] = 'micro-check'

    pattern_mentioned = bool(re.search(r'\b(checks?|stripes?|patterns?|grids?|lines?)\b', txt))
    if pattern_mentioned and re.search(r'\b(smaller|finer|tinier|tiny)\b', txt):
        updates['check_spacing'] = max(5, design.check_spacing - 3)
    elif pattern_mentioned and re.search(r'\b(larger|bigger|wider)\b', txt):
        updates['check_spacing'] = min(36, design.check_spacing + 5)
    if 'spread collar' in txt:
        updates['collar'] = 'spread'
    elif 'point collar' in txt:
        updates['collar'] = 'point'
    if re.search(r'\b(more green|greener)\b', txt):
        updates['base_color'] = '#287b5f'
    elif re.search(r'\b(more blue|bluer)\b', txt):
        updates['base_color'] = '#31668b'

    colors = sorted(COLOR_NAMES.items(), key=lambda p: -len(p[0]))
    color_name = '|'.join(re.escape(name) for name, _ in colors)
    # Assign explicit adjective + garment/pattern phrasing before generic single-color fallback.
    for name, value in colors:
        n = re.escape(name)
        # Examples: 'black checks', 'checks to black', 'checks should be black'.
        if re.search(r'(?<![a-z])' + n + r'\s+(?:checks?|stripes?|lines?|patterns?|grids?)\b', txt) or \
           re.search(r'\b(?:checks?|stripes?|lines?|patterns?|grids?)\s+(?:(?:should )?be|to|in|are|as)?\s*' + n + r'\b', txt):
            updates['line_color'] = value
        # Examples: 'green shirt', 'make the shirt green', 'base to green'.
        if re.search(r'(?<![a-z])' + n + r'\s+(?:shirt|fabric|base)\b', txt) or \
           re.search(r'\b(?:shirt|fabric|base|body)\s+(?:(?:should )?be|to|in|as|color)?\s*' + n + r'\b', txt):
            updates['base_color'] = value
    if not any(k in updates for k in ('line_color', 'base_color')):
        hits = [(name,value) for name,value in colors if re.search(r'(?<![a-z])' + re.escape(name) + r'(?![a-z])', txt)]
        if len(hits) == 1:
            if pattern_mentioned and not re.search(r'\b(shirt|base|fabric|body)\b', txt):
                updates['line_color'] = hits[0][1]
            elif not pattern_mentioned:
                updates['base_color'] = hits[0][1]
    revised = design.asdict()
    revised.update(updates)
    changed = [k for k, v in updates.items() if v != design.asdict()[k]]
    return Design.from_payload(revised), changed, None if changed else 'This edit made no supported change. Use the design controls for exact fields, or supply a rendered garment photo.'
