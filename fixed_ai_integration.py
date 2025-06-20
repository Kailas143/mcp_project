#!/usr/bin/env python3

import httpx
import asyncio
import json
from typing import Dict, Any, List
from dataclasses import dataclass
import re

class MCPBridge:
    """Bridge between AI assistants and our MCP server"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.mcp_server_url = mcp_server_url
        self.available_tools = []
    
    async def initialize(self):
        """Load available tools from MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.mcp_server_url}/tools")
                tools_data = response.json()
                
                self.available_tools = tools_data
                print(f"✅ Loaded {len(self.available_tools)} tools from MCP server")
                return True
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {e}")
            print("Make sure your MCP server is running with: python main.py")
            return False
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on the MCP server and return the result"""
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            
            print(f"🔧 Calling tool: {tool_name}")
            print(f"📋 Arguments: {arguments}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/tools/call",
                    json=payload
                )
                
                if response.status_code != 200:
                    return f"❌ HTTP Error {response.status_code}: {response.text}"
                
                result = response.json()
                
                if result.get("is_error"):
                    return f"❌ Tool Error: {result['content'][0]['text']}"
                
                return f"✅ {result['content'][0]['text']}"
                
        except Exception as e:
            return f"❌ Error calling tool {tool_name}: {str(e)}"

class ImprovedChatBot:
    """Improved chatbot with better parsing and error handling"""
    
    def __init__(self, mcp_bridge: MCPBridge):
        self.mcp_bridge = mcp_bridge
    
    async def process_message(self, user_input: str) -> str:
        """Process user message with improved parsing"""
        
        print(f"\n💬 Processing: '{user_input}'")
        
        user_lower = user_input.lower().strip()
        
        # Add note handling
        if any(phrase in user_lower for phrase in ["add note", "create note", "new note"]):
            return await self._handle_add_note_improved(user_input)
        
        # List notes
        elif any(phrase in user_lower for phrase in ["list notes", "show notes", "all notes"]):
            return await self.mcp_bridge.call_mcp_tool("list_notes", {})
        
        # Get specific note
        elif "get note" in user_lower or "show note" in user_lower:
            note_id = self._extract_number(user_input)
            if note_id:
                return await self.mcp_bridge.call_mcp_tool("get_note", {"id": str(note_id)})
            else:
                return "❌ Please specify a note ID (e.g., 'get note 1')"
        
        # Delete note
        elif "delete note" in user_lower or "remove note" in user_lower:
            note_id = self._extract_number(user_input)
            if note_id:
                return await self.mcp_bridge.call_mcp_tool("delete_note", {"id": str(note_id)})
            else:
                return "❌ Please specify a note ID (e.g., 'delete note 1')"
        
        # Calculator
        elif "calculate" in user_lower or any(op in user_input for op in ["+", "-", "*", "/", "="]):
            return await self._handle_calculation_improved(user_input)
        
        # Time
        elif any(phrase in user_lower for phrase in ["time", "date", "current time", "what time"]):
            return await self.mcp_bridge.call_mcp_tool("get_current_time", {})
        
        else:
            return self._show_help()
    
    def _extract_number(self, text: str) -> int:
        """Extract first number from text"""
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None
    
    async def _handle_add_note_improved(self, message: str) -> str:
        """Improved note creation with better parsing"""
        
        # Remove command keywords
        clean_msg = message
        for phrase in ["add note", "create note", "new note"]:
            clean_msg = re.sub(phrase, "", clean_msg, flags=re.IGNORECASE).strip()
        
        # Different parsing strategies
        title = ""
        content = ""
        
        # Strategy 1: Look for "Title: Content" pattern
        if ":" in clean_msg:
            parts = clean_msg.split(":", 1)
            title = parts[0].strip()
            content = parts[1].strip()
        
        # Strategy 2: If no colon, check for common patterns
        elif " about " in clean_msg.lower():
            # "add note about meeting" -> title="meeting", content="meeting note"
            about_part = clean_msg.lower().split(" about ", 1)[1]
            title = about_part.capitalize()
            content = f"Note about {about_part}"
        
        # Strategy 3: Use entire message as content with default title
        else:
            title = "Quick Note"
            content = clean_msg if clean_msg else "Empty note"
        
        # Ensure we have valid values
        if not title or title.isspace():
            title = "Untitled Note"
        if not content or content.isspace():
            content = "No content provided"
        
        print(f"📝 Parsed - Title: '{title}', Content: '{content}'")
        
        return await self.mcp_bridge.call_mcp_tool("add_note", {
            "title": title,
            "content": content
        })
    
    async def _handle_calculation_improved(self, message: str) -> str:
        """Improved calculation handling"""
        
        # Extract mathematical expression
        # Look for patterns like "calculate 2+3" or just "15 + 25 * 2"
        
        # First, try to find expression after "calculate"
        if "calculate" in message.lower():
            calc_part = message.lower().split("calculate", 1)[1].strip()
        else:
            calc_part = message
        
        # Extract mathematical expression
        expression = re.search(r'[0-9+\-*/().\s]+', calc_part)
        
        if expression:
            expr_str = expression.group().strip()
            print(f"🧮 Extracted expression: '{expr_str}'")
            return await self.mcp_bridge.call_mcp_tool("calculate", {"expression": expr_str})
        else:
            return "❌ Couldn't find a mathematical expression. Try: 'calculate 2 + 3' or just '15 + 25 * 2'"
    
    def _show_help(self) -> str:
        """Show available commands"""
        return """🤖 **Available Commands:**

📝 **Notes:**
• "add note: Title: Content"
• "add note about meeting"
• "list notes"
• "get note 1"
• "delete note 1"

🧮 **Calculator:**
• "calculate 15 + 25 * 2"
• "2 + 3 * 4"

🕐 **Time:**
• "what time is it?"
• "current date"

Try: "add note: Meeting: Discussed project timeline" """

async def main():
    """Main demo function with better error handling"""
    
    print("=== Improved MCP AI Integration Demo ===\n")
    
    # Initialize MCP bridge
    mcp_bridge = MCPBridge()
    
    if not await mcp_bridge.initialize():
        print("\n💡 To start the MCP server, run in another terminal:")
        print("   python main.py")
        return
    
    # Create improved chatbot
    chatbot = ImprovedChatBot(mcp_bridge)
    
    # Test with the examples that failed
    print("🧪 Testing with examples that previously failed:\n")
    
    test_cases = [
        "add note: Meeting Notes: Discussed Q4 planning",
        "add note: Shopping List: Milk, Bread, Eggs", 
        "list notes",
        "calculate 15 + 25 * 2",
        "what time is it?",
        "add note about today's meeting",  # Test different format
        "get note 1",
        "delete note 2"
    ]
    
    for i, test_message in enumerate(test_cases, 1):
        print(f"--- Test {i} ---")
        print(f"User: {test_message}")
        
        try:
            response = await chatbot.process_message(test_message)
            print(f"Bot: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        await asyncio.sleep(0.5)  # Small delay for readability
    
    # Interactive mode
    print("\n🎯 Interactive Mode (type 'quit', 'exit', or 'help' for commands):")
    print("Try: 'add note: Project Update: Sprint completed successfully'\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("👋 Goodbye!")
                break
            
            if user_input.lower() in ['help', 'h', '?']:
                print(chatbot._show_help())
                continue
            
            response = await chatbot.process_message(user_input)
            print(f"Bot: {response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())