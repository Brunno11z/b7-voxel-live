import random,threading,time
import pytest
from configuration import Settings,DEFAULT_AMOUNTS,load_settings
from game.model import World
from services.events import Event,EventRouter
from runtime import Runtime

def world(**kwargs):
 w=World(Settings(build_rate=0,**kwargs));w.running=True;return w

def test_grid_progress_materials_and_irregular_skyline():
 w=world();assert w.add(205)==205
 assert w.count==sum(w.heights)==205
 assert len(set(w.heights))>1
 assert w.progress==205/420
 assert all(w.blocks[x,y]==w.material(y) for x,y in w.blocks)
 assert all((x,y) in w.blocks for x,h in enumerate(w.heights) for y in range(h))

@pytest.mark.parametrize('action,amount', [('ZAP',3),('TNT',8),('BLACK_HOLE',12),('TORNADO',18)])
def test_attack_conserves_grid(action,amount):
 w=world();w.add(100);n,_=w.destroy(amount,action)
 assert n==amount and w.count==100-amount
 assert all((x,y) in w.blocks for x,h in enumerate(w.heights) for y in range(h))
 w.destroy(9999,action);assert w.count==0 and all(h==0 for h in w.heights)

@pytest.mark.parametrize('action',list(DEFAULT_AMOUNTS))
def test_every_gift_exact_amount(action):
 w=world(goal=100);w.add(140);router=EventRouter(w);before=w.count
 result=router.process(Event(test_action=action,count=3,id='one'))
 n=DEFAULT_AMOUNTS[action]*3
 if action=='WIN':assert w.wins==3
 elif action=='LOSE':assert w.wins==-3
 elif action in ('BUILD','CHICKEN','PHOENIX','SKY_WHALE'):assert w.count==before+n
 else:assert w.count==before-n
 assert result and router.process(Event(test_action=action,count=3,id='one')) is None

def test_combo_cumulative_and_final_retransmission():
 w=world();r=EventRouter(w)
 for i,(n,final) in enumerate([(1,False),(2,False),(2,False),(5,False),(5,True),(5,True)]):
  r.process(Event(test_action='BUILD',combo_id='abc',streakable=True,count=n,final=final,id=str(i)))
 assert w.count==40
 r.process(Event(test_action='BUILD',combo_id='new',streakable=True,count=2,final=True))
 assert w.count==56

def test_combo_without_group_waits_for_final():
 w=world();r=EventRouter(w)
 for i,n in enumerate([1,2,3]):r.process(Event(test_action='BUILD',id=str(i),count=n,streakable=True,final=False))
 assert w.count==0
 for _ in range(2):r.process(Event(test_action='BUILD',id='final',count=3,streakable=True,final=True))
 assert w.count==24

def test_defense_cancels_and_restarts_full_time():
 w=world(defense_seconds=2);w.add(w.capacity);w.tick(1)
 assert w.phase=='defending' and w.timer==1
 w.destroy(3,'ZAP');assert w.phase=='building'
 w.add(3);assert w.timer==2
 w.tick(2);assert w.wins==1 and w.phase=='celebrating'
 w.tick(1);assert w.wins==1
 w.tick(2);assert w.phase=='building' and w.count==0 and w.wins==1

def test_non_cancel_defense_still_requires_full_grid():
 w=world(defense_seconds=2,cancel_defense=False);w.add(w.capacity);w.destroy(8,'TNT')
 assert w.phase=='defending';w.tick(3);assert w.wins==0 and w.phase=='building'

def test_pending_policies_and_score_limits():
 for policy in ['repair','next_round']:
  w=world(pending_policy=policy,defense_seconds=1);r=EventRouter(w)
  w.add(w.capacity-2);result=r.process(Event(test_action='BUILD'))
  assert result['applied']==2 and result['pending']==6
  w.destroy(3,'ZAP');w.tick(.01)
  if policy=='repair':assert w.count==w.capacity and w.pending==3
  else:
   assert w.count==w.capacity-3 and w.pending==6
   w.add(3)
  w.tick(1);w.tick(3);assert w.count==w.capacity-w.capacity+(3 if policy=='repair' else 6)
 w=world(allow_negative=False);w.score(-4);assert w.wins==0

