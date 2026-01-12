# Quick Start Guide

## 🚀 Test Your Dual-Transport Sigma MCP Server

### Prerequisites
```bash
cd /Users/dragos/Documents/development/mcp-sigma-server
```

Ensure your `.env` file exists with:
```
SIGMA_CLIENT_ID=your_client_id
SIGMA_CLIENT_SECRET=your_client_secret
SIGMA_BASE_URL=https://aws-api.sigmacomputing.com
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🧪 Quick Tests

### 1️⃣ Test STDIO (works with existing Claude Desktop)
```bash
python sigma_mcp_server.py --transport stdio
```
**Expected**: Server starts and waits for connections  
**To stop**: Press `Ctrl+C`

---

### 2️⃣ Test HTTP (for internal-agents deployment)
```bash
python sigma_mcp_server.py --transport streamable-http --port 8000
```
**Expected**: Server starts on http://0.0.0.0:8000/mcp  
**To test**: In another terminal: `curl http://localhost:8000/mcp`  
**To stop**: Press `Ctrl+C`

---

### 3️⃣ Test Docker
```bash
docker-compose up --build
```
**Expected**: Container builds and starts  
**Access**: http://localhost:8000/mcp  
**View logs**: `docker-compose logs -f`  
**To stop**: `docker-compose down`

---

### 4️⃣ Run All Tests
```bash
./test_transports.sh
```
**Expected**: All tests pass ✅

---

## 🎯 Common Commands

| What | Command |
|------|---------|
| **STDIO mode** | `python sigma_mcp_server.py` |
| **HTTP mode** | `python sigma_mcp_server.py --transport streamable-http` |
| **Custom port** | `python sigma_mcp_server.py --transport streamable-http --port 3000` |
| **Debug mode** | `python sigma_mcp_server.py --log-level DEBUG` |
| **Docker start** | `docker-compose up -d` |
| **Docker logs** | `docker-compose logs -f` |
| **Docker stop** | `docker-compose down` |

---

## ✅ Success Indicators

### STDIO Mode
```
INFO - Starting Sigma Computing MCP Server with stdio transport...
INFO - Sigma API client initialized successfully
INFO - Successfully authenticated with Sigma Computing API
INFO - Server ready, waiting for MCP connections...
```

### HTTP Mode
```
INFO - Starting Sigma Computing MCP Server with streamable-http transport...
INFO - Running with Streamable HTTP transport on 0.0.0.0:8000...
INFO - Successfully authenticated with Sigma Computing API
INFO - Streamable HTTP session manager started!
INFO - Server ready at http://0.0.0.0:8000/mcp
INFO - Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🐛 Troubleshooting

### "Module not found"
```bash
pip install -r requirements.txt
```

### "SIGMA_CLIENT_ID not found"
```bash
# Check .env file exists
cat .env

# Or export manually
export SIGMA_CLIENT_ID="your_id"
export SIGMA_CLIENT_SECRET="your_secret"
```

### "Port already in use"
```bash
# Find what's using port 8000
lsof -i :8000

# Use a different port
python sigma_mcp_server.py --transport streamable-http --port 8001
```

### Docker build fails
```bash
# Clean and rebuild
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up
```

---

## 📚 More Information

- **Full Guide**: See [TRANSPORT_GUIDE.md](./TRANSPORT_GUIDE.md)
- **What Changed**: See [CHANGES_SUMMARY.md](./CHANGES_SUMMARY.md)
- **All Features**: See [README.md](./README.md)

---

## 🎉 Ready for Internal-Agents!

Once tested locally:
1. ✅ Share with Jonathan via #internal-agents Slack
2. ✅ They'll deploy to Kubernetes
3. ✅ Build Slack bot integration
4. ✅ Start querying Sigma from Slack!

---

**Need Help?** Check logs for error messages and refer to TRANSPORT_GUIDE.md

