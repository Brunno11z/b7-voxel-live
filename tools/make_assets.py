"""Reproducible original 2.5D pixel-art assets and synthesized sound. Pillow only at build time."""
from PIL import Image, ImageDraw
from pathlib import Path
import random, math, wave, struct, shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)
rng = random.Random(12)

def image(name='', size=(48, 48)):
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)

def save(im, name):
    im.save(OUT / f'{name}.png')

# Block textures (stone, gold, diamond, dirt, grass)
for name, base in [('stone', (164, 177, 171)), ('gold', (246, 197, 41)), ('diamond', (73, 216, 192)), ('dirt', (111, 72, 47)), ('grass', (83, 163, 42))]:
    for variant in range(4):
        im, d = image(name)
        d.rectangle((0, 0, 47, 47), fill=base)
        for k in range(70):
            x, y = rng.randrange(2, 45), rng.randrange(2, 45)
            n = rng.randint(-28, 26)
            col = tuple(max(0, min(255, c + n)) for c in base)
            d.rectangle((x, y, min(46, x + rng.randint(2, 9)), min(46, y + rng.randint(1, 5))), fill=col)
        light = tuple(min(255, c + 48) for c in base)
        dark = tuple(max(0, c - 45) for c in base)
        d.line((0, 0, 47, 0), fill=light, width=2)
        d.line((0, 0, 0, 47), fill=light, width=2)
        d.line((1, 46, 47, 46), fill=dark, width=2)
        d.line((46, 2, 46, 47), fill=dark, width=2)
        if name == 'diamond':
            d.polygon([(24, 8), (35, 19), (26, 35), (13, 24)], fill=(148, 255, 225), outline=(199, 255, 236))
            d.line((24, 8, 26, 35), fill=(226, 255, 240), width=2)
            d.line((13, 24, 35, 19), fill=(226, 255, 240))
        elif name == 'gold':
            d.polygon([(18, 10), (31, 14), (35, 27), (24, 36), (12, 26)], fill=(255, 215, 72))
            d.line((13, 26, 24, 32, 34, 25), fill=(255, 240, 145), width=3)
            d.rectangle((8, 8, 12, 11), fill=(255, 248, 176))
        elif name == 'stone':
            d.line((8, 17, 19, 12, 35, 16, 39, 29, 29, 37, 10, 32, 8, 17), fill=(205, 213, 204), width=3)
        if name == 'grass':
            d.rectangle((0, 0, 47, 9), fill=(115, 207, 58))
        save(im, f'{name}{variant}')

# Explorer 2D sprite frames backup
for state in ['idle', 'walk', 'jump', 'fall', 'build', 'land', 'celebrate']:
    for frame in range(6):
        im, d = image('', (36, 54))
        s = math.sin(frame * math.tau / 6)
        leg = int(s * 5) if state == 'walk' else (4 if state in ('jump', 'fall') else 0)
        squat = 3 if state == 'land' else 0
        d.line((15, 32 + squat, 13 - leg, 49), fill=(33, 50, 96), width=7)
        d.line((22, 33, 23 + leg, 50), fill=(44, 65, 126), width=7)
        d.rectangle((7 - leg, 48, 16 - leg, 52), fill=(46, 39, 38))
        d.rectangle((20 + leg, 49, 30 + leg, 53), fill=(46, 39, 38))
        d.rectangle((10, 19 + squat, 26, 35 + squat), fill=(21, 155, 176))
        d.rectangle((10, 19 + squat, 15, 32 + squat), fill=(18, 116, 143))
        d.rectangle((9, 2 + squat, 28, 21 + squat), fill=(183, 126, 82))
        d.rectangle((9, 2 + squat, 28, 8 + squat), fill=(65, 40, 25))
        d.rectangle((9, 5 + squat, 14, 16 + squat), fill=(72, 42, 26))
        d.rectangle((22, 10 + squat, 29, 15 + squat), fill=(215, 162, 113))
        d.rectangle((24, 10 + squat, 26, 12 + squat), fill=(41, 39, 41))
        d.rectangle((24, 18 + squat, 29, 19 + squat), fill=(111, 62, 39))
        arm_y = 12 if state == 'celebrate' else (21 if state == 'build' else 33 + int(s * 3))
        d.line((22, 24 + squat, 29, arm_y + squat), fill=(199, 141, 94), width=6)
        d.rectangle((18, 20 + squat, 25, 26 + squat), fill=(22, 158, 178))
        save(im, f'hero_{state}_{frame}')

