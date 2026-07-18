import json,os
from pathlib import Path
from .client import StdioMCPClient
from ..control_plane import RiskLevel
class MCPServerManager:
 def __init__(self,bus):self.bus=bus;self.clients={}
 def connect(self,name,client,risk=RiskLevel.WRITE):client.initialize();self.bus.register_mcp_server(name,client.list_tools(),client.call_tool,risk);self.clients[name]=client
 def load_config(self,path):
  for name,c in json.loads(Path(path).read_text()).get("mcpServers",{}).items():
   env=os.environ.copy();env.update(c.get("env",{}));self.connect(name,StdioMCPClient([c["command"],*c.get("args",[])],env,c.get("cwd")),RiskLevel(c.get("defaultRisk","write")))
 def status(self):return {"servers":sorted(self.clients),"count":len(self.clients)}
 def close(self):
  for c in self.clients.values():c.close()
