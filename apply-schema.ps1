# PowerShell script to apply database schema to existing PostgreSQL container

Write-Host "Applying database schema to PostgreSQL container..." -ForegroundColor Cyan
Write-Host ""

# Copy init-db.sql to container
Write-Host "1. Copying init-db.sql to container..." -ForegroundColor Yellow
docker cp init-db.sql autodocumentverification-postgres-1:/tmp/init-db.sql

# Execute the SQL script
Write-Host "2. Executing SQL script..." -ForegroundColor Yellow
docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -f /tmp/init-db.sql

Write-Host ""
Write-Host "✅ Database schema applied successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To verify, run:" -ForegroundColor Cyan
Write-Host "  docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -c '\dt'" -ForegroundColor White
