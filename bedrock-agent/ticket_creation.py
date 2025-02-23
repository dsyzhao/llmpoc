import json
import boto3
import urllib3
import datetime
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

region_name='us-east-1'
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
        FunctionName="hotel-help-desk-assistant-api-us-east-1-205154476688",
        InvocationType='Event', # Event - async; 'RequestResponse' - wait for response; DryRun - for testing
        LogType='None',
        Payload=payload)

    # print(f"--- {(time.time() - start_time):.2f} seconds for making api call ---")
    return "ticket is created successfully"

# def create_ticket(item, roomNumber, confirmTime, userInput="", quantity=1):
#     """Generate payload for the api call

#     :param item: item requested if any
#     :param quantity: how many items requested if applicable
#     :param serviceProfile: list of items and corresponding service type and department and request status
#     :param userInput: transcription
#     """

#     ticket = {
#               "ticket": {
#                   "requests": [
#                       {
#                           "roomNumber": roomNumber,
#                           "robotVer": "chimeInternal_DRAFT",
#                           "createBy": "205154476688",

#                         "dept": serviceProfile[item]['Department'],  

#                           "service": "Supplies",
#                         #   "service": serviceProfile[item]['Service Type'],  

#                           "subCategory": item, 
#                           "quantity": quantity,
#                           "requestTime": str(datetime.datetime.now(datetime.UTC)),

#                           "status": "Default", 
#                         #   "status": serviceProfile[item]['Bot Action'],  

#                           "input": userInput,
#                           "callIdFull": "99033d55-e034-4e8e-b6fb-d6b17fc122f6",
#                           "callStatus": "answer",
#                           "callback": "no",
#                           "confirmTime": str(confirmTime),
#                           "botNumber": "+16782030501"
#                       }
#                   ]
#               }
#           }
#     logger.info(f"{ticket = }")
#     return ticket
#     # api_response = call_api_endpoint(ticket)
#     # logger.info(f"{api_response = }")
#     # return json.dumps(api_response)

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

    try:
        phoneNumber = event['sessionAttributes']['hotel_phone_number']
    except:
        phoneNumber = '+16782030501'

    try:
        roomNumber=event['sessionAttributes']['room_number']
    except:
        roomNumber = '505'

    api_response = get_request_ticket_api(
        userInput=params['userInput'],
        phoneNumber=phoneNumber,
        confirmTime=params['confirmTime'],
        roomNumber=roomNumber)
    logger.info(f"{api_response = }")

    # ticket = create_ticket(item = params['itemOrService'], roomNumber = params['roomNumber'], confirmTime = params['confirmTime'])
    # ticket = create_ticket(item = params['itemOrService'], roomNumber = room_number, confirmTime = params['confirmTime'])
    # api_response = call_api_endpoint(ticket)
    # api_response = get_request_ticket_api(userInput: str, phoneNumber: str, confirmTime:str, roomNumber:str)
    # logger.info(f"{api_response = }")

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


    # logger.info(f"{agent = }\n{actionGroup = }\n{function = }\n")

    # session_state = {
    #      'sessionAttributes': {
    #         'hotel_phone_number': hotel_number,
    #         'room_number': room_number,
    #         'hotel_info' : json.dumps(hotel_info)
    #     }
    # }

    #event = {'function': 'create_ticket_fn', 'parameters': [{'name': 'itemOrService', 'type': 'string', 'value': 'towel'}, {'name': 'roomNumber', 'type': 'string', 'value': 'ROOM#'}, {'name': 'confirmTime', 'type': 'string', 'value': '2024_07_24_10_00_00'}, {'name': 'userInput', 'type': 'string', 'value': 'I need a towel'}], 'sessionAttributes': {'hotel_phone_number': '+16782030501', 'room_number': '123', 'hotel_info': '{"timezone": "America/New_York", "fd_hour": "Cycle", "fd_start_time": "07:00 AM", "fd_end_time": "07:00 PM", "eng_hour": "Cycle", "eng_request_time": "tomorrow_08:00 AM", "eng_start_time": "08:00 AM", "eng_end_time": "04:00 PM", "transfer_fo": "+16784336186", "address": "2401 Bass Pro Drive", "name": "Embassy Suites by Hilton - DFW Airport North", "city": "Grapevine", "class": "0"}'}, 'promptSessionAttributes': {}, 'inputText': 'right now', 'sessionId': '205154476688851', 'agent': {'name': 'single-agent', 'version': '6', 'id': 'HYCYYD7WKC', 'alias': 'GVSY6FZPVJ'}, 'actionGroup': 'request_item_service_ticket_api', 'messageVersion': '1.0'}

    
    #hotel_number = event.get('hotel_phone_number', '+16782030501')
    #room_number = event.get('room_number', '10001')