import boto3
import argparse
import datetime
import time


def check_lambda_exists(function_name):
    """
    function to check if the given function exists
    :param function_name: Name of the function to check if exists
    :return: bool
    """
    print("Checking if test function {} exist ..........".format(function_name))
    client = boto3.client('lambda')
    functions = client.list_functions()['Functions']
    return any(d['FunctionName'] == function_name for d in functions)


def clone_function(old_function_name,new_function_name,bucket,key):
    """
    function to create a function with exact configuration as another
    :param old_function_name: function to take the configuration from
    :param new_function_name: the name of the new cloned function
    :param bucket: name of the S3 bucket containing the lambda package
    :param key: S3 key of the lambda package
    :return: Arn of the new function
    """
    print("No test function for this branch found .....")
    print("creating function '{}'.....".format(new_function_name))
    client = boto3.client('lambda')
    response = client.get_function_configuration(FunctionName=old_function_name)
    old_function_arn = response['FunctionArn']
    to_remove = ['FunctionArn','ResponseMetadata','Version','LastModified',
                                    'CodeSha256','RevisionId','CodeSize']
    if 'VpcConfig' in response:
        if len(response['VpcConfig']['SubnetIds']) == 0 or len(response['VpcConfig']['SecurityGroupIds']) == 0:
            to_remove.append('VpcConfig')
        else:
            vpc = response['VpcConfig']
            vpc.pop('VpcId',None)
            response['VpcConfig'] = vpc
    for k in to_remove:
            response.pop(k,None)
    response['FunctionName'] = new_function_name
    response['Code'] = {'S3Bucket': bucket, 'S3Key': key}
    new_resp = client.create_function(**response)
    subscribe_to_topics(get_lambda_topics(old_function_arn), new_resp['FunctionArn'])
    return new_resp['FunctionArn']


def update_function(function_name,bucket,key):
    """
    updates the given function's code with a new package.
    :param function_name: name of the function to update
    :param bucket: S3 bucket containing the new lambda package
    :param key: S3 key of the new lambda package
    :return: Function Arn
    """
    print("Test function '{}' already exists".format(function_name))
    print("Updating ..................")
    client = boto3.client('lambda')
    response = client.update_function_code(FunctionName=function_name,
                                           S3Bucket=bucket, S3Key=key, Publish=True)
    print("Test function updated..")
    return response['FunctionArn']


def subscribe_to_topics(topics, function_arn):
    """
    function to subscribe a given function to the the provided topics
    :param function_arn: Arn of the function to subscribe
    :param topics: list of topics
    :return: None
    """
    client = boto3.client('sns')
    for arn in topics:
        client.subscribe(TopicArn=arn, Protocol='lambda', Endpoint=function_arn)


def get_lambda_topics(function_arn):
    """
    function to get the Topics that a given Lambda function depends on
    :param function_arn: ARN of the function
    :return: list of Topics Arn's
    """
    client = boto3.client('sns')
    subscriptions = client.list_subscriptions()['Subscriptions']
    lambda_topics = [s['TopicArn'] for s in subscriptions if s['Endpoint'] == function_arn]
    return lambda_topics


def check_lambda_errors(function_name,period):
    """
    function to check if the given lambda had errors in the specified period
    :param function_name: function name to test
    :param period: period for the cloudwatch metric
    :return: None
    """
    startTime = datetime.datetime.utcnow() - datetime.timedelta(seconds=period)
    print('waiting for {0} seconds before chekcing for errors'.format(period))
    time.sleep(period)
    client = boto3.client('cloudwatch')
    now_utc = datetime.datetime.utcnow().isoformat()
    response = client.get_metric_statistics(Namespace='AWS/Lambda', MetricName='Errors',
                                            Dimensions=[{'Name':'FunctionName', 'Value':function_name}],
                                            StartTime=startTime.isoformat(), EndTime=now_utc,
                                            Period=period, Statistics=['Sum'])['Datapoints']
    assert all(d['Sum'] == 0 for d in response)
    print("The test lambda had no errors")


def delete_test_lambda(function_name, branch):
    """
    function to delete a test function
    :param function_name: Repository name
    :param branch: branch of the function
    :return: None
    """
    client = boto3.client('lambda')
    client.delete_function(FunctionName='test-{}-{}'.format(function_name, branch))


def unsubscribe_function_from_sns(function_arn):
    client = boto3.client('sns')
    all_subscriptions = client.list_subscriptions()['Subscriptions']
    subscriptions = [s['SubscriptionArn'] for s in all_subscriptions if s['Endpoint'] == function_arn]
    if subscriptions:
        for s in subscriptions:
            client.unsubscribe(SubscriptionArn=s)
    return subscriptions


def get_function_arn(function_name):
    """
    Get lambda function ARN
    :param function_name: function name
    :return: Function ARN
    """
    client = boto3.client('lambda')
    return client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['promote','test','deploy_test','delete'])
    parser.add_argument('-f','--function', type=str, help='Repository name')
    parser.add_argument('-b','--bucket', type=str, help='Target bucket name')
    parser.add_argument('-k','--key', type=str, help='S3 key for lambda package')
    parser.add_argument('-w','--wait', type=int, help='Time to wait before testing')
    parser.add_argument('-B','--branch', type=str, help='branch name')
    args = parser.parse_args()
    if args.command == 'promote':
        update_function(args.function,args.bucket,args.key)
    elif args.command == 'test':
        check_lambda_errors("test-{}-{}".format(args.function, args.branch),args.wait)
    elif args.command == 'deploy_test':
        if check_lambda_exists("test-{}-{}".format(args.function,args.branch)):
            update_function("test-{}-{}".format(args.function, args.branch), args.bucket, args.key)
        else:
            print(clone_function(args.function, "test-{}-{}".format(args.function, args.branch), args.bucket, args.key))
    elif args.command == 'delete':
        unsubscribe_function_from_sns(get_function_arn('test-{}-{}'.format(args.function, args.branch)))
        delete_test_lambda(args.function, args.branch)
