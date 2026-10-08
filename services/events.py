"""One normalized event path for offline tests and actual live messages."""
import time, unicodedata
from dataclasses import dataclass, field
from collections import OrderedDict
from configuration import ACTIONS
@dataclass
class Event:
    kind: str = 'gift'
    id: str = ''
    user_id: str = 'test'
    name: str = 'Visitante'
    avatar: str = ''
    gift_id: str = ''
    gift_name: str = ''
    gift_icon: str = ''
    count: int = 1
    combo_id: str = ''
    streakable: bool = False
    final: bool = True
    comment: str = ''
    source: str = 'test'
    test_action: str = ''
    timestamp: float = field(default_factory=time.time)

def normalize_text(value):
    return unicodedata.normalize('NFKC',str(value)).strip().casefold()[:200]
class EventRouter:
    def __init__(self,world):
        self.world=world;self.seen=OrderedDict();self.combos=OrderedDict()
        self.cooldowns=OrderedDict();self.likes=OrderedDict();self.effects=deque_factory()
        self.catalog=OrderedDict();self.notice=''
    def prune(self,cache,now,ttl=1800,limit=4096):
        while cache and (len(cache)>limit or now-next(iter(cache.values()))[0]>ttl):cache.popitem(last=False)
    def delta(self,event):
        now=time.monotonic()
        for cache in (self.seen,self.combos,self.cooldowns,self.likes):self.prune(cache,now)
        n=max(1,int(event.count))
        if event.streakable and event.combo_id:
            key=(event.source,event.user_id,event.gift_id or event.test_action,event.combo_id)
            old=self.combos.get(key,(now,0))[1]
            self.combos[key]=(now,max(old,n));self.combos.move_to_end(key)
            return max(0,n-old)
        # If a stable group id is absent, process only the final cumulative message.
        if event.streakable and not event.final:return 0
        if event.id:
            key=(event.source,event.kind,event.id)
            if key in self.seen:return 0
            self.seen[key]=(now,True)
        return n
    def process(self,e):
        cfg=self.world.cfg
        if e.kind=='gift' and e.gift_id:
            self.catalog[e.gift_id]={'id':e.gift_id,'name':e.gift_name[:80],'icon':e.gift_icon}
            if len(self.catalog)>400:self.catalog.popitem(last=False)
        if e.source!=cfg.mode:return None
        n=self.delta(e)
        if n<=0:return None
        action=None;quantity=0
        if e.kind=='gift':
            if e.source=='test' and e.test_action in ACTIONS:action=e.test_action
            else:
                for m in cfg.mappings:
                    if (m.gift_id and m.gift_id==e.gift_id) or (not m.gift_id and normalize_text(m.gift_name)==normalize_text(e.gift_name)):
                        action=m.action;break
            if not action:
                self.notice=f'Presente recebido sem vínculo: {e.gift_name} (ID {e.gift_id})'
                return None
            quantity=cfg.amounts[action]*n
        else:
            name={'like':'likes','follow':'follows','comment':'comments','share':'shares'}.get(e.kind)
            if not name:return None
            rule=getattr(cfg,name)
            if not rule.enabled:return None
            if e.kind=='comment' and normalize_text(e.comment)!=normalize_text(rule.word):return None
            now=time.monotonic();key=(e.kind,e.user_id)
            if now-self.cooldowns.get(key,(-1e12,0))[0]<rule.cooldown:return None
            multiplier=1
            if e.kind=='like':
                total=self.likes.get(e.user_id,(now,0))[1]+n
                multiplier,total=divmod(total,rule.threshold)
                self.likes[e.user_id]=(now,total);self.likes.move_to_end(e.user_id)
                if not multiplier:return None
            self.cooldowns[key]=(now,True);self.cooldowns.move_to_end(key)
            action=rule.action;quantity=rule.amount*multiplier
        # Fair pause behavior: paused game rejects gameplay, clearly surfaced in status.
        if not self.world.running or self.world.phase in ('celebrating','goal'):
            self.notice='Interação recebida durante pausa/comemoração; sem aplicação.'
            return None
        pending=0;target=None
        if action in ('WIN','LOSE'):
            before=self.world.wins;self.world.score(quantity if action=='WIN' else -quantity)
            applied=self.world.wins-before;unit='vitória(s)'
        elif action in ('BUILD','CHICKEN','PHOENIX','SKY_WHALE'):
            applied=self.world.add(quantity);pending=self.world.add_pending(quantity-applied);unit='blocos'
        else:
            amount,target=self.world.destroy(quantity,action);applied=-amount;unit='blocos'
        result=dict(action=action,name=e.name[:40],avatar=e.avatar,gift=e.gift_name[:60],icon=e.gift_icon,
                    count=n,applied=applied,pending=pending,unit=unit,target=target,source=e.source)
        self.effects.append(result)
        return result

def deque_factory():
    from collections import deque
    return deque(maxlen=200)
