#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from botocore.exceptions import BotoCoreError, ClientError


def get_account_info(iam_client, sts_client):
    account_id = ""
    account_name = ""
    try:
        identity = sts_client.get_caller_identity()
        account_id = identity.get("Account", "")
    except (BotoCoreError, ClientError):
        account_id = ""

    try:
        aliases = iam_client.list_account_aliases().get("AccountAliases", [])
        if aliases:
            account_name = aliases[0]
    except (BotoCoreError, ClientError):
        account_name = ""

    return account_id, account_name


def get_ssm_os_versions(ssm_client):
    os_versions = {}
    try:
        paginator = ssm_client.get_paginator("describe_instance_information")
        for page in paginator.paginate():
            for info in page.get("InstanceInformationList", []):
                instance_id = info.get("InstanceId", "")
                platform_name = info.get("PlatformName", "")
                platform_version = info.get("PlatformVersion", "")
                if instance_id:
                    os_versions[instance_id] = " ".join(
                        part for part in [platform_name, platform_version] if part
                    ).strip()
    except (BotoCoreError, ClientError):
        pass

    return os_versions


def get_running_instances(ec2_client):
    instances = []
    paginator = ec2_client.get_paginator("describe_instances")
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append(instance)
    return instances


def get_name_tag(tags):
    if not tags:
        return ""
    for tag in tags:
        if tag.get("Key") == "Name":
            return tag.get("Value", "")
    return ""


def resolve_region(explicit_region):
    if explicit_region:
        return explicit_region

    session = boto3.Session()
    return (
        session.region_name
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )


def load_sheet_config(config_path="sheet_config.json"):
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("sheet_id")
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export running EC2 instances to CSV."
    )
    parser.add_argument(
        "--config",
        default="aws_accounts.json",
        help="Path to AWS accounts configuration file (default: aws_accounts.json).",
    )
    parser.add_argument(
        "--sheet-config",
        default="sheet_config.json",
        help="Path to Google Sheet configuration file (default: sheet_config.json).",
    )
    parser.add_argument(
        "--region",
        help="AWS region (e.g., us-east-1). Falls back to AWS_REGION/AWS_DEFAULT_REGION or AWS config.",
    )
    parser.add_argument(
        "--output",
        default="ec2_inventory.csv",
        help="Output CSV file name (default: ec2_inventory.csv).",
    )
    parser.add_argument(
        "--gcp-key",
        default="gcp-service-account.json",
        help="Path to Google service account JSON key file.",
    )
    parser.add_argument(
        "--sheet-id",
        help="Google Sheet ID to update (overrides sheet_config.json if provided).",
    )
    parser.add_argument(
        "--sheet-title",
        default="EC2 Inventory",
        help="Title for a new Google Sheet (default: EC2 Inventory).",
    )
    parser.add_argument(
        "--share-with",
        help="Email address to grant edit access to the Google Sheet.",
    )
    return parser.parse_args()


def upload_csv_to_google_sheet(
    csv_path,
    gcp_key_path,
    sheet_id=None,
    sheet_title="EC2 Inventory",
    share_with=None,
):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = service_account.Credentials.from_service_account_file(
        gcp_key_path, scopes=scopes
    )
    sheets_service = build("sheets", "v4", credentials=credentials)
    drive_service = build("drive", "v3", credentials=credentials)

    if not sheet_id:
        spreadsheet = (
            sheets_service.spreadsheets()
            .create(body={"properties": {"title": sheet_title}})
            .execute()
        )
        sheet_id = spreadsheet.get("spreadsheetId")

    with open(csv_path, "r", encoding="utf-8") as csvfile:
        rows = list(csv.reader(csvfile))

    sheets_service.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range="Sheet1",
    ).execute()

    (
        sheets_service.spreadsheets()
        .values()
        .update(
            spreadsheetId=sheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": rows},
        )
        .execute()
    )

    if share_with:
        drive_service.permissions().create(
            fileId=sheet_id,
            body={"type": "user", "role": "writer", "emailAddress": share_with},
            sendNotificationEmail=True,
        ).execute()

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def load_aws_accounts(config_path):
    if not os.path.exists(config_path):
        print(f"Error: AWS accounts config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config.get("accounts", [])


def process_account(account_config, region):
    aws_access_key_id = account_config.get("aws_access_key_id")
    aws_secret_access_key = account_config.get("aws_secret_access_key")
    account_region = account_config.get("region", region)
    
    if not aws_access_key_id or not aws_secret_access_key:
        print(f"Warning: Skipping account - missing credentials", file=sys.stderr)
        return []
    
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=account_region,
    )

    ec2_client = session.client("ec2")
    ssm_client = session.client("ssm")
    iam_client = session.client("iam")
    sts_client = session.client("sts")

    account_id, account_name = get_account_info(iam_client, sts_client)
    os_versions = get_ssm_os_versions(ssm_client)
    instances = get_running_instances(ec2_client)
    
    rows = []
    for instance in instances:
        instance_id = instance.get("InstanceId", "")
        instance_name = get_name_tag(instance.get("Tags", []))
        public_ip = instance.get("PublicIpAddress", "")
        private_ip = instance.get("PrivateIpAddress", "")
        ip_address = public_ip or private_ip
        key_name = instance.get("KeyName", "")
        os_version = os_versions.get(instance_id, "")
        if not os_version:
            os_version = instance.get("PlatformDetails", "")

        launch_time = instance.get("LaunchTime")
        if launch_time:
            now = datetime.now(timezone.utc)
            uptime_hours = round(
                (now - launch_time).total_seconds() / 3600, 2
            )
        else:
            uptime_hours = ""

        rows.append([
            account_id,
            account_name,
            account_region,
            instance_id,
            instance_name,
            ip_address,
            os_version,
            key_name,
            uptime_hours,
        ])
    
    print(f"Found {len(instances)} instances in account {account_id or 'unknown'} ({account_name or 'no-alias'})")
    return rows


def main():
    args = parse_args()
    region = resolve_region(args.region)
    
    accounts = load_aws_accounts(args.config)
    if not accounts:
        print("Error: No AWS accounts configured in config file", file=sys.stderr)
        sys.exit(1)

    output_file = args.output
    total_instances = 0
    
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "account_id",
                "account_name",
                "region",
                "instance_id",
                "instance_name",
                "ip_address",
                "os_version",
                "key_name",
                "uptime_hours",
            ]
        )

        for account_config in accounts:
            rows = process_account(account_config, region)
            for row in rows:
                writer.writerow(row)
            total_instances += len(rows)

    print(f"Wrote {total_instances} total instances to {output_file}")

    if args.gcp_key:
        sheet_id = args.sheet_id or load_sheet_config(args.sheet_config)
        sheet_url = upload_csv_to_google_sheet(
            output_file,
            args.gcp_key,
            sheet_id=sheet_id,
            sheet_title=args.sheet_title,
            share_with=args.share_with,
        )
        print(f"Uploaded to Google Sheet: {sheet_url}")


if __name__ == "__main__":
    main()
