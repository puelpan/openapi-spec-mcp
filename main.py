#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "mcp",
#   "pyyaml",
# ]
# ///

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
from urllib.request import urlopen

import mcp.server.stdio
import mcp.types as types
import yaml
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions


class OpenAPIServer:
    def __init__(self, docs_path: str):
        self.docs_source = docs_path
        self.docs_path = Path(docs_path) if not self._is_url(docs_path) else None
        self.server = Server("openapi-docs")
        self.spec = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing OpenAPI server with docs source: {docs_path}")
        self.load_spec()
        self.setup_handlers()

    def _is_url(self, path: str) -> bool:
        """Check if the path is a URL"""
        parsed = urlparse(path)
        return parsed.scheme in ("http", "https")

    def load_spec(self):
        """Load OpenAPI spec from the specified file or URL"""
        self.logger.info(f"Loading OpenAPI spec from {self.docs_source}")

        try:
            if self._is_url(self.docs_source):
                self._load_spec_from_url()
            else:
                self._load_spec_from_file()

            if self.spec:
                self.logger.info(
                    f"Successfully loaded OpenAPI spec from {self.docs_source}"
                )
        except Exception as e:
            self.logger.error(
                f"Failed to load OpenAPI spec from {self.docs_source}: {e}"
            )
            self.spec = None

    def _load_spec_from_url(self):
        """Load OpenAPI spec from a URL"""
        with urlopen(self.docs_source) as response:
            content = response.read().decode("utf-8")

        # Try to determine format from URL or content
        if self.docs_source.lower().endswith((".yaml", ".yml")):
            self.spec = yaml.safe_load(content)
        elif self.docs_source.lower().endswith(".json"):
            self.spec = json.loads(content)
        else:
            # Try JSON first, then YAML
            try:
                self.spec = json.loads(content)
            except json.JSONDecodeError:
                self.spec = yaml.safe_load(content)

    def _load_spec_from_file(self):
        """Load OpenAPI spec from a local file"""
        if not self.docs_path.exists():
            self.logger.error(f"OpenAPI spec file not found: {self.docs_path}")
            return

        with open(self.docs_path) as f:
            if self.docs_path.suffix.lower() in [".yaml", ".yml"]:
                self.spec = yaml.safe_load(f)
            elif self.docs_path.suffix.lower() == ".json":
                self.spec = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {self.docs_path.suffix}")

    def setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="search_endpoints",
                    description="Search API endpoints by keyword",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search term"}
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="get_endpoint",
                    description="Get details for a specific endpoint",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "method": {"type": "string"},
                        },
                        "required": ["path", "method"],
                    },
                ),
                types.Tool(
                    name="list_all_endpoints",
                    description="List all available API endpoints",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="search_schemas",
                    description="Search schema definitions by name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search term to match against schema names"}
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="get_schema",
                    description="Get a specific schema definition with all $ref references resolved",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema_name": {"type": "string", "description": "Name of the schema to retrieve"}
                        },
                        "required": ["schema_name"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            self.logger.info(f"Tool called: {name} with arguments: {arguments}")

            if name == "search_endpoints":
                query = arguments.get("query", "") if arguments else ""
                self.logger.debug(f"Searching endpoints with query: {query}")
                results = self.search_endpoints(query)
                self.logger.info(f"Found {len(results)} matching endpoints")
                return [
                    types.TextContent(type="text", text=json.dumps(results, indent=2))
                ]

            elif name == "get_endpoint":
                path = arguments.get("path", "") if arguments else ""
                method = arguments.get("method", "") if arguments else ""
                self.logger.debug(f"Getting endpoint details for: {method} {path}")
                result = self.get_endpoint_details(path, method)
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "list_all_endpoints":
                self.logger.debug("Listing all endpoints")
                results = self.list_endpoints()
                self.logger.info(f"Found {len(results)} total endpoints")
                return [
                    types.TextContent(type="text", text=json.dumps(results, indent=2))
                ]

            elif name == "search_schemas":
                query = arguments.get("query", "") if arguments else ""
                self.logger.debug(f"Searching schemas with query: {query}")
                results = self.search_schemas(query)
                self.logger.info(f"Found {len(results)} matching schemas")
                return [
                    types.TextContent(type="text", text=json.dumps(results, indent=2))
                ]

            elif name == "get_schema":
                schema_name = arguments.get("schema_name", "") if arguments else ""
                self.logger.debug(f"Getting schema details for: {schema_name}")
                result = self.get_schema_details(schema_name)
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            else:
                self.logger.error(f"Unknown tool requested: {name}")
                raise ValueError(f"Unknown tool: {name}")

    def search_endpoints(self, query: str) -> List[Dict]:
        """Search endpoints by keyword in path, summary, or description"""
        results = []
        if not self.spec or "paths" not in self.spec:
            return results

        query_lower = query.lower()
        for path, methods in self.spec["paths"].items():
            if isinstance(methods, dict):
                for method, details in methods.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        if (
                            query_lower in path.lower()
                            or query_lower in details.get("summary", "").lower()
                            or query_lower in details.get("description", "").lower()
                            or any(
                                query_lower in tag.lower()
                                for tag in details.get("tags", [])
                            )
                        ):
                            results.append(
                                {
                                    "path": path,
                                    "method": method.upper(),
                                    "summary": details.get("summary", ""),
                                    "tags": details.get("tags", []),
                                }
                            )
        return results

    def get_endpoint_details(self, path: str, method: str) -> Dict:
        """Get full details for a specific endpoint"""
        if not self.spec or "paths" not in self.spec:
            return {"error": "No spec loaded"}

        path_data = self.spec["paths"].get(path, {})
        method_data = path_data.get(method.lower(), {})

        if method_data:
            return {"path": path, "method": method.upper(), "details": method_data}
        return {"error": f"Endpoint {method.upper()} {path} not found"}

    def list_endpoints(self) -> List[Dict]:
        """List all available endpoints"""
        results = []
        if not self.spec or "paths" not in self.spec:
            return results

        for path, methods in self.spec["paths"].items():
            if isinstance(methods, dict):
                for method, details in methods.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        results.append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "summary": details.get("summary", ""),
                            }
                        )
        return results

    def resolve_schema_ref(self, ref: str, visited: set = None) -> Dict:
        """Resolve a $ref reference to its actual schema definition

        Args:
            ref: The reference string (e.g., "#/components/schemas/MySchema" or "#/definitions/MySchema")
            visited: Set of already visited references to prevent circular dependencies

        Returns:
            The resolved schema definition with all nested $ref resolved
        """
        if visited is None:
            visited = set()

        if ref in visited:
            return {"error": f"Circular reference detected: {ref}"}

        visited.add(ref)

        if not self.spec:
            return {"error": "No spec loaded"}

        # Parse the reference path
        # Supports both OpenAPI 3.0 (#/components/schemas/...) and Swagger 2.0 (#/definitions/...)
        if not ref.startswith("#/"):
            return {"error": f"Invalid reference format: {ref}"}

        ref_path = ref[2:].split("/")  # Remove "#/" and split

        # Navigate through the spec to find the referenced schema
        current = self.spec
        for part in ref_path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {"error": f"Reference not found: {ref}"}

        # Deep copy to avoid modifying the original spec
        import copy
        schema = copy.deepcopy(current)

        # Recursively resolve any nested $ref in the schema
        schema = self._resolve_nested_refs(schema, visited)

        return schema

    def _resolve_nested_refs(self, obj, visited: set):
        """Recursively resolve all $ref in a schema object"""
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                resolved = self.resolve_schema_ref(ref, visited.copy())
                # Merge any additional properties that might exist alongside $ref
                for key, value in obj.items():
                    if key != "$ref" and key not in resolved:
                        resolved[key] = value
                return resolved
            else:
                return {key: self._resolve_nested_refs(value, visited) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_nested_refs(item, visited) for item in obj]
        else:
            return obj

    def search_schemas(self, query: str) -> List[Dict]:
        """Search schema definitions by name or description

        Args:
            query: Search term to match against schema names

        Returns:
            List of matching schema names and their descriptions
        """
        results = []
        if not self.spec:
            return results

        # Support both OpenAPI 3.0 (components/schemas) and Swagger 2.0 (definitions)
        schemas = None
        if "components" in self.spec and "schemas" in self.spec["components"]:
            schemas = self.spec["components"]["schemas"]
            prefix = "#/components/schemas/"
        elif "definitions" in self.spec:
            schemas = self.spec["definitions"]
            prefix = "#/definitions/"
        else:
            return results

        query_lower = query.lower()
        for schema_name, schema_def in schemas.items():
            if query_lower in schema_name.lower():
                description = ""
                if isinstance(schema_def, dict):
                    description = schema_def.get("description", schema_def.get("title", ""))

                results.append({
                    "name": schema_name,
                    "ref": f"{prefix}{schema_name}",
                    "description": description,
                    "type": schema_def.get("type", "object") if isinstance(schema_def, dict) else "unknown"
                })

        return results

    def get_schema_details(self, schema_name: str) -> Dict:
        """Get full details for a specific schema with all references resolved

        Args:
            schema_name: Name of the schema (e.g., "PersonaSimplificada")

        Returns:
            The schema definition with all $ref resolved
        """
        if not self.spec:
            return {"error": "No spec loaded"}

        # Support both OpenAPI 3.0 and Swagger 2.0
        ref = None
        if "components" in self.spec and "schemas" in self.spec["components"]:
            if schema_name in self.spec["components"]["schemas"]:
                ref = f"#/components/schemas/{schema_name}"
        elif "definitions" in self.spec:
            if schema_name in self.spec["definitions"]:
                ref = f"#/definitions/{schema_name}"

        if not ref:
            return {"error": f"Schema '{schema_name}' not found"}

        resolved = self.resolve_schema_ref(ref)

        return {
            "name": schema_name,
            "ref": ref,
            "schema": resolved
        }

    async def run(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openapi-docs",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting OpenAPI MCP Server")

    parser = argparse.ArgumentParser(description="OpenAPI MCP Server")
    parser.add_argument(
        "docs_path",
        help="Full path to OpenAPI spec file (YAML or JSON) or URL to remote spec",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: INFO)",
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))
    logger.info(f"Log level set to {args.log_level}")

    try:
        server = OpenAPIServer(args.docs_path)
        logger.info("Server initialized successfully")
        await server.run()
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
