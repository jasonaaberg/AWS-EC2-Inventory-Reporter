# EC2 Inventory Script

This script collects EC2 instance information from multiple AWS accounts and exports it to both a CSV file and Google Sheets.

## Prerequisites

- Python 3.x
- AWS IAM credentials with appropriate permissions
- Google Cloud Service Account with Google Sheets API access

## Installation

1. Install required Python packages:
```bash
pip3 install --break-system-packages boto3 google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Quick Start

1. Clone the repository and navigate to the directory
2. Run the installation script:
```bash
./install.sh
```

3. **Copy and rename the example configuration files:**
```bash
cp aws_accounts.json.example aws_accounts.json
cp gcp-service-account.json.example gcp-service-account.json
```

4. Edit the configuration files with your actual credentials (see Configuration section below)
5. Run the script:
```bash
python3 ec2_inventory.py
```

**Important:** The `.example` files are templates included in the repository. You must rename them and add your actual credentials before the script will work.

## Configuration

### 1. AWS Account Setup

#### Create AWS IAM User and Access Keys

For each AWS account you want to monitor:

1. Log into the AWS Console
2. Go to **IAM** > **Users** > **Add users**
3. Create a user (e.g., `ec2-inventory-reader`)
4. Select **Programmatic access**
5. Attach the following policies:
   - `AmazonEC2ReadOnlyAccess` (for EC2 instance information)
   - `AmazonSSMReadOnlyAccess` (for OS version details)
   - `IAMReadOnlyAccess` (for account alias)
6. Complete the user creation and **save the Access Key ID and Secret Access Key**

#### Configure aws_accounts.json

1. If you haven't already, copy the example configuration file:
```bash
cp aws_accounts.json.example aws_accounts.json
```

2. Edit `aws_accounts.json` and replace the example values with your actual AWS credentials:
```json
{
  "accounts": [
    {
      "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "region": "us-east-1"
    },
    {
      "aws_access_key_id": "AKIAI44QH8DHBEXAMPLE",
      "aws_secret_access_key": "je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY",
      "region": "us-east-1"
    },
    {
      "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE3",
      "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY3",
      "region": "us-west-2"
    }
  ]
}
```

**Important:** Keep `aws_accounts.json` secure and never commit it to version control!

#### Adding More AWS Accounts

To add additional AWS accounts later, simply add another object to the `accounts` array in `aws_accounts.json`:

```json
{
  "accounts": [
    ... existing accounts ...,
    {
      "aws_access_key_id": "NEW_ACCESS_KEY_ID",
      "aws_secret_access_key": "NEW_SECRET_ACCESS_KEY",
      "region": "eu-west-1"
    }
  ]
}
```

### 2. Google Cloud Service Account Setup

#### Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one

#### Enable Required APIs

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for and enable:
   - **Google Sheets API**
   - **Google Drive API**

#### Create Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Enter a name (e.g., `ec2-inventory-uploader`)
4. Click **Create and Continue**
5. Skip the optional steps and click **Done**

#### Generate Service Account Key

1. Click on the newly created service account
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON** format
5. Click **Create** - this downloads the JSON key file
6. **Replace** the `gcp-service-account.json` file with the downloaded key:
```bash
# If you haven't copied the example file yet:
cp gcp-service-account.json.example gcp-service-account.json

# Then replace the contents with your downloaded key file
# Or simply overwrite it with the downloaded file
```
7. Make sure the file is in the same directory as the script

#### Share Google Sheet with Service Account

1. Open the `gcp-service-account.json` file
2. Copy the `client_email` value (e.g., `ec2-inventory-uploader@your-project.iam.gserviceaccount.com`)
3. Open your Google Sheet: https://docs.google.com/spreadsheets/d/133Q4pajDehzFzdpN9_PISi-6q9nGosnIcnDUXc_LN4A
4. Click the **Share** button
5. Paste the service account email
6. Give it **Editor** access
7. Uncheck **Notify people**
8. Click **Share**

### 3. Update Script Configuration (Optional)

The script has default values configured, but you can change them in `ec2_inventory.py`:

- **Google Sheet ID**: Line 105 - `default="133Q4pajDehzFzdpN9_PISi-6q9nGosnIcnDUXc_LN4A"`
- **GCP Key File**: Line 100 - `default="gcp-service-account.json"`
- **AWS Accounts Config**: Line 90 - `default="aws_accounts.json"`

## Usage

### Run the script:

```bash
python3 ec2_inventory.py
```

This will:
1. Read AWS credentials from `aws_accounts.json`
2. Query EC2 instances from all configured AWS accounts
3. Clear old data from the Google Sheet
4. Write fresh data to `ec2_inventory.csv`
5. Upload the data to Google Sheets

### Command-line Options:

```bash
python3 ec2_inventory.py --help
```

Options:
- `--config`: Path to AWS accounts config file (default: `aws_accounts.json`)
- `--region`: Override AWS region for all accounts
- `--output`: Output CSV filename (default: `ec2_inventory.csv`)
- `--gcp-key`: Path to Google service account key (default: `gcp-service-account.json`)
- `--sheet-id`: Google Sheet ID (default: configured in script)
- `--sheet-title`: Title for new Google Sheets (default: `EC2 Inventory`)
- `--share-with`: Email to share the Google Sheet with

## Automation with Cron

To run the script automatically on a schedule:

1. Open crontab:
```bash
crontab -e
```

2. Add a line to run the script (example: every day at 2 AM):
```
0 2 * * * cd /home/ubuntu/aws-ai && python3 ec2_inventory.py >> /home/ubuntu/aws-ai/ec2_inventory.log 2>&1
```

3. Check the log file for output:
```bash
tail -f /home/ubuntu/aws-ai/ec2_inventory.log
```

## Security Best Practices

1. **Protect your credentials:**
   - Never commit `aws_accounts.json` or `gcp-service-account.json` to version control
   - Set appropriate file permissions: `chmod 600 aws_accounts.json gcp-service-account.json`

2. **Use least privilege:**
   - AWS IAM users should only have read-only access
   - Google Service Account should only have access to the specific sheet

3. **Rotate credentials regularly:**
   - Update AWS access keys periodically
   - Regenerate Google service account keys as needed

## Troubleshooting

### "No module named 'google'" error
Install the Google API libraries:
```bash
pip3 install --break-system-packages google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### "No module named 'boto3'" error
Install boto3:
```bash
pip3 install --break-system-packages boto3
```

### "Error: AWS accounts config file not found"
Make sure `aws_accounts.json` exists in the same directory as the script.

### "The caller does not have permission" (Google Sheets error)
Make sure the service account email (from `gcp-service-account.json`) has been granted Editor access to the Google Sheet.

### No instances found
- Verify AWS credentials have the correct permissions
- Check that instances are in the `running` state
- Verify the region is correct in `aws_accounts.json`

## Output

The script generates:
- **ec2_inventory.csv**: Local CSV file with instance data
- **Google Sheet**: Updated with the same data (old data is cleared each run)

Columns:
- `account_id`: AWS Account ID
- `account_name`: AWS Account Alias
- `region`: AWS Region
- `instance_id`: EC2 Instance ID
- `instance_name`: Instance Name tag
- `ip_address`: Public or Private IP
- `os_version`: Operating system version
- `key_name`: SSH key pair name
- `uptime_hours`: Hours since instance launch