def draw_iso_cube(d, cx, cy, w, h, depth, top_col, front_col, side_col, outline=None):
    hw = w / 2
    hh = h / 2
    dx = depth * 0.866
    dy = depth * 0.5
    front = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    d.polygon(front, fill=front_col, outline=outline)
    top = [(cx - hw, cy - hh), (cx - hw + dx, cy - hh - dy), (cx + hw + dx, cy - hh - dy), (cx + hw, cy - hh)]
    d.polygon(top, fill=top_col, outline=outline)
    side = [(cx + hw, cy - hh), (cx + hw + dx, cy - hh - dy), (cx + hw + dx, cy + hh - dy), (cx + hw, cy + hh)]
    d.polygon(side, fill=side_col, outline=outline)

# 1. BUILD: 2.5D Golden Voxel Block
im, d = image('', (80, 80))
draw_iso_cube(d, 36, 44, 34, 34, 18, '#fff396', '#d99d14', '#b57d09', outline='#4a3203')
d.rectangle((26, 24, 30, 27), fill='#ffffff')
d.rectangle((31, 25, 33, 27), fill='#ffffff')
d.rectangle((22, 33, 25, 55), fill='#ffea78')
d.rectangle((47, 33, 50, 55), fill='#a6750b')
save(im, 'icon_BUILD')

# 2. CHICKEN: 2.5D Voxel Chicken
im, d = image('', (80, 80))
draw_iso_cube(d, 34, 46, 32, 28, 16, '#ffffff', '#e8e8e8', '#c4c4c4', outline='#383838')
draw_iso_cube(d, 48, 44, 8, 16, 10, '#ffffff', '#dadada', '#b8b8b8', outline='#383838')
draw_iso_cube(d, 26, 30, 20, 20, 12, '#ffffff', '#f4f4f4', '#d2d2d2', outline='#383838')
draw_iso_cube(d, 28, 17, 8, 6, 6, '#ff4747', '#d91c1c', '#a61212')
draw_iso_cube(d, 15, 32, 8, 7, 7, '#ffb82e', '#e09516', '#b06f05')
d.rectangle((17, 36, 22, 41), fill='#d91c1c')
d.rectangle((22, 27, 25, 30), fill='#182026')
d.rectangle((26, 60, 29, 71), fill='#e09516')
d.rectangle((38, 60, 41, 71), fill='#b06f05')
save(im, 'icon_CHICKEN')

# 3. PHOENIX: 2.5D Firebird with flaming 3D voxel wings
im, d = image('', (80, 80))
draw_iso_cube(d, 52, 28, 18, 30, 14, '#ffdd55', '#ff6f00', '#c23800')
draw_iso_cube(d, 36, 44, 22, 26, 14, '#ffe873', '#ff5100', '#ba2700', outline='#470d00')
draw_iso_cube(d, 20, 36, 18, 28, 12, '#fff39e', '#ff7b1a', '#d43f00')
draw_iso_cube(d, 32, 22, 14, 14, 8, '#ffeb85', '#ff6600', '#c42e00')
d.polygon([(36, 12), (44, 6), (41, 16)], fill='#ffe873')
d.polygon([(28, 12), (22, 4), (27, 16)], fill='#ff4d00')
draw_iso_cube(d, 23, 23, 6, 5, 5, '#ffe566', '#d9a300', '#997300')
d.rectangle((29, 20, 31, 23), fill='#ffffff')
for tx, ty, tcol in [(45, 62, '#ff8c00'), (54, 58, '#ff3700'), (48, 68, '#ffd000'), (38, 64, '#ff2200')]:
    draw_iso_cube(d, tx, ty, 6, 6, 4, tcol, tcol, '#8c1500')
save(im, 'icon_PHOENIX')

# 4. SKY_WHALE: 2.5D Voxel Sky Whale
im, d = image('', (80, 80))
draw_iso_cube(d, 60, 35, 12, 16, 8, '#70d6ff', '#2196f3', '#1565c0')
draw_iso_cube(d, 36, 46, 36, 22, 16, '#94e2ff', '#3aa7ff', '#1a75c7', outline='#0d4273')
d.rectangle((20, 48, 52, 57), fill='#e1f5fe')
draw_iso_cube(d, 38, 56, 14, 8, 8, '#64b5f6', '#1976d2', '#0d47a1')
draw_iso_cube(d, 18, 44, 16, 18, 12, '#b3ecff', '#4fc3f7', '#0288d1')
d.rectangle((16, 41, 19, 44), fill='#0a233a')
draw_iso_cube(d, 28, 26, 6, 8, 5, '#e0f7fa', '#80deea', '#26c6da')
draw_iso_cube(d, 25, 17, 7, 7, 5, '#ffffff', '#b2ebf2', '#4dd0e1')
draw_iso_cube(d, 34, 18, 6, 6, 4, '#e0f7fa', '#80deea', '#26c6da')
save(im, 'icon_SKY_WHALE')

