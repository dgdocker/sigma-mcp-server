#!/usr/bin/env python3
"""
Sigma Computing MCP Server

An MCP (Model Context Protocol) server that provides access to Sigma Computing's REST API.
Supports workbook management, dataset operations, user management, and data exports.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import click
import httpx
import uvicorn
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.cors import CORSMiddleware


# Configure logging (will be reconfigured in main() with proper format)
logger = logging.getLogger("sigma-mcp-server")

class SigmaAPI:
    """Sigma Computing API client wrapper"""
    
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_access_token(self) -> str:
        """Get or refresh access token"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        # Use form-encoded data as per Postman collection
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = await self.client.post(
            f"{self.base_url}/v2/auth/token",
            data=auth_data,  # Changed from json= to data=
            headers={"Content-Type": "application/x-www-form-urlencoded"}  # Changed content type
        )
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        # Tokens expire after 1 hour, refresh 5 minutes early
        self.token_expires_at = datetime.now() + timedelta(minutes=55)
        
        return self.access_token
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Sigma API"""
        token = await self.get_access_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        url = f"{self.base_url}{endpoint}"
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        
        # Handle 204 No Content (export not ready)
        if response.status_code == 204:
            return {"status": "not_ready", "message": "Export is still processing. Please wait and try again."}
        
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        elif response.headers.get("content-type", "").startswith("text/"):
            # Handle CSV and other text responses
            return {"data": response.text, "content_type": response.headers.get("content-type"), "size": len(response.content)}
        else:
            return {"data": response.content, "content_type": response.headers.get("content-type"), "size": len(response.content)}


# Initialize Sigma API client
sigma_api = None

def init_sigma_api():
    """Initialize Sigma API client from environment variables"""
    global sigma_api
    
    base_url = os.getenv("SIGMA_BASE_URL", "https://aws-api.sigmacomputing.com")
    client_id = os.getenv("SIGMA_CLIENT_ID")
    client_secret = os.getenv("SIGMA_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("SIGMA_CLIENT_ID and SIGMA_CLIENT_SECRET environment variables are required")
    
    sigma_api = SigmaAPI(base_url, client_id, client_secret)


# Create MCP server instance
server = Server("sigma-computing")

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available Sigma Computing resources"""
    return [
        Resource(
            uri=AnyUrl("sigma://workbooks"),
            name="Workbooks",
            description="Access to Sigma Computing workbooks",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("sigma://datasets"),
            name="Datasets", 
            description="Access to Sigma Computing datasets",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("sigma://members"),
            name="Members",
            description="Organization members and teams",
            mimeType="application/json",
        ),
        Resource(
            uri=AnyUrl("sigma://connections"),
            name="Connections",
            description="Data warehouse connections",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """Read Sigma Computing resources"""
    if not sigma_api:
        raise RuntimeError("Sigma API not initialized")
    
    uri_str = str(uri)
    
    if uri_str == "sigma://workbooks":
        data = await sigma_api.make_request("GET", "/v2/workbooks?limit=100")
        return json.dumps(data, indent=2)
    
    elif uri_str == "sigma://datasets":
        data = await sigma_api.make_request("GET", "/v2/datasets?limit=100")
        return json.dumps(data, indent=2)
    
    elif uri_str == "sigma://members":
        data = await sigma_api.make_request("GET", "/v2/members?limit=100")
        return json.dumps(data, indent=2)
    
    elif uri_str == "sigma://connections":
        data = await sigma_api.make_request("GET", "/v2/connections/paths?limit=100")
        return json.dumps(data, indent=2)
    
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available Sigma Computing tools"""
    return [
        Tool(
            name="sigma_list_workbooks",
            description="List all Sigma Computing workbooks",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of workbooks to return (default: 50, max: 1000)",
                        "default": 50
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token for pagination",
                    }
                }
            },
        ),
        Tool(
            name="sigma_get_workbook",
            description="Get detailed information about a specific workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier for the workbook",
                    }
                },
                "required": ["workbook_id"],
            },
        ),
        Tool(
            name="sigma_create_workbook",
            description="Create a new Sigma Computing workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the workbook",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the workbook",
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "ID of the folder to create workbook in",
                    }
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="sigma_export_workbook",
            description="Export from Sigma workbook. Three modes: (1) Full workbook - omit element_id and page_id for PDF/PNG/XLSX of all pages, (2) Single page - use page_id for PDF/PNG/XLSX of one page, (3) Element data - use element_id for CSV/JSON/XLSX of table/chart data. Returns queryId for sigma_download_export.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier for the workbook",
                    },
                    "element_id": {
                        "type": "string",
                        "description": "Element ID for data export (CSV, JSON, JSONL, XLSX). Get from sigma_list_page_elements.",
                    },
                    "page_id": {
                        "type": "string",
                        "description": "Page ID for single page export (PDF, PNG, XLSX only). Get from sigma_list_workbook_pages.",
                    },
                    "format_type": {
                        "type": "string",
                        "enum": ["csv", "xlsx", "json", "jsonl", "pdf", "png"],
                        "description": "Export format. Full workbook/page: pdf, png, xlsx. Element: all formats.",
                        "default": "pdf"
                    },
                    "pdf_layout": {
                        "type": "string",
                        "enum": ["portrait", "landscape"],
                        "description": "PDF layout orientation",
                        "default": "landscape"
                    },
                    "png_width": {
                        "type": "integer",
                        "description": "PNG width in pixels",
                    },
                    "png_height": {
                        "type": "integer",
                        "description": "PNG height in pixels",
                    },
                    "row_limit": {
                        "type": "integer",
                        "description": "Max rows to export (element exports only, up to 1M)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting row for batched exports (element exports only)",
                    }
                },
                "required": ["workbook_id"],
            },
        ),
        Tool(
            name="sigma_download_export",
            description="Download an exported file using the queryId from sigma_export_workbook. The export must be ready before downloading.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_id": {
                        "type": "string",
                        "description": "Query ID returned from sigma_export_workbook",
                    }
                },
                "required": ["query_id"],
            },
        ),
        Tool(
            name="sigma_list_datasets",
            description="List all Sigma Computing datasets",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of datasets to return",
                        "default": 50
                    }
                }
            },
        ),
        Tool(
            name="sigma_get_dataset",
            description="Get detailed information about a specific dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Unique identifier for the dataset",
                    }
                },
                "required": ["dataset_id"],
            },
        ),
        Tool(
            name="sigma_materialize_dataset",
            description="Trigger materialization of a dataset in the cloud data warehouse",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Unique identifier for the dataset",
                    },
                    "schedule": {
                        "type": "string",
                        "description": "Materialization schedule",
                        "default": "manual"
                    }
                },
                "required": ["dataset_id"],
            },
        ),
        Tool(
            name="sigma_list_members",
            description="List all organization members (paginated)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of members to return per page (max: 1000)",
                        "default": 50,
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token from nextPage in previous response",
                    },
                    "search": {
                        "type": "string",
                        "description": "Search filter for members (URL encode @ as %40 for emails)",
                    },
                    "includeArchived": {
                        "type": "boolean",
                        "description": "Include archived users in results",
                    },
                    "includeInactive": {
                        "type": "boolean",
                        "description": "Include inactive users in results",
                    }
                }
            },
        ),
        Tool(
            name="sigma_get_member",
            description="Get detailed information about a specific organization member by ID. Note: This endpoint may return 404 for some members depending on permissions or account status. Use sigma_list_members with search parameter as an alternative.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_id": {
                        "type": "string",
                        "description": "Unique identifier for the member (get from sigma_list_members)",
                    }
                },
                "required": ["member_id"],
            },
        ),
        Tool(
            name="sigma_create_member",
            description="Create a new member in the organization",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the new member",
                    },
                    "first_name": {
                        "type": "string",
                        "description": "First name of the member",
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Last name of the member",
                    },
                    "account_type": {
                        "type": "string",
                        "enum": ["viewer", "creator", "admin"],
                        "description": "Account type for the member",
                        "default": "viewer"
                    }
                },
                "required": ["email", "first_name", "last_name"],
            },
        ),
        Tool(
            name="sigma_list_member_teams",
            description="List all teams for a specific organization member",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_id": {
                        "type": "string",
                        "description": "Unique identifier for the member",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of teams to return per page (max: 1000)",
                        "default": 50,
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token from nextPage in previous response",
                    }
                },
                "required": ["member_id"],
            },
        ),
        Tool(
            name="sigma_list_teams",
            description="List all teams in the organization (paginated)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of teams to return per page (max: 1000)",
                        "default": 50,
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token from nextPage in previous response",
                    },
                    "name": {
                        "type": "string",
                        "description": "Filter teams by name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Filter teams by description",
                    },
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private"],
                        "description": "Filter teams by visibility (public or private)",
                    }
                }
            },
        ),
        Tool(
            name="sigma_grant_permissions",
            description="Grant permissions on a workbook to users or teams. Can grant to multiple users/teams in a single request.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook (get from sigma_list_workbooks)",
                    },
                    "grants": {
                        "type": "array",
                        "description": "Array of grant objects to apply",
                        "items": {
                            "type": "object",
                            "properties": {
                                "member_id": {
                                    "type": "string",
                                    "description": "Member ID to grant permissions to (get from sigma_list_members). Do not set both member_id and team_id.",
                                },
                                "team_id": {
                                    "type": "string",
                                    "description": "Team ID to grant permissions to (get from sigma_list_teams). Do not set both member_id and team_id.",
                                },
                                "permission": {
                                    "type": "string",
                                    "enum": ["view", "explore", "edit"],
                                    "description": "Permission level to grant: view (read-only), explore (can create variations), or edit (full editing)",
                                },
                                "tag_id": {
                                    "type": "string",
                                    "description": "Optional: Version tag ID to grant permissions on a specific version (get from sigma_list_tags)",
                                }
                            },
                            "required": ["permission"]
                        }
                    }
                },
                "required": ["workbook_id", "grants"],
            },
        ),
        Tool(
            name="sigma_list_grants",
            description="List all permission grants for a workbook, user, or team. Useful for auditing who has access to resources.",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Workbook ID to list grants for (get from sigma_list_workbooks). Specify one of: workbook_id, user_id, or team_id.",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User/member ID to list grants for (get from sigma_list_members). Specify one of: workbook_id, user_id, or team_id.",
                    },
                    "team_id": {
                        "type": "string",
                        "description": "Team ID to list grants for (get from sigma_list_teams). Specify one of: workbook_id, user_id, or team_id.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of grants to return per page (max: 1000)",
                        "default": 100,
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token from nextPage in previous response for pagination",
                    },
                    "direct_grants_only": {
                        "type": "boolean",
                        "description": "If true, only return direct grants (exclude inherited permissions)",
                        "default": False
                    }
                }
            },
        ),
        Tool(
            name="sigma_list_account_types",
            description="List all account types available in the organization",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return per page (max: 1000, default: 50)",
                        "maximum": 1000,
                        "default": 50
                    },
                    "page_token": {
                        "type": "string",
                        "description": "Page token for pagination",
                    }
                }
            },
        ),
        Tool(
            name="sigma_get_account_type_permissions",
            description="Get all feature permissions for a specific account type",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_type_id": {
                        "type": "string",
                        "description": "Unique identifier of the account type",
                    }
                },
                "required": ["account_type_id"],
            },
        ),
        Tool(
            name="sigma_list_workbook_tags",
            description="Get tags for a specific workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token for pagination",
                    }
                },
                "required": ["workbook_id"],
            },
        ),
        Tool(
            name="sigma_list_workbooks_by_tag",
            description="List all workbooks for a specific version tag (paginated). Use sigma_list_workbook_tags to get the tag ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_id": {
                        "type": "string",
                        "description": "Tag/version tag ID (get from sigma_list_workbook_tags using versionTagId)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of workbooks to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token from nextPage in previous response for pagination",
                    }
                },
                "required": ["tag_id"],
            },
        ),
        Tool(
            name="sigma_list_tags",
            description="List all version tags in the organization (paginated). Use this to discover available tags across all workbooks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of tags to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token from nextPage in previous response for pagination",
                    },
                    "search": {
                        "type": "string",
                        "description": "Search query to filter tags by name",
                    }
                }
            },
        ),
        Tool(
            name="sigma_list_workbook_pages",
            description="List all pages contained within a specified workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token for pagination",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Tag name to retrieve pages from version-tagged workbooks",
                    },
                    "bookmark_id": {
                        "type": "string",
                        "description": "Unique identifier of the bookmark to retrieve pages from saved view",
                    }
                },
                "required": ["workbook_id"],
            },
        ),
        Tool(
            name="sigma_list_page_elements",
            description="List all elements from a specific page within a workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook",
                    },
                    "page_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook page",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token for pagination",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Tag name to retrieve elements from version-tagged workbooks",
                    },
                    "bookmark_id": {
                        "type": "string",
                        "description": "Unique identifier of the bookmark to retrieve elements from saved view",
                    }
                },
                "required": ["workbook_id", "page_id"],
            },
        ),
        Tool(
            name="sigma_get_element_query",
            description="Get the SQL query associated with a specific element in a workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook",
                    },
                    "element_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook element",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token for pagination",
                    }
                },
                "required": ["workbook_id", "element_id"],
            },
        ),
        Tool(
            name="sigma_get_element_lineage",
            description="Get the lineage and dependencies of a specific workbook element",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook",
                    },
                    "element_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook element (must be a data element like table, pivot table, or visualization)",
                    }
                },
                "required": ["workbook_id", "element_id"],
            },
        ),
        Tool(
            name="sigma_list_element_columns",
            description="List columns associated with a specific element within a workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook",
                    },
                    "element_id": {
                        "type": "string",
                        "description": "Unique identifier of the workbook element",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return per page (max: 1000)",
                        "maximum": 1000
                    },
                    "page": {
                        "type": "string",
                        "description": "Page token for pagination",
                    }
                },
                "required": ["workbook_id", "element_id"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for Sigma Computing operations"""
    if not sigma_api:
        raise RuntimeError("Sigma API not initialized")
    
    try:
        if name == "sigma_list_workbooks":
            limit = arguments.get("limit", 50)
            page = arguments.get("page")
            
            params = {"limit": limit}
            if page:
                params["page"] = page
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            data = await sigma_api.make_request("GET", f"/v2/workbooks?{query_string}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_get_workbook":
            workbook_id = arguments["workbook_id"]
            data = await sigma_api.make_request("GET", f"/v2/workbooks/{workbook_id}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_create_workbook":
            payload = {
                "name": arguments["name"],
                "description": arguments.get("description", ""),
                "folderId": arguments.get("folder_id")
            }
            
            data = await sigma_api.make_request(
                "POST", 
                "/v2/workbooks",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_export_workbook":
            workbook_id = arguments["workbook_id"]
            element_id = arguments.get("element_id")
            page_id = arguments.get("page_id")
            format_type = arguments.get("format_type", "pdf")
            
            # Determine export mode
            if element_id:
                export_mode = "element"
            elif page_id:
                export_mode = "page"
            else:
                export_mode = "workbook"  # Full workbook export
            
            # Validate format for non-element exports
            if export_mode in ["page", "workbook"] and format_type in ["csv", "json", "jsonl"]:
                return [TextContent(type="text", text=f"Error: {export_mode.title()} exports only support pdf, png, or xlsx formats. Use element_id for {format_type} data exports.")]
            
            # Build format object based on type
            if format_type == "pdf":
                format_obj = {
                    "type": "pdf",
                    "layout": arguments.get("pdf_layout", "landscape")
                }
            elif format_type == "png":
                format_obj = {"type": "png"}
                if arguments.get("png_width"):
                    format_obj["pixelWidth"] = arguments["png_width"]
                if arguments.get("png_height"):
                    format_obj["pixelHeight"] = arguments["png_height"]
            else:
                format_obj = {"type": format_type}
            
            payload = {"format": format_obj}
            
            # Add element or page ID (omit both for full workbook)
            if element_id:
                payload["elementId"] = element_id
            elif page_id:
                payload["pageId"] = page_id
            # No ID = full workbook export
            
            # Add optional parameters (element exports only)
            if element_id:
                if arguments.get("row_limit"):
                    payload["rowLimit"] = arguments["row_limit"]
                if arguments.get("offset"):
                    payload["offset"] = arguments["offset"]
            
            data = await sigma_api.make_request(
                "POST",
                f"/v2/workbooks/{workbook_id}/export",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Add helpful context to response
            mode_info = {"export_mode": export_mode, "format": format_type}
            data.update(mode_info)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_download_export":
            query_id = arguments["query_id"]
            
            data = await sigma_api.make_request(
                "GET",
                f"/v2/query/{query_id}/download"
            )
            
            # Handle 204 Not Ready response
            if data.get("status") == "not_ready":
                return [TextContent(type="text", text="Export is still processing. Please wait a few seconds and try again.")]
            
            # Handle text responses (CSV, JSON, etc.)
            if isinstance(data.get("data"), str):
                content_type = data.get("content_type", "unknown")
                size = data.get("size", 0)
                content = data["data"]
                
                # Return the actual content for text formats
                if "csv" in content_type or "json" in content_type or "text" in content_type:
                    return [TextContent(type="text", text=f"Content-Type: {content_type}\nSize: {size} bytes\n\n{content}")]
                else:
                    return [TextContent(type="text", text=f"Export downloaded. Content-Type: {content_type}. Size: {size} bytes")]
            
            # Handle binary responses
            elif isinstance(data.get("data"), bytes):
                return [TextContent(type="text", text=f"Export downloaded (binary). Content-Type: {data.get('content_type', 'unknown')}. Size: {data.get('size', 0)} bytes")]
            
            else:
                return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_datasets":
            limit = arguments.get("limit", 50)
            data = await sigma_api.make_request("GET", f"/v2/datasets?limit={limit}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_get_dataset":
            dataset_id = arguments["dataset_id"]
            data = await sigma_api.make_request("GET", f"/v2/datasets/{dataset_id}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_materialize_dataset":
            dataset_id = arguments["dataset_id"]
            payload = {"schedule": arguments.get("schedule", "manual")}
            
            data = await sigma_api.make_request(
                "POST",
                f"/v2/datasets/{dataset_id}/materialize",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_members":
            limit = arguments.get("limit", 50)
            page = arguments.get("page")
            search = arguments.get("search")
            include_archived = arguments.get("includeArchived")
            include_inactive = arguments.get("includeInactive")
            
            params = {"limit": limit}
            if page:
                params["page"] = page
            if search:
                params["search"] = search
            if include_archived is not None:
                params["includeArchived"] = str(include_archived).lower()
            if include_inactive is not None:
                params["includeInactive"] = str(include_inactive).lower()
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            data = await sigma_api.make_request("GET", f"/v2/members?{query_string}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_get_member":
            member_id = arguments["member_id"]
            data = await sigma_api.make_request("GET", f"/v2/members/{member_id}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_create_member":
            payload = {
                "email": arguments["email"],
                "firstName": arguments["first_name"],
                "lastName": arguments["last_name"],
                "accountType": arguments.get("account_type", "viewer")
            }
            
            data = await sigma_api.make_request(
                "POST",
                "/v2/members",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_member_teams":
            member_id = arguments["member_id"]
            limit = arguments.get("limit", 50)
            page = arguments.get("page")
            
            params = {"limit": limit}
            if page:
                params["page"] = page
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            data = await sigma_api.make_request("GET", f"/v2/members/{member_id}/teams?{query_string}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_teams":
            limit = arguments.get("limit", 50)
            page = arguments.get("page")
            name = arguments.get("name")
            description = arguments.get("description")
            visibility = arguments.get("visibility")
            
            params = {"limit": limit}
            if page:
                params["page"] = page
            if name:
                params["name"] = name
            if description:
                params["description"] = description
            if visibility:
                params["visibility"] = visibility
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            data = await sigma_api.make_request("GET", f"/v2.1/teams?{query_string}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_grant_permissions":
            workbook_id = arguments["workbook_id"]
            grants_input = arguments["grants"]
            
            # Transform the input grants to the API format
            grants_payload = []
            for grant in grants_input:
                grant_obj = {
                    "grantee": {},
                    "permission": grant["permission"]
                }
                
                # Set either memberId or teamId
                if grant.get("member_id"):
                    grant_obj["grantee"]["memberId"] = grant["member_id"]
                elif grant.get("team_id"):
                    grant_obj["grantee"]["teamId"] = grant["team_id"]
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": "Each grant must specify either member_id or team_id"
                        }, indent=2)
                    )]
                
                # Add optional tagId
                if grant.get("tag_id"):
                    grant_obj["tagId"] = grant["tag_id"]
                
                grants_payload.append(grant_obj)
            
            payload = {"grants": grants_payload}
            
            data = await sigma_api.make_request(
                "POST",
                f"/v2/workbooks/{workbook_id}/grants",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Return success message with details
            result = {
                "success": True,
                "workbook_id": workbook_id,
                "grants_applied": len(grants_payload),
                "details": grants_payload
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "sigma_list_grants":
            # Build query parameters
            params = {}
            
            # Determine which filter to use
            if arguments.get("workbook_id"):
                params["inodeId"] = arguments["workbook_id"]
            elif arguments.get("user_id"):
                params["userId"] = arguments["user_id"]
            elif arguments.get("team_id"):
                params["teamId"] = arguments["team_id"]
            
            # Add pagination and filter parameters
            limit = arguments.get("limit", 100)
            params["limit"] = limit
            
            if arguments.get("page"):
                params["page"] = arguments["page"]
            
            if arguments.get("direct_grants_only"):
                params["directGrantsOnly"] = "true" if arguments["direct_grants_only"] else "false"
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            data = await sigma_api.make_request("GET", f"/v2/grants?{query_string}")
            
            # Enhance grants with resolved names
            if "entries" in data:
                # Get all unique member and team IDs
                member_ids = set()
                team_ids = set()
                
                for grant in data["entries"]:
                    if grant.get("memberId"):
                        member_ids.add(grant["memberId"])
                    elif grant.get("teamId"):
                        team_ids.add(grant["teamId"])
                
                # Fetch member names
                member_names = {}
                if member_ids:
                    try:
                        members_data = await sigma_api.make_request("GET", "/v2/members?limit=1000")
                        for member in members_data.get("entries", []):
                            mid = member.get("memberId")
                            if mid in member_ids:
                                email = member.get("email", "")
                                first = member.get("firstName", "")
                                last = member.get("lastName", "")
                                name = f"{first} {last} ({email})".strip()
                                if name.startswith("("):
                                    name = email
                                member_names[mid] = name
                    except Exception as e:
                        logger.warning(f"Could not fetch member names: {e}")
                
                # Fetch team names
                team_names = {}
                if team_ids:
                    try:
                        teams_data = await sigma_api.make_request("GET", "/v2.1/teams?limit=1000")
                        for team in teams_data.get("entries", []):
                            tid = team.get("teamId")
                            if tid in team_ids:
                                team_names[tid] = team.get("name", "Unknown")
                    except Exception as e:
                        logger.warning(f"Could not fetch team names: {e}")
                
                # Enhance each grant with resolved names
                for grant in data["entries"]:
                    if grant.get("memberId"):
                        mid = grant["memberId"]
                        grant["memberName"] = member_names.get(
                            mid, 
                            "Unknown (member not found)"
                        )
                    elif grant.get("teamId"):
                        tid = grant["teamId"]
                        grant["teamName"] = team_names.get(
                            tid,
                            "Unknown (possibly All Members or system team)"
                        )
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_account_types":
            page_size = arguments.get("page_size", 50)
            page_token = arguments.get("page_token")
            
            params = {"pageSize": page_size}
            if page_token:
                params["pageToken"] = page_token
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            data = await sigma_api.make_request("GET", f"/v2/accountTypes?{query_string}")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_get_account_type_permissions":
            account_type_id = arguments["account_type_id"]
            data = await sigma_api.make_request("GET", f"/v2/accountTypes/{account_type_id}/permissions")
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_workbook_tags":
            workbook_id = arguments["workbook_id"]
            limit = arguments.get("limit")
            page = arguments.get("page")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = f"/v2/workbooks/{workbook_id}/tags"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_workbooks_by_tag":
            tag_id = arguments["tag_id"]
            limit = arguments.get("limit")
            page = arguments.get("page")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = f"/v2/tags/{tag_id}/workbooks"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_tags":
            limit = arguments.get("limit")
            page = arguments.get("page")
            search = arguments.get("search")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            if search:
                params["search"] = search
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = "/v2/tags"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_workbook_pages":
            workbook_id = arguments["workbook_id"]
            limit = arguments.get("limit")
            page = arguments.get("page")
            tag = arguments.get("tag")
            bookmark_id = arguments.get("bookmark_id")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            if tag:
                params["tag"] = tag
            if bookmark_id:
                params["bookmarkId"] = bookmark_id
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = f"/v2/workbooks/{workbook_id}/pages"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_page_elements":
            workbook_id = arguments["workbook_id"]
            page_id = arguments["page_id"]
            limit = arguments.get("limit")
            page = arguments.get("page")
            tag = arguments.get("tag")
            bookmark_id = arguments.get("bookmark_id")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            if tag:
                params["tag"] = tag
            if bookmark_id:
                params["bookmarkId"] = bookmark_id
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = f"/v2/workbooks/{workbook_id}/pages/{page_id}/elements"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_get_element_query":
            workbook_id = arguments["workbook_id"]
            element_id = arguments["element_id"]
            limit = arguments.get("limit")
            page = arguments.get("page")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = f"/v2/workbooks/{workbook_id}/elements/{element_id}/query"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_get_element_lineage":
            workbook_id = arguments["workbook_id"]
            element_id = arguments["element_id"]
            
            endpoint = f"/v2/workbooks/{workbook_id}/lineage/elements/{element_id}"
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "sigma_list_element_columns":
            workbook_id = arguments["workbook_id"]
            element_id = arguments["element_id"]
            limit = arguments.get("limit")
            page = arguments.get("page")
            
            params = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()]) if params else ""
            endpoint = f"/v2/workbooks/{workbook_id}/elements/{element_id}/columns"
            if query_string:
                endpoint += f"?{query_string}"
            
            data = await sigma_api.make_request("GET", endpoint)
            
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def run_stdio_server():
    """Run server with STDIO transport (for Claude Desktop)."""
    logger.info("Running with STDIO transport...")
        
        # Test the API connection
        try:
            await sigma_api.get_access_token()
            logger.info("Successfully authenticated with Sigma Computing API")
        except Exception as e:
            logger.error(f"Failed to authenticate with Sigma API: {e}")
            raise
        
        logger.info("Server ready, waiting for MCP connections...")
        
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sigma-computing",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

def run_http_server(host: str, port: int):
    """Run server with Streamable HTTP transport (for internal-agents)."""
    logger.info(f"Running with Streamable HTTP transport on {host}:{port}...")
    
    # Test the API connection synchronously before starting server
    async def test_connection():
        try:
            await sigma_api.get_access_token()
            logger.info("Successfully authenticated with Sigma Computing API")
    except Exception as e:
            logger.error(f"Failed to authenticate with Sigma API: {e}")
        raise

    asyncio.run(test_connection())
    
    # Create the session manager
    session_manager = StreamableHTTPSessionManager(
        app=server,
        json_response=False,  # Use SSE streaming
    )
    
    # ASGI handler for streamable HTTP connections
    async def handle_streamable_http(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)
    
    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Manage session manager lifecycle."""
        async with session_manager.run():
            logger.info("Streamable HTTP session manager started!")
            try:
                yield
            finally:
                logger.info("Shutting down session manager...")
    
    # Create Starlette ASGI application
    starlette_app = Starlette(
        debug=False,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    starlette_app = CORSMiddleware(
        starlette_app,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        expose_headers=["Mcp-Session-Id"],
    )
    
    logger.info(f"Server ready at http://{host}:{port}/mcp")
    uvicorn.run(starlette_app, host=host, port=port)

@click.command()
@click.option(
    '--transport',
    type=click.Choice(['stdio', 'streamable-http']),
    default='stdio',
    help='Transport protocol to use'
)
@click.option('--host', default='0.0.0.0', help='Host to bind to (HTTP only)')
@click.option('--port', default=8000, type=int, help='Port to listen on (HTTP only)')
@click.option(
    '--log-level',
    default='INFO',
    help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
)
def main(transport: str, host: str, port: int, log_level: str):
    """Run the Sigma MCP Server with specified transport."""
    # Configure logging (force reconfigure)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    
    try:
        logger.info(f"Starting Sigma Computing MCP Server with {transport} transport...")
        logger.info(f"Arguments: transport={transport}, host={host}, port={port}")
        init_sigma_api()
        logger.info("Sigma API client initialized successfully")
        
        if transport == 'streamable-http':
            logger.info("Routing to HTTP server...")
            run_http_server(host, port)
        else:
            logger.info("Routing to STDIO server...")
            asyncio.run(run_stdio_server())
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()