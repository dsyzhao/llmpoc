import json
import boto3
import urllib3
import datetime
import logging
import time
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

region_name=os.environ.get('REGION', 'us-east-1')
session = boto3.Session(region_name=region_name)
lambda_client = session.client('lambda')


def call_api_endpoint(ticket_data):
    orderUrl = "http://54.175.83.87:33480/robot/order/create"
    http = urllib3.PoolManager(num_pools=1, headers={'Content-Type': 'application/json'})
    dataJson = json.dumps(ticket_data)
    resp = http.request('POST', orderUrl, body=dataJson, timeout=30, retries=5)
    result = json.loads(resp.data)
    return result

def get_request_ticket_api(userInput: str, phoneNumber: str, confirmTime:str, roomNumber:str) -> str:
    """receive userinput and create request ticket by invoking lambda funciton

    :param userInput: transcription
    :param confirmTime: time
    :param roomNumber: room
    :param phonenumber: phone
    """
    logger.info(f"get_request_ticket_api invoked")
    # start_time = time.time()
    payload = json.dumps({"userInput": userInput, "phoneNumber": phoneNumber, "confirmTime": confirmTime, "roomNumber": roomNumber})
    logger.info(f"{payload = }")

    response = lambda_client.invoke(
        FunctionName=os.environ.get('LAMBDA'),
        InvocationType='Event', # Event - async; 'RequestResponse' - wait for response; DryRun - for testing
        LogType='None',
        Payload=payload)

    # print(f"--- {(time.time() - start_time):.2f} seconds for making api call ---")
    return "ticket is created successfully"


def lambda_handler(event, context):
    start_time = time.time()
    logger.info(f"{event = }")
    logger.info(f"{context = }")

    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']

    parameters = event.get('parameters', [])
    params = {param['name']: param['value'] for param in parameters}
    logger.info(f"{params = }")


    phoneNumber = event['sessionAttributes']['hotel_phone_number']
    roomNumber=event['sessionAttributes']['room_number']

    api_response = get_request_ticket_api(
        userInput=params['userInput'],
        phoneNumber=phoneNumber,
        confirmTime=params['confirmTime'],
        roomNumber=roomNumber)
    logger.info(f"{api_response = }")


    # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
    responseBody =  {
        "TEXT": {
            "body": "The function {} was called successfully!".format(function)
        }
    }

    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    dummy_function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(dummy_function_response))
    logger.info(f"LATENCY TO FINISH: {time.time() - start_time:.2f} sec")

    return dummy_function_response
