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
