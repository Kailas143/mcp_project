{
            "name": "search_notes_by_content_date",
            "description": "Search notes that mention specific dates in their content (tomorrow, today, yesterday, next week, etc.)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "date_reference": {
                        "type": "string", 
                        "description": "Date reference to find in note content: 'tomorrow', 'today', 'yesterday', 'next week', etc."
                    }
                },
                "required": ["date_reference"]
            }
        },    
def get_stats(self) -> dict: 
    {
            "name": "search_notes_by_date",
            "description": "Search notes by date (today, yesterday, tomorrow, or specific date)",
            "input_schema": {
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
    },
    {
        "name": "search_notes",
        "description": "Search notes by keyword in title or content",
        "input_schema": {
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
    },#!/usr/bin/env python3

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configuration
DATA_DIR = Path("mcp_data")  # Directory to store data
NOTES_FILE = DATA_DIR / "notes.json"
CONFIG_FILE = DATA_DIR / "config.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class ToolResponse(BaseModel):
    content: List[Dict[str, str]]
    is_error: bool = False

class PersistentStorage:
    """Handles persistent storage for notes and other data"""
    
    def __init__(self):
        self.notes = []
        self.note_counter = 1
        self.load_data()
    
    def load_data(self):
        """Load notes from file"""
        try:
            if NOTES_FILE.exists():
                with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = data.get('notes', [])
                    self.note_counter = data.get('counter', 1)
                print(f"📁 Loaded {len(self.notes)} notes from {NOTES_FILE}")
            else:
                print(f"📁 No existing notes file found, starting fresh")
                self.save_data()  # Create initial file
        except Exception as e:
            print(f"❌ Error loading notes: {e}")
            self.notes = []
            self.note_counter = 1
    
    def save_data(self):
        """Save notes to file"""
        try:
            data = {
                'notes': self.notes,
                'counter': self.note_counter,
                'last_updated': datetime.now().isoformat()
            }
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = NOTES_FILE.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            temp_file.rename(NOTES_FILE)
            print(f"💾 Saved {len(self.notes)} notes to {NOTES_FILE}")
            
        except Exception as e:
            print(f"❌ Error saving notes: {e}")
    
    def add_note(self, title: str, content: str) -> dict:
        """Add a new note"""
        note = {
            'id': self.note_counter,
            'title': title,
            'content': content,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.notes.append(note)
        self.note_counter += 1
        self.save_data()  # Auto-save
        
        return note
    
    def get_notes(self) -> List[dict]:
        """Get all notes"""
        return self.notes
    
    def get_note(self, note_id: int) -> Optional[dict]:
        """Get a specific note by ID"""
        for note in self.notes:
            if note['id'] == note_id:
                return note
        return None
    
    def update_note(self, note_id: int, title: str = None, content: str = None) -> bool:
        """Update an existing note"""
        note = self.get_note(note_id)
        if note:
            if title is not None:
                note['title'] = title
            if content is not None:
                note['content'] = content
            note['updated_at'] = datetime.now().isoformat()
            self.save_data()  # Auto-save
            return True
        return False
    
    def delete_note(self, note_id: int) -> bool:
        """Delete a note"""
        for i, note in enumerate(self.notes):
            if note['id'] == note_id:
                deleted_note = self.notes.pop(i)
                self.save_data()  # Auto-save
                print(f"🗑️ Deleted note: {deleted_note['title']}")
                return True
        return False
    
    def search_notes_by_date(self, date_filter: str, keyword: str = None) -> List[dict]:
        """Search notes by date with optional keyword filter"""
        today = datetime.now().date()
        
        # Parse date filter
        if date_filter.lower() == "today":
            target_date = today
            match_type = "exact"
        elif date_filter.lower() == "yesterday":
            target_date = today - timedelta(days=1)
            match_type = "exact"
        elif date_filter.lower() == "tomorrow":
            target_date = today + timedelta(days=1)
            match_type = "smart_tomorrow"  # Special handling for tomorrow
        elif date_filter.lower() == "this week":
            # Current week (Monday to Sunday)
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            match_type = "range"
        elif date_filter.lower() == "last week":
            days_since_monday = today.weekday()
            this_week_start = today - timedelta(days=days_since_monday)
            week_start = this_week_start - timedelta(days=7)
            week_end = week_start + timedelta(days=6)
            match_type = "range"
        elif date_filter.lower() == "next week":
            days_since_monday = today.weekday()
            this_week_start = today - timedelta(days=days_since_monday)
            week_start = this_week_start + timedelta(days=7)
            week_end = week_start + timedelta(days=6)
            match_type = "range"
        else:
            # Try to parse as specific date (YYYY-MM-DD)
            try:
                target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                match_type = "exact"
            except ValueError:
                return []
        
        # Filter notes by date
        filtered_notes = []
        for note in self.notes:
            note_date = datetime.fromisoformat(note['created_at']).date()
            note_title_lower = note['title'].lower()
            note_content_lower = note['content'].lower()
            
            date_matches = False
            
            if match_type == "exact":
                date_matches = (note_date == target_date)
            elif match_type == "smart_tomorrow":
                # For "tomorrow" searches with keywords, be more intelligent:
                # 1. Notes created tomorrow
                # 2. Notes containing "tomorrow" in content
                # 3. If keyword provided, notes containing both the keyword AND "tomorrow"
                creation_date_matches = (note_date == target_date)
                content_mentions_tomorrow = "tomorrow" in note_title_lower or "tomorrow" in note_content_lower
                
                if keyword:
                    # If user searches "tomorrow exam notes", find notes that:
                    # - Contain both "tomorrow" and "exam" in content, OR
                    # - Were created tomorrow and contain "exam"
                    keyword_lower = keyword.lower()
                    keyword_in_content = keyword_lower in note_title_lower or keyword_lower in note_content_lower
                    
                    # Smart logic: If note contains both "tomorrow" and the keyword, it's relevant
                    contains_both = content_mentions_tomorrow and keyword_in_content
                    created_tomorrow_with_keyword = creation_date_matches and keyword_in_content
                    
                    date_matches = contains_both or created_tomorrow_with_keyword
                else:
                    # No keyword, just look for "tomorrow" references
                    date_matches = creation_date_matches or content_mentions_tomorrow
                    
            elif match_type == "range":
                date_matches = (week_start <= note_date <= week_end)
            
            # Apply additional keyword filter if provided and not already handled by smart_tomorrow
            if date_matches and keyword and match_type != "smart_tomorrow":
                keyword_lower = keyword.lower()
                title_match = keyword_lower in note_title_lower
                content_match = keyword_lower in note_content_lower
                keyword_matches = title_match or content_match
                
                if not keyword_matches:
                    date_matches = False
            
            if date_matches:
                filtered_notes.append(note)
        
        return filtered_notes
    
    def search_notes(self, keyword: str, search_in: str = "both") -> List[dict]:
        """Search notes by keyword"""
        keyword_lower = keyword.lower()
        results = []
        
        for note in self.notes:
            matches = False
            
            if search_in in ["title", "both"]:
                if keyword_lower in note['title'].lower():
                    matches = True
            
            if search_in in ["content", "both"]:
                if keyword_lower in note['content'].lower():
                    matches = True
            
            if matches:
                results.append(note)
        
        return results
    
    def search_notes_by_content_date(self, date_reference: str) -> List[dict]:
        """Search notes that mention specific dates in their content"""
        date_reference_lower = date_reference.lower()
        results = []
        
        for note in self.notes:
            title_match = date_reference_lower in note['title'].lower()
            content_match = date_reference_lower in note['content'].lower()
            
            if title_match or content_match:
                results.append(note)
        
        return results
        """Get storage statistics"""
        return {
            'total_notes': len(self.notes),
            'storage_location': str(NOTES_FILE.absolute()),
            'file_size_bytes': NOTES_FILE.stat().st_size if NOTES_FILE.exists() else 0,
            'last_updated': datetime.now().isoformat()
        }

# Initialize persistent storage
storage = PersistentStorage()

# FastAPI app
app = FastAPI(
    title="MCP Server with Persistent Storage",
    description="A Model Context Protocol server with file-based persistent storage",
    version="2.0.0"
)

@app.get("/")
async def root():
    """Health check endpoint"""
    stats = storage.get_stats()
    return {
        "message": "MCP Server with Persistent Storage is running!",
        "version": "2.0.0",
        "storage": stats
    }

@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return [
        {
            "name": "add_note",
            "description": "Add a new note with title and content (automatically saved to file)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content"}
                },
                "required": ["title", "content"]
            }
        },
        {
            "name": "list_notes",
            "description": "List all saved notes with their IDs, titles, and creation dates",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_note",
            "description": "Get a specific note by its ID",
            "input_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Note ID"}
                },
                "required": ["id"]
            }
        },
        {
            "name": "update_note",
            "description": "Update an existing note's title and/or content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Note ID"},
                    "title": {"type": "string", "description": "New title (optional)"},
                    "content": {"type": "string", "description": "New content (optional)"}
                },
                "required": ["id"]
            }
        },
        {
            "name": "delete_note",
            "description": "Delete a note by its ID (permanently removed from storage)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Note ID to delete"}
                },
                "required": ["id"]
            }
        },
        {
            "name": "calculate",
            "description": "Perform mathematical calculations",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                },
                "required": ["expression"]
            }
        },
        {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_storage_info",
            "description": "Get information about where notes are stored and storage statistics",
            "input_schema": {"type": "object", "properties": {}}
        }
    ]

