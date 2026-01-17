# Sigma Computing MCP Server

A Model Context Protocol (MCP) server that provides access to Sigma Computing's REST API. This server enables programmatic interaction with Sigma Computing workbooks, datasets, users, and more through a standardized interface.

## Features

- **Dual Transport Support**: STDIO (local) and HTTP/SSE (remote) transports
- **Authentication**: Automatic token management with refresh
- **Workbook Management**: List, create, update, delete, and export workbooks
- **Dataset Operations**: Access and materialize datasets
- **User Management**: Manage organization members and teams
- **Data Export**: Export workbook elements in multiple formats (CSV, XLSX, JSON, JSONL, PDF, PNG) with pagination support
- **Connection Management**: Access data warehouse connections
- **Docker Ready**: Production-ready containerization for deployment

## Transport Modes

This server supports two transport protocols:

### STDIO Transport (Default)
- **Use case**: Local Claude Desktop integration, CLI tools
- **Communication**: Standard input/output streams
- **Best for**: Development, personal use, single-user scenarios

### HTTP/SSE Transport (Streamable HTTP)
- **Use case**: Remote deployment, web services, internal agent frameworks
- **Communication**: HTTP with Server-Sent Events for streaming
- **Best for**: Production deployment, Slack bots, multi-user scenarios, Kubernetes/Docker deployments
- **Port**: 8000 (default)
- **Endpoint**: `/mcp`

You can switch between transports using the `--transport` flag when starting the server.

## Quick Start

### Prerequisites

- **Required:** Sigma Computing organization with API access and credentials (Client ID and Client Secret)
- **For Docker deployment:** Docker and Docker Compose
- **For Python deployment:** Python 3.11+

### Setup

Choose one of two deployment options:

---

### Option 1: Docker Compose (Recommended for HTTP/SSE Transport)

By default, Docker deployment uses **HTTP/SSE transport** on port 8000.

1. **Prepare environment file:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your credentials
   ```

2. **Configure credentials in `.env` file:**
   ```bash
   SIGMA_CLIENT_ID=your_actual_client_id
   SIGMA_CLIENT_SECRET=your_actual_client_secret
   SIGMA_BASE_URL=https://aws-api.sigmacomputing.com
   ```
   
   > **Note:** The API base URL depends on your Sigma organization's cloud provider. See [How to identify your API URL](#identifying-your-api-base-url) below.

3. **Build and run:**
   ```bash
   docker-compose up --build -d
   ```

4. **Verify the server is running:**
   ```bash
   curl http://localhost:8000/mcp
   ```

The server is now accessible at `http://localhost:8000/mcp` for HTTP/SSE connections.

---

### Option 2: Direct Python Execution (STDIO Transport)

By default, Python execution uses **STDIO transport** for local Claude Desktop integration.

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export SIGMA_CLIENT_ID="your_client_id"
   export SIGMA_CLIENT_SECRET="your_client_secret"
   export SIGMA_BASE_URL="https://aws-api.sigmacomputing.com"
   ```
   
   > **Note:** The API base URL depends on your Sigma organization's cloud provider. See [How to identify your API URL](#identifying-your-api-base-url) below.

3. **Run the server:**
   
   **STDIO mode (default):**
   ```bash
   python sigma_mcp_server.py
   ```
   
   **HTTP/SSE mode:**
   ```bash
   python sigma_mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8000
   ```

---

## Identifying Your API Base URL

The Sigma API base URL varies depending on which cloud provider hosts your organization. Using the correct URL is **required** for the server to work.

### Finding Your Base URL

You can find your organization's API base URL in two ways:

#### Method 1: Check in Sigma (Recommended)
1. Log into your Sigma Computing organization
2. Go to **Administration** > **Developer Access**
3. Look for **API base URL** - this is your correct URL

#### Method 2: Determine from Cloud Provider
1. Go to **Administration** > **Account** > **General Settings**
2. Check the **Cloud** field under **Site**
3. Match your cloud provider to the table below:

| Cloud Provider | Base URL |
|----------------|----------|
| AWS-US (West) | `https://aws-api.sigmacomputing.com` |
| AWS-US (East) | `https://api.us-a.aws.sigmacomputing.com` |
| AWS-CA | `https://api.ca.aws.sigmacomputing.com` |
| AWS-EU | `https://api.eu.aws.sigmacomputing.com` |
| AWS-UK | `https://api.uk.aws.sigmacomputing.com` |
| AWS-AU | `https://api.au.aws.sigmacomputing.com` |
| Azure-US | `https://api.us.azure.sigmacomputing.com` |
| Azure-EU | `https://api.eu.azure.sigmacomputing.com` |
| Azure-CA | `https://api.ca.azure.sigmacomputing.com` |
| Azure-UK | `https://api.uk.azure.sigmacomputing.com` |
| GCP | `https://api.sigmacomputing.com` |

