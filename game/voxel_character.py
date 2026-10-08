"""Articulated 2.5D cuboid mesh, orthographically projected and rasterized in pygame.
Actual 3D vertices, face lighting, depth sorting, and customizable voxel skins.
Includes presets for Rock Lee, Steve (default), Alex, Ninja, Neon, Zombie, and Custom.
"""
import math
import pygame as pg

PRESETS = {
    'default': {
        'hair': (62, 42, 27),
        'skin': (177, 125, 89),
        'shirt': (15, 168, 173),
        'pants': (62, 62, 139),
        'shoes': (68, 71, 77),
        'accent': (233, 232, 222),
        'eyes': (71, 65, 127)
    },
    'rock_lee': {
        'hair': (18, 18, 20),
        'skin': (218, 155, 110),
        'shirt': (28, 108, 56),    # Iconic green jumpsuit
        'pants': (28, 108, 56),    # Matching green pants
        'shoes': (235, 115, 20),   # Orange leg warmers
        'accent': (200, 35, 35),   # Red ninja belt
        'eyes': (20, 20, 25)       # Big expressive round eyes
    },
    'alex': {
        'hair': (180, 85, 28),
        'skin': (228, 180, 146),
        'shirt': (92, 124, 56),
        'pants': (74, 54, 34),
        'shoes': (52, 40, 30),
        'accent': (240, 230, 210),
        'eyes': (65, 110, 75)
    },
    'ninja': {
        'hair': (22, 22, 26),
        'skin': (190, 140, 105),
        'shirt': (28, 32, 38),
        'pants': (24, 27, 32),
        'shoes': (18, 20, 24),
        'accent': (210, 35, 35),
        'eyes': (220, 45, 45)
    },
    'neon': {
        'hair': (16, 20, 32),
        'skin': (165, 195, 215),
        'shirt': (22, 26, 38),
        'pants': (18, 22, 30),
        'shoes': (0, 245, 212),
        'accent': (0, 245, 212),
        'eyes': (255, 0, 128)
    },
    'zombie': {
        'hair': (35, 50, 25),
        'skin': (82, 128, 60),
        'shirt': (15, 118, 136),
        'pants': (45, 40, 78),
        'shoes': (32, 30, 48),
        'accent': (200, 200, 200),
        'eyes': (20, 20, 20)
    }
}

def hex_to_rgb(h, default=(128, 128, 128)):
    if not isinstance(h, str): return default
    h = h.lstrip('#')
    if len(h) == 6:
        try: return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except Exception: pass
    return default

