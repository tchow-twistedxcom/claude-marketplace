# n8n AI Agent Workflow Patterns

Building AI-powered workflows with LLM nodes and agent patterns.

## AI Agent Architecture

### Core Components
```yaml
ai_agent_workflow:
  agent_node:
    purpose: Orchestrates AI decision making
    type: "@n8n/n8n-nodes-langchain.agent"

  llm_node:
    purpose: Language model for reasoning
    types:
      - "@n8n/n8n-nodes-langchain.lmOpenAi"
      - "@n8n/n8n-nodes-langchain.lmChatAnthropic"
      - "@n8n/n8n-nodes-langchain.lmChatOllama"

  tool_nodes:
    purpose: Actions the agent can take
    note: ANY n8n node can be a tool

  memory_node:
    purpose: Conversation/context retention
    types:
      - "@n8n/n8n-nodes-langchain.memoryBufferWindow"
      - "@n8n/n8n-nodes-langchain.memoryXata"

  output_parser:
    purpose: Structure agent output
    types:
      - "@n8n/n8n-nodes-langchain.outputParserStructured"
```

## Basic AI Agent Setup

### Minimal Agent Workflow
```json
{
  "nodes": [
    {
      "id": "trigger-1",
      "name": "Chat Trigger",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "chat"
      }
    },
    {
      "id": "agent-1",
      "name": "AI Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.6,
      "position": [400, 300],
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.message }}",
        "options": {
          "systemMessage": "You are a helpful assistant."
        }
      }
    },
    {
      "id": "llm-1",
      "name": "OpenAI",
      "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
      "typeVersion": 1,
      "position": [400, 500],
      "parameters": {
        "model": "gpt-4",
        "options": {}
      }
    },
    {
      "id": "respond-1",
      "name": "Respond",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [700, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { response: $json.output } }}"
      }
    }
  ],
  "connections": {
    "Chat Trigger": {
      "main": [[{"node": "AI Agent", "type": "main", "index": 0}]]
    },
    "OpenAI": {
      "ai_languageModel": [[{"node": "AI Agent", "type": "ai_languageModel", "index": 0}]]
    },
    "AI Agent": {
      "main": [[{"node": "Respond", "type": "main", "index": 0}]]
    }
  }
}
```

## AI Agent with Tools

### Tool-Enabled Agent
```json
{
  "nodes": [
    {
      "id": "agent-1",
      "name": "AI Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.6,
      "position": [400, 300],
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.query }}"
      }
    },
    {
      "id": "http-tool-1",
      "name": "API Tool",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [400, 500],
      "parameters": {
        "method": "GET",
        "url": "https://api.example.com/data"
      }
    }
  ],
  "connections": {
    "API Tool": {
      "ai_tool": [[{"node": "AI Agent", "type": "ai_tool", "index": 0}]]
    }
  }
}
```

### Making Any Node an AI Tool
```yaml
any_node_as_tool:
  concept: |
    ANY n8n node can be used as an AI tool.
    Connect the node to the agent's ai_tool input.

  configuration:
    1. Add node to workflow
    2. Configure node parameters
    3. Connect to agent's ai_tool port
    4. Agent describes tool purpose from node name

  get_info:
    tool: get_node_as_tool_info
    params:
      nodeType: "nodes-base.httpRequest"

  community_nodes:
    env_var: N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
```

## Memory Patterns

### Window Buffer Memory
```json
{
  "id": "memory-1",
  "name": "Memory",
  "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
  "typeVersion": 1.2,
  "position": [400, 100],
  "parameters": {
    "sessionIdType": "customKey",
    "sessionKey": "={{ $json.sessionId }}",
    "contextWindowLength": 10
  }
}
```

### Connecting Memory
```json
{
  "Memory": {
    "ai_memory": [[{"node": "AI Agent", "type": "ai_memory", "index": 0}]]
  }
}
```

## Common AI Patterns

