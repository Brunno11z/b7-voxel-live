"""Generate reproducible gameplay screenshots without connecting to TikTok."""
import os,sys
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from configuration import Settings
from game.model import World
from game.render import Renderer
from services.events import EventRouter,Event
import pygame as pg
out=ROOT/'previews';out.mkdir(exist_ok=True)
w=World(Settings(build_rate=0));r=EventRouter(w);v=Renderer(w);w.running=True
for name,n,effect in [('01_inicio',58,None),('02_construcao',220,'PHOENIX'),('03_diamante',350,'TORNADO'),('04_defesa',420,None)]:
 w.restart();w.add(n);v.consume(r)
 v.hero.box.centerx=52+7.5*v.hero.cell;v.hero.box.bottom=-w.heights[7]*v.hero.cell
 for i in range(200):
  if effect and i==145:r.process(Event(test_action=effect,id=name,name='Bruno',count=1))
  w.tick(1/120);v.tick(1/120,r)
 v.draw();pg.image.save(v.canvas,out/f'{name}.png')
v.close()
print(out)
