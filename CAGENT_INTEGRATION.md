# CAgent Integration Guide

This guide explains how to integrate the Sigma MCP Server with Docker's **cagent** framework.

> **Note:** While this guide references Docker's cagent framework, the Sigma MCP Server is a **public, open-source tool** that works with any agent framework supporting MCP (Model Context Protocol) over HTTP/SSE transport.

## Overview

The cagent framework (developed by Docker) expects MCP servers to be deployed as HTTP/SSE services accessible via URL. The Sigma MCP Server supports this transport mode and is ready for integration with cagent-based workflows or other compatible agent systems.

## What is CAgent?

CAgent is Docker's agent framework for building AI-powered workflow automation. It supports:
- MCP (Model Context Protocol) for tool integration
- Multiple agent configurations
- Custom toolsets and scripts
- Memory persistence
- Integration with Slack, web UIs, and other interfaces

**More info:** This integration guide is specific to cagent, but the HTTP/SSE MCP server can be adapted for other agent frameworks.

## Folder Structure Example

If integrating into an agent repository (e.g., for organization-specific agents):

```
your-agents-repo/
├── sigma/
│   ├── agents/
│   │   └── sigma.yaml          # Agent configuration (copy from this repo)
│   ├── Dockerfile              # Copy from mcp-sigma-server repo
│   ├── requirements.txt        # Copy from mcp-sigma-server repo
│   ├── sigma_mcp_server.py     # Copy from mcp-sigma-server repo
│   └── README.md               # Documentation
├── other-agent/
└── ...
```

## Files to Copy

From the `mcp-sigma-server` repository, copy these files to your agent directory:

1. **sigma.yaml** → `your-agents-repo/sigma/agents/sigma.yaml`
2. **Dockerfile** → `your-agents-repo/sigma/Dockerfile`
3. **requirements.txt** → `your-agents-repo/sigma/requirements.txt`
4. **sigma_mcp_server.py** → `your-agents-repo/sigma/sigma_mcp_server.py`

## Configuration Updates Needed

### 1. Environment Variable Configuration

The `sigma.yaml` uses an environment variable for the MCP server URL:

```yaml
- type: mcp
  remote:
    url: ${env.SIGMA_MCP_URL}
    transport_type: streamable
```

You'll need to set `SIGMA_MCP_URL` in your deployment environment (e.g., via Kubernetes ConfigMap, Docker Compose, or shell environment variable).

**Example URL formats:**
- Local testing: `http://localhost:8000/mcp`
- Production deployment: `https://mcp-sigma.your-domain.com/mcp`

**Note:** The URL should point to where your Sigma MCP server is deployed and accessible to your agents.

### 2. Environment Variables

The integration requires configuration for both the MCP server and the agent:

**For the MCP Server (deployed separately):**
- `SIGMA_CLIENT_ID` - Your Sigma Computing API client ID
- `SIGMA_CLIENT_SECRET` - Your Sigma Computing API client secret
- `SIGMA_BASE_URL` - Your Sigma instance API base URL

**For the Agent (in your agent framework):**
- `SIGMA_MCP_URL` - URL of your deployed Sigma MCP server endpoint

### 3. Configuring Your Sigma Instance URL

The `SIGMA_BASE_URL` depends on which cloud provider hosts **your** Sigma Computing organization:

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

**To find your URL:**
1. Log into your Sigma Computing organization
2. Go to **Administration** > **Developer Access**
3. Look for **API base URL** - this is your correct URL

### 4. Kubernetes Secrets (Example)

Create a Kubernetes secret for your Sigma MCP server credentials:

```bash
kubectl create secret generic sigma-credentials \
  --from-literal=client-id='YOUR_SIGMA_CLIENT_ID' \
  --from-literal=client-secret='YOUR_SIGMA_CLIENT_SECRET' \
  --from-literal=base-url='YOUR_SIGMA_API_BASE_URL'
```

**Important:** Replace `YOUR_SIGMA_API_BASE_URL` with your actual Sigma instance URL from the table above.

### 5. Deployment Configuration

The Dockerfile already defaults to HTTP/SSE transport on port 8000. No additional changes needed.

## Testing Locally

### Step 1: Start the MCP Server

Build and run the Sigma MCP server with HTTP/SSE transport:

```bash
# Using Docker
cd path/to/mcp-sigma-server
docker-compose up --build -d

# Or run directly with Python
export SIGMA_CLIENT_ID="your_client_id"
export SIGMA_CLIENT_SECRET="your_client_secret"
export SIGMA_BASE_URL="your_sigma_api_url"
python sigma_mcp_server.py --transport streamable-http --port 8000
```

**Note:** Replace `your_sigma_api_url` with your actual Sigma instance API URL.

### Step 2: Configure and Test the Agent

Set the MCP server URL and run the agent:

```bash
# Set environment variable
export SIGMA_MCP_URL="http://localhost:8000/mcp"

# Run the agent with cagent
cagent run sigma.yaml --yolo

# Or test in your agent framework
```

### Verification

Test the MCP endpoint is accessible:

```bash
curl http://localhost:8000/mcp
```

## Deployment Steps

1. **Add Sigma agent** to your agent repository with the sigma/ folder
2. **Deploy to dev/staging environment** for testing
3. **Test via your agent interface** (Slack bot, web UI, etc.)
4. **Verify functionality** with real workbook/member queries
5. **Deploy to production** once validated

## Running with Auto-Approval

To avoid manual confirmation prompts for tool calls, use the `--yolo` flag:

```bash
cagent run ./agents/sigma.yaml --yolo
```

Or in your Dockerfile:

```dockerfile
ENTRYPOINT ["/cagent", "run", "./agents/sigma.yaml", "--yolo"]
```

## Authentication Flow

The MCP server authenticates to Sigma API using:
- Client ID and Client Secret from Kubernetes secrets
- Automatic token refresh (tokens expire after 1 hour)
- No additional authentication needed at MCP server level (VPN-protected)

## Health Checks

The HTTP server provides health check support:
- Endpoint: `http://localhost:8000/mcp`
- Kubernetes liveness/readiness probes can use this endpoint

## Support

- **MCP Server Issues**: [github.com/dgdocker/sigma-mcp-server](https://github.com/dgdocker/sigma-mcp-server)
- **Sigma API Documentation**: [help.sigmacomputing.com/reference](https://help.sigmacomputing.com/reference/get-started-sigma-api)
- **CAgent Framework**: Check your organization's agent framework documentation

## Additional Resources

- **Sigma API Credentials**: Create in your Sigma org at **Administration** > **Developer Access**
- **API Base URL**: Find in your Sigma org at **Administration** > **Developer Access**
- **MCP Protocol**: [Model Context Protocol documentation](https://modelcontextprotocol.io/)

