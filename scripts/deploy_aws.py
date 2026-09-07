import os
import sys
import time
import boto3

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION,
)

ec2 = session.client("ec2")
s3 = session.client("s3")

# 1. Ensure Security Group
group_name = "meteora-prototype-sg"
sgs = ec2.describe_security_groups(GroupNames=[group_name])
sg_id = sgs["SecurityGroups"][0]["GroupId"]

# 2. Latest Ubuntu AMI
images = ec2.describe_images(
    Owners=["099720109477"],
    Filters=[
        {"Name": "name", "Values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]},
        {"Name": "state", "Values": ["available"]},
    ],
)
sorted_images = sorted(images["Images"], key=lambda x: x["CreationDate"], reverse=True)
ami_id = sorted_images[0]["ImageId"]

# 3. User Data Script using Production Docker Compose
user_data_script = f"""#!/bin/bash
set -e
exec > /var/log/user-data.log 2>&1

echo "Installing Docker..."
apt-get update -y
apt-get install -y docker.io docker-compose-v2 git

systemctl start docker
systemctl enable docker

mkdir -p /opt/meteora
cd /opt/meteora
git clone https://github.com/Team-Cerevia/National-weather-intelligence.git .

echo "Starting Production Docker Compose stack..."
docker compose -f docker-compose.prod.yml up -d --build

echo "METEORA Live Deployment Complete!"
"""

# Launch EC2 Instance with KeyPair
instances = ec2.run_instances(
    ImageId=ami_id,
    InstanceType="t3.small",
    KeyName="meteora-ec2-key",
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[sg_id],
    UserData=user_data_script,
    BlockDeviceMappings=[
        {
            "DeviceName": "/dev/sda1",
            "Ebs": {
                "VolumeSize": 30,
                "VolumeType": "gp3",
                "DeleteOnTermination": True,
            },
        }
    ],
    TagSpecifications=[
        {
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": "METEORA-Weather-Intelligence-Prototype"}],
        }
    ],
)

instance_id = instances["Instances"][0]["InstanceId"]
print(f"EC2 Instance Launched: {instance_id}")

time.sleep(10)
instance_desc = ec2.describe_instances(InstanceIds=[instance_id])
public_ip = instance_desc["Reservations"][0]["Instances"][0].get("PublicIpAddress")

while not public_ip:
    time.sleep(5)
    instance_desc = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = instance_desc["Reservations"][0]["Instances"][0].get("PublicIpAddress")

print(f"Public IP: {public_ip}")
