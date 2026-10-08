"""Validated public settings and atomic persistence. No secrets in this model."""
import json, os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

ROOT = Path(__file__).resolve().parent
ACTIONS = ['BUILD','CHICKEN','PHOENIX','SKY_WHALE','WIN','ZAP','TNT','BLACK_HOLE','TORNADO','LOSE']
DEFAULT_AMOUNTS = dict(zip(ACTIONS, [8, 16, 36, 60, 1, 3, 8, 12, 18, 1]))
Action = Literal['BUILD','CHICKEN','PHOENIX','SKY_WHALE','WIN','ZAP','TNT','BLACK_HOLE','TORNADO','LOSE']

DEFAULT_ACTION_BADGES = {
    'BUILD': '🧱',
    'CHICKEN': '🐔',
    'PHOENIX': '🦅',
    'SKY_WHALE': '🐋',
    'WIN': '🏆',
    'ZAP': '⚡',
    'TNT': '💣',
    'BLACK_HOLE': '🕳️',
    'TORNADO': '🌪️',
    'LOSE': '💀'
}

DEFAULT_SKIN_COLORS = {
    'hair': '#3e2a1b',
    'skin': '#b17d59',
    'shirt': '#0fa8ad',
    'pants': '#3e3e8b',
    'shoes': '#44474d',
    'accent': '#e9e8de'
}

class Rule(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    action: Action = 'BUILD'
    amount: int = Field(1, ge=1, le=1000)
    threshold: int = Field(50, ge=1, le=100000)
    cooldown: float = Field(5, ge=0, le=3600)
    word: str = Field('construir', max_length=80)

class Mapping(BaseModel):
    model_config = ConfigDict(extra='forbid')
    gift_id: str = Field('', max_length=30, pattern=r'^\d*$')
    gift_name: str = Field('', max_length=80)
    action: Action = 'BUILD'

class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field('', max_length=80, pattern=r'^@?[A-Za-z0-9_.]*$')
    mode: Literal['test','live'] = 'test'
    control_mode: Literal['auto','manual'] = 'auto'
    columns: int = Field(14, ge=8, le=20)
    rows: int = Field(30, ge=6, le=60)
    build_rate: float = Field(3.5, ge=0, le=80)
    goal: int = Field(10, ge=1, le=10000)
    defense_seconds: float = Field(10, ge=1, le=120)
    cancel_defense: bool = True
    allow_negative: bool = True
    pending_policy: Literal['repair','next_round'] = 'repair'
    auto_restart: bool = True
    resolution: Literal['540x960','720x1280','1080x1920'] = '720x1280'
    borderless: bool = False
    show_barriers: bool = True
    show_supporter_avatar: bool = True
    show_thought_bubble: bool = True
    show_thought_bubble_manual: bool = False
    skin_preset: Literal['rei_coroa','pato_dourado','aesthetic_boy','guerreiro_voxel'] = 'rei_coroa'
    skin_colors: dict[str, str] = Field(default_factory=lambda: DEFAULT_SKIN_COLORS.copy())
    camera_smoothing: float = Field(3, ge=0.5, le=10)
    shake: float = Field(0.7, ge=0, le=2)
    volume: float = Field(0.5, ge=0, le=1)
    effects_volume: float = Field(0.8, ge=0, le=1)
    particles: int = Field(400, ge=0, le=1200)
    amounts: dict[Action, int] = Field(default_factory=lambda: DEFAULT_AMOUNTS.copy())
    action_badges: dict[Action, str] = Field(default_factory=lambda: DEFAULT_ACTION_BADGES.copy())
    mappings: list[Mapping] = Field(default_factory=list, max_length=200)
    likes: Rule = Field(default_factory=Rule)
    follows: Rule = Field(default_factory=Rule)
    comments: Rule = Field(default_factory=Rule)
    shares: Rule = Field(default_factory=Rule)

    def checked(self):
        if set(self.amounts) != set(ACTIONS) or any(v < 1 or v > 10000 for v in self.amounts.values()):
            raise ValueError('Quantidades: informe todas as ações, de 1 a 10000.')
        # Ensure action badges contain all actions
        for a in ACTIONS:
            if a not in self.action_badges:
                self.action_badges[a] = DEFAULT_ACTION_BADGES.get(a, '🎁')
        # Only validate filled-in mappings; ignore completely blank items
        non_empty = [m for m in self.mappings if m.gift_id.strip() or m.gift_name.strip()]
        ids = [m.gift_id.strip() for m in non_empty if m.gift_id.strip()]
        names = [m.gift_name.strip().casefold() for m in non_empty if not m.gift_id.strip() and m.gift_name.strip()]
        if len(set(ids)) != len(ids):
            raise ValueError('Existem presentes com IDs duplicados.')
        if len(set(names)) != len(names):
            raise ValueError('Existem presentes com nomes duplicados.')
        return self

def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def load_settings(path=None):
    path = Path(path or ROOT / 'config/settings.json')
    return Settings.model_validate_json(path.read_text('utf8')).checked() if path.exists() else Settings()
