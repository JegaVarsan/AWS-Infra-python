import boto3
from botocore.exceptions import ClientError

aws_region = 'us-east-1'

ec2_client = boto3.client('ec2', region_name=aws_region)
ec2_resource = boto3.resource('ec2', region_name=aws_region)

def main():
    vpc_id = None
    subnet_id = None
    instance_id = None
    security_group_id = None
    internet_gateway_id = None
    route_table_id = None
    key_name = 'testing'

    try:
        # Get the VPC ID
        vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['my_vpc']}])
        vpc_id = vpcs['Vpcs'][0]['VpcId'] if vpcs['Vpcs'] else None

        # Get the subnet ID
        if vpc_id:
            subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            subnet_id = subnets['Subnets'][0]['SubnetId'] if subnets['Subnets'] else None

        # Get the instance ID
        if subnet_id:
            instances = ec2_client.describe_instances(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])
            instance_id = instances['Reservations'][0]['Instances'][0]['InstanceId'] if instances['Reservations'] else None

        # Get the security group ID
        if vpc_id:
            security_groups = ec2_client.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            security_group_id = security_groups['SecurityGroups'][0]['GroupId'] if security_groups['SecurityGroups'] else None

        # Get the internet gateway ID
        if vpc_id:
            internet_gateways = ec2_client.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
            internet_gateway_id = internet_gateways['InternetGateways'][0]['InternetGatewayId'] if internet_gateways['InternetGateways'] else None

        # Get the route table ID
        if vpc_id:
            route_tables = ec2_client.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            route_table_id = route_tables['RouteTables'][0]['RouteTableId'] if route_tables['RouteTables'] else None

    except ClientError as e:
        print(f"Error retrieving resource IDs: {e}")
        return

    cleanup_resources(instance_id, key_name, security_group_id, subnet_id, route_table_id, internet_gateway_id, vpc_id)

def cleanup_resources(instance_id, key_name, group_id, subnet_id, route_table_id, internet_gateway_id, vpc_id):
    # Step 1: Terminate the EC2 instance
    delete_ec2_instance(instance_id)
    
    # Step 2: Delete the security group
    delete_security_group(group_id)
    
    # Step 3: Detach the internet gateway from the VPC
    detach_internet_gateway(vpc_id, internet_gateway_id)
    
    # Step 4: Delete the internet gateway
    delete_internet_gateway(internet_gateway_id)

    # Step 6: Delete the subnet
    delete_subnet(subnet_id)
    
    # Step 5: Delete the route table
    delete_route_table(route_table_id)
    
    # Step 7: Delete the VPC
    delete_vpc(vpc_id)
    
    # Step 8: Delete the key pair
    delete_key_pair(key_name)

def delete_ec2_instance(instance_id):
    if instance_id:
        try:
            ec2_client.terminate_instances(InstanceIds=[instance_id])
            print(f"Terminated instance: {instance_id}")
            waiter = ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[instance_id])
            print(f"Instance {instance_id} is terminated")
        except ClientError as e:
            print(f"Error terminating instance: {e}")

def delete_key_pair(key_name):
    try:
        ec2_client.delete_key_pair(KeyName=key_name)
        print(f"Deleted key pair: {key_name}")
    except ClientError as e:
        print(f"Error deleting key pair: {e}")

def delete_security_group(group_id):
    if group_id:
        try:
            ec2_client.delete_security_group(GroupId=group_id)
            print(f"Deleted security group: {group_id}")
        except ClientError as e:
            print(f"Error deleting security group: {e}")

def delete_subnet(subnet_id):
    if subnet_id:
        try:
            ec2_client.delete_subnet(SubnetId=subnet_id)
            print(f"Deleted subnet: {subnet_id}")
        except ClientError as e:
            print(f"Error deleting subnet: {e}")

def delete_route_table(route_table_id):
    if route_table_id:
        try:
            ec2_client.delete_route_table(RouteTableId=route_table_id)
            print(f"Deleted route table: {route_table_id}")
        except ClientError as e:
            print(f"Error deleting route table: {e}")

def detach_internet_gateway(vpc_id, internet_gateway_id):
    if vpc_id and internet_gateway_id:
        try:
            ec2_client.detach_internet_gateway(InternetGatewayId=internet_gateway_id, VpcId=vpc_id)
            print(f"Detached internet gateway: {internet_gateway_id} from VPC: {vpc_id}")
        except ClientError as e:
            print(f"Error detaching internet gateway: {e}")

def delete_internet_gateway(internet_gateway_id):
    if internet_gateway_id:
        try:
            ec2_client.delete_internet_gateway(InternetGatewayId=internet_gateway_id)
            print(f"Deleted internet gateway: {internet_gateway_id}")
        except ClientError as e:
            print(f"Error deleting internet gateway: {e}")

def delete_vpc(vpc_id):
    if vpc_id:
        try:
            ec2_client.delete_vpc(VpcId=vpc_id)
            print(f"Deleted VPC: {vpc_id}")
        except ClientError as e:
            print(f"Error deleting VPC: {e}")

if __name__ == "__main__":
    main()
