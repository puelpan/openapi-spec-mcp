# OpenAPI MCP Server

A Model Context Protocol (MCP) server that provides tools for querying and
exploring OpenAPI specifications. This server allows you to search endpoints,
get detailed endpoint information, and list all available API endpoints from
OpenAPI/Swagger documentation.

## Features

- **Search Endpoints**: Find API endpoints by keyword matching in paths,
  summaries, descriptions, or tags
- **Get Endpoint Details**: Retrieve complete information for a specific
  endpoint
- **List All Endpoints**: Get an overview of all available API endpoints
- **Flexible Input**: Supports both local files (YAML/JSON) and remote URLs
- **Auto-format Detection**: Automatically detects JSON or YAML format

## Installation

This script uses `uv` for dependency management. The required dependencies are
defined inline:

- `mcp`: Model Context Protocol library
- `pyyaml`: YAML parsing support

## Usage

### Basic Usage

```bash
# Using a local OpenAPI spec file
./main.py /path/to/openapi.yaml

# Using a remote OpenAPI spec URL
./main.py https://api.example.com/openapi.json

# With custom log level
./main.py /path/to/openapi.yaml --log-level DEBUG
```

### Command Line Arguments

- `docs_path` (required): Path to OpenAPI specification file (YAML or JSON) or
  URL to remote spec
- `--log-level` (optional): Set logging level (DEBUG, INFO, WARNING, ERROR).
  Default: INFO

### Supported File Formats

- **Local files**: `.yaml`, `.yml`, `.json`
- **Remote URLs**: Any URL ending in `.yaml`, `.yml`, `.json`, or auto-detected
  format

## Available Tools

When running as an MCP server, the following tools are available:

### 1. search_endpoints

Search for API endpoints using keywords.

**Parameters:**

- `query` (string): Search term to match against paths, summaries, descriptions,
  or tags

**Example Response:**

```json
[
  {
    "path": "/users/{id}",
    "method": "GET",
    "summary": "Get user by ID",
    "tags": ["users"]
  }
]
```

### 2. get_endpoint

Get detailed information for a specific endpoint.

**Parameters:**

- `path` (string): The API path (e.g., "/users/{id}")
- `method` (string): HTTP method (GET, POST, PUT, DELETE, PATCH)

**Example Response:**

```json
{
  "path": "/users/{id}",
  "method": "GET",
  "details": {
    "summary": "Get user by ID",
    "description": "Retrieve a specific user by their unique identifier",
    "parameters": [...],
    "responses": {...}
  }
}
```

### 3. list_all_endpoints

List all available API endpoints.

**Example Response:**

```json
[
  {
    "path": "/users",
    "method": "GET",
    "summary": "List all users"
  },
  {
    "path": "/users/{id}",
    "method": "GET",
    "summary": "Get user by ID"
  }
]
```

## Integration with MCP Clients

This server implements the Model Context Protocol and can be used with any
MCP-compatible client. The server communicates via stdio and provides structured
access to OpenAPI documentation.

## Claude code

```json
{
  "mcpServers": {
    "myapidocs": {
      "command": "/path/to/main.py",
      "args": [
        "/path/to/project/openapi-spec.json"
      ]
    },
    "otherapidocs": {
      "command": "/path/to/main.py",
      "args": [
        "https://api.example.com/openapi.json"
      ]
    }
  }
}
```

## Error Handling

- Invalid file paths or URLs will be logged and handled gracefully
- Unsupported file formats will raise clear error messages
- Network issues with remote URLs are caught and reported
- Missing or malformed OpenAPI specs return empty results with appropriate
  logging

## Logging

The server provides comprehensive logging at multiple levels:

- **INFO**: General operation status
- **DEBUG**: Detailed operation information
- **ERROR**: Error conditions and failures

Log output includes timestamps and structured information for debugging.
