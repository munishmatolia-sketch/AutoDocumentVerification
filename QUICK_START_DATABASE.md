# Quick Start: Database Integration

**Status**: ✅ OPERATIONAL  
**Date**: January 30, 2026

---

## 🚀 Quick Access

### Web Interface
```
http://localhost:8501
```

### API Documentation
```
http://localhost:8000/docs
```

### Database Access
```bash
docker exec -it autodocumentverification-postgres-1 \
  psql -U postgres -d document_forensics
```

---

## 📝 Quick Test

### 1. Upload Document (Web Interface)
1. Open http://localhost:8501
2. Upload a document
3. Click "Upload & Start Analysis"
4. Watch progress bar update in real-time
5. View results

### 2. Upload Document (API)
```bash
# Upload
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test.txt"

# Start analysis (use UUID from upload response)
curl -X POST http://localhost:8000/api/v1/analysis/start \
  -H "Content-Type: application/json" \
  -d '{"document_id": "YOUR-UUID-HERE"}'

# Check status
curl http://localhost:8000/api/v1/analysis/YOUR-UUID-HERE/status
```

---

## 🔍 Quick Verification

### Check Services
```bash
docker ps
```

### Check Database Tables
```bash
docker exec autodocumentverification-postgres-1 \
  psql -U postgres -d document_forensics -c "\dt"
```

### Check Documents
```bash
docker exec autodocumentverification-postgres-1 \
  psql -U postgres -d document_forensics \
  -c "SELECT id, filename, processing_status FROM documents;"
```

### Check Analysis Progress
```bash
docker exec autodocumentverification-postgres-1 \
  psql -U postgres -d document_forensics \
  -c "SELECT document_id, status, progress_percentage FROM analysis_progress ORDER BY created_at DESC LIMIT 5;"
```

### Check Analysis Results
```bash
docker exec autodocumentverification-postgres-1 \
  psql -U postgres -d document_forensics \
  -c "SELECT document_id, risk_level, confidence_score FROM analysis_results ORDER BY created_at DESC LIMIT 5;"
```

---

## 🔧 Quick Troubleshooting

### Services Not Running
```bash
docker-compose -f docker-compose.simple.yml up -d
```

### Check Logs
```bash
# API logs
docker logs autodocumentverification-api-1 --tail 50

# Web logs
docker logs autodocumentverification-web-1 --tail 50

# Database logs
docker logs autodocumentverification-postgres-1 --tail 50
```

### Restart Services
```bash
docker-compose -f docker-compose.simple.yml restart
```

### Rebuild Containers
```bash
docker-compose -f docker-compose.simple.yml build --no-cache
docker-compose -f docker-compose.simple.yml up -d
```

---

## 📚 Documentation

- **Full Summary**: `FINAL_DATABASE_INTEGRATION_SUMMARY.md`
- **Implementation Guide**: `DATABASE_INTEGRATION_GUIDE.md`
- **Completion Status**: `DATABASE_INTEGRATION_COMPLETE.md`

---

## ✅ What Works

- ✅ Document upload with database storage
- ✅ UUID → file path mapping
- ✅ Real analysis execution
- ✅ Real-time progress tracking
- ✅ Results storage in database
- ✅ Status monitoring from database

---

**Ready to use!** 🎉
