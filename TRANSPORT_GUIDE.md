# Sigma MCP Server - Transport Guide

This guide explains how to use the Sigma MCP Server with different transport protocols.

## Overview

The Sigma MCP Server supports two transport protocols:

1. **STDIO** - Standard Input/Output (for Claude Desktop and local development)
2. **Streamable HTTP** - HTTP with Server-Sent Events (for deployment and internal-agents)

## Quick Start

### STDIO Transport (Default)

For local testing with Claude Desktop:

```bash
python sigma_mcp_server.py --transport stdio
```

### Streamable HTTP Transport

For deployment or testing with HTTP clients:

```bash
python sigma_mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8000
```

## Detailed Usage

### Command-Line Options

```
python sigma_mcp_server.py [OPTIONS]

Options:
  --transport [stdio|streamable-http]  Transport protocol to use (default: stdio)
  --host TEXT                          Host to bind to (HTTP only, default: 0.0.0.0)
  --port INTEGER                       Port to listen on (HTTP only, default: 8000)
  --log-level TEXT                     Logging level (default: INFO)
  --help                               Show this message and exit
```

## Configuration

### Environment Variables

Both transports require the same environment variables:

```bash
export SIGMA_BASE_URL="https://aws-api.sigmacomputing.com"
export SIGMA_CLIENT_ID="your_client_id_here"
export SIGMA_CLIENT_SECRET="your_client_secret_here"
```

Or create a `.env` file:

```env
SIGMA_BASE_URL=https://aws-api.sigmacomputing.com
SIGMA_CLIENT_ID=your_client_id_here
SIGMA_CLIENT_SECRET=your_client_secret_here
```

## Deployment Options

### Option 1: Docker (Recommended for Deployment)

The Docker container uses Streamable HTTP by default:

```bash
# Build
docker build -t sigma-mcp-server .

# Run
docker run -d \
  -p 8000:8000 \
  -e SIGMA_CLIENT_ID="your_id" \
  -e SIGMA_CLIENT_SECRET="your_secret" \
  sigma-mcp-server
```

### Option 2: Docker Compose

```bash
# Update .env with your credentials
cp .env.example .env
nano .env

# Start the server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down
```

The server will be available at `http://localhost:8000/mcp`

### Option 3: Claude Desktop (STDIO)

Update your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sigma-computing": {
      "command": "python",
      "args": [
        "/absolute/path/to/mcp-sigma-server/sigma_mcp_server.py",
        "--transport",
        "stdio"
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

### Option 4: Internal-Agents (cagent)

For integration with internal-agents framework:

1. Deploy the MCP server with streamable-http transport
2. Configure your agent YAML:

```yaml
toolsets:
  - type: mcp
    remote:
      url: https://mcp-sigma.your-domain.com/mcp
      transport_type: streamable
```

## Testing

### Test Both Transports

Run the included test script:

```bash
./test_transports.sh
```

### Manual Testing

#### Test STDIO

```bash
# Start the server
python sigma_mcp_server.py --transport stdio

# The server will wait for JSON-RPC messages on stdin
```

#### Test HTTP

```bash
# Start the server
python sigma_mcp_server.py --transport streamable-http --port 8000

# In another terminal, test the endpoint
curl http://localhost:8000/mcp

# You should see a response or connection being established
```

## Troubleshooting

### STDIO Mode

**Issue**: Server starts but Claude Desktop doesn't connect

**Solution**: 
- Ensure the absolute path in Claude config is correct
- Check environment variables are set
- Restart Claude Desktop completely
- Check Claude Desktop logs

### HTTP Mode

**Issue**: Connection refused

**Solution**:
- Verify the server is running: `ps aux | grep sigma_mcp_server`
- Check the port is not in use: `lsof -i :8000`
- Ensure firewall allows the port
- Check logs for authentication errors

**Issue**: 403 Forbidden or authentication errors

**Solution**:
- Verify SIGMA_CLIENT_ID and SIGMA_CLIENT_SECRET are correct
- Check the Sigma API token is valid and not expired
- Ensure your Sigma account has API access enabled

### Docker

**Issue**: Container exits immediately

**Solution**:
```bash
# Check logs
docker logs sigma-mcp-server

# Common issues:
# - Missing environment variables
# - Invalid credentials
# - Port already in use
```

**Issue**: Health check failing

**Solution**:
```bash
# Check health manually
docker exec sigma-mcp-server curl http://localhost:8000/mcp

# If curl is not installed in container, check with docker logs
docker logs sigma-mcp-server
```

## Architecture Notes

### STDIO Transport
- Uses standard input/output streams
- Single client connection
- No network exposure
- Perfect for desktop integration

### Streamable HTTP Transport
- HTTP + Server-Sent Events (SSE)
- Multiple concurrent clients
- Network-accessible
- Stateless (no EventStore by default)
- CORS enabled for development

## Security Considerations

### STDIO
- ✅ No network exposure
- ✅ Credentials in environment only
- ✅ Single local user access

### HTTP
- ⚠️ Network accessible
- ✅ Behind VPN recommended
- ✅ No authentication at MCP level (VPN provides security)
- ⚠️ CORS set to allow all origins (adjust for production)

## Performance

- **STDIO**: Lowest latency, single connection
- **HTTP**: Slightly higher latency, supports multiple clients
- Both support the same Sigma API operations
- Token caching (55min) reduces auth overhead

## Next Steps

1. ✅ Test STDIO locally with Claude Desktop
2. ✅ Test HTTP locally with Docker
3. ✅ Deploy to Kubernetes/internal-agents
4. ✅ Integrate with Slack bot
5. ✅ Add monitoring and logging

## Support

For issues or questions:
- Check logs: `docker-compose logs -f` or check stderr output
- Review Sigma API documentation
- Verify credentials and network connectivity

