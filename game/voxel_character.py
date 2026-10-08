"""Articulated 2.5D Minecraft voxel character engine.
Renders standard 64x64 Minecraft RGBA skins in an isometric 3/4 front perspective
(facing the viewer), sampling base and overlay texture layers (crown, rose, suit, sleeves).
"""
import math
from pathlib import Path
from PIL import Image
import pygame as pg
from configuration import ROOT

SKINS_DIR = ROOT / 'assets/skins'

SKIN_FILES = {
    'rei_coroa': 'rei_coroa.png',
    'pato_dourado': 'pato_dourado.png',
    'aesthetic_boy': 'aesthetic_boy.png',
    'guerreiro_voxel': 'guerreiro_voxel.png'
}

BLOCK_PALETTES = {
    0: {'top': (94, 157, 52), 'front': (134, 96, 67), 'side': (108, 76, 52)},    # Grass/Dirt
    1: {'top': (160, 160, 160), 'front': (128, 128, 128), 'side': (98, 98, 98)}, # Stone
    2: {'top': (110, 245, 245), 'front': (75, 215, 225), 'side': (50, 175, 185)}, # Diamond
    'gold': {'top': (255, 235, 90), 'front': (245, 195, 35), 'side': (205, 155, 20)},
    'dirt': {'top': (134, 96, 67), 'front': (110, 78, 54), 'side': (90, 62, 42)}
}

def load_and_parse_skin(skin_path):
    """Parses standard Minecraft 64x64 RGBA skin into voxel UV face maps."""
    if not skin_path.exists():
        skin_path = SKINS_DIR / 'rei_coroa.png'
    im = Image.open(skin_path).convert('RGBA')
    w, h = im.size
    if h == 32:
        new_im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        new_im.paste(im, (0, 0))
        im = new_im

    parts = {
        'head': {'dim': (8, 8, 8), 'base': (0, 0), 'overlay': (32, 0)},
        'torso': {'dim': (8, 12, 4), 'base': (16, 16), 'overlay': (16, 32)},
        'right_arm': {'dim': (4, 12, 4), 'base': (40, 16), 'overlay': (40, 32)},
        'left_arm': {'dim': (4, 12, 4), 'base': (32, 48), 'overlay': (48, 48)},
        'right_leg': {'dim': (4, 12, 4), 'base': (0, 16), 'overlay': (0, 32)},
        'left_leg': {'dim': (4, 12, 4), 'base': (16, 48), 'overlay': (0, 48)},
    }

    def sample_face(base_uv, overlay_uv, dim, face_name):
        W, H, D = dim
        if face_name == 'front':
            bw, bh = W, H
            bu, bv = base_uv[0] + D, base_uv[1] + D
            ou, ov = overlay_uv[0] + D, overlay_uv[1] + D
        elif face_name == 'side': # Character right side facing viewer in 3/4 view
            bw, bh = D, H
            bu, bv = base_uv[0], base_uv[1] + D
            ou, ov = overlay_uv[0], overlay_uv[1] + D
        elif face_name == 'top':
            bw, bh = W, D
            bu, bv = base_uv[0] + D, base_uv[1]
            ou, ov = overlay_uv[0] + D, overlay_uv[1]
        else:
            return None

        grid = []
        for v in range(bh):
            row = []
            for u in range(bw):
                base_col = im.getpixel(((bu + u) % 64, (bv + v) % 64))
                over_col = im.getpixel(((ou + u) % 64, (ov + v) % 64))
                # Alpha composite overlay on top of base
                if over_col[3] > 40:
                    row.append(over_col[:3])
                else:
                    row.append(base_col[:3])
            grid.append(row)
        return grid

    data = {}
    for part_name, info in parts.items():
        data[part_name] = {
            'front': sample_face(info['base'], info['overlay'], info['dim'], 'front'),
            'side': sample_face(info['base'], info['overlay'], info['dim'], 'side'),
            'top': sample_face(info['base'], info['overlay'], info['dim'], 'top'),
        }
    return data


