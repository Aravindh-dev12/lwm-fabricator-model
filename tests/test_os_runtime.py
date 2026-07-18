import os,sys,tempfile,unittest
from pathlib import Path
from lwm_fab.control_plane import *
from lwm_fab.mcp import StdioMCPClient
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);b=CapabilityBus();register_builtin_linux_capabilities(b,self.root/"work");self.rt=AutomationControlPlane(b,AuditLog(self.root/"audit.jsonl"))
 def tearDown(self):self.t.cleanup()
 def test_approval_resume(self):
  w=Workflow.from_dict({"name":"x","steps":[{"id":"w","capability":"linux.files.write","arguments":{"path":"a","content":"ok"}},{"id":"r","capability":"linux.files.read","arguments":{"path":"a"},"depends_on":["w"]}]});r=self.rt.start(w);self.assertEqual(r.state,RunState.WAITING_APPROVAL);r=self.rt.approve(r.run_id,"w");self.assertEqual(r.results["r"].output["content"],"ok")
 def test_cycle_rejected(self):
  w=Workflow.from_dict({"steps":[{"id":"a","capability":"linux.system.info","depends_on":["b"]},{"id":"b","capability":"linux.system.info","depends_on":["a"]}]})
  with self.assertRaises(WorkflowValidationError):self.rt.start(w)
 def test_workspace_escape(self):
  r=self.rt.start(Workflow.from_dict({"steps":[{"id":"r","capability":"linux.files.read","arguments":{"path":"../x"}}]}));self.assertEqual(r.state,RunState.FAILED)
 def test_secret_not_audited(self):
  os.environ["LWM_SECRET_X"]="hidden-value";b=CapabilityBus();b.register(Capability("read","x","x"),lambda a:len(a["x"]));p=self.root/"secret.log";r=AutomationControlPlane(b,AuditLog(p)).start(Workflow.from_dict({"steps":[{"id":"x","capability":"read","arguments":{"x":"${{ secrets.X }}"}}]}));self.assertEqual(r.results["x"].output,12);self.assertNotIn("hidden-value",p.read_text())
 def test_real_mcp_stdio(self):
  c=StdioMCPClient([sys.executable,"-m","lwm_fab.mcp.example_server"])
  try:self.assertEqual(c.initialize()["serverInfo"]["name"],"lwm-example");self.assertEqual(c.call_tool("text_transform",{"text":"hi","operation":"upper"})["content"][0]["text"],"HI")
  finally:c.close()
if __name__=="__main__":unittest.main()
