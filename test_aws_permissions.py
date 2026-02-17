#!/usr/bin/env python3
"""Test AWS geo-routes permissions and available regions"""

import boto3
from botocore.exceptions import ClientError

def test_geo_routes():
    print("Testing AWS geo-routes service...\n")
    
    # Test identity
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✓ AWS Identity:")
        print(f"  Account: {identity['Account']}")
        print(f"  User: {identity['Arn']}\n")
    except Exception as e:
        print(f"✗ Failed to get identity: {e}\n")
        return
    
    # Check available regions for geo-routes
    print("Checking available regions for geo-routes...")
    try:
        session = boto3.Session()
        regions = session.get_available_regions('geo-routes')
        if not regions:
            print("⚠ No regions returned by boto3, trying known regions from AWS docs...")
            # From AWS docs: Enhanced Routes available in these regions
            regions = [
                'us-east-1', 'us-east-2', 'us-west-2',
                'ap-south-1', 'ap-southeast-2', 'ap-northeast-1',
                'ca-central-1', 'eu-central-1', 'eu-west-1', 
                'eu-west-2', 'eu-north-1', 'eu-west-3', 'sa-east-1'
            ]
        print(f"✓ Testing regions: {regions}\n")
    except Exception as e:
        print(f"✗ Could not get regions: {e}\n")
        regions = ['us-east-1', 'us-west-2', 'eu-west-1']  # Try common regions
    
    # Test geo-routes in different regions
    test_coords = {
        "Origin": [-122.339, 47.617],  # Seattle
        "Destination": [-122.335, 47.608],
        "Waypoints": [
            {"Position": [-122.337, 47.613]},
            {"Position": [-122.341, 47.611]}
        ],
        "TravelMode": "Car",
        "OptimizeSequencingFor": "FastestRoute"
    }
    
    for region in regions:
        print(f"Testing region: {region}")
        try:
            client = boto3.client('geo-routes', region_name=region)
            response = client.optimize_waypoints(**test_coords)
            print(f"✓ SUCCESS in {region}!")
            print(f"  Response keys: {list(response.keys())}\n")
            return region
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            print(f"✗ {region}: {error_code} - {error_msg}\n")
        except Exception as e:
            print(f"✗ {region}: {type(e).__name__}: {e}\n")
    
    print("\n❌ geo-routes failed in all regions")
    print("\nTroubleshooting:")
    print("1. Update boto3: pip install --upgrade boto3")
    print("2. Check IAM permissions include: geo-routes:OptimizeWaypoints")
    print("3. Verify geo-routes is available in your account/region")

if __name__ == "__main__":
    test_geo_routes()
