"""Deterministic grid/state machine. Only the game thread mutates this object."""
import math, random
from collections import deque
from configuration import Settings

class World:
    def __init__(self, settings: Settings, seed=7):
        self.cfg=settings; self.rng=random.Random(seed)
        self.wins=0;self.round=1;self.running=False;self.pending=0
        self.changes=deque(maxlen=4096);self.signals=deque(maxlen=256)
        self.restart()
    @property
    def capacity(self):return self.cfg.columns*self.cfg.rows
    @property
    def count(self):return len(self.blocks)
    @property
    def progress(self):return self.count/self.capacity
    @property
    def max_height(self):return max(self.heights,default=0)
    def restart(self, reset_score=False):
        self.blocks={};self.heights=[0]*self.cfg.columns;self.phase='building'
        self.timer=0.;self.credit=0.;self.pending=0;self.changes.clear()
        if reset_score:self.wins=0;self.round=1
        self.signals.append(('reset',None))
    def material(self,row):return min(2,int(row*3/self.cfg.rows))
    def add(self,amount):
        placed=0
        for _ in range(min(int(amount),self.capacity-self.count)):
            minimum=min(self.heights)
            candidates=[i for i,h in enumerate(self.heights) if h<self.cfg.rows and h<=minimum+4]
            # Bias toward valleys while preserving the irregular skyline of the video.
            weights=[1/(1+self.heights[i]-minimum)**0.65 for i in candidates]
            x=self.rng.choices(candidates,weights=weights,k=1)[0];y=self.heights[x]
            self.blocks[x,y]=self.material(y);self.heights[x]+=1
            self.changes.append(('add',x,y,self.material(y)));placed+=1
        self._check_full()
        return placed
    def place_block(self, column):
        """Places a single block on a specific column (used by the explorer/player)."""
        if self.count >= self.capacity or self.phase != 'building':
            return 0
        if 0 <= column < self.cfg.columns and self.heights[column] < self.cfg.rows:
            y = self.heights[column]
            mat = self.material(y)
            self.blocks[column, y] = mat
            self.heights[column] += 1
            self.changes.append(('add', column, y, mat))
            self._check_full()
            return 1
        return 0
    def destroy(self,amount,action):
        removed=0;center=self.rng.randrange(self.cfg.columns)
        for _ in range(min(int(amount),self.count)):
            candidates=[i for i,h in enumerate(self.heights) if h]
            if not candidates:break
            # All attacks work from exposed surfaces, so no unsupported floating cells.
            if action=='TORNADO':
                x=min(candidates,key=lambda c:(abs(c-center),-self.heights[c]));center=(center+1)%self.cfg.columns
            elif action=='ZAP':x=max(candidates,key=lambda c:self.heights[c]-abs(c-center)*0.2)
            else:x=min(candidates,key=lambda c:abs(c-center)*1.2-self.heights[c]*0.3)
            y=self.heights[x]-1;mat=self.blocks.pop((x,y));self.heights[x]-=1
            self.changes.append(('remove',x,y,mat));removed+=1
        if self.phase=='defending' and self.count<self.capacity and self.cfg.cancel_defense:
            self.phase='building';self.timer=0
        return removed,center
    def _check_full(self):
        if self.count==self.capacity and self.phase=='building':
            self.phase='defending';self.timer=self.cfg.defense_seconds
            self.signals.append(('defense',None))
    def add_pending(self,amount):
        accepted=min(amount,max(0,1000000-self.pending));self.pending+=accepted;return accepted
    def score(self,delta):
        self.wins+=int(delta)
        if not self.cfg.allow_negative:self.wins=max(0,self.wins)
        if self.wins>=self.cfg.goal and self.phase not in ('celebrating','goal'):
            self.phase='celebrating';self.timer=3;self.signals.append(('victory',None))
    def tick(self,dt):
        if not self.running:return
        if self.phase=='building':
            if self.pending and self.cfg.pending_policy=='repair':
                n=self.add(min(self.pending,8));self.pending-=n
            self.credit+=dt*self.cfg.build_rate
            n=int(self.credit)
            if n:self.credit-=n;self.add(n)
        elif self.phase=='defending':
            self.timer=max(0,self.timer-dt)
            if self.timer<=0:
                if self.count==self.capacity:
                    self.wins+=1;self.phase='celebrating';self.timer=3
                    self.signals.append(('victory',None))
                else:self.phase='building'
        elif self.phase=='celebrating':
            self.timer-=dt
            if self.timer<=0:
                if self.wins>=self.cfg.goal and not self.cfg.auto_restart:
                    self.phase='goal';self.running=False
                else:
                    pending=self.pending;reached=self.wins>=self.cfg.goal
                    self.restart();self.round+=1
                    if reached:self.wins=0
                    n=self.add(pending);self.pending=pending-n
    def snapshot(self):
        return dict(wins=self.wins,goal=self.cfg.goal,round=self.round,blocks=self.count,
                    capacity=self.capacity,progress=round(self.progress*100,1),phase=self.phase,
                    timer=round(max(0,self.timer),1),pending=self.pending,running=self.running)
