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

import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import AnyUrl


# Configure logging
logging.basicConfig(level=logging.INFO)
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
        
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            return {"data": response.content, "content_type": response.headers.get("content-type")}


# Initialize Sigma API client
sigma_api = None

def init_sigma_api():
    """Initialize Sigma API client from environment variables"""
    global sigma_api
    
    base_url = os.getenv("SIGMA_BASE_URL", "https://api.sigmacomputing.com")
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
        data = await sigma_api.make_request("GET", "/v2.1/members?limit=100")
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
            description="Export data from a Sigma Computing workbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workbook_id": {
                        "type": "string",
                        "description": "Unique identifier for the workbook",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["csv", "xlsx", "pdf", "png", "json"],
                        "description": "Export format",
                        "default": "csv"
                    },
                    "element_id": {
                        "type": "string",
                        "description": "Specific element ID to export",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the exported file",
                        "default": "export-data"
                    }
                },
                "required": ["workbook_id"],
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
            description="Get detailed information about a specific organization member by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_id": {
                        "type": "string",
                        "description": "Unique identifier for the member",
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
            description="List all teams in the organization",
            inputSchema={
                "type": "object",
                "properties": {}
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
            payload = {
                "format": arguments.get("format", "csv"),
                "elementId": arguments.get("element_id", ""),
                "name": arguments.get("name", "export-data")
            }
            
            data = await sigma_api.make_request(
                "POST",
                f"/v2/workbooks/{workbook_id}/export",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
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
            data = await sigma_api.make_request("GET", f"/v2.1/members?{query_string}")
            
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
            data = await sigma_api.make_request("GET", "/v2/teams")
            
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

async def main():
    """Main server entry point"""
    try:
        logger.info("Starting Sigma Computing MCP Server...")
        init_sigma_api()
        logger.info("Sigma API client initialized successfully")
        
        # Test the API connection
        try:
            await sigma_api.get_access_token()
            logger.info("Successfully authenticated with Sigma Computing API")
        except Exception as e:
            logger.error(f"Failed to authenticate with Sigma API: {e}")
            raise
        
        logger.info("Server ready, waiting for MCP connections...")
        
        # Run the server using stdin/stdout streams
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
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    # Add signal handlers for graceful shutdown
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)