**Default in this project:** `https://aws-api.sigmacomputing.com` (AWS-US West)

> 📚 **Official Documentation:** [Get Started with Sigma API - Prerequisites](https://help.sigmacomputing.com/reference/get-started-sigma-api#prerequisites)

---

## Claude Desktop Configuration

After deploying the server, configure Claude Desktop to use it.

**Config file location (macOS):** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Method 1: Direct Python (STDIO - Recommended for Local Use)

Add to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "sigma-computing": {
      "command": "python",
      "args": [
        "/absolute/path/to/mcp-sigma-server/sigma_mcp_server.py"
      ],
      "env": {
        "SIGMA_CLIENT_ID": "your_client_id",
        "SIGMA_CLIENT_SECRET": "your_client_secret",
        "SIGMA_BASE_URL": "https://aws-api.sigmacomputing.com"
      }
    }
  }
}
```

**Important:** 
- Replace `/absolute/path/to/mcp-sigma-server/` with the actual path to your project directory
- Replace credential placeholders with your actual Sigma Computing credentials

### Method 2: Connect to HTTP Server via mcp-remote

If you're running the server in Docker (HTTP mode), use `mcp-remote` as a bridge:

First, start the Docker container:
```bash
cd /path/to/mcp-sigma-server
docker-compose up -d
```

Then add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "sigma-computing": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp"
      ]
    }
  }
}
```

**Note:** This method allows Claude Desktop (which natively uses STDIO) to connect to the HTTP/SSE server running in Docker.

### Method 3: Docker with STDIO (Alternative)

Run the container with STDIO transport and connect directly:

```json
{
  "mcpServers": {
    "sigma-computing": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--env-file",
        "/absolute/path/to/.env",
        "mcp-sigma-server",
        "python",
        "sigma_mcp_server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### Verifying the Connection

After updating the config file:

1. **Restart Claude Desktop** completely (quit and reopen)
2. Look for the 🔌 MCP icon in Claude Desktop
3. You should see "sigma-computing" listed as a connected server
4. Test by asking Claude to list your Sigma workbooks

---

## Production Deployment (HTTP/SSE Transport)

The HTTP/SSE transport is designed for production deployments where the MCP server needs to be accessed remotely or integrated with internal frameworks.

### Use Cases

- **Internal Agent Frameworks**: Deploy as a service for Slack bots, AI agents, or workflow automation
- **Kubernetes/Docker**: Run as a containerized service with standard HTTP health checks
- **Multi-User Access**: Multiple clients can connect to a single server instance
- **Remote Access**: Access the MCP server over the network (with proper authentication/VPN)

### Docker Image Build

```bash
# Build the image
docker build -t sigma-mcp-server .

# Run with HTTP transport (default in Docker)
docker run -d \
  --name sigma-mcp-server \
  -p 8000:8000 \
  -e SIGMA_CLIENT_ID="your_client_id" \
  -e SIGMA_CLIENT_SECRET="your_client_secret" \
  -e SIGMA_BASE_URL="https://aws-api.sigmacomputing.com" \
  sigma-mcp-server
