import json
import boto3
import urllib3
import datetime
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session(region_name='us-east-1')
bedrock_client = session.client('bedrock-runtime')
# MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
MODEL_ID = "amazon.nova-micro-v1:0"

def get_info(userInput: str, hotelAddress: str):
    system = [
        {
            "text" : f"""
    You are a Hotel Local Advisor. The user asked: "{userInput}".
    Respond to the use with recommendation around the address: {hotelAddress}.
    Give top 3 places. Make your recommendations short and concise.
    Provide the name of the business, address and distance to the address.
    Give only distinct recommendations, do not repeat.
    """          
        }
    ]

    # Your user prompt
    messages = [
        {"role": "user", "content": [{"text":userInput}]},
    ]

    # Configure the inference parameters.
    inf_params = {"maxTokens": 300, "topP": 0.9, "temperature": 0.0}

    model_response = bedrock_client.converse(
        modelId=MODEL_ID, messages=messages, system=system, inferenceConfig=inf_params,
        # performanceConfig={'latency': 'optimized'} # error
    
    )

    logger.info(f"{model_response = }")
    return model_response["output"]["message"]["content"][0]['text']

def populate_function_response(event, response_body):
    return {'response': {'actionGroup': event['actionGroup'], 'function': event['function'],
                'functionResponse': {'responseBody': {'TEXT': {'body': str(response_body)}}}}}

def lambda_handler(event, context):
    logger.info(f"{event = }")

    # userInput = event.get("inputText", "Recommend me good restaraunts or fast-food places nearby")
    userInput = event["inputText"]
    try:
        hotel_info = json.loads(event['sessionAttributes']['hotel_info'])

        hotel_address = hotel_info['address']
        hotel_city = hotel_info['city']

        logger.info(f"Hotel address from event.sessionAttributes.hotel_info: {hotel_address = } {hotel_city = }")
    except:
        hotel_address, hotel_city = "2401 Bass Pro Drive", "Grapevine"
        logger.info(f"Fallback to default hotel address {hotel_address = } {hotel_city = }")
    hotelAddress = hotel_address + ', ' + hotel_city

    logger.info(f"{userInput = } {hotelAddress = }")
    result = get_info(userInput, hotelAddress)
    logger.info(f"{result = }")

    response = populate_function_response(event, result)
    logger.info(f"{response = }")

    return response


    # logger.info(f"{type(event) = }")

    # logger.info(f"{event['sessionAttributes'] = }")
    # logger.info(f"{type(event['sessionAttributes']) = }")

    # logger.info(f"{event['sessionAttributes']['hotel_info'] = }")
    # logger.info(f"{type(event['sessionAttributes']['hotel_info']) = }")

    # agent = event['agent']
    # actionGroup = event['actionGroup']
    # function = event['function']
    # parameters = event.get('parameters', [])

# event = {'messageVersion': '1.0', 
# 'function': 'get_info', 
# 'sessionId': '205154476688820', 
# 'agent': {'name': 'single-agent', 'version': '5', 'id': 'HYCYYD7WKC', 'alias': 'AAVMKJAUHH'}, 
# 'actionGroup': 'get_info', 
# 'sessionAttributes': {'hotel_phone_number': '+16782030501', 'room_number': '123', 
# 'hotel_info': '{"timezone": "America/New_York", "fd_hour": "Cycle", "fd_start_time": "07:00 AM", "fd_end_time": "07:00 PM", "eng_hour": "Cycle", 
# "eng_request_time": "tomorrow_08:00 AM", "eng_start_time": "08:00 AM", "eng_end_time": "04:00 PM", "transfer_fo": "+16784336186", 
# "address": "2401 Bass Pro Drive", 
# "name": "Embassy Suites by Hilton - DFW Airport North", "city": "Grapevine", "class": "0"}'}, 
# 'promptSessionAttributes': {}, 
# 'inputText': 'recommend me good fast food places nearby'}



    # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
    # responseBody =  {
    #     "TEXT": {
    #         "body": "The function {} was called successfully!".format(function),
    #         # "body": bedrock_response
    #         "bedrock_response": bedrock_response
    #     }
    # }

    # action_response = {
    #     'actionGroup': actionGroup,
    #     'function': function,
    #     'functionResponse': {
    #         'responseBody': responseBody
    #         # 'responseBody': bedrock_response
    #     }

    # }

    #dummy_function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    #print("Response: {}".format(dummy_function_response))


    #return dummy_function_response