class VoxelCharacter:
    def __init__(self, preset='rei_coroa'):
        self.preset = preset
        self.skin_name = preset
        self.skin_data = {}
        self.cache = {}
        self.load_skin(self.preset)

    @property
    def skin_preset(self):
        return self.preset

    @skin_preset.setter
    def skin_preset(self, val):
        self.set_skin(val)

    def set_skin(self, preset):
        if preset not in SKIN_FILES:
            preset = 'rei_coroa'
        if self.preset != preset or not self.skin_data:
            self.preset = preset
            self.skin_name = preset
            self.skin_preset = preset
            self.load_skin(preset)
            self.cache.clear()

    def load_skin(self, preset):
        filename = SKIN_FILES.get(preset, 'rei_coroa.png')
        skin_path = SKINS_DIR / filename
        self.skin_data = load_and_parse_skin(skin_path)

    def frame(self, state, frame, direction=1, held_material=0):
        key = (self.preset, state, frame % 12, direction, held_material)
        if key not in self.cache:
            self.cache[key] = self.render(state, frame % 12, direction, held_material)
        return self.cache[key]

    def render(self, state, frame, direction=1, held_material=0):
        surf = pg.Surface((160, 160), pg.SRCALPHA)
        polys = []

        # 3/4 front isometric projection angles (facing towards camera)
        scale = 3.2
        yaw = math.radians(24)
        pitch = math.radians(16)

        def project(p):
            x, y, z = p
            xx = math.cos(yaw) * x + math.sin(yaw) * z
            zz = -math.sin(yaw) * x + math.cos(yaw) * z
            yy = -math.cos(pitch) * y + math.sin(pitch) * zz
            depth = math.sin(pitch) * y + math.cos(pitch) * zz
            return (80 + xx * scale, 142 + yy * scale), depth

        def draw_box(center, size, part_name, angle_x=0, pivot=None, custom_colors=None):
            cx, cy, cz = center
            w, h, d = size

            def transform(p):
                if angle_x != 0 and pivot:
                    x, y, z = p
                    px, py, pz = pivot
                    y -= py; z -= pz
                    ry = y * math.cos(angle_x) - z * math.sin(angle_x)
                    rz = y * math.sin(angle_x) + z * math.cos(angle_x)
                    return x, py + ry, pz + rz
                return p

            part_tex = self.skin_data.get(part_name) if not custom_colors else None

            # Front face (+z, facing viewer)
            nu, nv = int(w), int(h)
            for v in range(nv):
                for u in range(nu):
                    if custom_colors:
                        col = custom_colors['front']
                    elif part_tex and 'front' in part_tex and v < len(part_tex['front']) and u < len(part_tex['front'][0]):
                        col = part_tex['front'][v][u]
                    else:
                        col = (140, 140, 140)
                    shade = 0.96
                    col = tuple(max(0, min(255, int(c * shade))) for c in col)
                    x0 = cx - w / 2 + (u / nu) * w
                    x1 = cx - w / 2 + ((u + 1) / nu) * w
                    y1 = cy + h / 2 - (v / nv) * h
                    y0 = cy + h / 2 - ((v + 1) / nv) * h
                    z = cz + d / 2
                    quad = [transform((x0, y0, z)), transform((x1, y0, z)), transform((x1, y1, z)), transform((x0, y1, z))]
                    proj = [project(p) for p in quad]
                    depth = sum(p[1] for p in proj) / 4
                    polys.append((depth, col, [p[0] for p in proj]))

            # Right side face (-x, facing viewer in 3/4 turn)
            nu, nv = int(d), int(h)
            for v in range(nv):
                for u in range(nu):
                    if custom_colors:
                        col = custom_colors['side']
                    elif part_tex and 'side' in part_tex and v < len(part_tex['side']) and u < len(part_tex['side'][0]):
                        col = part_tex['side'][v][u]
                    else:
                        col = (110, 110, 110)
                    shade = 0.78
                    col = tuple(max(0, min(255, int(c * shade))) for c in col)
                    z0 = cz - d / 2 + (u / nu) * d
                    z1 = cz - d / 2 + ((u + 1) / nu) * d
                    y1 = cy + h / 2 - (v / nv) * h
                    y0 = cy + h / 2 - ((v + 1) / nv) * h
                    x = cx - w / 2
                    quad = [transform((x, y0, z0)), transform((x, y0, z1)), transform((x, y1, z1)), transform((x, y1, z0))]
                    proj = [project(p) for p in quad]
                    depth = sum(p[1] for p in proj) / 4
                    polys.append((depth, col, [p[0] for p in proj]))

            # Top face (+y, facing up)
            nu, nv = int(w), int(d)
            for v in range(nv):
                for u in range(nu):
                    if custom_colors:
                        col = custom_colors['top']
                    elif part_tex and 'top' in part_tex and v < len(part_tex['top']) and u < len(part_tex['top'][0]):
                        col = part_tex['top'][v][u]
                    else:
                        col = (170, 170, 170)
                    shade = 1.15
                    col = tuple(max(0, min(255, int(c * shade))) for c in col)
                    x0 = cx - w / 2 + (u / nu) * w
                    x1 = cx - w / 2 + ((u + 1) / nu) * w
                    z0 = cz - d / 2 + (v / nv) * d
                    z1 = cz - d / 2 + ((v + 1) / nv) * d
                    y = cy + h / 2
                    quad = [transform((x0, y, z0)), transform((x1, y, z0)), transform((x1, y, z1)), transform((x0, y, z1))]
                    proj = [project(p) for p in quad]
                    depth = sum(p[1] for p in proj) / 4
                    polys.append((depth, col, [p[0] for p in proj]))

        # Harmonic animation poses
        s = math.sin(frame * math.tau / 12)
        s2 = math.sin(frame * math.tau / 6)
        walk = s * 0.65 if state == 'walk' else 0

        left, right = walk, -walk
        arm_left, arm_right = -walk * 0.85, walk * 0.85
        bob = math.cos(frame * math.tau / 6) * 1.2 if state == 'walk' else 0

        if state == 'jump':
            left = 0.50; right = -0.40; arm_left = -0.80; arm_right = 0.70
        elif state == 'fall':
            left = 0.20; right = -0.18; arm_left = -0.45; arm_right = 0.45
        elif state == 'build':
            # Dynamic placement swing: right arm lifts high holding the exact block being built
            arm_right = -1.25 + s * 0.35
            arm_left = 0.25
        elif state == 'celebrate':
            arm_left = -2.4 + s2 * 0.25
            arm_right = 2.4 - s2 * 0.25
            bob = abs(s) * 3.0

        crouch = 1.5 if state == 'land' else bob

        # Legs (4x12x4)
        draw_box((-2, 6, 0), (4, 12, 4), 'right_leg', angle_x=right, pivot=(-2, 12, 0))
        draw_box((2, 6, 0), (4, 12, 4), 'left_leg', angle_x=left, pivot=(2, 12, 0))

        # Torso (8x12x4)
        draw_box((0, 18 - crouch, 0), (8, 12, 4), 'torso')

        # Arms (4x12x4)
        # Right arm (with rose vine overlay on near side)
        draw_box((-6, 17 - crouch, 0), (4, 12, 4), 'right_arm', angle_x=arm_right, pivot=(-6, 23 - crouch, 0))
        # Left arm
        draw_box((6, 17 - crouch, 0), (4, 12, 4), 'left_arm', angle_x=arm_left, pivot=(6, 23 - crouch, 0))

        # Held block in hand when building: uses the EXACT material of the block being placed!
        if state == 'build':
            pal = BLOCK_PALETTES.get(held_material, BLOCK_PALETTES[0])
            draw_box((-7.5, 12 - crouch, 3), (4.5, 4.5, 4.5), 'block',
                     angle_x=arm_right, pivot=(-6, 23 - crouch, 0),
                     custom_colors={'top': pal['top'], 'front': pal['front'], 'side': pal['side']})

        # Head (8x8x8) with crown, rose and face
        draw_box((0, 28 - crouch, 0), (8, 8, 8), 'head')

        # Sort polygons back-to-front (painter's algorithm)
        for _, col, pts in sorted(polys, key=lambda f: f[0]):
            pg.draw.polygon(surf, col, pts)

        if direction < 0:
            surf = pg.transform.flip(surf, True, False)

        return surf

SKINS_METADATA = SKIN_FILES