```

### Health Check

The HTTP server includes a health check endpoint:

```bash
curl http://localhost:8000/mcp
```

### Environment Variables for HTTP Mode

In addition to Sigma credentials, you can configure:

```bash
--transport streamable-http  # Use HTTP/SSE transport
--host 0.0.0.0              # Bind to all interfaces
--port 8000                 # Port to listen on (default: 8000)
--log-level INFO            # Logging level
```

### Kubernetes Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sigma-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sigma-mcp-server
  template:
    metadata:
      labels:
        app: sigma-mcp-server
    spec:
      containers:
      - name: sigma-mcp-server
        image: sigma-mcp-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: SIGMA_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: sigma-credentials
              key: client-id
        - name: SIGMA_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: sigma-credentials
              key: client-secret
        - name: SIGMA_BASE_URL
          value: "https://aws-api.sigmacomputing.com"
        livenessProbe:
          httpGet:
            path: /mcp
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /mcp
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: sigma-mcp-server
spec:
  selector:
    app: sigma-mcp-server
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
```

---

## Available Tools

### Workbook Operations
- `sigma_list_workbooks` - List all workbooks with pagination
- `sigma_get_workbook` - Get detailed workbook information
- `sigma_create_workbook` - Create a new workbook
- `sigma_export_workbook` - Export full workbook, single page, or element data (PDF, PNG, XLSX, CSV, JSON)
- `sigma_download_export` - Download an exported file using the queryId
- `sigma_list_workbook_tags` - Get tags for a specific workbook
- `sigma_list_workbook_pages` - List all pages contained within a workbook
- `sigma_list_page_elements` - List all elements from a specific page within a workbook
- `sigma_get_element_query` - Get the SQL query associated with a specific element in a workbook
- `sigma_get_element_lineage` - Get the lineage and dependencies of a specific workbook element
- `sigma_list_element_columns` - List columns associated with a specific element within a workbook

### Dataset Operations
- `sigma_list_datasets` - List all available datasets
- `sigma_get_dataset` - Get detailed dataset information
- `sigma_materialize_dataset` - Trigger dataset materialization

### User Management
- `sigma_list_members` - List organization members (paginated)
- `sigma_get_member` - Get detailed information about a specific member by ID
- `sigma_create_member` - Create new organization member
- `sigma_list_member_teams` - List teams for a specific member
- `sigma_list_teams` - List organization teams (paginated)
- `sigma_list_account_types` - List all account types available in the organization
- `sigma_get_account_type_permissions` - Get all feature permissions for a specific account type

### Permissions Management
- `sigma_grant_permissions` - Grant permissions on workbooks to users or teams (supports version tags)
- `sigma_list_grants` - List all permission grants for a workbook, user, or team (with name resolution)

**⚠️ Known Limitation**: While `sigma_grant_permissions` supports granting permissions on specific version tags, the Sigma API does not return tag/version information when listing grants via `sigma_list_grants`. Tag-specific grants will appear as regular grants without any indication of which version tag they apply to. Use the Sigma UI to view version-specific grant details.

## Available Resources

- `sigma://workbooks` - Access to all workbooks
- `sigma://datasets` - Access to all datasets
- `sigma://members` - Organization members and teams
- `sigma://connections` - Data warehouse connections

## Usage Examples

### List Workbooks
```json
{
  "tool": "sigma_list_workbooks",
  "arguments": {
    "limit": 50,
    "page": "optional_page_token"
  }
}
```

### Get Workbook
```json
{
  "tool": "sigma_get_workbook",
  "arguments": {
    "workbook_id": "workbook-uuid-here"
  }
}
```

### Create Workbook
```json
{
  "tool": "sigma_create_workbook",
  "arguments": {
    "name": "My New Workbook",
    "description": "Optional description",
    "folder_id": "optional-folder-uuid"
  }
}
```

### Export Workbook Data

The export tool supports three modes:

#### Mode 1: Full Workbook Export (PDF/PNG/XLSX)
Export all visible pages as a single document:
```json
{
  "tool": "sigma_export_workbook", 
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "format_type": "pdf",
    "pdf_layout": "landscape"
  }
}
```

#### Mode 2: Single Page Export (PDF/PNG/XLSX)
Export one specific page:
```json
{
  "tool": "sigma_export_workbook", 
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "page_id": "page-id-here",
    "format_type": "pdf",
    "pdf_layout": "landscape"
  }
}
```

