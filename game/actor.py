import math, random
import pygame as pg

SCENARIO_LEFT = 52
SCENARIO_WIDTH = 616
SCENARIO_RIGHT = SCENARIO_LEFT + SCENARIO_WIDTH

class Explorer:
    def __init__(self, world):
        self.world = world
        self.rng = random.Random(44)
        self.reset()

    @property
    def cell(self):
        return SCENARIO_WIDTH / self.world.cfg.columns

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
        self.col_walk_dist = 0.0
        self.current_material = 0

    def rects(self, rect):
        c = self.cell
        left = SCENARIO_LEFT
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
                manual_left = bool(keys.get(pg.K_LEFT) or keys.get(pg.K_a))
                manual_right = bool(keys.get(pg.K_RIGHT) or keys.get(pg.K_d))
                manual_jump = bool(keys.get(pg.K_UP) or keys.get(pg.K_w) or keys.get(pg.K_SPACE))
            except Exception:
                pass

        jumped = False
        landed = False

        c = self.cell
        current_col = max(0, min(self.world.cfg.columns - 1, int((self.box.centerx - SCENARIO_LEFT) // c)))

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
        else:
            # Autonomous AI navigation within the scenario boundaries (52 to 668)
            if self.box.left < SCENARIO_LEFT + 2:
                self.direction = 1
            if self.box.right > SCENARIO_RIGHT - 2:
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

        self.box.clamp_ip(pg.FRect(SCENARIO_LEFT, -10000, SCENARIO_WIDTH, 20000))
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

        # Unified Building Rule (both Manual and Auto):
        # Normal construction happens when:
        # 1. Passing over a block ("passa por cima"): moving horizontally across columns
        # 2. Jumping over a block ("pula pelo bloco"): during jump initiation or in-air
        if self.world.running and self.world.phase == 'building' and self.world.credit >= 1.0 and self.place_cooldown <= 0:
            should_place = False
            target_col = current_col

            # Rule 1: Passing over a block (walking horizontally across columns)
            if self.grounded and abs(self.vx) > 15.0:
                if current_col != self.last_col:
                    should_place = True
                    target_col = current_col
                else:
                    self.col_walk_dist += abs(dx)
                    if self.col_walk_dist >= c * 0.75:
                        should_place = True
                        target_col = current_col
                        self.col_walk_dist = 0.0

            # Rule 2: Jumping over a block (pula pelo bloco)
            elif jumped or (not self.grounded and self.vy < 0):
                should_place = True
                ahead_col = current_col + self.direction
                if 0 <= ahead_col < self.world.cfg.columns and self.world.heights[ahead_col] <= self.world.heights[current_col]:
                    target_col = ahead_col
                else:
                    target_col = current_col

            if should_place:
                if self.world.place_block(target_col):
                    self.world.credit -= 1.0
                    self.last_col = target_col
                    self.place_cooldown = 0.20
                    self.build_timer = 0.18
                    self.current_material = self.world.material(max(0, self.world.heights[target_col] - 1))
                    self.recover_new_blocks()

        # State determination
        self.state = ('celebrate' if self.world.phase in ('celebrating', 'goal') else
                      'land' if self.land_timer else
                      'build' if self.build_timer > 0 else
                      'walk' if self.grounded and abs(self.vx) > 5 else
                      'jump' if self.vy < 0 else 'fall' if not self.grounded else 'idle')

        return jumped, landed