# 5. WIN: 2.5D Golden Trophy & Star
im, d = image('', (80, 80))
draw_iso_cube(d, 40, 64, 36, 12, 14, '#ffeb85', '#d49a15', '#996700', outline='#3d2900')
draw_iso_cube(d, 40, 53, 20, 10, 10, '#ffd84d', '#c28707', '#8a5b00')
draw_iso_cube(d, 40, 36, 30, 22, 14, '#fff5a8', '#f2ae1b', '#ba7f09', outline='#452e00')
d.rectangle((19, 28, 24, 42), fill='#f2ae1b', outline='#543700')
d.rectangle((56, 26, 61, 40), fill='#ba7f09', outline='#543700')
draw_iso_cube(d, 38, 36, 10, 10, 6, '#64ffda', '#00bfa5', '#00796b')
d.polygon([(36, 12), (40, 4), (44, 12), (52, 16), (44, 20), (40, 28), (36, 20), (28, 16)], fill='#ffffff', outline='#ffd600')
save(im, 'icon_WIN')

# 6. ZAP: 2.5D Lightning Bolt Extruded
im, d = image('', (80, 80))
segments = [(42, 16, 14, 16, 10), (34, 30, 16, 14, 10), (44, 40, 18, 14, 10), (28, 56, 14, 20, 8)]
for cx, cy, w, h, dep in segments:
    draw_iso_cube(d, cx, cy, w, h, dep, '#e0ffff', '#00e5ff', '#0097a7', outline='#004d40')
d.polygon([(46, 7), (26, 38), (42, 38), (28, 73), (56, 33), (40, 33)], fill='#ffffff')
for sx, sy in [(16, 28), (58, 22), (54, 55), (20, 60)]:
    draw_iso_cube(d, sx, sy, 5, 5, 4, '#ffffff', '#84ffff', '#00e5ff')
save(im, 'icon_ZAP')

# 7. TNT: 2.5D Isometric TNT Crate
im, d = image('', (80, 80))
draw_iso_cube(d, 36, 44, 36, 36, 18, '#ff6b6b', '#d32f2f', '#9a1a1a', outline='#3d0707')
hw, hh = 18, 18
dx, dy = 18 * 0.866, 18 * 0.5
cx, cy = 36, 44
d.polygon([(cx - hw, cy - 6), (cx + hw, cy - 6), (cx + hw, cy + 6), (cx - hw, cy + 6)], fill='#ffffff')
d.polygon([(cx + hw, cy - 6), (cx + hw + dx, cy - 6 - dy), (cx + hw + dx, cy + 6 - dy), (cx + hw, cy + 6)], fill='#d9d9d9')
d.text((23, 38), 'TNT', fill='#111111')
d.line([(36, 26), (36, 16), (42, 12)], fill='#5d4037', width=3)
draw_iso_cube(d, 43, 11, 7, 7, 5, '#ffffff', '#ffeb3b', '#ff9800')
save(im, 'icon_TNT')

# 8. BLACK_HOLE: 2.5D Cosmic Singularity Vortex
im, d = image('', (80, 80))
for r, col_top, col_front in [(28, '#e040fb', '#aa00ff'), (22, '#7c4dff', '#651fff'), (16, '#00e5ff', '#00b0ff')]:
    for i in range(10):
        angle = i * (math.tau / 10)
        px = 40 + math.cos(angle) * r
        py = 42 + math.sin(angle) * (r * 0.48)
        draw_iso_cube(d, px, py, 6, 6, 5, col_top, col_front, '#311b92')
draw_iso_cube(d, 40, 42, 22, 22, 12, '#1a102f', '#090514', '#000000', outline='#d500f9')
draw_iso_cube(d, 26, 32, 5, 5, 4, '#ffeb3b', '#ffc107', '#ff9800')
draw_iso_cube(d, 54, 46, 5, 5, 4, '#00e676', '#00c853', '#009624')
save(im, 'icon_BLACK_HOLE')