#### Mode 3: Element Data Export (CSV/JSON/XLSX)
Export data from a specific table or visualization:
```json
{
  "tool": "sigma_export_workbook", 
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "element_id": "element-uuid-here",
    "format_type": "csv"
  }
}
```

**Format Options by Mode:**
| Mode | Supported Formats |
|------|-------------------|
| Full Workbook | `pdf`, `png`, `xlsx` |
| Single Page | `pdf`, `png`, `xlsx` |
| Element Data | `csv`, `json`, `jsonl`, `xlsx`, `pdf`, `png` |

**Additional Parameters:**
- `pdf_layout` - `portrait` or `landscape` (default: landscape)
- `png_width`, `png_height` - Dimensions in pixels
- `row_limit` - Max rows (element exports only, up to 1M)
- `offset` - Starting row for batched exports (element only)

### Download Exported File
```json
{
  "tool": "sigma_download_export",
  "arguments": {
    "query_id": "query-id-from-export-response"
  }
}
```

> **Export Workflow:**
> 1. Call `sigma_export_workbook` → Returns `queryId`
> 2. Wait a few seconds for the export to complete (Sigma processes asynchronously)
> 3. Call `sigma_download_export` with the `queryId` → Returns the file content
> 
> Note: If you get a 204 response, the export is still processing. Wait and retry.

### List Datasets
```json
{
  "tool": "sigma_list_datasets",
  "arguments": {
    "limit": 50
  }
}
```

### Get Dataset
```json
{
  "tool": "sigma_get_dataset",
  "arguments": {
    "dataset_id": "dataset-uuid-here"
  }
}
```

### Materialize Dataset
```json
{
  "tool": "sigma_materialize_dataset",
  "arguments": {
    "dataset_id": "dataset-uuid-here",
    "schedule": "manual"
  }
}
```

### List Members (Paginated)
```json
{
  "tool": "sigma_list_members",
  "arguments": {
    "limit": 100,
    "page": "optional_page_token",
    "search": "user%40company.com",
    "includeArchived": true,
    "includeInactive": false
  }
}
```

> **Note:** The `search` parameter works for members (searches email, first name, last name) but is NOT supported by the Sigma API for workbooks endpoint.

### Get Specific Member
```json
{
  "tool": "sigma_get_member",
  "arguments": {
    "member_id": "member-uuid-here"
  }
}
```

### List Teams for Member
```json
{
  "tool": "sigma_list_member_teams",
  "arguments": {
    "member_id": "member-uuid-here",
    "limit": 50,
    "page": "optional_page_token"
  }
}
```

### List All Teams (Paginated)
```json
{
  "tool": "sigma_list_teams",
  "arguments": {
    "limit": 50,
    "page": "optional_page_token",
    "name": "optional_team_name_filter",
    "description": "optional_description_filter",
    "visibility": "public"
  }
}
```

### Create New Member
```json
{
  "tool": "sigma_create_member",
  "arguments": {
    "email": "user@company.com",
    "first_name": "John",
    "last_name": "Doe", 
    "account_type": "viewer"
  }
}
```

### Grant Permissions on Workbook

Grant permissions to users or teams on a workbook. You can grant to multiple users/teams in a single request.

#### Grant to a Single User
```json
{
  "tool": "sigma_grant_permissions",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "grants": [
      {
        "member_id": "member-uuid-here",
        "permission": "view"
      }
    ]
  }
}
```

#### Grant to a Team
```json
{
  "tool": "sigma_grant_permissions",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "grants": [
      {
        "team_id": "team-uuid-here",
        "permission": "explore"
      }
    ]
  }
}
```

#### Grant to Multiple Users and Teams
```json
{
  "tool": "sigma_grant_permissions",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "grants": [
      {
        "member_id": "member-uuid-1",
        "permission": "edit"
      },
      {
        "team_id": "team-uuid-1",
        "permission": "view"
      },
      {
        "member_id": "member-uuid-2",
        "permission": "explore"
      }
    ]
  }
}
```

**Permission Levels:**
- `view` - Read-only access to the workbook
- `explore` - Can create variations and explore data
- `edit` - Full editing capabilities

**Optional Parameters:**
- `tag_id` - Grant permissions on a specific version of the workbook (get from `sigma_list_workbook_tags`)

