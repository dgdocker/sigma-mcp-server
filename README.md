# Sigma Computing MCP Server

A Model Context Protocol (MCP) server that provides access to Sigma Computing's REST API. This server enables programmatic interaction with Sigma Computing workbooks, datasets, users, and more through a standardized interface.

## Features

- **Authentication**: Automatic token management with refresh
- **Workbook Management**: List, create, update, delete, and export workbooks
- **Dataset Operations**: Access and materialize datasets
- **User Management**: Manage organization members and teams
- **Data Export**: Export workbook data in multiple formats (CSV, XLSX, PDF, PNG, JSON)
- **Connection Management**: Access data warehouse connections

## Quick Start

### Prerequisites

- **Required:** Sigma Computing organization with API access and credentials (Client ID and Client Secret)
- **For Docker deployment:** Docker and Docker Compose
- **For Python deployment:** Python 3.11+

### Setup

Choose one of two deployment options:

---

### Option 1: Docker Compose (Recommended)

1. **Prepare environment file:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your credentials
   ```

2. **Configure credentials in `.env` file:**
   ```bash
   SIGMA_CLIENT_ID=your_actual_client_id
   SIGMA_CLIENT_SECRET=your_actual_client_secret
   SIGMA_BASE_URL=https://api.sigmacomputing.com
   ```

3. **Build and run:**
   ```bash
   docker-compose up --build
   ```

---

### Option 2: Direct Python Execution

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export SIGMA_CLIENT_ID="your_client_id"
   export SIGMA_CLIENT_SECRET="your_client_secret"
   export SIGMA_BASE_URL="https://api.sigmacomputing.com"
   ```

3. **Run the server:**
   ```bash
   python sigma_mcp_server.py
   ```

---

## Claude Desktop Configuration

After deploying the server, configure Claude Desktop to use it:

### For Option 1 (Docker Compose)

Add to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "sigma-computing": {
      "command": "docker",
      "args": [
        "compose",
        "-f",
        "/absolute/path/to/mcp-sigma-server/docker-compose.yml",
        "run",
        "--rm",
        "sigma-mcp-server"
      ]
    }
  }
}
```

**Important:** Replace `/absolute/path/to/mcp-sigma-server/` with the actual path to your project directory.

### For Option 2 (Direct Python)

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
        "SIGMA_BASE_URL": "https://api.sigmacomputing.com"
      }
    }
  }
}
```

**Important:** 
- Replace `/absolute/path/to/mcp-sigma-server/` with the actual path to your project directory
- Replace credential placeholders with your actual Sigma Computing credentials

### Verifying the Connection

After updating the config file:

1. **Restart Claude Desktop** completely (quit and reopen)
2. Look for the 🔌 MCP icon in Claude Desktop
3. You should see "sigma-computing" listed as a connected server
4. Test by asking Claude to list your Sigma workbooks

---

## Available Tools

### Workbook Operations
- `sigma_list_workbooks` - List all workbooks with pagination
- `sigma_get_workbook` - Get detailed workbook information
- `sigma_create_workbook` - Create a new workbook
- `sigma_export_workbook` - Export workbook data in various formats
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
- `sigma_list_teams` - List organization teams
- `sigma_list_account_types` - List all account types available in the organization
- `sigma_get_account_type_permissions` - Get all feature permissions for a specific account type

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
```json
{
  "tool": "sigma_export_workbook", 
  "arguments": {
    "workbook_id": "workbook-uuid-here",
    "format": "csv",
    "element_id": "optional-element-uuid",
    "name": "my-export"
  }
}
```

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

### List All Teams
```json
{
  "tool": "sigma_list_teams",
  "arguments": {}
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

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SIGMA_BASE_URL` | Sigma Computing API base URL | `https://api.sigmacomputing.com` |
| `SIGMA_CLIENT_ID` | Your Sigma Computing client ID | Required |
| `SIGMA_CLIENT_SECRET` | Your Sigma Computing client secret | Required |
| `LOG_LEVEL` | Logging level | `INFO` |

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

### Logs

View logs with Docker Compose:
```bash
docker-compose logs -f sigma-mcp-server
```

## Support

For issues related to:
- **MCP Server**: Create an issue in this repository
- **Sigma Computing API**: Check [Sigma Computing documentation](https://docs.sigmacomputing.com)
- **Authentication**: Contact your Sigma Computing administrator

## License

This project is provided as-is for integration with Sigma Computing's API. Please refer to Sigma Computing's terms of service for API usage guidelines.