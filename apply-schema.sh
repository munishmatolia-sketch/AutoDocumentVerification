#!/bin/bash
# Script to apply database schema to existing PostgreSQL container

echo "Applying database schema to PostgreSQL container..."
echo ""

# Copy init-db.sql to container
echo "1. Copying init-db.sql to container..."
docker cp init-db.sql autodocumentverification-postgres-1:/tmp/init-db.sql

# Execute the SQL script
echo "2. Executing SQL script..."
docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -f /tmp/init-db.sql

echo ""
echo "✅ Database schema applied successfully!"
echo ""
echo "To verify, run:"
echo "  docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -c '\\dt'"
