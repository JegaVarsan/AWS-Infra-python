import boto3
from botocore.exceptions import ClientError
import json
import time

aws_region = 'us-east-1'

ec2 = boto3.resource('ec2', region_name=aws_region)
ec2_client = boto3.client('ec2', region_name=aws_region)
iam_client = boto3.client('iam', region_name=aws_region)
s3_client = boto3.client('s3', region_name=aws_region)


# Specify resource names
vpc_name = 'my_vpc'
security_group_name = 'WEB-ACCESS'
instance_profile_name = 'EC2InstanceProfile'
role_name = 'EC2S3UploadRole'
s3_bucket_name = 'boto-infra-creation-327658721'


def create_s3_bucket(bucket_name):
    try:
        response =s3_client.create_bucket(
            Bucket=s3_bucket_name
        )
        print(f"S3 bucket '{bucket_name}' created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"S3 bucket '{bucket_name}' already exists and owned by you.")
        else:
            print(f"Error creating S3 bucket: {e}")
            return None
    return bucket_name

def main():
    # Create S3 bucket if it doesn't exist
    if not s3_client.list_buckets()['Buckets']:
        create_s3_bucket(s3_bucket_name)

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/24')
    vpc.create_tags(Tags=[{"Key": "Name", "Value": vpc_name}])
    vpc.wait_until_available()

    ec2_client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsSupport={'Value': True})
    ec2_client.modify_vpc_attribute(VpcId=vpc.id, EnableDnsHostnames={'Value': True})

    # Create and attach Internet Gateway
    internet_gateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internet_gateway.id)

    # Create Route Table and Route
    route_table = vpc.create_route_table()
    route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internet_gateway.id)

    # Create Subnet and associate with Route Table
    subnet = ec2.create_subnet(CidrBlock='10.0.0.0/26', VpcId=vpc.id)
    route_table.associate_with_subnet(SubnetId=subnet.id)

    # Create Security Group and Authorize Ingress
    security_group = ec2.create_security_group(GroupName=security_group_name, Description='Allow SSH and HTTP traffic', VpcId=vpc.id)
    security_group.authorize_ingress(
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 3000,
                'ToPort': 3000,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )

    # Create IAM Role
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        create_role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
            Description='Role to allow EC2 instances to call AWS services'
        )
        role_arn = create_role_response['Role']['Arn']
        print(f"Created role with ARN: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = iam_client.get_role(RoleName=role_name)['Role']['Arn']
        print(f"Role already exists with ARN: {role_arn}")

    # Attach policy to the role
    policy_arn = 'arn:aws:iam::aws:policy/AmazonS3FullAccess'
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    print(f"Attached policy {policy_arn} to role {role_name}")

    # Create instance profile and add role
    try:
        iam_client.create_instance_profile(InstanceProfileName=instance_profile_name)
        print(f"Created instance profile: {instance_profile_name}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"Instance profile already exists: {instance_profile_name}")

    # Adding role to instance profile
    try:
        iam_client.add_role_to_instance_profile(InstanceProfileName=instance_profile_name, RoleName=role_name)
        print(f"Added role {role_name} to instance profile {instance_profile_name}")
    except iam_client.exceptions.LimitExceededException:
        print(f"Role {role_name} already added to instance profile {instance_profile_name}")

    # Wait for the instance profile to become available
    print("Waiting for instance profile to become available...")
    time.sleep(20)

    # Create Key-Pair
    try:
        outfile = open('testing.pem', 'w')
        key_pair = ec2.create_key_pair(KeyName='testing')
        KeyPairOut = str(key_pair.key_material)
        outfile.write(KeyPairOut)
        outfile.close()
    except ClientError as e:
        if 'InvalidKeyPair.Duplicate' in str(e):
            print("Key pair already exists.")
        else:
            raise
    
    user_data_script = '''#!/bin/bash
    sudo apt-get update -y
    sudo apt-get install -y git curl
    curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash -
    sudo apt-get install -y nodejs npm
    sudo apt-get install -y awscli
    git clone https://github.com/JegaVarsan/Reactjs-Simple-Project.git /home/ubuntu/react-app
    cd /home/ubuntu/react-app
    npm install

    # Run the application in the background
    npm start > /tmp/npm_start_output.log 2>&1 &

    # Check if npm start was successful
    sleep 30  # Wait for a bit to let npm start the application
    if ps aux | grep -q '[n]pm start'; then
        echo "Application deployment succeeded" > /tmp/deployment_status.txt
    else
        echo "Application deployment failed" > /tmp/deployment_status.txt
        cat /tmp/npm_start_output.log >> /tmp/deployment_status.txt
    fi

    # Upload deployment status to S3 bucket
    sudo snap install aws-cli --classic
    aws s3 cp /tmp/deployment_status.txt s3://boto-infra-creation-327658721/deployment_status.txt
    '''

    # Create EC2 instance
    instances = ec2.create_instances(
        ImageId='ami-04a81a99f5ec58529',
        InstanceType='t2.micro',
        MaxCount=1,
        MinCount=1,
        NetworkInterfaces=[{
            'SubnetId': subnet.id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [security_group.group_id]
        }],
        KeyName='testing',
        UserData=user_data_script,
        IamInstanceProfile={'Name': instance_profile_name}
    )

    instance_id = instances[0].id
    print(f"EC2 instance created with ID: {instance_id}")

if __name__ == "__main__":
    main()
