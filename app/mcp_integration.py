import requests
import json
from typing import Dict, Any

class MCPClient:
    """Handles MCP tool calls"""
    
    def __init__(self, base_url: str = "http://localhost:8001/mcp"):
        self.base_url = base_url

    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict:
        """Execute a tool through MCP"""
        print(f"🔧 Calling tool: {tool_name}")
        print(f"📍 URL: {self.base_url}/call")
        print(f"📦 Params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/call",
                json={
                    "tool_name": tool_name,
                    "params": params
                },
            )
            print(f"📡 Response status: {response.status_code}")
            print(f"📄 Response content: {response.text[:500]}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: Could not connect to {self.base_url}")
            print(f"Error details: {str(e)}")
            raise
        except requests.exceptions.Timeout:
            print("❌ Request timed out after 20 seconds")
            raise
        except Exception as e:
            print(f"❌ Unexpected error in call_tool: {str(e)}")
            raise

    def list_tools(self) -> Dict:
        """Get available tools"""
        response = requests.get(f"{self.base_url}/tools")
        response.raise_for_status()
        return response.json()