#!/usr/bin/env python3
"""
MCP Server for Claude Desktop
Converts your HTTP-based server to standard MCP protocol
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

# Import MCP SDK
try:
    from mcp.server.stdio import stdio_server
    from mcp.server import Server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolRequest,
        CallToolResult,
    )
except ImportError:
    print("❌ MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Reuse your storage logic
from main_with_persistence import PersistentStorage

# Initialize storage
storage = PersistentStorage()

# Create MCP server
server = Server("persistent-notes")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools for Claude"""
    return [
        Tool(
            name="add_note",
            description="Add a new note with title and content (automatically saved to file)",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content"}
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="list_notes",
            description="List all saved notes with their IDs, titles, and creation dates",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_note",
            description="Get a specific note by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"}
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="search_notes_by_date",
            description="Search notes by date (today, yesterday, tomorrow, or specific date) with optional keyword",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_filter": {
                        "type": "string", 
                        "description": "Date filter: 'today', 'yesterday', 'tomorrow', 'this week', 'last week', or date in YYYY-MM-DD format"
                    },
                    "keyword": {
                        "type": "string", 
                        "description": "Optional keyword to search in note titles and content"
                    }
                },
                "required": ["date_filter"]
            }
        ),
        Tool(
            name="search_notes",
            description="Search notes by keyword in title or content",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Keyword to search for"},
                    "search_in": {
                        "type": "string", 
                        "description": "Where to search: 'title', 'content', or 'both' (default)"
                    }
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="calculate",
            description="Perform mathematical calculations",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                },
                "required": ["expression"]
            }
        ),
        Tool(
            name="get_current_time",
            description="Get the current date and time",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_storage_info",
            description="Get information about where notes are stored and storage statistics",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls from Claude"""
    
    try:
        if name == "add_note":
            title = arguments.get("title", "")
            content = arguments.get("content", "")
            
            if not title or not content:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: Both title and content are required")],
                    isError=True
                )
            
            note = storage.add_note(title, content)
            return CallToolResult(
                content=[TextContent(type="text", text=f"✅ Note added successfully! ID: {note['id']}, Title: {note['title']}")]
            )
        
        elif name == "list_notes":
            notes = storage.get_notes()
            
            if not notes:
                return CallToolResult(
                    content=[TextContent(type="text", text="📝 No notes found.")]
                )
            
            notes_text = []
            for note in notes:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"📝 ID: {note['id']} - {note['title']} (Created: {created})")
            
            result = "📝 Your Notes:\n" + "\n".join(notes_text)
            return CallToolResult(content=[TextContent(type="text", text=result)])
        
        elif name == "get_note":
            note_id = int(arguments.get("id", 0))
            note = storage.get_note(note_id)
            
            if not note:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"❌ Note with ID {note_id} not found.")],
                    isError=True
                )
            
            created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
            updated = datetime.fromisoformat(note['updated_at']).strftime("%Y-%m-%d %H:%M")
            
            result = f"📄 Note {note['id']}\n"
            result += f"Title: {note['title']}\n"
            result += f"Content: {note['content']}\n"
            result += f"Created: {created}\n"
            result += f"Updated: {updated}"
            
            return CallToolResult(content=[TextContent(type="text", text=result)])
        
        elif name == "search_notes_by_date":
            date_filter = arguments.get("date_filter", "today")
            keyword = arguments.get("keyword")
            
            results = storage.search_notes_by_date(date_filter, keyword)
            
            if not results:
                filter_desc = f"'{date_filter}'"
                if keyword:
                    filter_desc += f" with keyword '{keyword}'"
                return CallToolResult(
                    content=[TextContent(type="text", text=f"📅 No notes found for {filter_desc}.")]
                )
            
            notes_text = []
            for note in results:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"📝 ID: {note['id']} - {note['title']} (Created: {created})")
                preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                notes_text.append(f"   📄 Content: {preview}")
            
            filter_desc = f"📅 Smart search results for '{date_filter}'"
            if keyword:
                filter_desc += f" + '{keyword}'"
            
            result = filter_desc + ":\n" + "\n".join(notes_text)
            return CallToolResult(content=[TextContent(type="text", text=result)])
        
        elif name == "search_notes":
            keyword = arguments.get("keyword", "")
            search_in = arguments.get("search_in", "both")
            
            if not keyword:
                return CallToolResult(
                    content=[TextContent(type="text", text="❌ Error: Keyword is required for search")],
                    isError=True
                )
            
            results = storage.search_notes(keyword, search_in)
            
            if not results:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"🔍 No notes found containing '{keyword}' in {search_in}.")]
                )
            
            notes_text = []
            for note in results:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"🔍 ID: {note['id']} - {note['title']} (Created: {created})")
            
            result = f"🔍 Search results for '{keyword}' in {search_in}:\n" + "\n".join(notes_text)
            return CallToolResult(content=[TextContent(type="text", text=result)])
        
        elif name == "calculate":
            expression = arguments.get("expression", "")
            
            if not expression:
                return CallToolResult(
                    content=[TextContent(type="text", text="❌ Error: Expression is required")],
                    isError=True
                )
            
            try:
                # Safe evaluation of mathematical expressions
                result = eval(expression, {"__builtins__": {}}, {})
                return CallToolResult(
                    content=[TextContent(type="text", text=f"🧮 {expression} = {result}")]
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"❌ Calculation error: {str(e)}")],
                    isError=True
                )
        
        elif name == "get_current_time":
            current_time = datetime.now().isoformat()
            return CallToolResult(
                content=[TextContent(type="text", text=f"🕐 Current date and time: {current_time}")]
            )
        
        elif name == "get_storage_info":
            stats = storage.get_stats()
            
            info = f"📁 **Storage Information:**\n"
            info += f"📍 Location: {stats['storage_location']}\n"
            info += f"📊 Total Notes: {stats['total_notes']}\n"
            info += f"💾 File Size: {stats['file_size_bytes']} bytes\n"
            info += f"🕐 Last Updated: {stats['last_updated']}\n"
            info += f"\n💡 **Note:** All notes are automatically saved to the JSON file above."
            
            return CallToolResult(content=[TextContent(type="text", text=info)])
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"❌ Unknown tool: {name}")],
                isError=True
            )
    
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Error executing tool {name}: {str(e)}")],
            isError=True
        )

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())