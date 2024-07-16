import boto3
from botocore.exceptions import ClientError

aws_region = 'us-east-1'

ec2 = boto3.resource('ec2', region_name=aws_region)
ec2_client = boto3.client('ec2', region_name=aws_region)
iam_client = boto3.client('iam', region_name=aws_region)
logs_client = boto3.client('logs', region_name=aws_region)
s3_client = boto3.client('s3', region_name=aws_region)

# Specify the names of resources to delete
vpc_name = 'my_vpc'
security_group_name = 'WEB-ACCESS'
instance_profile_name = 'EC2InstanceProfile'
role_name = 'EC2S3UploadRole'
log_group_name = '/aws/ec2/deployment'
s3_bucket_name = 'boto-infra-creation-327658721'

def get_vpc_by_name(name):
    vpcs = ec2.vpcs.filter(Filters=[{'Name': 'tag:Name', 'Values': [name]}])
    return list(vpcs)[0] if vpcs else None


def delete_s3_bucket():
    try:
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name)
        objects = response.get('Contents', [])
        if objects:
            s3_client.delete_objects(
                Bucket=s3_bucket_name,
                Delete={'Objects': [{'Key': obj['Key']} for obj in objects]}
            )
            print(f"Deleted objects from S3 bucket: {s3_bucket_name}")

        s3_client.delete_bucket(Bucket=s3_bucket_name)
        print(f"S3 bucket '{s3_bucket_name}' deleted successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"S3 bucket '{s3_bucket_name}' not found.")
        else:
            print(f"Error deleting S3 bucket: {e}")

def delete_instances(vpc):
    instances = vpc.instances.all()
    instance_ids = [instance.id for instance in instances]
    if instance_ids:
        print(f"Terminating instances: {instance_ids}")
        ec2_client.terminate_instances(InstanceIds=instance_ids)
        for instance in instances:
            instance.wait_until_terminated()
        print("Instances terminated.")

def delete_security_groups(vpc):
    security_groups = list(vpc.security_groups.all())
    for sg in security_groups:
        if sg.group_name != 'default':  # do not delete the default security group
            print(f"Deleting security group: {sg.group_id}")
            sg.delete()
    print("Security groups deleted.")

def delete_subnets(vpc):
    subnets = list(vpc.subnets.all())
    for subnet in subnets:
        print(f"Deleting subnet: {subnet.id}")
        subnet.delete()
    print("Subnets deleted.")

def delete_route_tables(vpc):
    route_tables = list(vpc.route_tables.all())
    for rt in route_tables:
        if not rt.associations:  # Only delete route tables without associations
            print(f"Deleting route table: {rt.id}")
            rt.delete()
    print("Route tables deleted.")

def detach_internet_gateways(vpc):
    igws = list(vpc.internet_gateways.all())
    for igw in igws:
        print(f"Detaching internet gateway: {igw.id}")
        vpc.detach_internet_gateway(InternetGatewayId=igw.id)
        igw.delete()
    print("Internet gateways detached and deleted.")

def delete_vpc(vpc):
    print(f"Deleting VPC: {vpc.id}")
    vpc.delete()
    print("VPC deleted.")

def delete_instance_profile(profile_name):
    try:
        print(f"Removing role from instance profile: {profile_name}")
        iam_client.remove_role_from_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name
        )
        print(f"Deleting instance profile: {profile_name}")
        iam_client.delete_instance_profile(InstanceProfileName=profile_name)
        print("Instance profile deleted.")
    except iam_client.exceptions.NoSuchEntityException:
        print("Instance profile or role not found.")

def delete_iam_role(role_name):
    try:
        print(f"Detaching policy from role: {role_name}")
        policy_arn =  'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print(f"Deleting role: {role_name}")
        iam_client.delete_role(RoleName=role_name)
        print("IAM role deleted.")
    except iam_client.exceptions.NoSuchEntityException:
        print("Role or policy not found.")

def delete_log_group(log_group_name):
    try:
        print(f"Deleting log group: {log_group_name}")
        logs_client.delete_log_group(logGroupName=log_group_name)
        print("Log group deleted.")
    except logs_client.exceptions.ResourceNotFoundException:
        print("Log group not found.")

def main():
    delete_instance_profile(instance_profile_name)
    delete_iam_role(role_name)
    delete_log_group(log_group_name)
    
    vpc = get_vpc_by_name(vpc_name)
    if vpc:
        delete_instances(vpc)
        delete_security_groups(vpc)
        delete_subnets(vpc)
        detach_internet_gateways(vpc)
        delete_route_tables(vpc)
        delete_vpc(vpc)
        delete_s3_bucket()
    else:
        print(f"VPC {vpc_name} not found.")

if __name__ == "__main__":
    main()