> **Note:** Each grant must specify either `member_id` OR `team_id`, not both. Get member IDs from `sigma_list_members` and team IDs from `sigma_list_teams`.

### List Grants on Workbook

List all permission grants to audit who has access to a workbook. The response includes automatically resolved member and team names.

#### List Grants for a Workbook
```json
{
  "tool": "sigma_list_grants",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "limit": 100
  }
}
```

#### List All Grants for a User
```json
{
  "tool": "sigma_list_grants",
  "arguments": {
    "user_id": "member-uuid-here",
    "limit": 100
  }
}
```

#### List All Grants for a Team
```json
{
  "tool": "sigma_list_grants",
  "arguments": {
    "team_id": "team-uuid-here",
    "limit": 100
  }
}
```

#### List Only Direct Grants (Exclude Inherited)
```json
{
  "tool": "sigma_list_grants",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "direct_grants_only": true,
    "limit": 100
  }
}
```

**Response Format:**
The tool automatically resolves member and team names. If a team cannot be found in the API, it's marked as "Unknown (possibly All Members or system team)" - this typically indicates a special system team like "All Members" that grants access to everyone in the organization.

**Query Options:**
- Specify ONE of: `workbook_id`, `user_id`, or `team_id`
- Use `limit` and `page` for pagination (max 1000 per page)
- Use `direct_grants_only` to exclude inherited permissions

> **Note:** System teams like "All Members" may not appear in `sigma_list_teams` but will show in grants as "Unknown (possibly All Members or system team)". If you see this, it typically means all organization members have access.

### List Account Types
```json
{
  "tool": "sigma_list_account_types",
  "arguments": {
    "page_size": 50,
    "page_token": "optional_page_token"
  }
}
```

### Get Account Type Permissions
```json
{
  "tool": "sigma_get_account_type_permissions",
  "arguments": {
    "account_type_id": "account-type-uuid-here"
  }
}
```

### Get Workbook Tags
```json
{
  "tool": "sigma_list_workbook_tags",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "limit": 100,
    "page": "optional_page_token"
  }
}
```

### List Workbook Pages
```json
{
  "tool": "sigma_list_workbook_pages",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "limit": 100,
    "page": "optional_page_token",
    "tag": "optional_tag_name",
    "bookmark_id": "optional_bookmark_id"
  }
}
```

### List Page Elements
```json
{
  "tool": "sigma_list_page_elements",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "page_id": "page-uuid-here",
    "limit": 100,
    "page": "optional_page_token",
    "tag": "optional_tag_name",
    "bookmark_id": "optional_bookmark_id"
  }
}
```

### Get Element SQL Query
```json
{
  "tool": "sigma_get_element_query",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "element_id": "element-uuid-here",
    "limit": 100,
    "page": "optional_page_token"
  }
}
```

### Get Element Lineage
```json
{
  "tool": "sigma_get_element_lineage",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "element_id": "element-uuid-here"
  }
}
```

### List Element Columns
```json
{
  "tool": "sigma_list_element_columns",
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "element_id": "element-uuid-here",
    "limit": 100,
    "page": "optional_page_token"
  }
}
```

## Configuration

### Command-Line Arguments

The server accepts the following command-line arguments:

| Argument | Description | Default | Options |
|----------|-------------|---------|---------|
| `--transport` | Transport protocol to use | `stdio` | `stdio`, `streamable-http` |
| `--host` | Host to bind to (HTTP only) | `0.0.0.0` | Any valid IP/hostname |
| `--port` | Port to listen on (HTTP only) | `8000` | Any valid port number |
| `--log-level` | Logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

**Examples:**