@app.post("/tools/call", response_model=ToolResponse)
async def call_tool(tool_call: ToolCall):
    """Call a specific tool"""
    
    try:
        if tool_call.name == "add_note":
            title = tool_call.arguments.get("title", "")
            content = tool_call.arguments.get("content", "")
            
            if not title or not content:
                return ToolResponse(
                    content=[{"type": "text", "text": "Error: Both title and content are required"}],
                    is_error=True
                )
            
            note = storage.add_note(title, content)
            return ToolResponse(
                content=[{"type": "text", "text": f"Note added successfully! ID: {note['id']}, Title: {note['title']}"}]
            )
        
        elif tool_call.name == "list_notes":
            notes = storage.get_notes()
            
            if not notes:
                return ToolResponse(
                    content=[{"type": "text", "text": "No notes found."}]
                )
            
            notes_text = []
            for note in notes:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"📝 ID: {note['id']} - {note['title']} (Created: {created})")
            
            result = "📝 Notes:\n" + "\n".join(notes_text)
            return ToolResponse(content=[{"type": "text", "text": result}])
        
        elif tool_call.name == "get_note":
            note_id = int(tool_call.arguments.get("id", 0))
            note = storage.get_note(note_id)
            
            if not note:
                return ToolResponse(
                    content=[{"type": "text", "text": f"Note with ID {note_id} not found."}],
                    is_error=True
                )
            
            created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
            updated = datetime.fromisoformat(note['updated_at']).strftime("%Y-%m-%d %H:%M")
            
            result = f"📄 Note {note['id']}\n"
            result += f"Title: {note['title']}\n"
            result += f"Content: {note['content']}\n"
            result += f"Created: {created}\n"
            result += f"Updated: {updated}"
            
            return ToolResponse(content=[{"type": "text", "text": result}])
        
        elif tool_call.name == "update_note":
            note_id = int(tool_call.arguments.get("id", 0))
            title = tool_call.arguments.get("title")
            content = tool_call.arguments.get("content")
            
            if storage.update_note(note_id, title, content):
                return ToolResponse(
                    content=[{"type": "text", "text": f"Note {note_id} updated successfully!"}]
                )
            else:
                return ToolResponse(
                    content=[{"type": "text", "text": f"Note with ID {note_id} not found."}],
                    is_error=True
                )
        
        elif tool_call.name == "delete_note":
            note_id = int(tool_call.arguments.get("id", 0))
            
            if storage.delete_note(note_id):
                return ToolResponse(
                    content=[{"type": "text", "text": f"Note {note_id} deleted successfully!"}]
                )
            else:
                return ToolResponse(
                    content=[{"type": "text", "text": f"Note with ID {note_id} not found."}],
                    is_error=True
                )
        
        elif tool_call.name == "search_notes_by_date":
            date_filter = tool_call.arguments.get("date_filter", "today")
            keyword = tool_call.arguments.get("keyword")
            
            print(f"🔍 Searching notes: date_filter='{date_filter}', keyword='{keyword}'")  # Debug
            
            results = storage.search_notes_by_date(date_filter, keyword)
            
            if not results:
                filter_desc = f"'{date_filter}'"
                if keyword:
                    filter_desc += f" with keyword '{keyword}'"
                return ToolResponse(
                    content=[{"type": "text", "text": f"No notes found for {filter_desc}."}]
                )
            
            notes_text = []
            for note in results:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"📝 ID: {note['id']} - {note['title']} (Created: {created})")
                # Show content preview for better context
                preview = note['content'][:50] + "..." if len(note['content']) > 50 else note['content']
                notes_text.append(f"   📄 Content: {preview}")
            
            filter_desc = f"📅 Smart search results for '{date_filter}'"
            if keyword:
                filter_desc += f" + '{keyword}'"
            
            result = filter_desc + ":\n" + "\n".join(notes_text)
            return ToolResponse(content=[{"type": "text", "text": result}])
        
        elif tool_call.name == "search_notes":
            keyword = tool_call.arguments.get("keyword", "")
            search_in = tool_call.arguments.get("search_in", "both")
            
            if not keyword:
                return ToolResponse(
                    content=[{"type": "text", "text": "Error: Keyword is required for search"}],
                    is_error=True
                )
            
            results = storage.search_notes(keyword, search_in)
            
            if not results:
                return ToolResponse(
                    content=[{"type": "text", "text": f"No notes found containing '{keyword}' in {search_in}."}]
                )
            
            notes_text = []
            for note in results:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"🔍 ID: {note['id']} - {note['title']} (Created: {created})")
            
            result = f"🔍 Search results for '{keyword}' in {search_in}:\n" + "\n".join(notes_text)
            return ToolResponse(content=[{"type": "text", "text": result}])
        
        elif tool_call.name == "search_notes_by_content_date":
            date_reference = tool_call.arguments.get("date_reference", "")
            
            if not date_reference:
                return ToolResponse(
                    content=[{"type": "text", "text": "Error: Date reference is required"}],
                    is_error=True
                )
            
            results = storage.search_notes_by_content_date(date_reference)
            
            if not results:
                return ToolResponse(
                    content=[{"type": "text", "text": f"No notes found mentioning '{date_reference}' in their content."}]
                )
            
            notes_text = []
            for note in results:
                created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
                notes_text.append(f"📝 ID: {note['id']} - {note['title']} (Created: {created})")
                # Show a preview of the content
                preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                notes_text.append(f"   Content: {preview}")
            
            result = f"📅 Notes mentioning '{date_reference}':\n" + "\n".join(notes_text)
            return ToolResponse(content=[{"type": "text", "text": result}])
        
        elif tool_call.name == "calculate":
            expression = tool_call.arguments.get("expression", "")
            
            if not expression:
                return ToolResponse(
                    content=[{"type": "text", "text": "Error: Expression is required"}],
                    is_error=True
                )
            
            try:
                # Safe evaluation of mathematical expressions
                result = eval(expression, {"__builtins__": {}}, {})
                return ToolResponse(
                    content=[{"type": "text", "text": f"{expression} = {result}"}]
                )
            except Exception as e:
                return ToolResponse(
                    content=[{"type": "text", "text": f"Calculation error: {str(e)}"}],
                    is_error=True
                )
        
        elif tool_call.name == "get_current_time":
            current_time = datetime.now().isoformat()
            return ToolResponse(
                content=[{"type": "text", "text": f"Current date and time: {current_time}"}]
            )
        
        elif tool_call.name == "get_storage_info":
            stats = storage.get_stats()
            
            info = f"📁 **Storage Information:**\n"
            info += f"📍 Location: {stats['storage_location']}\n"
            info += f"📊 Total Notes: {stats['total_notes']}\n"
            info += f"💾 File Size: {stats['file_size_bytes']} bytes\n"
            info += f"🕐 Last Updated: {stats['last_updated']}\n"
            info += f"\n💡 **Note:** All notes are automatically saved to the JSON file above."
            
            return ToolResponse(content=[{"type": "text", "text": info}])
        
        else:
            return ToolResponse(
                content=[{"type": "text", "text": f"Unknown tool: {tool_call.name}"}],
                is_error=True
            )
    
    except Exception as e:
        return ToolResponse(
            content=[{"type": "text", "text": f"Error executing tool {tool_call.name}: {str(e)}"}],
            is_error=True
        )

if __name__ == "__main__":
    print("🚀 Starting MCP Server with Persistent Storage...")
    print(f"📁 Data will be stored in: {DATA_DIR.absolute()}")
    print(f"📝 Notes file: {NOTES_FILE.absolute()}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)