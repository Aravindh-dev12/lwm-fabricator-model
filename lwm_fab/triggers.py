from dataclasses import dataclass
import json,time,uuid
from pathlib import Path
@dataclass
class Trigger:
 trigger_id:str;workflow_id:str;kind:str;enabled:bool=True;interval_seconds:float|None=None;webhook_path:str|None=None;next_run_at:float|None=None
 def to_dict(self):return vars(self).copy()
class WorkflowCatalog:
 def __init__(self,state_dir):self.directory=Path(state_dir)/"workflows";self.directory.mkdir(parents=True,exist_ok=True)
 def save(self,w):(self.directory/f"{w.workflow_id}.json").write_text(json.dumps(w.to_dict(),indent=2))
 def get(self,i):
  from .control_plane import Workflow
  return Workflow.from_dict(json.loads((self.directory/f"{i}.json").read_text()))
 def list(self):return [json.loads(p.read_text()) for p in self.directory.glob("*.json")]
class TriggerEngine:
 def __init__(self,runtime,catalog,on_run=None):self.runtime=runtime;self.catalog=catalog;self.on_run=on_run;self.path=catalog.directory.parent/"triggers.json";self.triggers={};self._load()
 def _load(self):
  if self.path.exists():
   for d in json.loads(self.path.read_text()):t=Trigger(**d);self.triggers[t.trigger_id]=t
 def _save(self):self.path.write_text(json.dumps([t.to_dict() for t in self.triggers.values()],indent=2))
 def add_webhook(self,w,path=None):self.catalog.get(w);t=Trigger(str(uuid.uuid4()),w,"webhook",webhook_path=(path or str(uuid.uuid4())).strip("/"));self.triggers[t.trigger_id]=t;self._save();return t
 def add_interval(self,w,seconds):
  if seconds<1:raise ValueError("Interval must be at least one second")
  self.catalog.get(w);t=Trigger(str(uuid.uuid4()),w,"interval",interval_seconds=seconds,next_run_at=time.time()+seconds);self.triggers[t.trigger_id]=t;self._save();return t
 def _run(self,w):
  wf=self.catalog.get(w);r=self.runtime.start(wf)
  if self.on_run:self.on_run(wf,r)
  return r
 def fire_webhook(self,path):
  t=next((t for t in self.triggers.values() if t.enabled and t.webhook_path==path.strip("/")),None)
  if not t:raise KeyError("Webhook not found")
  return self._run(t.workflow_id)
 def tick(self,now=None):
  now=now or time.time();due=[t for t in self.triggers.values() if t.enabled and t.kind=="interval" and (t.next_run_at or 0)<=now]
  for t in due:t.next_run_at=now+(t.interval_seconds or 1)
  if due:self._save()
  return [self._run(t.workflow_id) for t in due]
