# Docker MCP Registry Submission Guide

## ✅ Preparation Complete!

Your repository is now ready for Docker MCP Registry submission.

### Files Created
- ✅ `server.yaml` - Registry configuration with secrets and environment variables
- ✅ `tools.json` - All 20 MCP tools documented
- ✅ `Dockerfile` - Container configuration (already existed)
- ✅ `README.md` - Comprehensive documentation (already existed)

### Git Status
- ✅ 3 commits ready to push
- ✅ Latest commit: `9635a1a` (Docker MCP Registry submission files)

---

## 🚀 Step 1: Push to GitHub

First, push all commits to your GitHub repository:

```bash
cd /Users/dragos/Documents/development/mcp-sigma-server
git push -u origin master
```

**Important:** Wait for this to complete successfully before proceeding to Step 2.

---

## 📝 Step 2: Fork Docker MCP Registry

1. Go to: https://github.com/docker/mcp-registry
2. Click the **Fork** button in the top-right corner
3. Fork to your personal GitHub account (`dgdocker`)
4. Clone your fork locally:

```bash
cd ~/Documents/development
git clone https://github.com/dgdocker/mcp-registry.git
cd mcp-registry
```

---

## 📦 Step 3: Add Your Server to the Registry

### Option A: Using the Wizard (Recommended)

```bash
cd mcp-registry
task wizard
```

When prompted:
- **GitHub URL:** `https://github.com/dgdocker/sigma-mcp-server`
- **Category:** `data-analytics`
- **Environment Variables:** 
  - `SIGMA_CLIENT_ID` (secret)
  - `SIGMA_CLIENT_SECRET` (secret)
  - `SIGMA_BASE_URL` (env var)

The wizard will:
- Detect your Dockerfile
- Find your `tools.json` 
- Create the proper directory structure under `servers/sigma-computing/`

### Option B: Manual Copy (If wizard fails)

```bash
cd mcp-registry
mkdir -p servers/sigma-computing
cp /Users/dragos/Documents/development/mcp-sigma-server/server.yaml servers/sigma-computing/
cp /Users/dragos/Documents/development/mcp-sigma-server/tools.json servers/sigma-computing/
```

---

## 🧪 Step 4: Test Locally (Optional but Recommended)

Test your server configuration before submitting:

```bash
cd mcp-registry

# Build the catalog (skips tool listing since we have tools.json)
task catalog -- sigma-computing

# Import to Docker Desktop
docker mcp catalog import $PWD/catalogs/sigma-computing/catalog.yaml

# Test in Docker Desktop's MCP Toolkit UI
# Configure your Sigma credentials and enable the server

# When done testing, reset
docker mcp catalog reset
```

---

## 🎯 Step 5: Submit Pull Request

### Commit Your Changes

```bash
cd mcp-registry
git add servers/sigma-computing/
git commit -m "Add Sigma Computing MCP Server

- Support for Sigma Computing REST API
- 20 tools for workbook, dataset, and user management
- Workbook operations: list, create, export, pages, elements
- Dataset operations: list, get, materialize
- User management: members, teams, account types
- Element analysis: SQL queries, lineage, columns
"

git push origin master
```

### Create the Pull Request

1. Go to your fork: https://github.com/dgdocker/mcp-registry
2. Click **"Compare & pull request"** button
3. Set the PR title:
   ```
   Add Sigma Computing MCP Server
   ```

4. In the PR description, include:
   ```markdown
   ## Server Overview
   
   MCP server providing access to Sigma Computing's REST API for business intelligence and data analytics.
   
   ## Features
   - 20 MCP tools covering workbooks, datasets, and user management
   - Support for all major Sigma API endpoints
   - Secure credential management via Docker secrets
   - Multi-cloud support (AWS, Azure, GCP)
   
   ## Testing
   - ✅ Dockerfile validated
   - ✅ tools.json provided (server requires credentials before running)
   - ✅ Tested locally with Docker Desktop MCP Toolkit
   
   ## Documentation
   - Repository: https://github.com/dgdocker/sigma-mcp-server
   - Official Sigma API: https://help.sigmacomputing.com/reference/get-started-sigma-api
   
   ## Configuration Required
   - Sigma Computing organization with API access
   - Client ID and Client Secret from Sigma Computing Developer Access
   - Correct API base URL for your cloud provider
   ```

5. Click **"Create pull request"**

---

## 🔐 Step 6: Submit Test Credentials

The Docker team needs to test your server. Submit credentials using their form:

**Form URL:** https://forms.gle/6Lw3nsvu2d6nFg8e6

**What to provide:**
- Your PR number (from Step 5)
- Test Sigma Computing credentials:
  - Client ID
  - Client Secret
  - Base URL (your cloud's API endpoint)

**Important:** Use test/sandbox credentials if possible, not production credentials.

---

## ⏱️ Step 7: Wait for Review

- The Docker team will review your PR
- They may request changes or ask questions
- CI checks will run automatically
- Address any feedback promptly

**Timeline:** Typically 2-7 days for review

---

## 🎉 Step 8: After Approval

Once your PR is merged:

1. **Wait 24 hours** for processing
2. Your server will appear in:
   - Docker Desktop's MCP Toolkit
   - Docker Hub at `mcp/sigma-computing`
   - MCP Registry catalog

3. Docker will build and host your image with:
   - Cryptographic signatures
   - Provenance tracking
   - SBOMs (Software Bill of Materials)
   - Automatic security updates

---

## 📋 Pre-Submission Checklist

Before submitting your PR, verify:

- [ ] All code pushed to GitHub successfully
- [ ] `server.yaml` has correct GitHub URL and commit hash
- [ ] `tools.json` contains all 20 tools
- [ ] Dockerfile builds successfully
- [ ] README.md is comprehensive
- [ ] License allows public consumption (MIT/Apache recommended)
- [ ] `.env` file is gitignored (no secrets in repo)
- [ ] Test credentials ready for Docker team
- [ ] PR description is clear and complete

---

## 🆘 Troubleshooting

### If CI fails with "Cannot list tools"
- ✅ Already handled! Your `tools.json` prevents this issue
- The registry won't try to run your server without credentials

### If build fails
- Check Dockerfile syntax
- Ensure all dependencies in requirements.txt
- Verify Python version compatibility (3.11+)

### If the PR is delayed
- Be patient, reviews can take a few days
- Respond promptly to any feedback
- Check CI logs for specific issues

---

## 📞 Support

- **Registry Issues:** Create issue at https://github.com/docker/mcp-registry/issues
- **Server Issues:** Create issue at https://github.com/dgdocker/sigma-mcp-server/issues
- **Sigma API Help:** https://help.sigmacomputing.com/

---

## 🎊 Success!

Once merged, users worldwide can install your Sigma Computing MCP Server with:

```bash
docker mcp server enable sigma-computing
```

Your contribution helps the MCP ecosystem grow! 🚀

