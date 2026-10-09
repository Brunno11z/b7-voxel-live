import math, random, queue
from collections import OrderedDict, deque
import pygame as pg
from configuration import ROOT, ACTIONS, DEFAULT_ACTION_BADGES
from services.avatars import AvatarCache
from game.actor import Explorer, SCENARIO_LEFT, SCENARIO_WIDTH, SCENARIO_RIGHT
from game.voxel_character import VoxelCharacter
from game.presentation import NAMES, action_description, gift_caption

POSITIVE = set(ACTIONS[:5])
LABELS = {'BUILD': 'CONSTRUIR', 'CHICKEN': 'GALINHA', 'PHOENIX': 'FÊNIX', 'SKY_WHALE': 'BALEIA', 'WIN': '+VITÓRIA', 'ZAP': 'RAIO', 'TNT': 'TNT', 'BLACK_HOLE': 'BURACO', 'TORNADO': 'TORNADO', 'LOSE': '-VITÓRIA'}

def draw_iso_cube_at(surf, cx, cy, w, h, depth, top_col, front_col, side_col, alpha=255):
    hw = w * 0.5
    hh = h * 0.5
    dx = depth * 0.866
    dy = depth * 0.5
    front = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    top = [(cx - hw, cy - hh), (cx - hw + dx, cy - hh - dy), (cx + hw + dx, cy - hh - dy), (cx + hw, cy - hh)]
    side = [(cx + hw, cy - hh), (cx + hw + dx, cy - hh - dy), (cx + hw + dx, cy + hh - dy), (cx + hw, cy + hh)]
    if alpha < 255:
        max_dim = int(max(40, (w + h + depth) * 2.5))
        s = pg.Surface((max_dim, max_dim), pg.SRCALPHA)
        ox, oy = max_dim * 0.5 - cx, max_dim * 0.5 - cy
        pg.draw.polygon(s, (*top_col[:3], alpha), [(p[0] + ox, p[1] + oy) for p in top])
        pg.draw.polygon(s, (*front_col[:3], alpha), [(p[0] + ox, p[1] + oy) for p in front])
        pg.draw.polygon(s, (*side_col[:3], alpha), [(p[0] + ox, p[1] + oy) for p in side])
        surf.blit(s, (cx - max_dim * 0.5, cy - max_dim * 0.5))
    else:
        pg.draw.polygon(surf, top_col, top)
        pg.draw.polygon(surf, front_col, front)
        pg.draw.polygon(surf, side_col, side)

