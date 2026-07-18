import argparse,json,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from lwm_fab.control_plane import *
from lwm_fab.mcp import MCPServerManager
from lwm_fab.triggers import WorkflowCatalog,TriggerEngine
class Service:
 def __init__(self,workspace,state,mcp=None,token=None):
  self.state=Path(state);self.state.mkdir(parents=True,exist_ok=True);b=CapabilityBus();register_builtin_linux_capabilities(b,workspace);self.rt=AutomationControlPlane(b,AuditLog(self.state/"audit.jsonl"));self.m=MCPServerManager(b);self.token=token;self.workflows={};self.catalog=WorkflowCatalog(state);self.triggers=TriggerEngine(self.rt,self.catalog,self.persist)
  if mcp:self.m.load_config(mcp)
 def persist(self,w,r):self.workflows[r.run_id]=w;(self.state/"runs").mkdir(exist_ok=True);(self.state/"runs"/f"{r.run_id}.json").write_text(json.dumps({"workflow":w.to_dict(),"run":r.to_dict()},indent=2))
 def run(self,d):w=Workflow.from_dict(d);r=self.rt.start(w);self.persist(w,r);return r
class Handler(BaseHTTPRequestHandler):
 service=None
 def out(self,n,d):b=json.dumps(d,default=str).encode();self.send_response(n);self.send_header("Content-Type","application/json");self.send_header("Access-Control-Allow-Origin","*");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
 def auth(self):
  if self.service.token and self.headers.get("Authorization")!=f"Bearer {self.service.token}":self.out(401,{"error":"Unauthorized"});return False
  return True
 def do_GET(self):
  if self.path=="/health":return self.out(200,{"status":"ok","mcp":self.service.m.status()})
  if not self.auth():return
  if self.path=="/capabilities":return self.out(200,{"capabilities":self.service.rt.bus.discover()})
  if self.path=="/workflows":return self.out(200,{"workflows":self.service.catalog.list()})
  if self.path.startswith("/runs/"):
   try:return self.out(200,self.service.rt.get_run(self.path.split("/")[2]).to_dict())
   except KeyError:return self.out(404,{"error":"Run not found"})
  self.out(404,{"error":"Not found"})
 def do_POST(self):
  try:
   if self.path.startswith("/webhooks/"):return self.out(202,self.service.triggers.fire_webhook(self.path[10:]).to_dict())
   if not self.auth():return
   if self.path=="/workflows/run":return self.out(202,self.service.run(self.body()).to_dict())
   if self.path=="/workflows":w=Workflow.from_dict(self.body());self.service.rt.validate(w);self.service.catalog.save(w);return self.out(201,w.to_dict())
   if self.path=="/triggers/webhook":d=self.body();return self.out(201,self.service.triggers.add_webhook(d["workflow_id"],d.get("path")).to_dict())
   if self.path=="/triggers/interval":d=self.body();return self.out(201,self.service.triggers.add_interval(d["workflow_id"],float(d["seconds"])).to_dict())
   if self.path.endswith("/approve"):d=self.body();return self.out(200,self.service.rt.approve(self.path.split("/")[2],d["step_id"]).to_dict())
   self.out(404,{"error":"Not found"})
  except Exception as e:self.out(400,{"error":str(e)})
 def log_message(self,*a):pass
def main():
 p=argparse.ArgumentParser();p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=8765);p.add_argument("--workspace",default=".");p.add_argument("--state-dir",default=".lwm-os");p.add_argument("--mcp-config");a=p.parse_args();Handler.service=Service(a.workspace,a.state_dir,a.mcp_config,os.getenv("LWM_API_TOKEN"));ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
if __name__=="__main__":main()
