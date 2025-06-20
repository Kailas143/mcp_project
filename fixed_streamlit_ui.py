async def _handle_date_search(self, date_filter: str, keyword: str = None) -> str:
        """Handle date-based note searches"""
        try:
            result = await self.mcp_client.call_tool("search_notes_by_date", {
                "date_filter": date_filter,
                "keyword": keyword
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return result['content'][0]['text']
        except Exception as e:
            return f"❌ Error searching notes by date: {str(e)}"#!/usr/bin/env python3

import streamlit as st
import asyncio
import httpx
import json
import re
from datetime import datetime
from typing import Dict, Any

# Configure Streamlit page
st.set_page_config(
    page_title="MCP AI Assistant - Fixed",
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
            print(f"🔧 Calling {tool_name} with: {arguments}")  # Debug
            response = await client.post(f"{self.base_url}/tools/call", json=payload)
            result = response.json()
            print(f"📤 Response: {result}")  # Debug
            return result

class FixedAIAssistant:
    """Fixed AI assistant with proper error handling"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def process_message(self, message: str) -> str:
        """Process user message with improved error handling"""
        
        message_lower = message.lower().strip()
        
        # Check for multi-step requests first
        is_multistep = any(word in message_lower for word in [" then ", " and ", " also "])
        
        if is_multistep:
            return await self._handle_multistep_request(message)
        
        # Check for date-related queries FIRST (most flexible approach)
        date_keywords = ['today', 'tomorrow', 'yesterday', 'this week', 'last week', 'next week']
        has_date_keyword = any(keyword in message_lower for keyword in date_keywords)
        has_notes_keyword = any(word in message_lower for word in ['notes', 'note'])
        
        if has_date_keyword and has_notes_keyword:
            return await self._handle_smart_date_search(message)
        
        # Single intent detection for non-date queries
        if "add note" in message_lower:
            return await self._handle_add_note_simple(message)
        elif "list notes" in message_lower or "show all notes" in message_lower or "all notes" in message_lower:
            return await self._handle_list_notes()
        elif "storage info" in message_lower:
            return await self._handle_storage_info()
        elif "search notes" in message_lower or "find notes" in message_lower:
            return await self._handle_search_notes(message)
        elif "calculate" in message_lower or any(op in message for op in ["+", "-", "*", "/", "="]):
            return await self._handle_calculation(message)
        elif "time" in message_lower:
            return await self._handle_time()
        else:
            return self._show_help()
    
    async def _handle_add_note_simple(self, message: str) -> str:
        """Simple note creation with better parsing"""
        try:
            # Extract content after "add note"
            content = message.lower().replace("add note about", "").replace("add note", "").strip()
            
            if not content:
                content = "Empty note"
            
            # Use simple title and content
            title = "Quick Note"
            
            print(f"🔧 Creating note with title='{title}', content='{content}'")
            
            result = await self.mcp_client.call_tool("add_note", {
                "title": title,
                "content": content
            })
            
            if result.get("is_error"):
                return f"❌ Note Error: {result['content'][0]['text']}"
            else:
                return f"✅ {result['content'][0]['text']}"
                
        except Exception as e:
            return f"❌ Error creating note: {str(e)}"
    
    async def _handle_multistep_request(self, message: str) -> str:
        """Handle complex multi-step requests"""
        results = []
        message_lower = message.lower()
        
        print(f"🔍 Processing multi-step request: {message}")  # Debug
        
        try:
            # Step 1: Handle note creation - IMPROVED DETECTION
            note_triggers = ["add note", "create note", "add a note", "create a note"]
            note_created = False
            
            for trigger in note_triggers:
                if trigger in message_lower and not note_created:
                    print(f"🔍 Found note trigger: {trigger}")  # Debug
                    
                    # Find start of note content
                    trigger_pos = message_lower.find(trigger)
                    note_start = trigger_pos + len(trigger)
                    
                    # Handle "about" keyword
                    remaining_text = message_lower[note_start:note_start+10]
                    if remaining_text.strip().startswith("about"):
                        about_pos = message_lower.find("about", note_start)
                        note_start = about_pos + 5
                    
                    # Find where note content ends (before conjunctions)
                    end_markers = [" then ", " and calculate", " and tell", ", then", ", and", " then calculate"]
                    note_end = len(message)
                    
                    for marker in end_markers:
                        marker_pos = message_lower.find(marker, note_start)
                        if marker_pos != -1:
                            note_end = min(note_end, marker_pos)
                            print(f"🔍 Found end marker '{marker}' at position {marker_pos}")  # Debug
                    
                    note_content = message[note_start:note_end].strip()
                    print(f"🔍 Extracted note content: '{note_content}'")  # Debug
                    
                    if note_content and len(note_content) > 1:  # Must have actual content
                        try:
                            note_result = await self.mcp_client.call_tool("add_note", {
                                "title": "Meeting Note",
                                "content": note_content
                            })
                            
                            if note_result.get("is_error"):
                                results.append(f"❌ Note Error: {note_result['content'][0]['text']}")
                            else:
                                results.append(f"📝 {note_result['content'][0]['text']}")
                                note_created = True
                        except Exception as e:
                            results.append(f"❌ Note creation failed: {str(e)}")
                    else:
                        print(f"🔍 Note content too short or empty: '{note_content}'")  # Debug
                    
                    break  # Stop after first successful trigger
            
            if not note_created:
                results.append("📝 Note: Could not extract note content from request")
            
            # Step 2: Handle calculations - IMPROVED
            calc_patterns = [
                r'calculate\s+([0-9+\-*/().\s]+)',
                r'(\d+\s*\*\s*\d+)',
                r'(\d+\s*[\+\-\/]\s*\d+)',
                r'(\d+\s*\*\s*\d+)',  # Specific for multiplication
            ]
            
            calculation_done = False
            for pattern in calc_patterns:
                if not calculation_done:
                    match = re.search(pattern, message)
                    if match:
                        expression = match.group(1) if len(match.groups()) > 0 else match.group(0)
                        expression = expression.strip()
                        
                        print(f"🔍 Found calculation: '{expression}'")  # Debug
                        
                        try:
                            calc_result = await self.mcp_client.call_tool("calculate", {
                                "expression": expression
                            })
                            
                            if calc_result.get("is_error"):
                                results.append(f"❌ Calculation Error: {calc_result['content'][0]['text']}")
                            else:
                                results.append(f"🧮 {calc_result['content'][0]['text']}")
                                calculation_done = True
                        except Exception as e:
                            results.append(f"❌ Calculation failed: {str(e)}")
                        break
            
            # Step 3: Handle time request - IMPROVED
            time_triggers = ["tell me the time", "what time", "current time", "time"]
            time_done = False
            
            for trigger in time_triggers:
                if trigger in message_lower and not time_done:
                    print(f"🔍 Found time trigger: {trigger}")  # Debug
                    
                    try:
                        time_result = await self.mcp_client.call_tool("get_current_time", {})
                        
                        if time_result.get("is_error"):
                            results.append(f"❌ Time Error: {time_result['content'][0]['text']}")
                        else:
                            results.append(f"🕐 {time_result['content'][0]['text']}")
                            time_done = True
                    except Exception as e:
                        results.append(f"❌ Time request failed: {str(e)}")
                    break
            
            # Summary
            print(f"🔍 Multi-step results: {len(results)} operations completed")  # Debug
            
            # Combine results
            if results:
                return "\n\n".join(results)
            else:
                return "❌ I couldn't process any parts of your multi-step request. Please try breaking it down."
                
        except Exception as e:
            return f"❌ Error processing multi-step request: {str(e)}"
    
    async def _handle_list_notes(self) -> str:
        """Handle listing notes"""
        try:
            result = await self.mcp_client.call_tool("list_notes", {})
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return f"📝 {result['content'][0]['text']}"
        except Exception as e:
            return f"❌ Error listing notes: {str(e)}"
    
    async def _handle_storage_info(self) -> str:
        """Handle storage info request"""
        try:
            result = await self.mcp_client.call_tool("get_storage_info", {})
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return result['content'][0]['text']
        except Exception as e:
            return f"❌ Error getting storage info: {str(e)}"
    
    async def _handle_calculation(self, message: str) -> str:
        """Handle calculations"""
        try:
            # Extract mathematical expression
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
                return "❌ Could not find a mathematical expression to calculate"
        except Exception as e:
            return f"❌ Error calculating: {str(e)}"
    
    async def _handle_time(self) -> str:
        """Handle time requests"""
        try:
            result = await self.mcp_client.call_tool("get_current_time", {})
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return f"🕐 {result['content'][0]['text']}"
        except Exception as e:
            return f"❌ Error getting time: {str(e)}"
    
    def _extract_date_and_keyword(self, message: str) -> tuple:
        """Extract date reference and optional keyword from natural language"""
        message_lower = message.lower()
        
        # Date patterns to look for
        date_patterns = {
            'today': ['today', "today's"],
            'tomorrow': ['tomorrow', "tomorrow's"],
            'yesterday': ['yesterday', "yesterday's"],
            'this week': ['this week', 'week'],
            'last week': ['last week'],
            'next week': ['next week']
        }
        
        detected_date = None
        keyword = None
        
        # Find date reference
        for date_key, patterns in date_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    detected_date = date_key
                    break
            if detected_date:
                break
        
        # Extract keyword if present
        if detected_date:
            # Remove common command words and date references
            clean_message = message_lower
            
            # Remove command words
            command_words = ['show', 'notes', 'find', 'search', 'get', 'list', 'all']
            for word in command_words:
                clean_message = clean_message.replace(word, ' ')
            
            # Remove date references
            for patterns in date_patterns.values():
                for pattern in patterns:
                    clean_message = clean_message.replace(pattern, ' ')
            
            # Extract remaining meaningful words
            remaining_words = [word.strip() for word in clean_message.split() if word.strip() and len(word.strip()) > 1]
            
            # If we have remaining words, use them as keyword
            if remaining_words:
                keyword = ' '.join(remaining_words)
        
        return detected_date, keyword
    
    async def _handle_smart_date_search(self, message: str) -> str:
        """Handle intelligent date-based searches with automatic keyword extraction"""
        date_filter, keyword = self._extract_date_and_keyword(message)
        
        if not date_filter:
            return "❌ Could not detect a date reference in your message"
        
        print(f"🔍 Smart search - Date: '{date_filter}', Keyword: '{keyword}'")  # Debug
        
        try:
            # Use the enhanced search that looks at both creation date and content
            result = await self.mcp_client.call_tool("search_notes_by_date", {
                "date_filter": date_filter,
                "keyword": keyword
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return result['content'][0]['text']
        except Exception as e:
            return f"❌ Error in smart date search: {str(e)}"
        """Handle date-based note searches"""
        try:
            result = await self.mcp_client.call_tool("search_notes_by_date", {
                "date_filter": date_filter,
                "keyword": keyword
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return result['content'][0]['text']
        except Exception as e:
            return f"❌ Error searching notes by date: {str(e)}"
    
    async def _handle_search_notes(self, message: str) -> str:
        """Handle keyword searches in notes"""
        try:
            # Extract keyword from message
            message_lower = message.lower()
            if "search notes for" in message_lower:
                keyword = message_lower.split("search notes for", 1)[1].strip()
            elif "find notes about" in message_lower:
                keyword = message_lower.split("find notes about", 1)[1].strip()
            elif "search for" in message_lower:
                keyword = message_lower.split("search for", 1)[1].strip()
            else:
                # Extract everything after "search notes" or "find notes"
                for phrase in ["search notes", "find notes"]:
                    if phrase in message_lower:
                        keyword = message_lower.split(phrase, 1)[1].strip()
                        break
                else:
                    return "❌ Please specify what to search for. Example: 'search notes for meeting'"
            
            if not keyword:
                return "❌ Please specify a keyword to search for"
            
            result = await self.mcp_client.call_tool("search_notes", {
                "keyword": keyword,
                "search_in": "both"
            })
            
            if result.get("is_error"):
                return f"❌ Error: {result['content'][0]['text']}"
            else:
                return result['content'][0]['text']
        except Exception as e:
            return f"❌ Error searching notes: {str(e)}"
    
    def _show_help(self) -> str:
        """Show available commands"""
        return """🤖 **Fixed MCP AI Assistant - Available Commands:**

📝 **Notes:**
• "add note about our meeting"
• "list notes" / "show notes"

📅 **Smart date searches (AUTO-DETECTS keywords):**
• "show notes today" - All today's notes
• "tomorrow meeting notes" - Tomorrow's notes about meetings  
• "yesterday exam notes" - Yesterday's notes about exams
• "today project notes" - Today's notes about projects
• "this week client notes" - This week's notes about clients
• "tomorrow presentation notes" - Tomorrow's notes about presentations

🔍 **Works with ANY keyword automatically:**
• "tomorrow [anything] notes" - Finds tomorrow's notes containing [anything]
• "today [keyword] notes" - Finds today's notes containing [keyword]
• No need to manually add each keyword!

🔍 **Search notes:**
• "search notes for meeting"
• "find notes about project"
• "search for client"

🧮 **Calculator:**
• "calculate 3 * 50000"
• "15 + 25 * 2"

🕐 **Time:**
• "what time is it?"

💾 **Storage:**
• "storage info"

✨ **Multi-step (FIXED):**
• "Add a note about our meeting, then calculate 3 * 50000, and tell me the time"

🔧 **Debug Info:**
Check the terminal/console for detailed debug output when commands run."""

# Streamlit App
def main():
    st.title("🤖 Fixed MCP AI Assistant")
    st.subheader("Multi-step processing with better error handling")
    
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
                    st.info("Make sure your MCP server is running with: python main_with_persistence.py")
        
        st.header("🧪 Test Commands")
        st.code("""
# Smart date + keyword searches (AUTO-DETECTS)
tomorrow meeting notes
today exam notes  
yesterday client notes
this week project notes
tomorrow presentation notes

# Traditional commands still work
add note about project update
list notes
search notes for meeting
calculate 3 * 50000
storage info

# Multi-step (FIXED)
Add a note about our meeting, then calculate 3 * 50000, and tell me the time
        """, language="text")
        
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hello! I'm your **Fixed** MCP AI Assistant. The multi-step processing has been completely rewritten. Try: 'Add a note about our meeting, then calculate 3 * 50000, and tell me the time'"
            }
        ]
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Try the multi-step command..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process with AI assistant
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    client = MCPClient(mcp_url)
                    assistant = FixedAIAssistant(client)
                    response = asyncio.run(assistant.process_message(prompt))
                    
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}\n\nMake sure the MCP server is running: python main_with_persistence.py"
                    st.write(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()