class Renderer:
    def __init__(self, world):
        pg.init()
        self.world = world
        self.assets = ROOT / 'assets'
        self.canvas = pg.Surface((720, 1280))
        self.screen = None
        self.display_config = None
        self.configure_display()
        pg.display.set_caption('B7 VOXEL LIVE')
        self.font_cartoon_path = self.assets / 'font_cartoon.ttf'
        self.font_default_path = self.assets / 'font.ttf'
        self.font_path = self.font_cartoon_path if self.font_cartoon_path.exists() else self.font_default_path
        self.fonts = {}
        self.text_cache = OrderedDict()
        self.rng = random.Random(81)
        self.textures = {}
        self.icons = {}
        self.frames = {}
        self.character = VoxelCharacter(getattr(self.world.cfg, 'skin_preset', 'rei_coroa'))
        self.gift_catalog = {}
        self.badge_surfaces = {}

        for mat in ['stone', 'gold', 'diamond', 'grass', 'dirt']:
            self.textures[mat] = [pg.image.load(str(self.assets / f'{mat}{i}.png')).convert_alpha() for i in range(4)]
        for key in ACTIONS:
            self.icons[key] = pg.image.load(str(self.assets / f'icon_{key}.png')).convert_alpha()
        self.gift_icon = pg.image.load(str(self.assets / 'gift.png')).convert_alpha()

        for state in ['idle', 'walk', 'jump', 'fall', 'build', 'land', 'celebrate']:
            self.frames[state] = [pg.transform.scale(pg.image.load(str(self.assets / f'hero_{state}_{i}.png')).convert_alpha(), (44, 66)) for i in range(6)]
        self.tree = pg.image.load(str(self.assets / 'tree.png')).convert_alpha()
        self.default_avatar = pg.image.load(str(self.assets / 'avatar.png')).convert_alpha()
        self.avatars = AvatarCache()
        self.avatar_surfaces = OrderedDict()
        self.hero = Explorer(world)
        self.world.hero = self.hero
        self.hero_bubble = None

        self.camera = 0.0
        self.time = 0.0
        self.shake = 0.0
        self.particles = []
        self.effects = deque(maxlen=24)
        self.toasts = deque(maxlen=16)
        self.current_toast = None
        self.toast_time = 0
        self.pops = {}
        self.clouds = [(self.rng.randrange(720), self.rng.randrange(210, 1100), self.rng.uniform(0.7, 1.5)) for _ in range(11)]
        self.sky = pg.Surface((720, 1280))
        for y in range(1280):
            a = y / 1280
            pg.draw.line(self.sky, (int(61 + 85 * a), int(171 + 56 * a), int(216 + 27 * a)), (0, y), (720, y))
        self.sounds = {}
        self.last_sound = {}
        self.last_state = None
        self.tile_size = None
        try:
            if hasattr(pg, 'mixer') and pg.mixer and pg.mixer.get_init():
                pg.mixer.set_num_channels(12)
                for f in self.assets.glob('*.wav'):
                    self.sounds[f.stem] = pg.mixer.Sound(str(f))
        except (AttributeError, NotImplementedError, Exception):
            pass

    def get_action_badge(self, key, cfg):
        badge = (getattr(cfg, 'action_badges', None) or {}).get(key, '') or DEFAULT_ACTION_BADGES.get(key, '🎁')
        badge = str(badge).strip()
        if badge.startswith(('http://', 'https://')):
            self.avatars.request(badge)
            if badge in self.avatar_surfaces:
                return pg.transform.scale(self.avatar_surfaces[badge], (24, 24))
        if badge in self.badge_surfaces:
            return self.badge_surfaces[badge]
        try:
            from PIL import Image, ImageDraw
            im = Image.new('RGBA', (28, 28), (0, 0, 0, 0))
            draw = ImageDraw.Draw(im)
            draw.ellipse([0, 0, 27, 27], fill=(16, 16, 24, 240), outline=(255, 215, 60, 255), width=2)
            draw.text((14, 13), badge[:2], fill=(255, 255, 255, 255), anchor="mm")
            surf = pg.image.frombytes(im.tobytes(), im.size, 'RGBA')
            self.badge_surfaces[badge] = surf
            return surf
        except Exception:
            return pg.transform.scale(self.gift_icon, (24, 24))

    def configure_display(self):
        cfg = self.world.cfg
        value = (cfg.resolution, cfg.borderless)
        if value != self.display_config:
            w, h = map(int, cfg.resolution.split('x'))
            # Safety check: if running on desktop and requested height exceeds screen, fit safely without clipping
            try:
                info = pg.display.Info()
                if info.current_h > 0 and h >= info.current_h and not cfg.borderless:
                    factor = (info.current_h - 85) / h
                    w = int(w * factor)
                    h = int(h * factor)
            except Exception:
                pass
            self.screen = pg.display.set_mode((w, h), pg.NOFRAME if cfg.borderless else pg.RESIZABLE)
            self.display_config = value

    def get_font(self, size):
        if size not in self.fonts:
            try:
                self.fonts[size] = pg.font.Font(str(self.font_path), size)
            except Exception:
                self.fonts[size] = pg.font.Font(str(self.font_default_path), size)
        return self.fonts[size]

    def text(self, text, size, color=(255, 255, 255), center=None, pos=None, outline=False, outline_color=(0, 0, 0), outline_px=2):
        text = str(text)
        key = (text, size, color, outline, outline_color, outline_px)
        if key not in self.text_cache:
            font = self.get_font(size)
            surf = font.render(text, True, color)
            if outline:
                px = outline_px
                w, h = surf.get_size()
                bg = pg.Surface((w + px * 2, h + px * 2), pg.SRCALPHA)
                stroke_surf = font.render(text, True, outline_color)
                # Contorno contínuo estilo cartoon em todas as direções
                for dx in range(-px, px + 1):
                    for dy in range(-px, px + 1):
                        if dx != 0 or dy != 0:
                            bg.blit(stroke_surf, (dx + px, dy + px))
                bg.blit(surf, (px, px))
                surf = bg
            self.text_cache[key] = surf
            if len(self.text_cache) > 512:
                self.text_cache.popitem(last=False)
        surf = self.text_cache[key]
        rect = surf.get_rect(center=center) if center else surf.get_rect(topleft=pos or (0, 0))
        self.canvas.blit(surf, rect)
        return rect

    def sound(self, name):
        if name == 'BUILD': name = 'build'
        if name in ('WIN', 'LOSE'): name = 'victory'
        if name not in self.sounds or self.time - self.last_sound.get(name, -100) < 0.07:
            return
        self.last_sound[name] = self.time
        sound = self.sounds[name]
        sound.set_volume(self.world.cfg.volume * self.world.cfg.effects_volume)
        channel = pg.mixer.find_channel()
        if channel:
            channel.play(sound)

    def ground_y(self):
        return 890 + self.camera

    def point(self, x, row):
        return SCENARIO_LEFT + (x + 0.5) * self.hero.cell, self.ground_y() - (row + 0.5) * self.hero.cell

    def emit(self, x, y, color, n=10):
        available = max(0, self.world.cfg.particles - len(self.particles))
        for _ in range(min(n, available)):
            self.particles.append([x, y, self.rng.uniform(-110, 110), self.rng.uniform(-180, -40), self.rng.uniform(0.35, 0.9), color, self.rng.randint(3, 8)])

    def consume(self, router):
        self.gift_catalog = dict(router.catalog)
        while self.world.changes:
            kind, x, y, mat = self.world.changes.popleft()
            px, py = self.point(x, y)
            color = [(191, 206, 200), (255, 225, 85), (160, 255, 227)][mat]
            self.emit(px, py, color, 4 if kind == 'add' else 12)
            if kind == 'add':
                self.pops[x, y] = self.time
                self.sound('build')
        while self.world.signals:
            kind, _ = self.world.signals.popleft()
            if kind == 'reset':
                self.hero.reset()
                self.pops.clear()
                self.particles.clear()
                self.camera = 0.0
                self.effects.clear()
                self.toasts.clear()
                self.current_toast = None
                self.toast_time = 0
                self.hero_bubble = None
            if kind == 'victory':
                self.sound('victory')
        while router.effects:
            effect = router.effects.popleft()
            effect['start'] = self.time
            x = effect['target'] if effect['target'] is not None else self.rng.randrange(self.world.cfg.columns)
            effect['x'] = SCENARIO_LEFT + (x + 0.5) * self.hero.cell
            effect['y'] = -self.world.heights[x] * self.hero.cell
            self.effects.append(effect)
            self.toasts.append(effect)
            # Show floating gift emoji bubble above hero
            self.hero_bubble = {'action': effect['action'], 'start': self.time}
            if effect.get('avatar'):
                self.avatars.request(effect['avatar'])
            if effect.get('icon'):
                self.avatars.request(effect['icon'])
            self.sound(effect['action'])
            if effect['action'] not in POSITIVE:
                self.shake = 0.45
        while True:
            try:
                url, data = self.avatars.ready.get_nowait()
            except queue.Empty:
                break
            self.avatar_surfaces[url] = pg.image.frombytes(data, (64, 64), 'RGBA').convert_alpha()
            if len(self.avatar_surfaces) > 128:
                self.avatar_surfaces.popitem(last=False)

    def tick(self, dt, router, keys=None):
        self.time += dt
        self.configure_display()
        # Synchronize skin configuration
        cfg = self.world.cfg
        self.character.set_skin(getattr(cfg, 'skin_preset', 'rei_coroa'))
        if cfg.control_mode == 'manual' or not getattr(cfg, 'show_thought_bubble', True):
            self.hero_bubble = None
        self.consume(router)
        if self.world.running:
            jumped, landed = self.hero.tick(dt, keys)
            if jumped: self.sound('jump')
            if landed: self.sound('land')
            if self.hero.build_timer > 0.15 and not self.hero_bubble:
                self.hero_bubble = {'action': 'BUILD', 'start': self.time}

        target = max(0, self.world.max_height * self.hero.cell - 300)
        target = max(target, -self.hero.box.top - 800)
        previous = self.camera
        self.camera += (target - self.camera) * (1 - math.exp(-self.world.cfg.camera_smoothing * dt))
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt + self.camera - previous
            p[3] += 280 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0][:self.world.cfg.particles]
        self.pops = {k: v for k, v in self.pops.items() if self.time - v < 0.25}
        self.effects = deque((e for e in self.effects if self.time - e['start'] < 2.2), maxlen=24)
        self.shake = max(0.0, self.shake - dt)
        self.toast_time -= dt
        if self.toast_time <= 0:
            self.current_toast = self.toasts.popleft() if self.toasts else None
            self.toast_time = 3.0 if self.current_toast else 0.0

    def cloud(self, x, y, scale):
        color = (240, 252, 248)
        shadow = (203, 236, 233)
        u = int(24 * scale)
        for dx, dy, w, h in [(0, 1, 4, 1), (1, 0, 1, 1), (2, -1, 1, 2)]:
            r = pg.Rect(x + dx * u, y + dy * u, w * u, h * u)
            pg.draw.rect(self.canvas, color, r)
            pg.draw.rect(self.canvas, shadow, (r.x, r.bottom - 5, r.width, 5))
            pg.draw.polygon(self.canvas, (250, 255, 251), [(r.x, r.y), (r.x + 10, r.y - 7), (r.right + 10, r.y - 7), (r.right, r.y)])
            pg.draw.polygon(self.canvas, (183, 219, 223), [(r.right, r.y), (r.right + 10, r.y - 7), (r.right + 10, r.bottom - 7), (r.right, r.bottom)])

    def scene(self):
        self.canvas.blit(self.sky, (0, 0))
        g = self.ground_y()
        c = self.hero.cell
        for i, (x, y, s) in enumerate(self.clouds):
            xx = (x + self.time * (5 + i % 3) * s) % 880 - 120
            yy = (y + self.camera * 0.15) % 1100 + 90
            self.cloud(xx, yy, s)

        for i in range(12):
            h = 80 + (i * 71) % 210
            pg.draw.rect(self.canvas, (129, 207, 226), (i * 69, 1190 - h + self.camera * 0.18, 48, h + 150))

        if g < 1510:
            def cube(x, y, w, h, col, dx=17, dy=-11):
                pg.draw.polygon(self.canvas, tuple(max(0, int(a * 0.65)) for a in col), [(x + w, y), (x + w + dx, y + dy), (x + w + dx, y + h + dy), (x + w, y + h)])
                pg.draw.polygon(self.canvas, tuple(min(255, int(a * 1.2)) for a in col), [(x, y), (x + dx, y + dy), (x + w + dx, y + dy), (x + w, y)])
                pg.draw.rect(self.canvas, col, (x, y, w, h))
                pg.draw.line(self.canvas, tuple(max(0, int(a * 0.85)) for a in col), (x + 3, y + 2), (x + w - 3, y + 2), 2)
            cube(110, g - 135, 31, 135, (111, 74, 42))
            for tx, ty, tw, th, col in [(17, -198, 76, 75, (77, 153, 40)), (87, -215, 72, 89, (59, 139, 38)), (47, -258, 84, 83, (101, 174, 48)), (3, -151, 72, 48, (83, 161, 39))]:
                cube(tx, g + ty, tw, th, col)
            pg.draw.polygon(self.canvas, (132, 205, 67), [(0, g), (16, g - 11), (736, g - 11), (720, g)])
            for x in range(0, 720, 44):
                self.canvas.blit(pg.transform.scale(self.textures['grass'][x // 44 % 4], (44, 28)), (x, g))
                for y in range(int(g) + 28, 1280, 44):
                    self.canvas.blit(pg.transform.scale(self.textures['dirt'][x // 44 % 4], (44, 44)), (x, y))
            pg.draw.rect(self.canvas, (54, 71, 65), (0, g + 24, 720, 9))

        if self.tile_size != int(math.ceil(c)):
            self.tile_size = int(math.ceil(c))
            self.tiles = {m: [pg.transform.scale(t, (self.tile_size, self.tile_size)) for t in ts] for m, ts in self.textures.items()}

        depth = (15, -11)
        for (x, y), mat in sorted(self.world.blocks.items(), key=lambda item: (-item[0][0], item[0][1])):
            sx = SCENARIO_LEFT + x * c
            sy = g - (y + 1) * c
            if sy > 1280 or sy + c + depth[1] < 0:
                continue
            tile = self.tiles[['stone', 'gold', 'diamond'][mat]][(x * 7 + y * 3) % 4]
            base = [(158, 174, 165), (237, 183, 34), (60, 197, 169)][mat]
            dx, dy = depth
            if (x + 1, y) not in self.world.blocks:
                side = [(sx + c, sy), (sx + c + dx, sy + dy), (sx + c + dx, sy + c + dy), (sx + c, sy + c)]
                pg.draw.polygon(self.canvas, tuple(int(v * 0.68) for v in base), side)
                pg.draw.line(self.canvas, tuple(int(v * 0.5) for v in base), side[1], side[2], 2)
                for j in range(1, 4):
                    yy = sy + c * j / 4
                    pg.draw.line(self.canvas, tuple(int(v * 0.8) for v in base), (sx + c, yy), (sx + c + dx, yy + dy), 1)
            if (x, y + 1) not in self.world.blocks:
                top = [(sx, sy), (sx + dx, sy + dy), (sx + c + dx, sy + dy), (sx + c, sy)]
                pg.draw.polygon(self.canvas, tuple(min(255, int(v * 1.17) + 15) for v in base), top)
                pg.draw.lines(self.canvas, tuple(min(255, v + 55) for v in base), False, top[:3], 2)
                for j in range(1, 4):
                    xx = sx + c * j / 4
                    pg.draw.line(self.canvas, tuple(min(255, v + 30) for v in base), (xx, sy), (xx + dx, sy + dy), 1)
            self.canvas.blit(tile, (round(sx), round(sy)))
            age = self.time - self.pops.get((x, y), -100)
            if age < 0.22:
                overlay = pg.Surface((self.tile_size, self.tile_size), pg.SRCALPHA)
                overlay.fill((255, 255, 205, int(170 * (1 - age / 0.22))))
                self.canvas.blit(overlay, (round(sx), round(sy)))

        column = max(0, min(self.world.cfg.columns - 1, int((self.hero.box.centerx - SCENARIO_LEFT) / c)))
        surface_y = g - self.world.heights[column] * c
        shadow = pg.Surface((50, 12), pg.SRCALPHA)
        pg.draw.ellipse(shadow, (13, 49, 48, 105), (0, 0, 50, 12))
        self.canvas.blit(shadow, (self.hero.box.centerx - 19, surface_y - 9))

        state = self.hero.state if self.world.running else 'idle'
        frame = int(self.hero.time * 12) % 12
        mat = getattr(self.hero, 'current_material', 0)
        sprite = self.character.frame(state, frame, self.hero.direction, mat)
        self.canvas.blit(sprite, (self.hero.box.centerx - 77 + 6, g + self.hero.box.bottom - 139 - 5))
        for p in self.particles:
            pg.draw.rect(self.canvas, p[5], (p[0], p[1], p[6], p[6]))

    def draw_effects(self):
        """All powers, tornado, and gift effects rendered in rich 2.5D."""
        for e in list(self.effects):
            a = self.time - e['start']
            p = a / 2.2
            key = e['action']
            x = e['x']
            y = self.ground_y() + e['y']

            if key in ('BUILD', 'WIN', 'LOSE'):
                # 2.5D Isometric Voxel Cube Fountain
                for bi in range(8):
                    b_ang = bi * (math.tau / 8) + a * 4
                    b_rad = a * 85
                    bx_pos = x + math.cos(b_ang) * b_rad
                    by_pos = (y - 50) + math.sin(b_ang) * (b_rad * 0.6) - abs(math.sin(a * 6 + bi)) * 35
                    cube_col = (255, 230, 90) if key != 'LOSE' else (210, 100, 255)
                    draw_iso_cube_at(self.canvas, bx_pos, by_pos, 10, 10, 6, cube_col,
                                     tuple(int(c * 0.8) for c in cube_col), tuple(int(c * 0.6) for c in cube_col))
            elif key == 'CHICKEN':
                # 2.5D Animated Voxel Chicken
                size = 90
                xx = -size + p * (720 + size * 2)
                yy = max(240, y - 100) + math.sin(a * 7) * 22
                wing = math.sin(a * 22) * 12
                draw_iso_cube_at(self.canvas, xx, yy, 36, 32, 20, (255, 255, 255), (230, 230, 230), (195, 195, 195))
                draw_iso_cube_at(self.canvas, xx - 20, yy - 4 + wing, 12, 18, 12, (255, 255, 255), (220, 220, 220), (180, 180, 180))
                draw_iso_cube_at(self.canvas, xx + 20, yy - 4 - wing, 12, 18, 12, (255, 255, 255), (220, 220, 220), (180, 180, 180))
                draw_iso_cube_at(self.canvas, xx + 8, yy - 20, 10, 8, 8, (255, 70, 70), (220, 30, 30), (160, 15, 15))
            elif key == 'PHOENIX':
                # 2.5D Soaring Voxel Firebird with articulated 3D wings
                size = 140
                xx = -size + p * (720 + size * 2)
                yy = max(240, y - 120) + math.sin(a * 6) * 24
                wing_flap = math.sin(a * 16) * 28
                draw_iso_cube_at(self.canvas, xx, yy, 38, 44, 24, (255, 230, 100), (255, 90, 10), (180, 40, 0))
                draw_iso_cube_at(self.canvas, xx - 34, yy - 12 + wing_flap, 32, 20, 18, (255, 245, 140), (255, 130, 20), (200, 60, 0))
                draw_iso_cube_at(self.canvas, xx + 34, yy - 12 - wing_flap, 32, 20, 18, (255, 245, 140), (255, 130, 20), (200, 60, 0))
                for ei in range(5):
                    ex = xx - 40 - ei * 16 + math.sin(a * 10 + ei) * 8
                    ey = yy + 10 + math.cos(a * 8 + ei) * 12
                    draw_iso_cube_at(self.canvas, ex, ey, 8, 8, 5, (255, 255, 180), (255, 140, 20), (200, 30, 0))
            elif key == 'SKY_WHALE':
                # 2.5D Giant Voxel Sky Whale with undulating flippers & spout
                size = 190
                xx = -size + p * (720 + size * 2)
                yy = max(220, y - 140) + math.sin(a * 4) * 20
                fin_wave = math.sin(a * 8) * 14
                draw_iso_cube_at(self.canvas, xx, yy, 74, 46, 32, (150, 230, 255), (45, 155, 245), (20, 95, 185))
                draw_iso_cube_at(self.canvas, xx + 12, yy + 22 + fin_wave, 28, 14, 16, (120, 210, 255), (30, 130, 220), (15, 80, 160))
                for wi in range(6):
                    wx = xx - 18 + math.sin(a * 14 + wi) * 10
                    wy = yy - 32 - wi * 12
                    draw_iso_cube_at(self.canvas, wx, wy, 8, 8, 6, (255, 255, 255), (180, 240, 255), (80, 200, 255))
            elif key == 'ZAP':
                # 2.5D Volumetric Voxel Lightning Pillar
                bolt_tiers = 12
                curr_x = x
                for i in range(bolt_tiers):
                    seg_top = 180 + i * (y - 180) / bolt_tiers
                    seg_bot = 180 + (i + 1) * (y - 180) / bolt_tiers
                    next_x = x + math.sin(i * 3.7 + a * 20) * 24
                    mid_x = (curr_x + next_x) * 0.5
                    mid_y = (seg_top + seg_bot) * 0.5
                    h_seg = seg_bot - seg_top
                    draw_iso_cube_at(self.canvas, mid_x, mid_y, 16, h_seg, 10, (245, 255, 255), (90, 245, 230), (40, 180, 170))
                    curr_x = next_x
                for si in range(8):
                    spark_ang = si * (math.tau / 8) + a * 5
                    spark_r = a * 120
                    sx_pos = x + math.cos(spark_ang) * spark_r
                    sy_pos = y + math.sin(spark_ang) * (spark_r * 0.5) - abs(math.sin(a * 10 + si)) * 30
                    draw_iso_cube_at(self.canvas, sx_pos, sy_pos, 7, 7, 5, (255, 255, 255), (100, 255, 235), (40, 210, 195))
            elif key == 'TNT':
                # 2.5D Isometric TNT Crate & Shrapnel Detonation
                if a < 0.45:
                    throb = 1.0 + math.sin(a * 35) * 0.12
                    sz = 48 * throb
                    draw_iso_cube_at(self.canvas, x, y - 55, sz, sz, sz * 0.5, (255, 130, 130), (220, 50, 50), (160, 25, 25))
                    spark_x = x + 12 + math.sin(a * 40) * 4
                    spark_y = y - 55 - sz * 0.5 - 12
                    draw_iso_cube_at(self.canvas, spark_x, spark_y, 8, 8, 5, (255, 255, 255), (255, 215, 30), (255, 120, 0))
                else:
                    blast_time = a - 0.45
                    for bi in range(24):
                        b_ang = bi * (math.tau / 24)
                        b_speed = 90 + (bi % 5) * 45
                        bx_pos = x + math.cos(b_ang) * b_speed * blast_time
                        by_pos = (y - 55) + math.sin(b_ang) * (b_speed * 0.5) * blast_time + 400 * (blast_time ** 2)
                        b_col = [(255, 60, 60), (255, 175, 40), (255, 235, 80), (130, 80, 50)][bi % 4]
                        draw_iso_cube_at(self.canvas, bx_pos, by_pos, 8, 8, 6, b_col, tuple(int(c * 0.8) for c in b_col), tuple(int(c * 0.5) for c in b_col))
            elif key == 'BLACK_HOLE':
                # 2.5D Cosmic Gravitational Singularity Vortex
                center_y = y - 45
                for ring in range(3):
                    rad = 28 + ring * 18
                    vox_count = 8 + ring * 4
                    rot_speed = 8.0 - ring * 1.8
                    for k in range(vox_count):
                        angle = -a * rot_speed + k * (math.tau / vox_count)
                        spiral_r = max(12, rad * (1.0 - p * 0.6))
                        px = x + math.cos(angle) * spiral_r
                        py = center_y + math.sin(angle) * (spiral_r * 0.45)
                        col = [(230, 90, 255), (150, 70, 255), (60, 220, 255)][ring]
                        draw_iso_cube_at(self.canvas, px, py, 7, 7, 5, col, tuple(int(c * 0.8) for c in col), tuple(int(c * 0.6) for c in col))
                draw_iso_cube_at(self.canvas, x, center_y, 28, 28, 16, (38, 20, 65), (15, 8, 28), (5, 2, 10))
                pg.draw.ellipse(self.canvas, (215, 60, 255), (x - 35, center_y - 18, 70, 36), 3)
            elif key == 'TORNADO':
                # 2.5D True Voxel Tornado Funnel
                tornado_x = x + math.sin(a * 3.5) * 85
                tiers = 14
                for tier in range(tiers):
                    ty = y - tier * 20
                    rad = 16 + tier * 8.5
                    speed = 10.0 + tier * 1.8
                    cube_count = 4 + tier // 3
                    cube_sz = 9 + tier // 2
                    for k in range(cube_count):
                        angle = a * speed + k * (math.tau / cube_count) + tier * 0.35
                        px = tornado_x + math.cos(angle) * rad
                        py = ty + math.sin(angle) * (rad * 0.30)
                        z = math.sin(angle)
                        shade = 0.8 + 0.35 * z
                        top = (min(255, int(225 * shade)), min(255, int(240 * shade)), min(255, int(248 * shade)))
                        front = (int(175 * shade), int(205 * shade), int(220 * shade))
                        side = (int(130 * shade), int(165 * shade), int(185 * shade))
                        draw_iso_cube_at(self.canvas, px, py, cube_sz, cube_sz, cube_sz * 0.6, top, front, side)
                for di in range(6):
                    d_angle = a * 14 + di * 1.05
                    d_rad = 30 + di * 18
                    d_y = y - 60 - di * 35 + math.sin(a * 8 + di) * 20
                    dx_pos = tornado_x + math.cos(d_angle) * d_rad
                    dy_pos = d_y + math.sin(d_angle) * (d_rad * 0.35)
                    d_col = [(240, 195, 45), (145, 160, 155), (85, 215, 195)][di % 3]
                    draw_iso_cube_at(self.canvas, dx_pos, dy_pos, 10, 10, 6, d_col,
                                     tuple(int(c * 0.8) for c in d_col), tuple(int(c * 0.6) for c in d_col))


    def draw_fixed_barriers(self):
        """Draws fixed 2.5D containment barriers on the screen edges (remains fixed on screen)."""
        if not getattr(self.world.cfg, 'show_barriers', True):
            return
        top_y = 178
        bot_y = 1280
        bw = 28
        # Left barrier: x=24 to 52. Right barrier: x=668 to 696.
        for side, bx in [(0, 24), (1, 668)]:
            # Beacon cap at the top
            beacon_pulse = (math.sin(self.time * 8) + 1) * 0.5
            beacon_color = (255, int(100 + 120 * beacon_pulse), 40)
            pg.draw.rect(self.canvas, (32, 38, 46), (bx - 2, top_y, bw + 4, 18), border_radius=4)
            pg.draw.circle(self.canvas, beacon_color, (bx + bw // 2, top_y + 9), 6)
            pg.draw.circle(self.canvas, (255, 255, 200), (bx + bw // 2, top_y + 9), 3)

            # Voxel pillar segments
            y = top_y + 18
            seg = 0
            while y < bot_y:
                sh = min(36, bot_y - y)
                is_hazard = (seg % 4 == 1)

                if is_hazard:
                    base = (245, 185, 30)
                    pg.draw.rect(self.canvas, base, (bx, y, bw, sh))
                    for k in range(-bw, sh, 14):
                        pts = [(bx, max(y, y + k)), (bx + bw, max(y, y + k + bw)),
                               (bx + bw, min(y + sh, y + k + bw + 6)), (bx, min(y + sh, y + k + 6))]
                        pg.draw.polygon(self.canvas, (35, 37, 42), pts)
                else:
                    base = (46, 52, 60)
                    pg.draw.rect(self.canvas, base, (bx, y, bw, sh))
                    pg.draw.rect(self.canvas, (55, 62, 72), (bx + 4, y + 4, bw - 8, sh - 8))

                pg.draw.line(self.canvas, (110, 125, 140) if not is_hazard else (255, 235, 150), (bx, y), (bx + bw - 1, y), 2)
                pg.draw.line(self.canvas, (20, 24, 28), (bx, y + sh - 1), (bx + bw - 1, y + sh - 1), 2)
                pg.draw.line(self.canvas, (18, 20, 24), (bx, y), (bx, y + sh), 2)
                pg.draw.line(self.canvas, (18, 20, 24), (bx + bw, y), (bx + bw, y + sh), 2)
                y += sh
                seg += 1

    def draw_hero_bubble(self):
        """Floating 2.5D gift emoji balloon above the hero during actions."""
        cfg = self.world.cfg
        if cfg.control_mode == 'manual' or not getattr(cfg, 'show_thought_bubble', True):
            self.hero_bubble = None
            return
        if not self.hero_bubble:
            return
        age = self.time - self.hero_bubble['start']
        if age > 1.8:
            self.hero_bubble = None
            return

        alpha = int(255 * (1.0 - max(0.0, (age - 1.2) / 0.6)))
        float_y = math.sin(age * 5.0) * 4.0
        bx = int(self.hero.box.centerx)
        by = int(self.ground_y() + self.hero.box.top - 40 + float_y)

        bubble_surf = pg.Surface((44, 40), pg.SRCALPHA)
        pg.draw.rect(bubble_surf, (255, 255, 255, min(240, alpha)), (0, 0, 44, 32), border_radius=12)
        pg.draw.polygon(bubble_surf, (255, 255, 255, min(240, alpha)), [(16, 32), (28, 32), (22, 39)])
        action_key = self.hero_bubble.get('action', 'BUILD')
        badge = self.get_action_badge(action_key, cfg)
        if badge:
            scaled_badge = pg.transform.scale(badge, (22, 22))
            bubble_surf.blit(scaled_badge, (11, 5))
        self.canvas.blit(bubble_surf, (bx - 22, by))

    def hud(self):
        w = self.world
        cfg = w.cfg

        # 🏆 Placa de Vitórias original como antes (b7_voxel_hud_actions_preview.png)
        color = (168, 56, 66) if w.wins < 0 else (202, 161, 35)
        pg.draw.rect(self.canvas, (255, 245, 173), (239, 69, 242, 61), border_radius=23)
        pg.draw.rect(self.canvas, color, (243, 72, 234, 54), border_radius=20)
        self.text(f'VITÓRIAS {w.wins}/{cfg.goal}', 24, center=(360, 99), outline=True, outline_color=(50, 30, 10), outline_px=2)

        # Barra de Progresso
        pg.draw.rect(self.canvas, (41, 109, 130), (100, 151, 520, 29), border_radius=15)
        fill = int(514 * w.progress)
        if fill:
            pg.draw.rect(self.canvas, (255, 213, 55), (103, 154, max(10, fill), 23), border_radius=12)
        if fill > 20:
            pg.draw.line(self.canvas, (255, 235, 125), (111, 159), (100 + fill - 5, 159), 3)
        self.text(f'{w.progress * 100:.0f}%', 16, center=(360, 165), outline=True)
        if w.pending:
            self.text(f'+{w.pending} blocos aguardando', 17, center=(360, 200), outline=True)

        if w.phase == 'defending':
            pg.draw.rect(self.canvas, (156, 43, 51), (219, 284, 282, 114), border_radius=12)
            self.text('DEFENDA A CONSTRUÇÃO!', 17, center=(360, 308), outline=True, outline_px=2)
            self.text(str(math.ceil(w.timer)), 44, center=(360, 348), outline=True, outline_px=2)
            self.text('SEGUNDOS', 12, center=(360, 379))
        elif w.phase in ('celebrating', 'goal'):
            pg.draw.rect(self.canvas, (28, 124, 106), (187, 226, 346, 110), border_radius=14)
            self.text('META CONCLUÍDA!' if w.wins >= cfg.goal else 'CONSTRUÇÃO DEFENDIDA!', 21, center=(360, 257))
            self.text('Nova rodada em instantes' if w.phase == 'celebrating' else 'Inicie pelo painel', 17, center=(360, 305))

        # Cartões de Ações / Presentes (com tamanho ajustável 0-100 e opção de ocultar para tela limpa)
        show_cards = getattr(cfg, 'show_gift_cards', True)
        card_scale_pct = getattr(cfg, 'gift_cards_scale', 100)
        card_scale = max(0.0, min(1.0, card_scale_pct / 100.0))

        if show_cards and card_scale > 0.05:
            base_bw = 64
            base_bh = 76
            bw = max(24, int(base_bw * card_scale))
            bh = max(28, int(base_bh * card_scale))

                    # Cartões de Ações / Presentes (com tamanho ajustável 0-100, fonte cartoon e opção de ocultar para tela limpa)
        show_cards = getattr(cfg, 'show_gift_cards', True)
        card_scale_pct = getattr(cfg, 'gift_cards_scale', 100)
        card_scale = max(0.0, min(1.0, card_scale_pct / 100.0))

        if show_cards and card_scale > 0.08:
            base_bw = 64
            base_bh = 76
            bw = max(24, int(base_bw * card_scale))
            bh = max(28, int(base_bh * card_scale))
            spacing = max(bh + 6, int(82 * card_scale))
            start_y = 242

            title_pt = max(7, min(10, int(9 * card_scale)))
            amount_pt = max(8, min(12, int(11 * card_scale)))
            icon_sz = max(16, int(32 * card_scale))
            badge_sz = max(14, int(22 * card_scale))

            for side, actions in enumerate([ACTIONS[:5], ACTIONS[5:]]):
                cx = 40 if side == 0 else 680
                bx = cx - bw // 2

                for i, key in enumerate(actions):
                    by = start_y + i * spacing
                    base_t = self.time * 0.5 + i * 0.15 + (0.5 if side == 1 else 0.0)

                    # Fundo preto puro para máximo contraste
                    pg.draw.rect(self.canvas, (10, 12, 16), (bx, by, bw, bh), border_radius=max(3, int(10 * card_scale)))

                    # Contorno neon gamer com leve pulso RGB
                    rgb_r = int(128 + 127 * math.sin(base_t * math.tau))
                    rgb_g = int(128 + 127 * math.sin((base_t + 0.33) * math.tau))
                    rgb_b = int(128 + 127 * math.sin((base_t + 0.67) * math.tau))
                    border_color = (80, 240, 120) if side == 0 else (255, 75, 95)
                    neon_color = (
                        (border_color[0] * 3 + rgb_r) // 4,
                        (border_color[1] * 3 + rgb_g) // 4,
                        (border_color[2] * 3 + rgb_b) // 4,
                    )
                    pg.draw.rect(self.canvas, neon_color, (bx, by, bw, bh), width=2, border_radius=max(3, int(10 * card_scale)))

                    # Badge / Emoji ou foto customizada no topo
                    badge_surf = self.get_action_badge(key, cfg)
                    if badge_sz != 24:
                        badge_surf = pg.transform.smoothscale(badge_surf, (badge_sz, badge_sz))
                    bw_sz, bh_sz = badge_surf.get_size()
                    self.canvas.blit(badge_surf, (cx - bw_sz // 2, by + max(1, int(3 * card_scale))))

                    # Ícone central grande
                    caption, url = gift_caption(key, cfg, self.gift_catalog)
                    self.avatars.request(url)
                    icon = self.avatar_surfaces.get(url, self.icons[key])
                    scaled_icon = pg.transform.smoothscale(icon, (icon_sz, icon_sz))
                    icon_y = by + max(12, int(21 * card_scale))
                    self.canvas.blit(scaled_icon, (cx - icon_sz // 2, icon_y))

                    # Nome real do presente, com contorno cartoon destacado
                    bound = any(m.action == key for m in cfg.mappings)
                    title = caption if bound else LABELS.get(key, key)
                    title = str(title).strip().upper()
                    title_font = self.get_font(title_pt)
                    max_width = bw - 6

                    if title_font.size(title)[0] > max_width:
                        words = title.split()
                        lines = []
                        current = ''
                        for word in words:
                            candidate = f'{current} {word}'.strip()
                            if title_font.size(candidate)[0] <= max_width:
                                current = candidate
                            elif current:
                                lines.append(current)
                                current = word
                            else:
                                fitted = word
                                while len(fitted) > 1 and title_font.size(fitted + '…')[0] > max_width:
                                    fitted = fitted[:-1]
                                current = fitted + ('…' if fitted != word else '')
                        if current:
                            lines.append(current)
                        if len(lines) > 2:
                            lines = lines[:2]
                            last = lines[1]
                            while len(last) > 1 and title_font.size(last + '…')[0] > max_width:
                                last = last[:-1]
                            lines[1] = last + '…'
                    else:
                        lines = [title]

                    # Texto do título com contorno cartoon preto reforçado
                    title_start_y = by + max(28, int(57 * card_scale))
                    line_step = max(7, int(9 * card_scale))
                    for line_index, line in enumerate(lines):
                        ty = title_start_y + line_index * line_step
                        if ty < by + bh - 10:
                            self.text(line, title_pt, (255, 255, 255), center=(cx, ty), outline=True, outline_color=(0, 0, 0), outline_px=1)

                    # Valor destacado com contorno nítido
                    sign = '+' if side == 0 else '-'
                    value = f'{sign}{cfg.amounts[key]}'
                    if key in ('WIN', 'LOSE'):
                        value += ' WIN'
                    val_color = (112, 255, 139) if side == 0 else (255, 131, 147)
                    amount_font = self.get_font(amount_pt)
                    while len(value) > 1 and amount_font.size(value)[0] > max_width:
                        value = value[:-1]
                    val_y = by + bh - max(5, int(7 * card_scale))
                    self.text(value, amount_pt, val_color, center=(cx, val_y), outline=True, outline_color=(0, 0, 0), outline_px=2)

# Toasts de apoiadores
        if self.current_toast and w.phase not in ('celebrating', 'goal', 'defending'):
            e = self.current_toast
            positive = e['action'] in POSITIVE
            box = pg.Surface((500, 64), pg.SRCALPHA)
            box.fill((10, 10, 14, 235))
            self.canvas.blit(box, (110, 185))
            pg.draw.rect(self.canvas, (93, 239, 156) if positive else (255, 125, 140), (110, 185, 5, 64))
            pg.draw.rect(self.canvas, (40, 45, 55), (110, 185, 500, 64), width=1, border_radius=4)
            if getattr(cfg, 'show_supporter_avatar', True):
                raw_avatar = self.avatar_surfaces.get(e['avatar'], self.default_avatar)
                avatar = pg.transform.scale(raw_avatar, (46, 46))
                mask = pg.Surface((46, 46), pg.SRCALPHA)
                pg.draw.circle(mask, (255, 255, 255), (23, 23), 23)
                masked_avatar = avatar.copy()
                masked_avatar.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
                self.canvas.blit(masked_avatar, (122, 194))
                pg.draw.circle(self.canvas, (255, 215, 60), (145, 217), 23, width=2)
                text_x = 180
            else:
                text_x = 125
            icon = self.avatar_surfaces.get(e.get('icon'), self.icons.get(e.get('action'), self.gift_icon))
            self.canvas.blit(pg.transform.scale(icon, (38, 38)), (560, 198))
            self.text(e['name'][:22] + f' ×{e["count"]}', 19, pos=(text_x, 194))
            applied = e.get("applied", e.get("count", 1))
            unit = e.get("unit", "blocos")
            amount = f"{applied:+d} {unit}"
            if e.get("pending"):
                amount += f" · +{e['pending']} na fila"
            self.text(amount, 14, (174, 231, 222), pos=(text_x, 225))

        if not w.running and w.phase != 'goal':
            self.text('INICIE PELO PAINEL' if w.count == 0 else 'PAUSADO', 19, center=(360, 855), outline=True)

    def draw(self):
        self.scene()
        self.draw_fixed_barriers()
        self.draw_effects()
        self.draw_hero_bubble()
        if self.shake:
            offset = int(math.sin(self.time * 90) * self.shake * 18 * self.world.cfg.shake)
            self.canvas.scroll(dx=offset)
        self.hud()

        sw, sh = self.screen.get_size()
        scale = min(sw / 720, sh / 1280)
        tw = max(1, int(720 * scale))
        th = max(1, int(1280 * scale))
        ox = (sw - tw) // 2
        oy = (sh - th) // 2

        self.screen.fill((14, 16, 22))

        # Modo Horizontal: desenha painéis laterais gamers com atalhos e informações da live
        if ox > 60:
            # Painel esquerdo
            pg.draw.rect(self.screen, (20, 24, 32), (0, 0, ox - 4, sh))
            pg.draw.line(self.screen, (40, 50, 65), (ox - 4, 0), (ox - 4, sh), 2)
            self.draw_screen_text('B7 VOXEL LIVE', 20, (255, 215, 60), center=((ox - 4) // 2, 45))
            mode_txt = 'MODO: MANUAL' if self.world.cfg.control_mode == 'manual' else 'MODO: AUTOMÁTICO'
            mode_col = (100, 230, 255) if self.world.cfg.control_mode == 'manual' else (120, 255, 140)
            self.draw_screen_text(mode_txt, 14, mode_col, center=((ox - 4) // 2, 85))
            self.draw_screen_text('CONTROLES:', 13, (180, 195, 215), center=((ox - 4) // 2, 135))
            self.draw_screen_text('A/D / Setas : Mover', 12, (220, 230, 240), center=((ox - 4) // 2, 165))
            self.draw_screen_text('Espaço / Cima : Pular', 12, (220, 230, 240), center=((ox - 4) // 2, 190))
            self.draw_screen_text('M : Alternar Modo', 12, (220, 230, 240), center=((ox - 4) // 2, 215))
            self.draw_screen_text('H : Ocultar Presentes', 12, (220, 230, 240), center=((ox - 4) // 2, 240))
            self.draw_screen_text('P : Pausar Jogo', 12, (220, 230, 240), center=((ox - 4) // 2, 265))
            self.draw_screen_text('Construção ao passar/pular', 11, (255, 215, 80), center=((ox - 4) // 2, 300))

            # Painel direito
            rx = ox + tw + 4
            rw = sw - rx
            if rw > 0:
                pg.draw.rect(self.screen, (20, 24, 32), (rx, 0, rw, sh))
                pg.draw.line(self.screen, (40, 50, 65), (rx, 0), (rx, sh), 2)
                self.draw_screen_text('STATUS DA LIVE', 18, (255, 215, 60), center=(rx + rw // 2, 45))
                self.draw_screen_text(f'RODADA {self.world.round}', 14, (200, 230, 255), center=(rx + rw // 2, 85))
                self.draw_screen_text(f'VITÓRIAS: {self.world.wins}/{self.world.cfg.goal}', 14, (120, 255, 140), center=(rx + rw // 2, 120))
                self.draw_screen_text(f'PROGRESSO: {self.world.progress*100:.0f}%', 14, (255, 220, 80), center=(rx + rw // 2, 155))
                if self.world.pending:
                    self.draw_screen_text(f'PENDENTES: +{self.world.pending}', 13, (120, 220, 255), center=(rx + rw // 2, 190))
                self.draw_screen_text(f'BLOCOS: {self.world.count}/{self.world.capacity}', 12, (180, 195, 215), center=(rx + rw // 2, 225))

        self.screen.blit(pg.transform.scale(self.canvas, (tw, th)), (ox, oy))
        pg.display.flip()

    def draw_screen_text(self, text, size, color, center):
        key = (f'screen_{text}', size, color)
        if key not in self.text_cache:
            self.text_cache[key] = self.get_font(size).render(str(text), True, color)
        surf = self.text_cache[key]
        self.screen.blit(surf, (center[0] - surf.get_width() // 2, center[1] - surf.get_height() // 2))

    def close(self):
        self.avatars.closed.set()
        pg.quit()
