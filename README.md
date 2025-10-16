# OpenAPI MCP Server

MCP server that turns any OpenAPI/Swagger spec into queryable tools for your
LLM. Search endpoints, get endpoint details, and explore schemas from your API
documentation.

## Setup for Claude Code

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-api": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/puelpan/openapi-spec-mcp.git@main",
        "openapi-spec-mcp",
        "/path/to/your/openapi.yaml"
      ]
    }
  }
}
```

Or use a remote URL:

```json
{
  "mcpServers": {
    "my-api": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/puelpan/openapi-spec-mcp.git@main",
        "openapi-spec-mcp",
        "https://api.example.com/openapi.json"
      ]
    }
  }
}
```

## Available Tools

- **search_endpoints**: Find endpoints by keyword
- **get_endpoint**: Get detailed endpoint info (parameters, responses, etc.)
- **list_all_endpoints**: List all available endpoints
- **search_schemas**: Find schema definitions by name
- **get_schema**: Get schema details with resolved references

## Supported Formats

- Local files: `.yaml`, `.yml`, `.json`
- Remote URLs: Any OpenAPI spec URL (format auto-detected)