```bash
# STDIO mode (default)
python sigma_mcp_server.py

# HTTP mode on default port
python sigma_mcp_server.py --transport streamable-http

# HTTP mode on custom port with debug logging
python sigma_mcp_server.py --transport streamable-http --port 9000 --log-level DEBUG
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SIGMA_BASE_URL` | Sigma Computing API base URL (see [Identifying Your API Base URL](#identifying-your-api-base-url)) | `https://aws-api.sigmacomputing.com` |
| `SIGMA_CLIENT_ID` | Your Sigma Computing client ID | Required |
| `SIGMA_CLIENT_SECRET` | Your Sigma Computing client secret | Required |

### Getting Sigma Computing API Credentials

1. Log in to your Sigma Computing organization
2. Go to **Administration** > **Developer Access**
3. Create a new **Client Credential**
4. Copy the Client ID and Client Secret
5. Ensure the credential has appropriate permissions for your use case

## Development

### Project Structure
```
.
├── sigma_mcp_server.py    # Main MCP server implementation
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Docker Compose setup
├── .env.example          # Environment variables template
└── README.md            # This file
```

### Adding New Endpoints

To add support for additional Sigma Computing API endpoints:

1. Add the new tool definition in `handle_list_tools()`
2. Implement the tool logic in `handle_call_tool()`
3. Update the API client methods if needed

### Testing

```bash
# Test the server locally
python sigma_mcp_server.py

# Test with Docker
docker-compose up --build
```

## Security Considerations

- Store API credentials securely using environment variables
- The server runs as a non-root user in the Docker container
- API tokens are automatically refreshed and expire after 1 hour
- Use resource limits in production deployments

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your Client ID and Client Secret
2. **Connection Issues**: Check your network connectivity to Sigma Computing
3. **Permission Errors**: Ensure your API credentials have the necessary permissions
4. **HTTP Connection Failed**: 
   - Ensure the Docker container is running: `docker ps | grep sigma-mcp-server`
   - Check the server is listening: `curl http://localhost:8000/mcp`
   - Verify port 8000 is not blocked by firewall
5. **Claude Desktop Not Connecting**:
   - For STDIO: Check file paths and environment variables in config
   - For HTTP via mcp-remote: Ensure `npx mcp-remote` is accessible and Docker container is running

### Logs

View logs with Docker Compose:
```bash
docker-compose logs -f sigma-mcp-server
```

Check specific container logs:
```bash
docker logs sigma-mcp-server
```

Test HTTP endpoint health:
```bash
# Should return a redirect or SSE stream header
curl -v http://localhost:8000/mcp
```

Check which transport mode is running:
```bash
docker logs sigma-mcp-server 2>&1 | grep "transport"
```

## Agent Framework Integration

### Docker CAgent Framework

This repository includes a pre-configured agent file (`sigma.yaml`) for integration with Docker's **cagent** framework. CAgent enables AI-powered workflow automation with support for:
- Slack bot integration
- Web UI interfaces
- Custom toolsets
- Memory persistence

**Quick start for cagent users:**
1. Deploy the Sigma MCP Server with HTTP/SSE transport
2. Copy `sigma.yaml` to your agent configuration directory
3. Set environment variables (`SIGMA_MCP_URL`, Sigma API credentials)
4. Run with `cagent run sigma.yaml --yolo`

**Detailed guide:** See [CAGENT_INTEGRATION.md](CAGENT_INTEGRATION.md) for complete integration instructions.

### Other Agent Frameworks

The HTTP/SSE transport makes this MCP server compatible with any agent framework that supports the Model Context Protocol. The `sigma.yaml` configuration can be adapted for other systems.

## Documentation Files

- **[README.md](README.md)** - Main documentation (this file)
- **[TRANSPORT_GUIDE.md](TRANSPORT_GUIDE.md)** - Detailed guide for STDIO vs HTTP/SSE transports
- **[CAGENT_INTEGRATION.md](CAGENT_INTEGRATION.md)** - Integration guide for Docker's cagent framework
- **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** - Summary of code changes and architecture
- **[QUICK_START.md](QUICK_START.md)** - Quick reference for common commands

## Support

For issues related to:
- **MCP Server**: Create an issue in this repository
- **Sigma Computing API**: Check [Sigma Computing documentation](https://docs.sigmacomputing.com)
- **Authentication**: Contact your Sigma Computing administrator
- **CAgent Integration**: See [CAGENT_INTEGRATION.md](CAGENT_INTEGRATION.md)

## License

This project is provided as-is for integration with Sigma Computing's API. Please refer to Sigma Computing's terms of service for API usage guidelines.