#!/usr/bin/env python3

import httpx
import asyncio
import json
from typing import Dict, Any, List
from dataclasses import dataclass
import openai  # For OpenAI integration
from anthropic import Anthropic  # For Claude integration

@dataclass
class MCPTool:
    name: str
    description: str
    parameters: Dict[str, Any]

class MCPBridge:
    """Bridge between AI assistants and our MCP server"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.mcp_server_url = mcp_server_url
        self.http_client = httpx.AsyncClient()
        self.available_tools = []
    
    async def initialize(self):
        """Load available tools from MCP server"""
        try:
            response = await self.http_client.get(f"{self.mcp_server_url}/tools")
            tools_data = response.json()
            
            self.available_tools = []
            for tool in tools_data:
                # Convert MCP tool format to AI assistant format
                self.available_tools.append(MCPTool(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool["input_schema"]
                ))
            
            print(f"Loaded {len(self.available_tools)} tools from MCP server")
            return True
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            return False
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on the MCP server and return the result"""
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            
            response = await self.http_client.post(
                f"{self.mcp_server_url}/tools/call",
                json=payload
            )
            
            result = response.json()
            
            if result.get("is_error"):
                return f"Error: {result['content'][0]['text']}"
            
            return result["content"][0]["text"]
            
        except Exception as e:
            return f"Error calling tool {tool_name}: {str(e)}"
    
    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function calling format"""
        openai_tools = []
        
        for tool in self.available_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        
        return openai_tools
    
    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to Anthropic/Claude tool format"""
        anthropic_tools = []
        
        for tool in self.available_tools:
            anthropic_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters
            })
        
        return anthropic_tools
    
    async def close(self):
        await self.http_client.aclose()

class OpenAIIntegration:
    """Integration with OpenAI GPT models"""
    
    def __init__(self, api_key: str, mcp_bridge: MCPBridge):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.mcp_bridge = mcp_bridge
    
    async def chat_with_tools(self, user_message: str) -> str:
        """Chat with OpenAI using MCP tools"""
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant with access to note management and calculation tools. Use these tools when appropriate to help the user."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        tools = self.mcp_bridge.get_openai_tools()
        
        # First API call
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Check if the model wants to call a function
        if assistant_message.tool_calls:
            # Add assistant's message to conversation
            messages.append(assistant_message)
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Call our MCP server
                tool_result = await self.mcp_bridge.call_mcp_tool(
                    function_name, 
                    function_args
                )
                
                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
            
            # Get final response from the model
            final_response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
            
            return final_response.choices[0].message.content
        
        return assistant_message.content

class AnthropicIntegration:
    """Integration with Anthropic Claude"""
    
    def __init__(self, api_key: str, mcp_bridge: MCPBridge):
        self.client = Anthropic(api_key=api_key)
        self.mcp_bridge = mcp_bridge
    
    async def chat_with_tools(self, user_message: str) -> str:
        """Chat with Claude using MCP tools"""
        
        tools = self.mcp_bridge.get_anthropic_tools()
        
        # First API call
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            tools=tools
        )
        
        # Check if Claude wants to use a tool
        if response.stop_reason == "tool_use":
            tool_use = None
            for content in response.content:
                if content.type == "tool_use":
                    tool_use = content
                    break
            
            if tool_use:
                # Call our MCP server
                tool_result = await self.mcp_bridge.call_mcp_tool(
                    tool_use.name,
                    tool_use.input
                )
                
                # Continue conversation with tool result
                follow_up = self.client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": user_message
                        },
                        {
                            "role": "assistant",
                            "content": response.content
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": tool_result
                                }
                            ]
                        }
                    ],
                    tools=tools
                )
                
                return follow_up.content[0].text
        
        return response.content[0].text