# 9. TORNADO: 2.5D Spiral Voxel Funnel
im, d = image('', (80, 80))
tiers = [(10, 64, 8, 4), (14, 56, 12, 5), (18, 47, 16, 6), (24, 37, 20, 7), (30, 27, 25, 8), (36, 17, 30, 9)]
for rad, y, count, sz in tiers:
    for i in range(count):
        angle = i * (math.tau / count) + y * 0.1
        px = 40 + math.cos(angle) * rad
        py = y + math.sin(angle) * (rad * 0.28)
        draw_iso_cube(d, px, py, sz, sz, sz // 2 + 1, '#ffffff', '#b0bec5', '#78909c')
for dx_v, dy_v, col in [(20, 22, '#8d6e63'), (58, 30, '#546e7a'), (26, 48, '#7cb342'), (52, 52, '#d4e157')]:
    draw_iso_cube(d, dx_v, dy_v, 5, 5, 4, col, col, '#37474f')
save(im, 'icon_TORNADO')

# 10. LOSE: 2.5D Broken Voxel Skull / Relic
im, d = image('', (80, 80))
draw_iso_cube(d, 36, 44, 32, 32, 16, '#e1bee7', '#ab47bc', '#7b1fa2', outline='#311b92')
d.line([(28, 30), (33, 40), (29, 50)], fill='#2a0845', width=3)
d.line([(44, 32), (40, 42), (45, 54)], fill='#2a0845', width=3)
draw_iso_cube(d, 28, 40, 7, 7, 5, '#1a0029', '#12001c', '#000000')
draw_iso_cube(d, 44, 40, 7, 7, 5, '#1a0029', '#12001c', '#000000')
draw_iso_cube(d, 48, 22, 10, 10, 7, '#ce93d8', '#8e24aa', '#4a148c')
save(im, 'icon_LOSE')

# 11. GIFT: 2.5D Gift Box Icon
im, d = image('', (80, 80))
draw_iso_cube(d, 36, 46, 32, 30, 16, '#ff4081', '#e91e63', '#ad1457', outline='#4a001d')
hw, hh = 16, 15
dx, dy = 16 * 0.866, 16 * 0.5
cx, cy = 36, 46
d.rectangle((cx - 4, cy - hh, cx + 4, cy + hh), fill='#ffea00')
d.rectangle((cx - hw, cy - 3, cx + hw, cy + 3), fill='#ffd600')
d.polygon([(cx - 4, cy - hh), (cx - 4 + dx, cy - hh - dy), (cx + 4 + dx, cy - hh - dy), (cx + 4, cy - hh)], fill='#fff176')
d.polygon([(cx - hw + dx/2, cy - hh - dy/2 - 3), (cx - hw + dx/2 + dx, cy - hh - dy/2 - 3),
           (cx - hw + dx/2 + dx, cy - hh - dy/2 + 3), (cx - hw + dx/2, cy - hh - dy/2 + 3)], fill='#ffd600')
draw_iso_cube(d, 38, 22, 12, 10, 8, '#ffffff', '#fff176', '#ffd600')
d.polygon([(34, 20), (22, 14), (28, 24)], fill='#ffea00')
d.polygon([(46, 20), (58, 14), (52, 24)], fill='#ffd600')
save(im, 'gift')

# Default avatar and tree
im, d = image('', (64, 64))
d.rectangle((0, 0, 63, 63), fill='#203d57')
d.rectangle((21, 12, 43, 33), fill='#ffd594')
d.rectangle((13, 37, 51, 63), fill='#36bbce')
save(im, 'avatar')

im, d = image('', (180, 240))
d.rectangle((76, 104, 111, 235), fill='#795035')
for i in range(14):
    x = rng.randrange(0, 140)
    y = rng.randrange(5, 120)
    s = rng.randrange(28, 56)
    d.rectangle((x, y, x + s, y + s), fill=rng.choice(['#54a834', '#6ebc3b', '#84d64a', '#429431']))
save(im, 'tree')

# Sound synthesis
for name, freq, duration in [('build', 740, 0.075), ('jump', 380, 0.14), ('land', 130, 0.08), ('TNT', 85, 0.48),
                             ('ZAP', 920, 0.3), ('BLACK_HOLE', 170, 0.8), ('TORNADO', 120, 0.6), ('CHICKEN', 620, 0.3),
                             ('PHOENIX', 540, 0.5), ('SKY_WHALE', 210, 0.75), ('victory', 600, 1.0)]:
    with wave.open(str(OUT / f'{name}.wav'), 'wb') as f:
        f.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        data = []
        for i in range(int(22050 * duration)):
            t = i / 22050
            env = (1 - t / duration) ** 1.5
            pitch = freq * (1 + t / duration * 0.5)
            if name == 'victory':
                pitch = [523, 659, 784, 1047][min(3, int(t * 4))]
            val = math.sin(math.tau * pitch * t) * 0.55 + math.sin(math.tau * pitch * 2 * t) * 0.1
            if name in ('TNT', 'TORNADO'):
                val = rng.uniform(-1, 1) * 0.7
            data.append(struct.pack('<h', int(val * env * 16000)))
        f.writeframes(b''.join(data))

font = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
if font.exists():
    shutil.copy(font, OUT / 'font.ttf')
print('2.5D assets generated successfully:', len(list(OUT.iterdir())))
