import boto3
import os
import pytz
import requests
from datetime import datetime

# Set your work start and end hours (in 24-hour format)
WORK_START_HOUR = 7
WORK_START_MIN = 50
WORK_END_HOUR = 19
WORK_END_MIN = 50

def is_work_hours():
    now = datetime.now(pytz.timezone("America/New_York"))
    work_start = now.replace(hour=WORK_START_HOUR, minute=WORK_START_MIN, second=0, microsecond=0)
    work_end = now.replace(hour=WORK_END_HOUR, minute=WORK_END_MIN, second=0, microsecond=0)

    return work_start <= now < work_end



def notify_slack(message, text, webhook_url):
    attachments = [{
        "color": "#0000FF",
        "text": message,
        "author_name": text
    }]
    slack_data = {
        "username": "MerCloud BOT for RDS Instances",
        "icon_emoji": ":bot:",
        "channel": os.environ["SLACK_CHANNEL"],
        "text": ":AWS: RDS Offhours notifier",
        "attachments": attachments
    }
    response = requests.post(webhook_url, json=slack_data, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        print('OK!')
    else:
        print('Unable to post the response to Slack!')

def start_rds_instance(client, instance):
    instance_id = instance['DBInstanceIdentifier']
    instance_status = instance['DBInstanceStatus']
    instance_arn = instance['DBInstanceArn']

    if instance_status == 'stopped':
        client.start_db_instance(DBInstanceIdentifier=instance_id)
        return f"Starting DB instance {instance_id}; arn value: {instance_arn}"
    elif instance_status == 'available':
        return f"DB Instance {instance_id} is already started; arn value: {instance_arn}"
    elif instance_status == 'starting':
        return f"DB Instance {instance_id} is already in starting state; arn value: {instance_arn}"
    elif instance_status == 'stopping':
        return f"DB Instance {instance_id} is in stopping state. Please start the instance after stopping is complete; arn value: {instance_arn}"
    else:
        return f"Unknown state for DB instance {instance_id}: {instance_status}; arn value: {instance_arn}"

def start_rds_cluster(client, cluster):
    cluster_id = cluster['DBClusterIdentifier']
    cluster_status = cluster['Status']
    cluster_arn = cluster['DBClusterArn']

    if cluster_status == 'stopped':
        client.start_db_cluster(DBClusterIdentifier=cluster_id)
        return f"Starting DB cluster {cluster_id}; arn value: {cluster_arn}"
    elif cluster_status == 'available':
        return f"DB Cluster {cluster_id} is already started; arn value: {cluster_arn}"
    elif cluster_status == 'starting':
        return f"DB Cluster {cluster_id} is already in starting state; arn value: {cluster_arn}"
    elif cluster_status == 'stopping':
        return f"DB Cluster {cluster_id} is in stopping state. Please start the cluster after stopping is complete; arn value: {cluster_arn}"
    else:
        return f"Unknown state for DB Cluster {cluster_id}: {cluster_status}; arn value: {cluster_arn}"


def stop_rds_instance(client, instance):
    instance_id = instance['DBInstanceIdentifier']
    instance_status = instance['DBInstanceStatus']
    instance_arn = instance['DBInstanceArn']

    if instance_status == 'available':
        client.stop_db_instance(DBInstanceIdentifier=instance_id)
        return f"Stopping DB instance {instance_id}; arn value: {instance_arn}"
    elif instance_status == 'stopped':
        return f"DB Instance {instance_id} is already stopped; arn value: {instance_arn}"
    elif instance_status == 'starting':
        return f"DB Instance {instance_id} is in starting state. Please stop the instance after starting is complete; arn value: {instance_arn}"
    elif instance_status == 'stopping':
        return f"DB Instance {instance_id} is already in stopping state; arn value: {instance_arn}"
    else:
        return f"Unknown state for DB instance {instance_id}: {instance_status}; arn value: {instance_arn}"

def stop_rds_cluster(client, cluster):
    cluster_id = cluster['DBClusterIdentifier']
    cluster_status = cluster['Status']
    cluster_arn = cluster['DBClusterArn']

    if cluster_status == 'available':
        client.stop_db_cluster(DBClusterIdentifier=cluster_id)
        return f"Stopping DB cluster {cluster_id}; arn value: {cluster_arn}"
    elif cluster_status == 'stopped':
        return f"DB Cluster {cluster_id} is already stopped; arn value: {cluster_arn}"
    elif cluster_status == 'starting':
        return f"DB Cluster {cluster_id} is in starting state. Please stop the cluster after starting is complete; arn value: {cluster_arn}"
    elif cluster_status == 'stopping':
        return f"DB Cluster {cluster_id} is already in stopping state; arn value: {cluster_arn}"
    else:
        return f"Unknown state for DB Cluster {cluster_id}: {cluster_status}; arn value: {cluster_arn}"

def manage_rds_instances_and_clusters(region, account_details, webhook_url, action):
    client = boto3.client('rds', region_name=region)
    response = client.describe_db_instances()
    v_read_replica = []
    slack_messages = []

    for instance in response['DBInstances']:
        read_replica = instance['ReadReplicaDBInstanceIdentifiers']
        v_read_replica.extend(read_replica)

    for instance in response['DBInstances']:
        message = ''
        text = f"Account details: {account_details}, Region: {region} , Engine Name: {instance['Engine']}"

        if instance['Engine'] not in ['aurora-mysql', 'aurora-postgresql']:
            if instance['DBInstanceIdentifier'] not in v_read_replica and len(instance['ReadReplicaDBInstanceIdentifiers']) == 0:
                arn = instance['DBInstanceArn']
                resp2 = client.list_tags_for_resource(ResourceName=arn)

                if len(resp2['TagList']) == 0:
                    print(f"DB Instance {instance['DBInstanceIdentifier']} is not part of autostop")
                else:
                    for tag in resp2['TagList']:
                        if tag['Key'] == os.environ['KEY'] and tag['Value'] == os.environ['VALUE']:
                            if action == 'start':
                                message += start_rds_instance(client, instance)
                            elif action == 'stop':
                                message += stop_rds_instance(client, instance)
                            break
                    else:
                        print(f"DB instance {instance['DBInstanceIdentifier']} is not part of autostop")

        if message:
            slack_messages.append((message, text))
        else:
            print(message)

    # Process RDS clusters
    response2 = client.describe_db_clusters()
    
    for cluster in response2['DBClusters']:
        message = ''
        text = f"Account details: {account_details}, Region: {region}, Engine Name: {cluster['Engine']}"
        cluarn = cluster['DBClusterArn']
        resp2 = client.list_tags_for_resource(ResourceName=cluarn)

        if len(resp2['TagList']) == 0:
            print(f"DB Cluster {cluster['DBClusterIdentifier']} is not part of autostop")
        else:
            for tag in resp2['TagList']:
                if tag['Key'] == os.environ['KEY'] and tag['Value'] == os.environ['VALUE']:
                    if action == 'start':
                        message += start_rds_cluster(client, cluster)
                    elif action == 'stop':
                        message += stop_rds_cluster(client, cluster)
                    break
            else:
                print(f"DB Cluster {cluster['DBClusterIdentifier']} is not part of autostop")

        if message:
            slack_messages.append((message, text))
        else:
            print(message)

    # Send Slack messages
    for message, text in slack_messages:
        notify_slack(message, text, webhook_url)



def lambda_handler(event, context):
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    account_alias = boto3.client('iam').list_account_aliases()['AccountAliases'][0]

    if "-sandbox-" in account_alias:
        regions = ['us-east-1']
    elif "-compass" in account_alias:
        regions = ['us-east-1']
    elif "-eu" in account_alias:
        regions = ['eu-west-1', 'eu-central-1']
    elif "-apac" in account_alias:
        regions = ['ap-southeast-2']
    else:
        print("No Account Matches")
    webhook_url = os.environ["SLACK_ENDPOINT"]

    if regions and is_work_hours():
        for region in regions:
            manage_rds_instances_and_clusters(region, account_alias, webhook_url, 'start')
    elif regions and not is_work_hours():
        for region in regions:
            if datetime.now(pytz.timezone("America/New_York")).weekday() == 0:
                manage_rds_instances_and_clusters(region, account_alias, webhook_url, 'start')
            else:
                manage_rds_instances_and_clusters(region, account_alias, webhook_url, 'stop')
    else:
        print("No Account Matches or outside of work hours")