### RAG (Retrieval Augmented Generation)
```yaml
pattern: rag
components:
  - Document loader (PDF, web page)
  - Text splitter
  - Vector store (Pinecone, Supabase)
  - Retriever
  - AI Agent with retriever tool

workflow:
  1. Load documents
  2. Split into chunks
  3. Generate embeddings
  4. Store in vector database
  5. Query with retriever tool
  6. Generate response with context
```

### Conversational Bot
```yaml
pattern: conversation
components:
  - Webhook trigger
  - Memory node
  - AI Agent
  - Response handler

features:
  - Session management
  - Context retention
  - Multi-turn conversations
```

### Task Automation Agent
```yaml
pattern: task_agent
components:
  - Trigger (schedule/webhook)
  - AI Agent with tools:
    - HTTP Request (APIs)
    - Database (queries)
    - Email (notifications)
    - Slack (messaging)

capabilities:
  - Autonomous task execution
  - Decision making
  - Error handling
  - Result reporting
```

### Data Processing Agent
```yaml
pattern: data_processor
components:
  - Data source trigger
  - AI Agent with:
    - Code node (processing)
    - Classification tools
    - Output formatting

use_cases:
  - Document classification
  - Data extraction
  - Content summarization
  - Sentiment analysis
```

## LLM Node Configuration

### OpenAI Chat Model
```json
{
  "id": "openai-1",
  "name": "OpenAI",
  "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
  "typeVersion": 1,
  "position": [400, 500],
  "parameters": {
    "model": "gpt-4-turbo",
    "options": {
      "temperature": 0.7,
      "maxTokens": 1000,
      "topP": 1,
      "frequencyPenalty": 0,
      "presencePenalty": 0
    }
  }
}
```

### Anthropic Claude
```json
{
  "id": "claude-1",
  "name": "Claude",
  "type": "@n8n/n8n-nodes-langchain.lmChatAnthropic",
  "typeVersion": 1,
  "position": [400, 500],
  "parameters": {
    "model": "claude-3-opus-20240229",
    "options": {
      "temperature": 0.7,
      "maxTokensToSample": 1000
    }
  }
}
```

### Local LLM (Ollama)
```json
{
  "id": "ollama-1",
  "name": "Ollama",
  "type": "@n8n/n8n-nodes-langchain.lmChatOllama",
  "typeVersion": 1,
  "position": [400, 500],
  "parameters": {
    "model": "llama2",
    "baseUrl": "http://localhost:11434",
    "options": {}
  }
}
```

## Output Parsing

### Structured Output Parser
```json
{
  "id": "parser-1",
  "name": "Output Parser",
  "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
  "typeVersion": 1,
  "position": [600, 500],
  "parameters": {
    "schemaType": "manual",
    "inputSchema": {
      "type": "object",
      "properties": {
        "summary": { "type": "string" },
        "sentiment": { "type": "string", "enum": ["positive", "negative", "neutral"] },
        "keywords": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

## Agent Configuration Options

### System Message
```json
{
  "parameters": {
    "options": {
      "systemMessage": "You are a helpful customer service assistant. Be concise and professional. Always verify information before providing it."
    }
  }
}
```

### Return Intermediate Steps
```json
{
  "parameters": {
    "options": {
      "returnIntermediateSteps": true
    }
  }
}
```

## Best Practices

### Agent Design
```yaml
guidelines:
  - Clear system message
  - Focused tool set (3-5 tools max)
  - Proper error handling
  - Memory for conversations
  - Output parsing for structure

performance:
  - Use appropriate model size
  - Set reasonable token limits
  - Implement caching where possible
  - Monitor API costs
```

### Tool Selection
```yaml
tool_guidelines:
  - Name tools clearly
  - Provide tool descriptions
  - Limit to necessary tools
  - Handle tool errors gracefully

common_tools:
  - HTTP Request: API calls
  - Database: Data queries
  - Code: Custom logic
  - Slack/Email: Notifications
  - Calculator: Math operations
```

### Error Handling
```yaml
ai_error_handling:
  - Use IF node for validation
  - Add fallback responses
  - Log failed interactions
  - Implement retry logic
  - Set timeouts appropriately
```
