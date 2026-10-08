import math, random
import pygame as pg

class Explorer:
    def __init__(self, world):
        self.world = world
        self.rng = random.Random(44)
        self.reset()

    @property
    def cell(self):
        return 616 / self.world.cfg.columns

    def reset(self):
        self.box = pg.FRect(305, -100, 30, 94)
        self.vx = 0.0
        self.vy = 0.0
        self.direction = 1
        self.grounded = False
        self.time = 0.0
        self.state = 'idle'
        self.cooldown = 0.0
        self.stuck = 0.0
        self.land_timer = 0.0
        self.build_timer = 0.0
        self.coyote_timer = 0.0
        self.place_cooldown = 0.0
        self.last_col = -1

    def rects(self, rect):
        c = self.cell
        left = 52
        lo = max(0, int((rect.left - left) // c) - 1)
        hi = min(self.world.cfg.columns, int((rect.right - left) // c) + 2)
        low = max(0, int(-rect.bottom // c) - 1)
        high = min(self.world.cfg.rows, int(-rect.top // c) + 2)
        return [pg.FRect(left + x * c, -(y + 1) * c, c, c) for x in range(lo, hi) for y in range(low, high) if (x, y) in self.world.blocks]

    def recover_new_blocks(self):
        # Construction can appear below the feet: push to the highest overlapping surface.
        hits = [r for r in self.rects(self.box) if self.box.colliderect(r)]
        if hits:
            self.box.bottom = min(r.top for r in hits)
            self.vy = min(0, self.vy)
            self.grounded = True

    def tick(self, dt, keys=None):
        self.time += dt
        self.cooldown = max(0, self.cooldown - dt)
        self.land_timer = max(0, self.land_timer - dt)
        self.build_timer = max(0, self.build_timer - dt)
        self.place_cooldown = max(0, self.place_cooldown - dt)
        self.recover_new_blocks()

        auto_mode = (self.world.cfg.control_mode == 'auto')
        manual_left = False
        manual_right = False
        manual_jump = False

        if keys is not None and not auto_mode:
            try:
                manual_left = bool(keys[pg.K_LEFT] or keys[pg.K_a])
                manual_right = bool(keys[pg.K_RIGHT] or keys[pg.K_d])
                manual_jump = bool(keys[pg.K_UP] or keys[pg.K_w] or keys[pg.K_SPACE])
            except Exception:
                pass

        jumped = False
        landed = False

        c = self.cell
        current_col = max(0, min(self.world.cfg.columns - 1, int((self.box.centerx - 52) // c)))

        if not auto_mode and keys is not None:
            # Manual player control
            target_vx = 0.0
            if manual_left:
                target_vx -= 110.0
                self.direction = -1
            if manual_right:
                target_vx += 110.0
                self.direction = 1

            accel = 750.0 if self.grounded else 450.0
            if target_vx != 0.0:
                if self.vx < target_vx:
                    self.vx = min(target_vx, self.vx + accel * dt)
                else:
                    self.vx = max(target_vx, self.vx - accel * dt)
            else:
                friction = 850.0 if self.grounded else 200.0
                if self.vx > 0:
                    self.vx = max(0.0, self.vx - friction * dt)
                elif self.vx < 0:
                    self.vx = min(0.0, self.vx + friction * dt)

            # Manual jump
            if (self.grounded or self.coyote_timer > 0) and manual_jump and not self.cooldown:
                self.vy = -580.0
                self.grounded = False
                self.coyote_timer = 0.0
                self.cooldown = 0.4
                jumped = True

            # Manual placement: as the character moves, place blocks
            if self.place_cooldown <= 0 and (manual_left or manual_right or abs(self.vx) > 15.0):
                target_col = current_col
                ahead_col = current_col + self.direction
                if 0 <= ahead_col < self.world.cfg.columns and self.world.heights[ahead_col] < self.world.heights[current_col]:
                    target_col = ahead_col
                if self.world.place_block(target_col):
                    self.build_timer = 0.18
                    self.place_cooldown = 0.32
                    self.recover_new_blocks()
        else:
            # Autonomous AI navigation
            if self.box.left < 54:
                self.direction = 1
            if self.box.right > 666:
                self.direction = -1

            ahead = self.box.move(self.direction * 26, 0)
            obstacle = any(ahead.colliderect(r) for r in self.rects(ahead))
            probe = pg.FRect(self.box.centerx + self.direction * 40, self.box.bottom, 10, 12)
            ledge = not any(probe.colliderect(r) for r in self.rects(probe)) and self.box.bottom < -1

            if self.grounded and not self.cooldown and (obstacle or ledge or self.rng.random() < dt * 0.5):
                self.vy = -580.0
                self.grounded = False
                self.cooldown = 0.65
                jumped = True

            self.vx = self.direction * (88.0 if self.grounded else 100.0)

        # Horizontal move & collide
        dx = self.vx * dt
        oldx = self.box.x
        self.box.x += dx
        for r in self.rects(self.box):
            if self.box.colliderect(r):
                if dx > 0:
                    self.box.right = r.left
                else:
                    self.box.left = r.right
                self.vx = 0.0

        self.box.clamp_ip(pg.FRect(52, -10000, 616, 20000))
        if abs(self.box.x - oldx) < 0.1 and auto_mode:
            self.stuck += dt
        else:
            self.stuck = 0.0
        if self.stuck > 1.8 and auto_mode:
            self.direction *= -1
            self.stuck = 0.0
            self.cooldown = 0.0

        # Vertical move & collide
        self.vy = min(800.0, self.vy + 1200.0 * dt)
        dy = self.vy * dt
        before = self.grounded
        self.grounded = False
        self.box.y += dy

        for r in self.rects(self.box):
            if self.box.colliderect(r):
                if dy >= 0:
                    self.box.bottom = r.top
                    self.grounded = True
                else:
                    self.box.top = r.bottom
                self.vy = 0.0

        if self.box.bottom >= 0:
            self.box.bottom = 0.0
            self.vy = 0.0
            self.grounded = True

        if self.grounded and not before:
            self.land_timer = 0.13
            landed = True
            self.coyote_timer = 0.0
        elif not self.grounded and before:
            self.coyote_timer = 0.10

        if self.coyote_timer > 0:
            self.coyote_timer -= dt

        # State determination
        self.state = ('celebrate' if self.world.phase in ('celebrating', 'goal') else
                      'land' if self.land_timer else
                      'build' if self.build_timer > 0 else
                      'walk' if self.grounded else
                      'jump' if self.vy < 0 else 'fall')

        if self.grounded and self.cooldown > 0.45:
            self.state = 'build'

        return jumped, landed
