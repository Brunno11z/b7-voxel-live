import threading,time
from fastapi.testclient import TestClient
from configuration import Settings
from runtime import Runtime
from panel.server import make_app

def test_controls_csrf_websocket_simulation_and_validation(tmp_path):
 r=Runtime(Settings(build_rate=0),tmp_path/'settings.json');stop=threading.Event()
 def run():
  while not stop.is_set():r.process_commands();r.publish();time.sleep(.003)
 thread=threading.Thread(target=run);thread.start()
 try:
  with TestClient(make_app(r)) as client:
   assert client.get('/').status_code==200
   token=client.get('/api/session').json()['token'];headers={'Origin':'http://testserver','X-B7-Token':token}
   assert client.post('/api/game/start',json={}).status_code==403
   assert client.post('/api/game/start',json={},headers=headers).status_code==200
   result=client.post('/api/simulate',json={'action':'CHICKEN','count':3,'combo':True},headers=headers)
   assert result.status_code==200 and r.world.count==48
   with client.websocket_connect('/ws',headers={'Origin':'http://testserver'}) as ws:
    ws.send_json({'token':token});state=ws.receive_json();assert state['blocks']==48
    assert 'key' not in state['config']
   assert client.post('/api/game/pause',json={},headers=headers).status_code==200 and not r.world.running
   bad=r.world.cfg.model_dump();bad['rows']=0
   assert client.post('/api/settings',json=bad,headers=headers).status_code==422
   assert client.post('/api/game/reset',json={},headers=headers).status_code==200 and r.world.count==0
 finally:stop.set();thread.join()
