"""
Check failed records from upload job
"""

from app.models.mongo_models import FailedRecordModel
from mongoengine import connect
from app.config import MONGO_URI, MONGO_DB_NAME

# Connect to MongoDB
connect(db=MONGO_DB_NAME, host=MONGO_URI, alias='default', uuidRepresentation='standard')

# Get job ID from command line or use the one from logs
import sys
job_id = sys.argv[1] if len(sys.argv) > 1 else "c4354095-a53d-4292-b73a-f85b3ae5e668"

print(f"Checking failed records for job: {job_id}\n")
print("=" * 80)

failed_records = FailedRecordModel.objects(upload_job_id=job_id)

if not failed_records:
    print("✅ No failed records found!")
else:
    print(f"Found {len(failed_records)} failed records:\n")
    
    for idx, record in enumerate(failed_records, 1):
        print(f"\n{idx}. Failed Record")
        print(f"   Entity: {record.entity_name}")
        print(f"   Row: {record.row_number}")
        print(f"   Error Type: {record.error_type}")
        print(f"   Error Message: {record.error_message}")
        print(f"   Data: {record.original_data}")
        print("-" * 80)

print("\n" + "=" * 80)
print("Done!")
