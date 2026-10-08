"""Shared, explicit action descriptions used by the game's live gift guide."""
NAMES={'BUILD':'Construção','CHICKEN':'Galinha','PHOENIX':'Fênix','SKY_WHALE':'Baleia do céu','WIN':'Vitória extra','ZAP':'Raio','TNT':'Explosão TNT','BLACK_HOLE':'Buraco negro','TORNADO':'Tornado','LOSE':'Perder vitória'}
def action_description(action,amount):
    if action=='WIN':return f'Ganha {amount} vitória'+('s' if amount!=1 else '')
    if action=='LOSE':return f'Perde {amount} vitória'+('s' if amount!=1 else '')
    verb='Constrói' if action in ('BUILD','CHICKEN','PHOENIX','SKY_WHALE') else 'Destrói'
    return f'{verb} {amount} blocos'
def gift_caption(action,settings,catalog):
    bindings=[m for m in settings.mappings if m.action==action]
    if not bindings:return 'Sem presente vinculado',''
    m=bindings[0];detected=catalog.get(m.gift_id,{})
    label=m.gift_name or detected.get('name') or f'ID {m.gift_id}'
    if len(bindings)>1:label+=f' +{len(bindings)-1}'
    return label,detected.get('icon','')
