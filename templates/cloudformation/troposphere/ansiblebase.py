#!/usr/bin/env python

from troposphere import Ref, Template, ec2, Parameter, Output, Join, GetAtt, Base64

from troposphere.iam import Role, InstanceProfile
from troposphere.iam import PolicyType as IAMPolicy

from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole


t = Template()


kp = Parameter(
    "KeyPair",
    Description="Name of an existing EC2 KeyPair to SSH",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair."
  )
t.add_parameter(kp)

sg = ec2.SecurityGroup('HelloWolrdAnsibleWebServerSecurityGroup')
sg.GroupDescription = "Allow SSH and TCP/3000 access"

sg.SecurityGroupIngress = [
ec2.SecurityGroupRule(
    IpProtocol="tcp",
    FromPort="22",
    ToPort="22",
    CidrIp="0.0.0.0/0",
  ),
ec2.SecurityGroupRule(
    IpProtocol="tcp",
    FromPort="3000",
    ToPort="3000",
    CidrIp="0.0.0.0/0",
  )]
t.add_resource(sg)

t.add_resource(Role(
    "HelloWorldRole",
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[AssumeRole],
                Principal=Principal("Service", ["ec2.amazonaws.com"])
            )
        ]
    )
))

t.add_resource(IAMPolicy(
    "HelloWorldPolicy",
    PolicyName="HelloWorldRole",
    PolicyDocument=Policy(
        Statement=[
            Statement(Effect=Allow, Action=[Action("ec2", "*")],
                      Resource=["*"])
        ]
    ),
    Roles=[Ref("HelloWorldRole")]
))

profile = InstanceProfile(
    "AnsibleHelloWorldInstanceProfile",
    Path="/",
    Roles=[Ref("HelloWorldRole")]
)

t.add_resource(profile)

ud = Base64(Join('\n', [
        "#!/bin/bash",
        "exec > /var/log/userdata.log 2>&1",
        "sudo yum install --enablerepo=epel -y git",
        "sudo pip install ansible",
        "/usr/local/bin/ansible-pull -U https://github.com/EffectiveDevOpsWithAWS/ansible helloworld.yml -C helloworldrole -i localhost",
        "echo '*/10 * * * * /usr/local/bin/ansible-pull -U https://github.com/EffectiveDevOpsWithAWS/ansible helloworld.yml -C helloworldrole -i localhost' > /etc/cron.d/ansible-pull"
    ]))

instance = ec2.Instance("HelloWorld",
    ImageId="ami-f5f41398",
    InstanceType="t2.micro",
    SecurityGroups=[Ref(sg)],
    KeyName=Ref(kp),
    UserData=ud,
    IamInstanceProfile=Ref(profile)
)

t.add_resource(instance)

ip = Output(
    "InstancePublicIp",
    Description="Public IP of our instance.",
    Value=GetAtt(instance, "PublicIp")
  )
t.add_output(ip)

# Print out CloudFormation template in JSON
print t.to_json()
