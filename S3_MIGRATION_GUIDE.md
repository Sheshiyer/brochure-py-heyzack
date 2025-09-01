# S3 Migration Guide

This guide walks you through migrating Google Drive images to AWS S3 and updating all data sources with the new S3 URLs.

## Prerequisites

### 1. AWS Account Setup

1. **Create AWS Account**: If you don't have one, sign up at [aws.amazon.com](https://aws.amazon.com)

2. **Create IAM User** (Recommended for security):
   - Go to AWS Console → IAM → Users → Create User
   - User name: `smart-home-s3-migration`
   - Attach policies:
     - `AmazonS3FullAccess` (for bucket operations)
     - Or create custom policy with minimal permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutBucketPolicy"
            ],
            "Resource": [
                "arn:aws:s3:::smart-home-product-images",
                "arn:aws:s3:::smart-home-product-images/*"
            ]
        }
    ]
}
```

3. **Get Access Keys**:
   - Go to IAM → Users → [your-user] → Security credentials
   - Create access key → Command Line Interface (CLI)
   - **Save the Access Key ID and Secret Access Key securely**

### 2. Install Dependencies

```bash
# Install required Python packages
pip install boto3 requests

# Or if using requirements.txt
pip install -r requirements.txt
```

## Migration Process

### Step 1: Configure AWS Credentials

**Option A: Environment Variables (Recommended)**
```bash
export AWS_ACCESS_KEY_ID="your_access_key_here"
export AWS_SECRET_ACCESS_KEY="your_secret_key_here"
export AWS_DEFAULT_REGION="us-east-1"  # or your preferred region
```

**Option B: AWS CLI Configuration**
```bash
# Install AWS CLI first
pip install awscli

# Configure credentials
aws configure
# Enter your Access Key ID, Secret Access Key, and region
```

**Option C: Credentials File**
Create `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = your_access_key_here
aws_secret_access_key = your_secret_key_here
```

And `~/.aws/config`:
```ini
[default]
region = us-east-1
```

### Step 2: Verify Migration Plan

Before starting migration, review the plan:

```bash
# Check the migration plan
cat reports/s3_migration_plan.json

# Verify backup is complete
cat reports/validation_backup_report_*.json
```

### Step 3: Execute S3 Migration

```bash
# Run the S3 migration script
python3 scripts/s3_migration_executor.py
```

**What this script does:**
1. ✅ Validates AWS credentials
2. ✅ Creates S3 bucket `smart-home-product-images`
3. ✅ Sets public read policy for images
4. ✅ Downloads images from Google Drive
5. ✅ Uploads images to S3 with proper content types
6. ✅ Generates migration results report

**Expected Output:**
```
=== S3 Migration Executor ===
=== AWS S3 Setup ===
✅ AWS S3 client initialized successfully (Region: us-east-1)
✅ S3 bucket 'smart-home-product-images' created successfully
✅ Public read access configured for images
✅ Loaded migration plan: 46 images to migrate

=== Migrating 46 Images ===
[1/46] Processing: https://drive.google.com/file/d/...
  📥 Downloading...
  📤 Uploading to S3...
  ✅ Migrated successfully
...

=== Migration Summary ===
✅ Successfully migrated: 46 images
❌ Failed migrations: 0 images
📊 Results saved: reports/s3_migration_results_20250827_173045.json
🎉 Migration completed! S3 bucket: smart-home-product-images
```

### Step 4: Update Data Sources

After successful migration, update all data files:

```bash
# Update JSON and CSV files with S3 URLs
python3 scripts/update_data_sources.py
```

**What this script does:**
1. ✅ Loads migration results
2. ✅ Creates backups of all data files
3. ✅ Updates `products.json` with S3 URLs
4. ✅ Updates `products_hierarchical_enhanced.json` with S3 URLs
5. ✅ Updates CSV file with S3 URLs
6. ✅ Creates rollback script

**Expected Output:**
```
=== Data Source S3 URL Updater ===
✅ Loaded migration results: s3_migration_results_20250827_173045.json
   Successful migrations: 46
   Failed migrations: 0

