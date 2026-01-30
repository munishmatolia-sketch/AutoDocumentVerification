# Quick Test Guide - Document Forensics v0.2.0

## ✅ System is Ready!

All services are running and the authentication issue has been fixed. You can now upload documents without logging in.

---

## Test the Upload Functionality

### Step 1: Open the Web Interface
Open your browser and navigate to:
```
http://localhost:8501
```

### Step 2: Upload a Document (No Login Required!)
1. You'll see the Document Forensics interface
2. **Skip the login** - authentication is now optional
3. Look for the "Upload Document" section
4. Click "Browse files" or drag & drop a file
5. Supported formats:
   - PDF (.pdf)
   - Word (.docx, .doc)
   - Excel (.xlsx, .xls)
   - Text (.txt)
   - Images (.jpg, .png, .bmp, .tiff)

### Step 3: Start Analysis
1. After selecting a file, add optional details:
   - Description (optional)
   - Tags (optional, comma-separated)
   - Priority (1-10, default is 5)
2. Click "Upload & Start Analysis"
3. **Expected Result**: 
   - ✅ Upload succeeds
   - ✅ Document ID displayed
   - ✅ Analysis starts automatically
   - ✅ No authentication errors!

### Step 4: View Results
1. Wait for analysis to complete
2. View forgery detection results
3. Check confidence scores
4. Review detected indicators
5. Download detailed report

---

## What Changed?

### Before (Broken)
```
❌ Upload failed: {"detail":"Could not validate credentials"}
```

### After (Fixed)
```
✅ Upload successful!
✅ Document ID: 12345
✅ Analysis started
```

### Technical Changes
- Upload endpoint now accepts anonymous users
- Analysis endpoint now accepts anonymous users
- User tracking: authenticated users tracked by username, others as "anonymous"
- API container restarted with the fix

---

## Alternative: Test with Authentication (Optional)

If you want to track uploads by username:

### Test Accounts
| Username | Password | Permissions |
|----------|----------|-------------|
| admin    | secret   | Full access |
| analyst  | secret   | Read + Write |
| viewer   | secret   | Read only |

### Steps
1. Open http://localhost:8501
2. Enter username and password
3. Click "Login"
4. Upload documents (tracked with your username)

---

## API Testing (For Developers)

### Test Upload via API
```bash
# Create a test file
echo "This is a test document for forgery detection." > test.txt

# Upload without authentication
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test.txt" \
  -F "description=Test upload" \
  -F "priority=5"

# Expected response:
# {
#   "success": true,
#   "document_id": "...",
#   "document": {...}
# }
```

### Test Analysis via API
```bash
# Start analysis (replace DOCUMENT_ID with actual ID)
curl -X POST http://localhost:8000/api/v1/analysis/start \
  -H "Content-Type: application/json" \
  -d '{"document_id": "1"}'

# Expected response:
# {
#   "status": "success",
#   "message": "Analysis started successfully",
#   "document_id": 1
# }
```

### View API Documentation
Open in browser:
```
http://localhost:8000/docs
```

---

## Troubleshooting

### If Upload Still Fails

1. **Check API logs**:
   ```powershell
   docker logs autodocumentverification-api-1 --tail 50
   ```

2. **Check web logs**:
   ```powershell
   docker logs autodocumentverification-web-1 --tail 50
   ```

3. **Verify containers are running**:
   ```powershell
   docker-compose -f docker-compose.simple.yml ps
   ```

4. **Restart all services**:
   ```powershell
   docker-compose -f docker-compose.simple.yml restart
   ```

### If Web Interface Won't Load

1. **Check if port 8501 is available**:
   ```powershell
   netstat -ano | findstr :8501
   ```

2. **Restart web container**:
   ```powershell
   docker-compose -f docker-compose.simple.yml restart web
   ```

3. **Check web container logs**:
   ```powershell
   docker logs autodocumentverification-web-1
   ```

---

## Expected Behavior

### Successful Upload Flow
```
1. User opens http://localhost:8501
2. User selects a file
3. User clicks "Upload & Start Analysis"
4. System uploads file (no authentication required)
5. System generates document ID
6. System starts forgery detection analysis
7. System displays results with confidence scores
8. User can download detailed report
```

### What You Should See
- ✅ Upload progress indicator
- ✅ Document ID displayed
- ✅ Analysis status updates
- ✅ Forgery detection results
- ✅ Confidence scores (0.0 - 1.0)
- ✅ Risk level (LOW, MEDIUM, HIGH, CRITICAL)
- ✅ Detailed indicators with evidence
- ✅ Download report button

---

## Sample Test Documents

Create these test files to verify different document types:

### 1. Text File
```bash
echo "This is a test document for forgery detection." > test.txt
```

### 2. Simple PDF (if you have a PDF)
Use any existing PDF file from your system.

### 3. Word Document (if you have Word)
Create a simple .docx file with some text.

### 4. Image (if you have an image)
Use any .jpg or .png file from your system.

---

## Success Indicators

You'll know it's working when:
- ✅ No "Could not validate credentials" error
- ✅ Upload completes successfully
- ✅ Document ID is displayed
- ✅ Analysis starts automatically
- ✅ Results are shown with confidence scores
- ✅ You can download the report

---

## Next Steps After Testing

Once upload works:
1. Test different document types (PDF, Word, Excel, Text, Images)
2. Try the forgery detection features
3. Generate and review reports
4. Test batch processing (multiple documents)
5. Explore the API documentation
6. Provide feedback on results

---

## Support

If you encounter any issues:
1. Check the logs (commands above)
2. Verify all containers are running
3. Ensure ports 8501 and 8000 are not blocked
4. Try restarting the services
5. Check the documentation files:
   - `DEPLOYMENT_COMPLETE_v0.2.0.md`
   - `AUTHENTICATION_FIX.md`
   - `FINAL_DEPLOYMENT_VERIFICATION.md`

---

**System Status**: ✅ Ready for Testing  
**Web Interface**: http://localhost:8501  
**API Documentation**: http://localhost:8000/docs  
**Authentication**: Optional (no login required for demo)

**Go ahead and test the upload functionality!** 🚀
