#!/usr/bin/env python3

import httpx
import asyncio
import json
from typing import Dict, Any

class SimpleMCPClient:
    """Simple client to interact with the MCP server"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def list_tools(self):
        """List available tools"""
        response = await self.client.get(f"{self.base_url}/tools")
        return response.json()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Call a specific tool with arguments"""
        payload = {
            "name": tool_name,
            "arguments": arguments
        }
        response = await self.client.post(f"{self.base_url}/tools/call", json=payload)
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

async def main():
    """Example usage of the MCP client"""
    client = SimpleMCPClient()
    
    try:
        print("=== MCP Server Demo ===\n")
        
        # List available tools
        print("1. Available tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
        print()
        
        # Add some notes
        print("2. Adding notes:")
        note1_result = await client.call_tool("add_note", {
            "title": "Meeting Notes",
            "content": "Discussed project timeline and deliverables"
        })
        print(f"   {note1_result['content'][0]['text']}")
        
        note2_result = await client.call_tool("add_note", {
            "title": "Shopping List",
            "content": "Milk, Bread, Eggs, Coffee"
        })
        print(f"   {note2_result['content'][0]['text']}")
        print()
        
        # List all notes
        print("3. Listing all notes:")
        list_result = await client.call_tool("list_notes", {})
        print(f"   {list_result['content'][0]['text']}")
        print()
        
        # Get a specific note
        print("4. Getting note with ID 1:")
        get_result = await client.call_tool("get_note", {"id": "1"})
        print(f"   {get_result['content'][0]['text']}")
        print()
        
        # Perform calculations
        print("5. Performing calculations:")
        calc_result = await client.call_tool("calculate", {
            "expression": "15 + 25 * 2"
        })
        print(f"   {calc_result['content'][0]['text']}")
        
        calc_result2 = await client.call_tool("calculate", {
            "expression": "(100 - 30) / 7"
        })
        print(f"   {calc_result2['content'][0]['text']}")
        print()
        
        # Get current time
        print("6. Getting current time:")
        time_result = await client.call_tool("get_current_time", {})
        print(f"   {time_result['content'][0]['text']}")
        print()
        
        # Delete a note
        print("7. Deleting note with ID 2:")
        delete_result = await client.call_tool("delete_note", {"id": "2"})
        print(f"   {delete_result['content'][0]['text']}")
        
        # List notes again to confirm deletion
        print("\n8. Listing notes after deletion:")
        list_result2 = await client.call_tool("list_notes", {})
        print(f"   {list_result2['content'][0]['text']}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())