=== Updating Data Sources with S3 URLs ===
📋 Found 46 URL mappings to apply

📝 Updating: products.json
    Updated drive_link: https://drive.google.com/file/d/... -> S3
  ✅ Updated products.json: 46 URLs

📝 Updating: products_hierarchical_enhanced.json
    Updated drive_link: https://drive.google.com/file/d/... -> S3
  ✅ Updated products_hierarchical_enhanced.json: 46 URLs

📝 Updating: SMART HOME FOLLOWING PROJECT - All Products.csv
    Updated CSV row: https://drive.google.com/file/d/... -> S3
  ✅ Updated SMART HOME FOLLOWING PROJECT - All Products.csv: 46 URLs

=== Update Summary ===
📊 Total URL mappings: 46
✅ Total updates made: 138
📁 Files updated: 3
🎉 Data sources successfully updated with S3 URLs!
```

## Verification

### 1. Test S3 URLs

```bash
# Test a few S3 URLs
curl -I "https://smart-home-product-images.s3.amazonaws.com/smart-home/tuya/IPB215.jpg"
# Should return HTTP 200 OK
```

### 2. Verify Data Updates

```bash
# Check that Drive links are replaced
grep -c "s3.amazonaws.com" data/products.json
grep -c "drive.google.com" data/products.json  # Should be 0
```

### 3. Test Application

Run your application and verify that images load correctly from S3.

## Rollback (If Needed)

If something goes wrong, you can rollback:

```bash
# Run the generated rollback script
./backups/pre_s3_update_*/rollback_s3_updates.sh

# Or manually restore from backup
cp backups/pre_s3_update_*/products.json data/
cp backups/pre_s3_update_*/products_hierarchical_enhanced.json data/
cp "backups/pre_s3_update_*/SMART HOME FOLLOWING PROJECT - All Products.csv" data/
```

## Cost Estimation

**S3 Storage Costs** (us-east-1):
- 46 images × ~1.5MB average = ~69MB total
- Standard storage: $0.023/GB/month
- Monthly cost: ~$0.002 (less than 1 cent)

**S3 Request Costs**:
- PUT requests: 46 × $0.0005/1000 = ~$0.00002
- GET requests: Depends on usage

**Data Transfer**:
- First 1GB/month free
- Your images (~69MB) are well within free tier

**Total estimated monthly cost: < $0.01**

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   ```
   ❌ AWS credentials not found in environment variables
   ```
   **Solution**: Set environment variables or run `aws configure`

2. **Bucket Already Exists (Different Region)**
   ```
   ❌ Failed to create S3 bucket: BucketAlreadyExists
   ```
   **Solution**: Choose a different bucket name in the script

3. **Permission Denied**
   ```
   ❌ Failed to create S3 bucket: AccessDenied
   ```
   **Solution**: Check IAM permissions for your user

4. **Google Drive Download Failed**
   ```
   ❌ Download failed: 403 Forbidden
   ```
   **Solution**: Some Drive links may have changed permissions. Check the error details.

5. **Network Timeout**
   ```
   ❌ Download failed: Read timeout
   ```
   **Solution**: The script will retry. Large images may take longer.

### Debug Mode

For detailed debugging, modify the scripts to add more logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Notes

1. **Never commit AWS credentials** to version control
2. **Use IAM users** instead of root account
3. **Limit permissions** to only what's needed
4. **Rotate access keys** regularly
5. **Monitor S3 usage** in AWS Console

## Next Steps

After successful migration:

1. ✅ Update Google Sheets with S3 URLs (if needed)
2. ✅ Test application thoroughly
3. ✅ Monitor S3 costs and usage
4. ✅ Set up CloudFront CDN for better performance (optional)
5. ✅ Configure S3 lifecycle policies for cost optimization (optional)

## Support

If you encounter issues:

1. Check the generated reports in `reports/` directory
2. Review backup files in `backups/` directory
3. Check AWS CloudTrail for API call logs
4. Verify IAM permissions in AWS Console

---

**Migration Status**: Ready to execute
**Estimated Time**: 5-10 minutes for 46 images
**Risk Level**: Low (full backups created)