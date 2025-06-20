def _handle_general_query(message: str) -> str:
        """Handle general queries"""
        return """🤖 I'm an AI assistant with access to several tools. I can help you with:

📝 **Notes**: 
- "add note: Title: Content" - Create a new note
- "list notes" - Show all notes
- "get note 1" - Show specific note
- "delete note 1" - Delete a note

🧮 **Calculations**:
- "calculate 2 + 3 * 4"
- "15 + 25 * 2"
- "calculate revenue for 3 deals worth $50k each"

🕐 **Time**:
- "what time is it?"
- "current date"

✨ **Multi-step requests**:
- "Add a note about our meeting, then calculate 3 * 50000, and tell me the time"

Try asking me something like "add note: Meeting: Discuss project timeline" or "calculate 15 * 3"!"""#!/usr/bin/env python3

import streamlit as st
import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any

# Configure Streamlit page
st.set_page_config(
    page_title="MCP AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

class MCPClient:
    """Simple MCP client for Streamlit"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def get_tools(self):
        """Get available tools from MCP server"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/tools")
            return response.json()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Call a tool on the MCP server"""
        async with httpx.AsyncClient() as client:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            response = await client.post(f"{self.base_url}/tools/call", json=payload)
            return response.json()

class AIAssistant:
    """Simple AI assistant that uses MCP tools"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def process_message(self, message: str) -> str:
        """Process user message and handle multi-step requests"""
        message_lower = message.lower()
        results = []
        
        # Check for multi-step requests (contains "then", "and", "also")
        is_multistep = any(word in message_lower for word in [" then ", " and ", " also "])
        
        if is_multistep:
            return await self._handle_multistep_request(message)
        
        # Single intent detection
        if any(word in message_lower for word in ["add note", "create note", "new note"]):
            return await self._handle_add_note_intent(message)
        
        elif any(word in message_lower for word in ["list notes", "show notes", "all notes", "show all notes", "list all notes"]):
            return await self._handle_list_notes()
        
        elif any(word in message_lower for word in ["get note", "show note", "note"]) and any(char.isdigit() for char in message):
            return await self._handle_get_note_intent(message)
        
        elif any(word in message_lower for word in ["delete note", "remove note"]) and any(char.isdigit() for char in message):
            return await self._handle_delete_note_intent(message)
        
        elif any(word in message_lower for word in ["calculate", "compute", "math"]) or any(op in message for op in ["+", "-", "*", "/", "="]):
            return await self._handle_calculation_intent(message)
        
        elif any(word in message_lower for word in ["time", "date", "current time", "what time"]):
            return await self._handle_time_intent()
        
        elif any(word in message_lower for word in ["list tools", "show tools", "available tools", "what tools"]):
            return await self._handle_list_tools()
        
        elif any(word in message_lower for word in ["storage info", "where stored", "storage location", "file location"]):
            return await self._handle_storage_info()
        
        else:
            return _handle_general_query(message)
    
    async def _handle_add_note_intent(self, message: str) -> str:
        """Handle note creation"""
        # Simple parsing to extract title and content
        if ":" in message:
            parts = message.split(":", 2)
            if len(parts) >= 3:
                title = parts[1].strip()
                content = parts[2].strip()
            elif len(parts) == 2:
                title = "Quick Note"
                content = parts[1].strip()
            else:
                title = "Quick Note"
                content = message
        else:
            title = "Quick Note"
            content = message.replace("add note", "").replace("create note", "").replace("new note", "").strip()
        
        result = await self.mcp_client.call_tool("add_note", {
            "title": title,
            "content": content
        })
        
        if result.get("is_error"):
            return f"❌ Error: {result['content'][0]['text']}"
        else:
            return f"✅ {result['content'][0]['text']}"
    
    async def _handle_list_notes(self) -> str:
        """Handle listing notes"""
        result = await self.mcp_client.call_tool("list_notes", {})
        
        if result.get("is_error"):
            return f"❌ Error: {result['content'][0]['text']}"
        else:
            return f"📝 {result['content'][0]['text']}"
    
    async def _handle_get_note_intent(self, message: str) -> str:
        """Handle getting a specific note"""
        import re
        note_id = re.search(r'\d+', message)
        if note_id:
            result = await self.mcp_client.call_tool("get_note", {
                "id": note_id.group()
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return f"📄 {result['content'][0]['text']}"
        else:
            return "❌ Please specify a note ID (e.g., 'get note 1')"
    
    async def _handle_delete_note_intent(self, message: str) -> str:
        """Handle deleting a note"""
        import re
        note_id = re.search(r'\d+', message)
        if note_id:
            result = await self.mcp_client.call_tool("delete_note", {
                "id": note_id.group()
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return f"🗑️ {result['content'][0]['text']}"
        else:
            return "❌ Please specify a note ID (e.g., 'delete note 1')"
    
    async def _handle_calculation_intent(self, message: str) -> str:
        """Handle calculations"""
        import re
        
        # Try to extract mathematical expression
        # Look for patterns like "calculate 2+3" or just "2+3"
        expression_match = re.search(r'[0-9+\-*/().\s]+', message)
        if expression_match:
            expression = expression_match.group().strip()
            
            result = await self.mcp_client.call_tool("calculate", {
                "expression": expression
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return f"🧮 {result['content'][0]['text']}"
        else:
            return "❌ I couldn't find a mathematical expression to calculate. Try something like '2 + 3 * 4'"
    
    async def _handle_time_intent(self) -> str:
        """Handle time requests"""
        result = await self.mcp_client.call_tool("get_current_time", {})
        
        if result.get("is_error"):
            return f"❌ Error: {result['content'][0]['text']}"
        else:
            return f"🕐 {result['content'][0]['text']}"
    
    async def _handle_multistep_request(self, message: str) -> str:
        """Handle complex requests with multiple steps"""
        results = []
        message_lower = message.lower()
        
        # Step 1: Check for note creation
        if any(phrase in message_lower for phrase in ["add note", "create note", "note about"]):
            # Extract note content
            note_content = ""
            note_title = "Meeting Note"
            
            for phrase in ["add note about", "create note about", "note about"]:
                if phrase in message_lower:
                    start_idx = message_lower.find(phrase) + len(phrase)
                    # Find end of note content (before "then", "and", etc.)
                    end_markers = [" then ", " and then ", " and ", " also "]
                    end_idx = len(message)
                    for marker in end_markers:
                        marker_idx = message_lower.find(marker, start_idx)
                        if marker_idx != -1:
                            end_idx = min(end_idx, marker_idx)
                    note_content = message[start_idx:end_idx].strip()
                    break
            
            # Handle simple "add note" without "about"
            if not note_content and any(phrase in message_lower for phrase in ["add note", "create note"]):
                # Look for content after the command and before conjunctions
                start_phrases = ["add note", "create note"]
                for start_phrase in start_phrases:
                    if start_phrase in message_lower:
                        start_idx = message_lower.find(start_phrase) + len(start_phrase)
                        end_markers = [" then ", " and then ", " and ", " also "]
                        end_idx = len(message)
                        for marker in end_markers:
                            marker_idx = message_lower.find(marker, start_idx)
                            if marker_idx != -1:
                                end_idx = min(end_idx, marker_idx)
                        note_content = message[start_idx:end_idx].strip()
                        break
            
            if note_content:
                note_result = await self.mcp_client.call_tool("add_note", {
                    "title": note_title,
                    "content": note_content
                })
                if note_result.get("is_error"):
                    results.append(f"❌ Note Error: {note_result['content'][0]['text']}")
                else:
                    results.append(f"📝 {note_result['content'][0]['text']}")
            else:
                results.append("❌ Could not extract note content from your request")
        
        # Step 2: Check for calculations
        if any(phrase in message_lower for phrase in ["calculate", "revenue", "deals worth"]):
            # Look for mathematical patterns
            import re
            
            # Pattern for "3 deals worth $50k each" or similar
            deals_pattern = r'(\d+)\s+deals?\s+worth\s+\$?(\d+)k?\s+each'
            match = re.search(deals_pattern, message_lower)
            
            if match:
                num_deals = int(match.group(1))
                deal_value = int(match.group(2))
                if 'k' in match.group(0) or deal_value < 1000:
                    deal_value *= 1000  # Convert k to thousands
                
                expression = f"{num_deals} * {deal_value}"
                calc_result = await self.mcp_client.call_tool("calculate", {
                    "expression": expression
                })
                
                if calc_result.get("is_error"):
                    results.append(f"❌ Calculation Error: {calc_result['content'][0]['text']}")
                else:
                    # Format the result nicely
                    total = num_deals * deal_value
                    results.append(f"🧮 Quarterly Revenue: {num_deals} deals × ${deal_value:,} = ${total:,}")
            else:
                # Look for other mathematical expressions
                math_pattern = r'[0-9+\-*/().\s]+'
                math_match = re.search(math_pattern, message)
                if math_match:
                    expression = math_match.group().strip()
                    calc_result = await self.mcp_client.call_tool("calculate", {
                        "expression": expression
                    })
                    if not calc_result.get("is_error"):
                        results.append(f"🧮 {calc_result['content'][0]['text']}")
        
        # Step 3: Check for time request
        if any(phrase in message_lower for phrase in ["time", "what time", "current time"]):
            time_result = await self.mcp_client.call_tool("get_current_time", {})
            if time_result.get("is_error"):
                results.append(f"❌ Time Error: {time_result['content'][0]['text']}")
            else:
                results.append(f"🕐 {time_result['content'][0]['text']}")
        
        # Combine all results
        if results:
            return "\n\n".join(results)
        else:
            return "❌ I couldn't identify the specific actions in your request. Try breaking it down into simpler steps."

# Streamlit App
def main():
    st.title("🤖 MCP AI Assistant")
    st.subheader("Chat with an AI that has access to tools via Model Context Protocol")
    
    # Sidebar
    with st.sidebar:
        st.header("🛠️ MCP Server Status")
        
        # Server connection test
        mcp_url = st.text_input("MCP Server URL", value="http://localhost:8000")
        
        if st.button("Test Connection"):
            with st.spinner("Testing connection..."):
                try:
                    client = MCPClient(mcp_url)
                    tools = asyncio.run(client.get_tools())
                    st.success(f"✅ Connected! Found {len(tools)} tools")
                    
                    with st.expander("Available Tools"):
                        for tool in tools:
                            st.write(f"**{tool['name']}**: {tool['description']}")
                            
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
                    st.info("Make sure your MCP server is running on the specified URL")
        
        st.header("💡 Example Commands")
        st.code("""
# Notes
add note: Meeting: Discuss Q4 goals
list notes
get note 1
delete note 2

# Calculations  
calculate 15 + 25 * 2
compute (100 - 30) / 7

# Time
what time is it?
current date
        """, language="text")
        
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hello! I'm your MCP AI Assistant. I can help you with notes, calculations, and more. What would you like to do?"
            }
        ]
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process with AI assistant
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    client = MCPClient(mcp_url)
                    assistant = AIAssistant(client)
                    response = asyncio.run(assistant.process_message(prompt))
                    
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}\n\nMake sure the MCP server is running at {mcp_url}"
                    st.write(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()