def test_goal_pause_and_auto_restart():
 w=world(goal=1,auto_restart=False,defense_seconds=1);w.add(w.capacity);w.tick(1);w.tick(3)
 assert w.phase=='goal' and not w.running and w.wins==1
 w=world(goal=1,auto_restart=True,defense_seconds=1);w.add(w.capacity);w.tick(1);w.tick(3)
 assert w.phase=='building' and w.running and w.wins==0

def test_frame_rate_independent_construction():
 a=World(Settings(build_rate=7));b=World(Settings(build_rate=7));a.running=b.running=True
 for _ in range(240):a.tick(1/24)
 for _ in range(1200):b.tick(1/120)
 assert abs(a.count-b.count)<=1 and a.count in (69,70)

def test_real_mode_gift_mapping_and_test_isolation():
 cfg=Settings(mode='live',build_rate=0,mappings=[dict(gift_id='12345',gift_name='Custom',action='TNT')])
 w=World(cfg);w.running=True;w.add(100);r=EventRouter(w)
 assert r.process(Event(source='test',test_action='BUILD')) is None
 e=Event(source='live',gift_id='12345',gift_name='Custom',id='evt')
 r.process(e);assert w.count==92
 r.process(e);assert w.count==92
 assert list(r.catalog)==['12345']

def test_rules_threshold_word_and_cooldown():
 w=world();w.cfg.likes.enabled=True;w.cfg.likes.threshold=10;w.cfg.likes.cooldown=0
 w.cfg.comments.enabled=True;w.cfg.comments.word='construir';w.cfg.comments.cooldown=5
 r=EventRouter(w)
 r.process(Event(kind='like',count=9,id='a'));assert w.count==0
 r.process(Event(kind='like',count=12,id='b'));assert w.count==2
 assert r.process(Event(kind='comment',comment=' CONSTRUIR ',id='c'))
 assert r.process(Event(kind='comment',comment='construir',id='d')) is None
 assert r.process(Event(kind='comment',comment='__import__(os)',user_id='x',id='e')) is None

def test_many_interleaved_actions_keep_invariants():
 w=world();r=EventRouter(w);rng=random.Random(19)
 for i in range(1000):
  action=rng.choice(['BUILD','CHICKEN','PHOENIX','ZAP','TNT','TORNADO'])
  r.process(Event(test_action=action,id=str(i)))
  if w.phase in ('celebrating','goal'):w.restart();w.running=True
  w.tick(.05)
  assert w.count==sum(w.heights)==len(w.blocks)
  assert 0<=w.progress<=1
  assert all(0<=x<w.cfg.columns and 0<=y<w.cfg.rows for x,y in w.blocks)

def test_concurrent_producers_one_game_thread_and_persistence(tmp_path):
 runtime=Runtime(Settings(build_rate=0,rows=60),tmp_path/'settings.json');runtime.world.running=True
 def send(k):
  for i in range(40):runtime.submit_event(Event(test_action='BUILD',id=f'{k}-{i}'))
 threads=[threading.Thread(target=send,args=(k,)) for k in range(5)]
 for t in threads:t.start()
 for t in threads:t.join()
 while not runtime.commands.empty():runtime.process_commands()
 assert runtime.world.count+runtime.world.pending==5*40*8
 cfg=runtime.world.cfg.model_dump();cfg['volume']=.2;cfg['goal']=17
 f=runtime.command('settings',cfg);runtime.process_commands();assert f.result()['ok']
 reloaded=load_settings(tmp_path/'settings.json');assert reloaded.goal==17 and reloaded.volume==.2

def test_character_walk_jump_fall_and_collisions():
 import pygame as pg
 from game.actor import Explorer
 pg.init();w=world();w.add(140);hero=Explorer(w)
 # Start on a column surface to evaluate normal physics, not loading inside a prefilled wall.
 hero.box.centerx=52+6.5*hero.cell;hero.box.bottom=-w.heights[6]*hero.cell
 states=set();xs=set()
 for i in range(1400):
  if i==400:w.destroy(100,'TORNADO')
  hero.tick(1/120);states.add(hero.state);xs.add(round(hero.box.x))
  assert not any(hero.box.colliderect(r) for r in hero.rects(hero.box))
  assert hero.box.bottom<=.001
 assert 'walk' in states and 'jump' in states and 'fall' in states and len(xs)>50
 pg.quit()
