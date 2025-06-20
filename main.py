#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
from datetime import datetime
import json
import re

# Initialize FastAPI app
app = FastAPI(
    title="Simple MCP Server",
    description="A simple Model Context Protocol server using FastAPI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class Note(BaseModel):
    id: str
    title: str
    content: str
    created_at: str

class AddNoteRequest(BaseModel):
    title: str
    content: str

class GetNoteRequest(BaseModel):
    id: str

class DeleteNoteRequest(BaseModel):
    id: str

class CalculateRequest(BaseModel):
    expression: str

class MCPToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPResponse(BaseModel):
    content: List[Dict[str, str]]
    is_error: Optional[bool] = False

class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]

# In-memory storage
notes_storage: Dict[str, Note] = {}
note_counter = 1

# MCP Tool definitions
AVAILABLE_TOOLS = [
    MCPTool(
        name="add_note",
        description="Add a new note to the system",
        input_schema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the note"
                },
                "content": {
                    "type": "string",
                    "description": "Content of the note"
                }
            },
            "required": ["title", "content"]
        }
    ),
    MCPTool(
        name="get_note",
        description="Retrieve a note by its ID",
        input_schema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "ID of the note to retrieve"
                }
            },
            "required": ["id"]
        }
    ),
    MCPTool(
        name="list_notes",
        description="List all available notes",
        input_schema={
            "type": "object",
            "properties": {}
        }
    ),
    MCPTool(
        name="delete_note",
        description="Delete a note by its ID",
        input_schema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "ID of the note to delete"
                }
            },
            "required": ["id"]
        }
    ),
    MCPTool(
        name="calculate",
        description="Perform basic mathematical calculations",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')"
                }
            },
            "required": ["expression"]
        }
    ),
    MCPTool(
        name="get_current_time",
        description="Get the current date and time",
        input_schema={
            "type": "object",
            "properties": {}
        }
    )
]

# Helper functions
def safe_eval(expression: str) -> float:
    """Safely evaluate a mathematical expression"""
    # Remove any non-mathematical characters
    sanitized = re.sub(r'[^0-9+\-*/().\s]', '', expression)
    if sanitized != expression:
        raise ValueError("Invalid characters in expression")
    
    # Use eval with restricted globals for safety
    allowed_names = {
        "__builtins__": {},
        "__name__": "__main__",
    }
    return eval(sanitized, allowed_names)

# API Routes

@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "name": "Simple MCP Server",
        "version": "1.0.0",
        "description": "A FastAPI-based MCP server with note management and calculation tools",
        "capabilities": ["tools"]
    }

@app.get("/tools", response_model=List[MCPTool])
async def list_tools():
    """List all available MCP tools"""
    return AVAILABLE_TOOLS

@app.post("/tools/call", response_model=MCPResponse)
async def call_tool(request: MCPToolRequest):
    """Execute an MCP tool with given arguments"""
    global note_counter
    
    try:
        tool_name = request.name
        args = request.arguments
        
        if tool_name == "add_note":
            title = args.get("title")
            content = args.get("content")
            
            if not title or not content:
                raise HTTPException(status_code=400, detail="Title and content are required")
            
            note_id = str(note_counter)
            note = Note(
                id=note_id,
                title=title,
                content=content,
                created_at=datetime.now().isoformat()
            )
            notes_storage[note_id] = note
            note_counter += 1
            
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": f"Note added successfully! ID: {note_id}"
                }]
            )
        
        elif tool_name == "get_note":
            note_id = args.get("id")
            if not note_id:
                raise HTTPException(status_code=400, detail="Note ID is required")
            
            note = notes_storage.get(note_id)
            if not note:
                return MCPResponse(
                    content=[{
                        "type": "text",
                        "text": f"Note with ID {note_id} not found."
                    }]
                )
            
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": f"Title: {note.title}\nContent: {note.content}\nCreated: {note.created_at}"
                }]
            )
        
        elif tool_name == "list_notes":
            if not notes_storage:
                return MCPResponse(
                    content=[{
                        "type": "text",
                        "text": "No notes found."
                    }]
                )
            
            note_list = "\n".join([
                f"ID: {note.id} - {note.title}" 
                for note in notes_storage.values()
            ])
            
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": f"Notes:\n{note_list}"
                }]
            )
        
        elif tool_name == "delete_note":
            note_id = args.get("id")
            if not note_id:
                raise HTTPException(status_code=400, detail="Note ID is required")
            
            deleted_note = notes_storage.pop(note_id, None)
            message = (
                f"Note with ID {note_id} deleted successfully." 
                if deleted_note 
                else f"Note with ID {note_id} not found."
            )
            
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": message
                }]
            )
        
        elif tool_name == "calculate":
            expression = args.get("expression")
            if not expression:
                raise HTTPException(status_code=400, detail="Expression is required")
            
            try:
                result = safe_eval(expression)
                return MCPResponse(
                    content=[{
                        "type": "text",
                        "text": f"{expression} = {result}"
                    }]
                )
            except Exception as e:
                return MCPResponse(
                    content=[{
                        "type": "text",
                        "text": f"Calculation error: {str(e)}"
                    }],
                    is_error=True
                )
        
        elif tool_name == "get_current_time":
            current_time = datetime.now().isoformat()
            return MCPResponse(
                content=[{
                    "type": "text",
                    "text": f"Current date and time: {current_time}"
                }]
            )
        
        else:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    
    except HTTPException:
        raise
    except Exception as e:
        return MCPResponse(
            content=[{
                "type": "text",
                "text": f"Error: {str(e)}"
            }],
            is_error=True
        )

# Additional convenience endpoints (non-MCP)
@app.get("/notes")
async def get_all_notes():
    """Get all notes (convenience endpoint)"""
    return list(notes_storage.values())

@app.post("/notes")
async def create_note(note_request: AddNoteRequest):
    """Create a new note (convenience endpoint)"""
    global note_counter
    
    note_id = str(note_counter)
    note = Note(
        id=note_id,
        title=note_request.title,
        content=note_request.content,
        created_at=datetime.now().isoformat()
    )
    notes_storage[note_id] = note
    note_counter += 1
    
    return note

@app.get("/notes/{note_id}")
async def get_note(note_id: str):
    """Get a specific note (convenience endpoint)"""
    note = notes_storage.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a specific note (convenience endpoint)"""
    note = notes_storage.pop(note_id, None)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": f"Note {note_id} deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )