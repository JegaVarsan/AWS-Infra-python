# import boto3

# # Initialize Boto3 clients for EC2 and VPC
# ec2_client = boto3.client('ec2')
# ec2_resource = boto3.resource('ec2')
# vpc_client = boto3.client('ec2')

# # Create VPC
# def create_vpc(cidr_block):
#     print("Creating VPC...")
#     response = vpc_client.create_vpc(CidrBlock=cidr_block)
#     vpc_id = response['Vpc']['VpcId']
#     print(f"VPC created with ID: {vpc_id}")
#     return vpc_id

# # Create subnet within VPC
# def create_subnet(vpc_id, cidr_block):
#     print("Creating subnet...")
#     response = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock=cidr_block)
#     subnet_id = response['Subnet']['SubnetId']
#     print(f"Subnet created with ID: {subnet_id}")
#     return subnet_id

# # Create EC2 instance
# def create_ec2_instance(subnet_id):
#     print("Creating EC2 instance...")
#     instances = ec2_resource.create_instances(
#         ImageId='ami-xxxxxxxx',  # Replace with your desired AMI ID
#         InstanceType='t2.micro',  # Replace with your desired instance type
#         MaxCount=1,
#         MinCount=1,
#         NetworkInterfaces=[
#             {
#                 'SubnetId': subnet_id,
#                 'DeviceIndex': 0,
#                 'AssociatePublicIpAddress': True
#             }
#         ]
#     )
#     instance_id = instances[0].id
#     print(f"EC2 instance created with ID: {instance_id}")
#     return instance_id

# # Create security group
# def create_security_group(vpc_id):
#     print("Creating security group...")
#     response = ec2_client.create_security_group(
#         GroupName='MySecurityGroup',
#         Description='Security group for my EC2 instance',
#         VpcId=vpc_id
#     )
#     security_group_id = response['GroupId']
#     print(f"Security group created with ID: {security_group_id}")
#     return security_group_id

# # Authorize inbound traffic to EC2 instance
# def authorize_security_group_ingress(security_group_id):
#     print("Authorizing security group ingress...")
#     ec2_client.authorize_security_group_ingress(
#         GroupId=security_group_id,
#         IpPermissions=[
#             {
#                 'IpProtocol': 'tcp',
#                 'FromPort': 22,
#                 'ToPort': 22,
#                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Example: allow SSH from anywhere
#             },
#             {
#                 'IpProtocol': 'tcp',
#                 'FromPort': 80,
#                 'ToPort': 80,
#                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Example: allow HTTP from anywhere
#             }
#         ]
#     )
#     print("Ingress rules added to security group.")

# # Create route table and associate with subnet
# def create_route_table(vpc_id, subnet_id):
#     print("Creating route table and associating with subnet...")
#     route_table = ec2_resource.create_route_table(VpcId=vpc_id)
#     route_table.create_route(
#         DestinationCidrBlock='0.0.0.0/0',
#         GatewayId='igw-xxxxxxxx'  # Replace with your Internet Gateway ID
#     )
#     route_table.associate_with_subnet(SubnetId=subnet_id)
#     print("Route table created and associated with subnet.")

# # Example usage
# def main():
#     # Create VPC
#     vpc_id = create_vpc('10.0.0.0/16')

#     # Create subnet
#     subnet_id = create_subnet(vpc_id, '10.0.1.0/24')

#     # Create EC2 instance
#     instance_id = create_ec2_instance(subnet_id)

#     # Create security group
#     security_group_id = create_security_group(vpc_id)

#     # Authorize inbound traffic to EC2 instance
#     authorize_security_group_ingress(security_group_id)

#     # Create route table and associate with subnet
#     create_route_table(vpc_id, subnet_id)

# if __name__ == '__main__':
#     main()



import boto3
from botocore.exceptions import ClientError

aws_region = 'us-east-1'

ec2 = boto3.resource('ec2',region_name=aws_region)
ec2Client = boto3.client('ec2',region_name=aws_region)

def main():
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/24')

    vpc.create_tags(Tags=[{"Key": "Name", "Value": "my_vpc"}])

    vpc.wait_until_available()

    
    ec2Client.modify_vpc_attribute( VpcId = vpc.id , EnableDnsSupport = { 'Value': True } )
    ec2Client.modify_vpc_attribute( VpcId = vpc.id , EnableDnsHostnames = { 'Value': True } )

    internetgateway = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=internetgateway.id)

    routetable = vpc.create_route_table()
    route = routetable.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internetgateway.id)

    subnet = ec2.create_subnet(CidrBlock='10.0.0.0/26', VpcId=vpc.id)
    routetable.associate_with_subnet(SubnetId=subnet.id)

    securitygroup = ec2.create_security_group(GroupName='WEB-ACCESS', Description='Allow SSH and HTTP traffic', VpcId=vpc.id)
    securitygroup.authorize_ingress(
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

    # CloudWatch Setup

    logs_client = boto3.client('logs', region_name='us-east-1')

    log_group_name = '/aws/ec2/deployment'
    log_stream_name = 'application_deployment_status'

    # Create Log Group
    try:
        logs_client.create_log_group(logGroupName=log_group_name)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass

    # Create Log Stream
    try:
        logs_client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass

    try:
        # create a file to store the key locally
        outfile = open('testing.pem', 'w')
        
        # call the boto ec2 function to create a key pair
        key_pair = ec2.create_key_pair(KeyName='testing')
        
        # capture the key and store it in a file
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
    git clone https://github.com/JegaVarsan/Reactjs-Simple-Project.git /home/ubuntu/react-app
    cd /home/ubuntu/react-app
    npm install
    npm start
    '''


    # Create a linux instance in the subnet
    instances = ec2.create_instances(
    ImageId='ami-04a81a99f5ec58529',
    InstanceType='t2.micro',
    MaxCount=1,
    MinCount=1,
    NetworkInterfaces=[{
    'SubnetId': subnet.id,
    'DeviceIndex': 0,
    'AssociatePublicIpAddress': True,
    'Groups': [securitygroup.group_id]
    }],
    KeyName='testing',
    UserData=user_data_script
    )


if __name__ == "__main__":
    main()


