# Simple MCP Server with FastAPI

A simple Model Context Protocol (MCP) server implementation using Python and FastAPI. This project demonstrates how to create an MCP-compatible server that provides tools for note management and basic calculations.

## Features

- **Note Management**: Add, retrieve, list, and delete notes
- **Calculator**: Perform basic mathematical calculations
- **Time Service**: Get current date and time
- **RESTful API**: FastAPI-based with automatic OpenAPI documentation
- **MCP Compatible**: Follows MCP protocol standards
- **Docker Support**: Containerized deployment

## Tools Available

1. **add_note** - Add a new note with title and content
2. **get_note** - Retrieve a specific note by ID
3. **list_notes** - List all available notes
4. **delete_note** - Delete a note by ID
5. **calculate** - Perform mathematical calculations
6. **get_current_time** - Get current date and time

## Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   python main.py
   ```
   
   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access the API**:
   - Server: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - OpenAPI Schema: http://localhost:8000/openapi.json

### Using Docker

1. **Build the image**:
   ```bash
   docker build -t simple-mcp-server .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 simple-mcp-server
   ```

## Usage Examples

### Using the Client Example

Run the provided client example to see all tools in action:

```bash
python client_example.py
```

### Manual API Testing

#### List Available Tools
```bash
curl http://localhost:8000/tools
```

#### Add a Note
```bash
curl -X POST "http://localhost:8000/tools/call" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "add_note",
       "arguments": {
         "title": "My First Note",
         "content": "This is the content of my note"
       }
     }'
```

#### Get a Note
```bash
curl -X POST "http://localhost:8000/tools/call" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "get_note",
       "arguments": {
         "id": "1"
       }
     }'
```

#### List All Notes
```bash
curl -X POST "http://localhost:8000/tools/call" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "list_notes",
       "arguments": {}
     }'
```

#### Perform Calculation
```bash
curl -X POST "http://localhost:8000/tools/call" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "calculate",
       "arguments": {
         "expression": "15 + 25 * 2"
       }
     }'
```

#### Get Current Time
```bash
curl -X POST "http://localhost:8000/tools/call" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "get_current_time",
       "arguments": {}
     }'
```

## API Endpoints

### MCP Protocol Endpoints

- `GET /` - Server information
- `GET /tools` - List available tools
- `POST /tools/call` - Execute a tool

### Convenience REST Endpoints

- `GET /notes` - Get all notes
- `POST /notes` - Create a new note
- `GET /notes/{note_id}` - Get a specific note
- `DELETE /notes/{note_id}` - Delete a specific note

## Project Structure

```
simple-mcp-server/
├── main.py              # Main FastAPI application
├── client_example.py    # Example client usage
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
└── README.md           # This file
```

## Development

### Adding New Tools

To add a new tool:

1. Define the tool in the `AVAILABLE_TOOLS` list
2. Add the tool logic in the `call_tool` endpoint
3. Update the documentation

### Testing

The server includes automatic API documentation at `/docs` when running. You can also test the MCP protocol compatibility using the provided client example.

## MCP Protocol Compliance

This server implements the Model Context Protocol (MCP) specification:

- **Tools**: Provides discoverable tools with JSON schema validation
- **Request/Response**: Uses standard MCP request/response format
- **Error Handling**: Proper error responses with `is_error` flag
- **Content Types**: Supports text content type in responses

## Security Notes

- The calculator uses `eval()` with input sanitization - only basic mathematical operations are allowed
- No authentication is implemented - add authentication for production use
- CORS is enabled for all origins - restrict for production use

## License

MIT License - Feel free to use this project as a starting point for your own MCP servers.