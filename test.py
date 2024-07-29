
import boto3
from botocore.exceptions import ClientError
import json
import time

aws_region = 'us-east-1'

ec2 = boto3.resource('ec2', region_name=aws_region)
ec2_client = boto3.client('ec2', region_name=aws_region)
iam_client = boto3.client('iam', region_name=aws_region)
s3_client = boto3.client('s3', region_name=aws_region)
logs_client = boto3.client('logs', region_name=aws_region)

# Specify resource names
vpc_name = 'my_vpc'
security_group_name = 'WEB-ACCESS'
instance_profile_name = 'EC2InstanceProfile'
role_name = 'EC2S3UploadRole'
s3_bucket_name = 'boto-infra-creation-327658721'
log_group_name = '/aws/ec2/deployment'
log_stream_name = 'application_deployment_status'


def create_s3_bucket(bucket_name):
    try:
        response = s3_client.create_bucket(
            Bucket=bucket_name
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
    
    # create_s3_bucket(s3_bucket_name)
    
    response = s3_client.get_object(Bucket='boto-infra-creation-327658721', Key='deployment_status.txt')
    decoded_result = response['Body'].read().decode('utf-8')
    print(decoded_result.splitlines()[0]) 


if __name__ == "__main__":
    main()
