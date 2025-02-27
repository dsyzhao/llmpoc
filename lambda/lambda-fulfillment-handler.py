import logging
import boto3
import uuid
import pprint
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import lru_cache
import os


logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

session = boto3.Session(region_name=os.environ.get('REGION', 'us-east-1'))
bedrock_agent_client = session.client('bedrock-agent')
bedrock_agent_runtime_client = session.client('bedrock-agent-runtime')


def invoke_agent_helper(query, session_id, agent_id, alias_id, enable_trace=False, memory_id=None, session_state=None, end_session=False):
    if not session_state:
        session_state = {}

    agent_response = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        enableTrace=enable_trace,
        endSession=end_session,
        memoryId=memory_id,
        sessionState=session_state
    )

    if enable_trace:
        logger.info(pprint.pprint(agent_response))
    print(f"{agent_response = }")
    event_stream = agent_response['completion']
    try:
        for event in event_stream:
            print(event)
            if 'chunk' in event:
                data = event['chunk']['bytes']
                if enable_trace:
                    logger.info(f"Final answer ->\n{data.decode('utf8')}")
                agent_answer = data.decode('utf8')
                return agent_answer, ''
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                if enable_trace:
                    logger.info(json.dumps(event['trace'], indent=2))
            elif 'returnControl' in event:
                response_with_roc_allowed = bedrock_agent_runtime_client.invoke_agent(
                    agentId=agent_id,
                    agentAliasId=alias_id, 
                    sessionId=session_id,
                    enableTrace=enable_trace, 
                    endSession=end_session,
                    memoryId=memory_id,
                    sessionState={
                        'invocationId': event["returnControl"]["invocationId"],
                        'returnControlInvocationResults': [{
                                'functionResult': {
                                    'actionGroup': event["returnControl"]["invocationInputs"][0]["functionInvocationInput"]["actionGroup"],
                                    'function': event["returnControl"]["invocationInputs"][0]["functionInvocationInput"]["function"],
                                    #'confirmationState': 'CONFIRM',
                                    'responseBody': {
                                        "TEXT": {
                                            'body': ''
                                        }
                                    }
                                }
                        }]}
                )
                event_stream = response_with_roc_allowed['completion']
                for response_event in event_stream:
                    if 'chunk' in response_event:
                        data = response_event['chunk']['bytes']
                        if enable_trace:
                            logger.info(f"Final answer ->\n{data.decode('utf8')}")
                        agent_answer = data.decode('utf8')
                        return agent_answer, 'transferFD'
                    elif 'trace' in response_event:
                        if enable_trace:
                            logger.info(json.dumps(response_event['trace'], indent=2))
                    else:
                        raise Exception("unexpected event.", response_event)
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)

@lru_cache(maxsize=128)
def items_availability(hotel_number: str):
    s3_client = boto3.client('s3')
    bucket_name = os.environ.get('BUCKET', 'botconfig205154476688v2') # 'botconfig205154476688v2'
    file_path = f'{hotel_number}serviceInfo.json'
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
        data = response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Error occurred while retrieving {file_path}: {e}")
        data = "{}"

    data = json.loads(data)
    unavailable_items = [k for k, v in data.items() if v['Avaliable'] == 'No']
    available_items = [k for k, v in data.items() if v['Avaliable'] == 'Yes']

    logger.info(f"{unavailable_items = }")
    logger.info(f"{available_items = }")


    dept_items = {} # {'Engineering': ['Ipod Docking Station', 'Laptop Charger', 'USB Charger Hub', 'USB Plug', ...
    for item, details in data.items():
        department = details.get('Department')
        if details['Avaliable'] == 'Yes':
            if department not in dept_items:
                dept_items[department] = []
            dept_items[department].append(item)
    dept_items = {k:', '.join(v) for k,v in dept_items.items()}
    logger.info(f"{dept_items = }")

    return unavailable_items, available_items, dept_items

@lru_cache(maxsize=128)
def get_hotel_info_from_s3(hotel_number: str):
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('BUCKET', 'botconfig205154476688v2') # 'botconfig205154476688v2'
        file_path = 'hotel_number.json'

        response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
        data = response['Body'].read().decode('utf-8')
        data = json.loads(data)

        hotel_info = data[hotel_number]
        print(f"HOTEL INFO FROM S3: {hotel_info = }")
    except:
        hotel_info = {
                "timezone": "America/New_York",
                "fd_hour": "Cycle",
                "fd_start_time": "07:00 AM",
                "fd_end_time": "07:00 PM",
                "eng_hour": "Cycle",
                "eng_request_time": "tomorrow_08:00 AM",
                "eng_start_time": "08:00 AM",
                "eng_end_time": "04:00 PM",
                "transfer_fo": "+16784336186",
                "address": "2401 Bass Pro Drive",
                "name": "Embassy Suites by Hilton - DFW Airport North",
                "city": "Grapevine",
                "class": "0"}
        print(f"HOTEL INFO FROM S3 FAILED")
    return hotel_info


def response_to_empty_transcription(event):
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": event["sessionState"]["intent"]["name"],
                "state": "Fulfilled"
            }
        },
        "messages": [{
            "contentType": "PlainText",
            "content": "Would you repeat what you just said?"
        }]
    }


def get_current_timestamp(timezone):
    utc_now = datetime.now(ZoneInfo("UTC"))
    try:
        local_time = utc_now.astimezone(ZoneInfo(timezone))
    except Exception as e:
        # local_time = utc_now.astimezone(ZoneInfo("America/New_York"))
        local_time = utc_now
        logger.error(f"Wrong timezone {e = }")
    formatted_time = local_time.strftime("%Y_%m_%d_%H_%M_%S")
    return formatted_time


