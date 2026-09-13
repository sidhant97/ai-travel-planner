import json
from mcp_server import MCPServer

class MCPClient:
    def __init__(self):
        self.server = MCPServer()

    def get_tool_definitions(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Fetch current live weather and 3-day forecast for Singapore. Use this whenever questions mention weather, rain, outdoor activities vs indoor planning.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "Number of forecast days (1-3)", "default": 3}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "convert_currency",
                    "description": "Convert funds between currencies (e.g. INR to SGD, USD to SGD). Use when the prompt mentions budget or currency exchange.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number", "description": "Amount to convert"},
                            "from_curr": {"type": "string", "description": "Source 3-letter currency code (e.g. INR, USD)"},
                            "to_curr": {"type": "string", "description": "Target 3-letter currency code (default SGD)", "default": "SGD"}
                        },
                        "required": ["amount", "from_curr"]
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, arguments: dict):
        if tool_name == "get_weather":
            return self.server.get_weather(**arguments)
        elif tool_name == "convert_currency":
            return self.server.convert_currency(**arguments)
        return {"status": "error", "message": f"Tool '{tool_name}' not recognized."}