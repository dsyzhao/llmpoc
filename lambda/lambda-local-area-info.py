import json
import boto3
import urllib3
import datetime
import logging
import time
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session(region_name=os.environ.get('REGION', 'us-east-1'))
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