class VoxelCharacter:
    def __init__(self, preset='default', custom_colors=None):
        self.cache = {}
        self.preset = preset
        self.custom_colors = custom_colors or {}

    @property
    def skin_preset(self):
        return self.preset

    @skin_preset.setter
    def skin_preset(self, val):
        self.preset = val

    def set_skin(self, preset, custom_colors=None):
        if self.preset != preset or (custom_colors and self.custom_colors != custom_colors):
            self.preset = preset
            if custom_colors is not None:
                self.custom_colors = custom_colors
            self.cache.clear()

    def get_colors(self):
        base = PRESETS.get(self.preset, PRESETS['default']).copy()
        if self.preset == 'custom' and self.custom_colors:
            for k, hex_val in self.custom_colors.items():
                if k in base:
                    base[k] = hex_to_rgb(hex_val, base[k])
        return base

    def frame(self, state, frame, direction=1):
        key = (self.preset, tuple(sorted(self.custom_colors.items())), state, frame % 12, direction)
        if key not in self.cache:
            self.cache[key] = self.render(state, frame % 12, direction)
        return self.cache[key]

    def render(self, state, frame, direction):
        surf = pg.Surface((154, 154), pg.SRCALPHA)
        polys = []
        scale = 3.05
        yaw = math.radians(-28)
        pitch = math.radians(14)

        colors = self.get_colors()
        skin = colors['skin']
        shirt = colors['shirt']
        pants = colors['pants']
        hair = colors['hair']
        shoes = colors['shoes']
        accent = colors['accent']
        eyes = colors['eyes']

        def project(p):
            x, y, z = p
            xx = math.cos(yaw) * x - math.sin(yaw) * z
            zz = math.sin(yaw) * x + math.cos(yaw) * z
            return (77 + xx * scale, 139 + (-math.cos(pitch) * y + math.sin(pitch) * zz) * scale), zz * math.cos(pitch) - y * math.sin(pitch)

        def part(center, size, color, angle=0, pivot=None, skin_cb=None):
            cx, cy, cz = center
            w, h, d = size

            def transform(p):
                if pivot:
                    x, y, z = p
                    px, py, pz = pivot
                    y -= py; z -= pz
                    return x, py + y * math.cos(angle) - z * math.sin(angle), pz + y * math.sin(angle) + z * math.cos(angle)
                return p

            verts = [(cx + sx * w / 2, cy + sy * h / 2, cz + sz * d / 2)
                     for sx, sy, sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
            faces = [
                ([0, 1, 2, 3], 0.94, 'front'),
                ([1, 5, 6, 2], 0.69, 'side'),
                ([3, 2, 6, 7], 1.14, 'top'),
                ([4, 0, 3, 7], 0.78, 'left'),
                ([5, 4, 7, 6], 0.60, 'back'),
                ([4, 5, 1, 0], 0.50, 'bottom')
            ]

            for ids, shade, face in faces:
                if face not in ('front', 'side', 'top'):
                    continue
                points = [verts[i] for i in ids]
                a, b, c, e = points
                nu = max(1, int(w if face != 'side' else d))
                nv = max(1, int(h if face != 'top' else d))
                for u in range(nu):
                    for v in range(nv):
                        quad = []
                        for du, dv in [(0,0),(1,0),(1,1),(0,1)]:
                            U = (u + du) / nu
                            V = (v + dv) / nv
                            quad.append(transform(tuple(a[k] + (b[k] - a[k]) * U + (e[k] - a[k]) * V for k in range(3))))
                        col = skin_cb(face, u, v, nu, nv) if skin_cb else color
                        variation = ((u * 17 + v * 23 + int(cx * 7)) % 7 - 3) * 1.4
                        col = tuple(max(0, min(255, int(ch * shade + variation))) for ch in col)
                        projected = [project(p) for p in quad]
                        polys.append((sum(p[1] for p in projected) / 4, col, [p[0] for p in projected]))

        def head_skin(face, u, v, nu, nv):
            if face == 'top':
                return hair
            if face == 'side':
                return hair if v >= 3 else skin
            # Front face
            # Hairline / bowl cut
            if self.preset == 'rock_lee':
                if v >= 6 or (v >= 5 and u in (0, 1, 6, 7)):
                    return hair
                # Thick iconic Lee eyebrows
                if v == 5 and u in (1, 2, 5, 6):
                    return hair
                # Big expressive eyes with white glint
                if v == 4 and u in (1, 2, 5, 6):
                    return (255, 255, 255) if u in (2, 5) else eyes
                if v == 2 and u in (3, 4):
                    return (160, 95, 65)
                return skin
            else:
                if v >= 6 or (v >= 5 and u in (0, 1, 6, 7)):
                    return hair
                if v == 4 and u in (1, 2, 5, 6):
                    return accent if u in (1, 6) else eyes
                if v == 2 and u in (3, 4):
                    return (145, 89, 61)
                if v <= 1 and 1 <= u <= 6:
                    return (88, 52, 37)
                return skin

        # Fluid harmonic articulated poses
        s = math.sin(frame * math.tau / 12)
        s2 = math.sin(frame * math.tau / 6)
        walk = s * 0.65 if state == 'walk' else 0

        left, right = walk, -walk
        arm_left, arm_right = -walk * 0.9, walk * 0.9
        bob = math.cos(frame * math.tau / 6) * 1.2 if state == 'walk' else 0

        if state == 'jump':
            left = 0.52; right = -0.42; arm_left = -0.85; arm_right = 0.72
        elif state == 'fall':
            left = 0.20; right = -0.18; arm_left = -0.52; arm_right = 0.48
        elif state == 'build':
            # Dynamic block placement swing: right arm lifts high holding a block and swings forward
            arm_right = -1.25 + s * 0.35
            arm_left = 0.25
        elif state == 'celebrate':
            # Joyous victory jump with arms raised high
            arm_left = -2.5 + s2 * 0.25
            arm_right = 2.5 - s2 * 0.25
            bob = abs(s) * 3.0

        crouch = 1.6 if state == 'land' else bob

        # Legs with shoes / leg-warmers
        def leg(x, angle):
            part((x, 6, 0), (4, 12, 4), pants, angle, (x, 12, 0))
            # Shoe / leg warmer
            part((x, 1.2, -0.35), (4.1, 2.4, 4.6), shoes, angle, (x, 12, 0))
            if self.preset == 'rock_lee':
                # Orange leg warmer band
                part((x, 3.6, -0.2), (4.05, 2.4, 4.2), shoes, angle, (x, 12, 0))

        leg(-2, left)
        leg(2, right)

        # Torso / Shirt
        part((0, 18 - crouch, 0), (8, 12, 4), shirt)
        # Belt / accent sash (e.g. Rock Lee red waist sash or ninja sash)
        if self.preset in ('rock_lee', 'ninja'):
            part((0, 13.5 - crouch, 0), (8.2, 2.5, 4.2), accent)

        # Arms
        for x, a in [(-6, arm_left), (6, arm_right)]:
            pivot = (x, 23 - crouch, 0)
            part((x, 16 - crouch, 0), (4, 10, 4), skin, a, pivot)
            part((x, 22 - crouch, 0), (4.05, 4, 4.05), shirt, a, pivot)

        # When building: place a cute 2.5D mini-voxel block in right hand!
        if state == 'build':
            part((7.5, 12 - crouch, 2), (4.5, 4.5, 4.5), (255, 215, 60), arm_right, (6, 23 - crouch, 0))

        # Head
        part((0, 28 - crouch, 0), (8, 8, 8), skin, skin_cb=head_skin)

        # Render sorted 2.5D polygons
        for _, col, points in sorted(polys, key=lambda f: f[0], reverse=True):
            pg.draw.polygon(surf, col, points)

        if direction < 0:
            surf = pg.transform.flip(surf, True, False)

        return surf
