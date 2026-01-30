# Upload Error Fix - v0.2.0

## Issue
When trying to upload a document through the web interface, users received the error:
```
Upload failed: Upload error: HTTPConnectionPool(host='localhost', port=8000): 
Max retries exceeded with url: /api/v1/documents/upload 
(Caused by NewConnectionError("HTTPConnection(host='localhost', port=8000): 
Failed to establish a new connection: [Errno 111] Connection refused"))
```

## Root Cause
The web container was trying to connect to `localhost:8000`, but in Docker:
- `localhost` inside a container refers to the container itself, not the host machine
- The API service is running in a separate container named `api`
- Containers need to communicate using Docker network names

## Solution
Added the `api_base_url` configuration setting and ensured it uses the correct Docker service name.

### Changes Made

#### 1. Added `api_base_url` to Settings (`src/document_forensics/core/config.py`)
```python
# API settings
api_base_url: str = "http://localhost:8000/api/v1"  # Default for local development
api_rate_limit: str = "100/minute"
cors_origins: str = "http://localhost:3000,http://localhost:8501"
allowed_origins: str = "http://localhost:3000,http://localhost:8501"
```

#### 2. Updated Docker Compose Environment Variable (`docker-compose.simple.yml`)
**Before:**
```yaml
environment:
  - API_BASE_URL=http://api:8000
  - PYTHONPATH=/app/src
```

**After:**
```yaml
environment:
  - API_BASE_URL=http://api:8000/api/v1
  - PYTHONPATH=/app/src
```

### How It Works

1. **In Docker**: The web container reads `API_BASE_URL` from environment variables
   - Value: `http://api:8000/api/v1`
   - `api` is the Docker service name that resolves to the API container's IP

2. **Local Development**: Without Docker, it defaults to `http://localhost:8000/api/v1`
   - This allows developers to run the web interface locally

3. **Streamlit App**: Reads the setting via `settings.api_base_url`
   ```python
   self.api_base_url = getattr(settings, 'api_base_url', 'http://localhost:8000/api/v1')
   ```

## Verification Steps

### 1. Check Environment Variable
```bash
docker exec autodocumentverification-web-1 env | grep API_BASE_URL
```
Output: `API_BASE_URL=http://api:8000/api/v1`

### 2. Test Container Connectivity
```bash
docker exec autodocumentverification-web-1 curl -s http://api:8000/docs
```
Should return the API documentation HTML.

### 3. Test Upload Through Web Interface
1. Open http://localhost:8501
2. Upload a document
3. Should succeed without connection errors

## Docker Networking Explained

In Docker Compose:
- Each service gets a hostname matching its service name
- Services can communicate using these hostnames
- The `api` service is accessible at `http://api:8000` from other containers
- From the host machine, it's accessible at `http://localhost:8000`

```
┌─────────────────────────────────────────┐
│         Docker Network                  │
│                                         │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ web:8501     │───▶│ api:8000     │  │
│  │ (Streamlit)  │    │ (FastAPI)    │  │
│  └──────────────┘    └──────────────┘  │
│         │                    │          │
└─────────┼────────────────────┼──────────┘
          │                    │
          ▼                    ▼
    localhost:8501      localhost:8000
    (from host)         (from host)
```

## Current Status

✅ **All services configured correctly**
- Web container uses `http://api:8000/api/v1` to reach API
- API container is accessible from web container
- Upload functionality should now work

## Testing the Fix

### Upload a Test Document
1. Open http://localhost:8501
2. Click "Upload Document"
3. Select a file (PDF, Word, Excel, Text, or Image)
4. Click "Upload"
5. Should see success message and document ID

### Check API Directly
```bash
# From host machine
curl http://localhost:8000/docs
```

### Check from Web Container
```bash
# From inside web container
docker exec autodocumentverification-web-1 curl http://api:8000/docs
```

## Additional Notes

### Environment Variable Priority
Pydantic Settings reads environment variables in this order:
1. Environment variables (highest priority)
2. `.env` file
3. Default values in code (lowest priority)

### For Production
In production, set `API_BASE_URL` to your actual API endpoint:
```yaml
environment:
  - API_BASE_URL=https://api.yourdomain.com/api/v1
```

---

**Fix Applied**: January 30, 2026
**Status**: ✅ Resolved
**Ready for Testing**: Yes