class InteractiveChatBot:
    """Interactive chat interface that uses MCP tools"""
    
    def __init__(self, mcp_bridge: MCPBridge):
        self.mcp_bridge = mcp_bridge
        self.conversation_history = []
    
    async def process_message(self, user_input: str) -> str:
        """Process user message and determine if tools are needed"""
        
        # Simple rule-based tool detection (in real scenario, use AI)
        if "add note" in user_input.lower() or "create note" in user_input.lower():
            return await self._handle_add_note(user_input)
        elif "list notes" in user_input.lower() or "show notes" in user_input.lower():
            return await self._handle_list_notes()
        elif "calculate" in user_input.lower() or "=" in user_input or "+" in user_input:
            return await self._handle_calculation(user_input)
        elif "time" in user_input.lower() or "date" in user_input.lower():
            result = await self.mcp_bridge.call_mcp_tool("get_current_time", {})
            return f"Current time: {result}"
        else:
            return "I can help you with notes, calculations, and getting the current time. What would you like to do?"
    
    async def _handle_add_note(self, user_input: str) -> str:
        """Handle note creation with simple parsing"""
        # Simple parsing - in reality, you'd use NLP or AI
        parts = user_input.split(":")
        if len(parts) >= 2:
            title = parts[0].replace("add note", "").replace("create note", "").strip()
            content = ":".join(parts[1:]).strip()
        else:
            title = "Quick Note"
            content = user_input.replace("add note", "").replace("create note", "").strip()
        
        result = await self.mcp_bridge.call_mcp_tool("add_note", {
            "title": title,
            "content": content
        })
        return result
    
    async def _handle_list_notes(self) -> str:
        """Handle listing notes"""
        result = await self.mcp_bridge.call_mcp_tool("list_notes", {})
        return result
    
    async def _handle_calculation(self, user_input: str) -> str:
        """Handle calculations"""
        # Extract mathematical expression
        import re
        expression = re.search(r'[0-9+\-*/().\s]+', user_input)
        if expression:
            result = await self.mcp_bridge.call_mcp_tool("calculate", {
                "expression": expression.group().strip()
            })
            return result
        else:
            return "I couldn't find a mathematical expression to calculate."

async def demo_ai_integration():
    """Demonstration of AI integration"""
    
    # Initialize MCP bridge
    mcp_bridge = MCPBridge()
    
    if not await mcp_bridge.initialize():
        print("Could not connect to MCP server. Make sure it's running on localhost:8000")
        return
    
    print("\n=== MCP AI Integration Demo ===\n")
    
    # Demo 1: Simple rule-based chatbot
    print("1. Testing Simple Rule-Based Chatbot:")
    chatbot = InteractiveChatBot(mcp_bridge)
    
    test_messages = [
        "add note: Meeting Notes: Discussed Q4 planning",
        "add note: Shopping List: Milk, Bread, Eggs",
        "list notes",
        "calculate 15 + 25 * 2",
        "what time is it?"
    ]
    
    for message in test_messages:
        print(f"User: {message}")
        response = await chatbot.process_message(message)
        print(f"Bot: {response}\n")
    
    # Demo 2: Interactive mode
    print("2. Interactive Mode (type 'quit' to exit):")
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
            
            response = await chatbot.process_message(user_input)
            print(f"Bot: {response}")
            
        except KeyboardInterrupt:
            break
    
    await mcp_bridge.close()
    print("Demo completed!")

# Example usage with real AI APIs (commented out - requires API keys)
async def demo_with_real_ai():
    """Example of using real AI APIs - requires API keys"""
    
    # Uncomment and add your API keys to test
    # OPENAI_API_KEY = "your-openai-api-key"
    # ANTHROPIC_API_KEY = "your-anthropic-api-key"
    
    mcp_bridge = MCPBridge()
    await mcp_bridge.initialize()
    
    # # OpenAI Integration
    # openai_integration = OpenAIIntegration(OPENAI_API_KEY, mcp_bridge)
    # response = await openai_integration.chat_with_tools(
    #     "Add a note about today's meeting and then calculate 25 * 4"
    # )
    # print(f"OpenAI Response: {response}")
    
    # # Anthropic Integration  
    # anthropic_integration = AnthropicIntegration(ANTHROPIC_API_KEY, mcp_bridge)
    # response = await anthropic_integration.chat_with_tools(
    #     "List all my notes and tell me what time it is"
    # )
    # print(f"Claude Response: {response}")
    
    await mcp_bridge.close()

if __name__ == "__main__":
    asyncio.run(demo_ai_integration())