def lambda_handler(event, context):

    #event = {'SchemaVersion': '1.0', 'Sequence': 3, 'InvocationEventType': 'ACTION_FAILED', 'ActionData': {'Type': 'CallAndBridge', 'Parameters': {'Endpoints': [{'BridgeEndpointType': 'AWS', 'Uri': '7000', 'Arn': 'arn:aws:chime:us-east-1:353485474178:vc/exmpb1pkojv3qkmdlebcym'}], 'CallTimeoutSeconds': 30, 'CallerIdNumber': '+17578277310', 'RingbackTone': {'Type': 'S3', 'BucketName': 'callandbridgestack-wavfiles205154476688', 'Key': 'ringback.wav'}, 'CallId': '644941c9-1a4c-46d6-bac4-4d7d81ede904'}, 'ErrorType': 'InvalidActionParameter', 'ErrorMessage': 'Resource does not belong to the current AWS account'}, 'CallDetails': {'TransactionId': 'a133b1e9-91bc-425c-8488-5cca5342bee6', 'AwsAccountId': '205154476688', 'AwsRegion': 'us-east-1', 'SipRuleId': '66023a6f-c28b-445f-97de-17bd382ee59a', 'SipMediaApplicationId': '20274012-cc85-41e4-afce-ae7913e56f7f', 'Participants': [{'CallId': '644941c9-1a4c-46d6-bac4-4d7d81ede904', 'ParticipantTag': 'LEG-A', 'To': '+16782030501', 'From': '+17578277310', 'Direction': 'Inbound', 'StartTimeInMilliseconds': '1740033373130', 'Status': 'Connected'}], 'TransactionAttributes': {'serviceCallType': 'TransferFD', 'fakeConfirmedItems': '', 'confirmedItems': ''}}}
    print("LEX EVENT: -----", event)

    if 'InvocationEventType' in event and event['InvocationEventType'] == 'ACTION_FAILED' and event['CallDetails']['TransactionAttributes']['serviceCallType'] == 'TransferFD':
        query = 'Front Desk is not available!create a front desk callback request ticket for the user'
        intent_name = "FallbackIntent"
    
    elif 'transcriptions' in event:
        query = event['transcriptions'][0].get('transcription', None)
        intent_name = event["sessionState"]["intent"]["name"]

        # Guardrail clauses for empty transcription
        if not query:
            return response_to_empty_transcription(event)
        elif len(query.strip()) == 0:
            return response_to_empty_transcription(event)

    agent_id = os.environ.get('AGENT_ID', 'QPUIAGLFMO')
    agent_alias_id = os.environ.get('AGENT_ALIAS_ID', 'FN2KWQFPLG')

    if 'phone_number' in event:
        hotel_number = event["phone_number"]
    else:
        hotel_number = '+16782030501' # for test purpose

    if 'room_number' in event:
        room_number = event["room_number"]
    else:
        room_number = '123' # for test purpose
    logger.info(f"Default {hotel_number = }  {room_number = }")

    hotel_info = get_hotel_info_from_s3(hotel_number)

    hotel_class = hotel_info["class"]
    time_zone = hotel_info["timezone"]
    fd_start_time = hotel_info["fd_start_time"]
    fd_end_time = hotel_info["fd_end_time"]
    eng_start_time = hotel_info["eng_start_time"]
    eng_end_time = hotel_info["eng_end_time"]

    if hotel_class == '0':
        hotel_tone = "Luxury & Upper Upscale" 
    elif hotel_class == '1':
        hotel_tone = "Upscale & Upper Midscale"
    else:
        hotel_tone = "Midscale & Economy"
    
    unavailable_items, available_items, dept_items = items_availability(hotel_number)
    current_datetime = get_current_timestamp(hotel_info['timezone'])

    ## create a random id for session initiator id
    session_id:str = event.get('sessionId', str(uuid.uuid4()))
    memory_id:str = room_number # 'room123'
    enable_trace:bool = False
    end_session:bool = False
    session_state = {
         'sessionAttributes': {
            'hotel_phone_number': hotel_number,
            'room_number': room_number,
            'hotel_info' : json.dumps(hotel_info)
        },
        'promptSessionAttributes': {
            'hotel_tone' : hotel_tone,
            'current_datetime': current_datetime,
            'fd_start_time' : fd_start_time,
            'fd_end_time' : fd_end_time,
            'eng_start_time' : eng_start_time,
            'eng_end_time': eng_end_time,
            'unavailable_items': ', '.join(unavailable_items),
            'available_items' : ', '.join(available_items),
            'dept_items' : json.dumps(dept_items)
        }
    }
    logger.info(f"{session_state = }")
    
    start_time = time.time()
    contents, action_group = invoke_agent_helper(query, session_id, agent_id, agent_alias_id, enable_trace=enable_trace, memory_id=memory_id, session_state=session_state)
    print (f"{contents = }")
    print (f"{action_group = }")

    print("--- %s seconds for agent to finish creating response ---" % (time.time() - start_time))

    if action_group == 'transferFD':
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": intent_name,
                    "state": "Fulfilled"
                },
                "sessionAttributes" : {
                    "serviceType" : "TransferFD"
                }
            },
            "messages": [{
                "contentType": "PlainText",
                "content": contents
            }],
            "sessionId": event["sessionId"]
        }

    else:
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": intent_name,
                    "state": "Fulfilled"
                }
            },
            "messages": [{
                "contentType": "PlainText",
                "content": contents
            }]
        }
