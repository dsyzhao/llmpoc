import json
import boto3
import urllib3
import datetime
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session(region_name=os.environ.get('REGION', 'us-east-1'))
bedrock_client = session.client('bedrock-runtime')

def get_item(userInput: str, items: str):
    """from the provided user request choose the right category for name of the requested service items. 

    :param userInput: transcription
    """

    MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

    system = [
        {
            "text": f"""
            From the provided user request, choose the correct category for the requested service items and their respective quantities.

            <guidelines>
            - First, look for an exact match.
            - If no exact match is found, look for a semantically similar category.
            - The output **must** be a **valid JSON array** containing objects formatted as follows:
            
            ```json
            [
                {{"item": "selected category", "quantity": "requested quantity"}}
            ]
            ```

            - Ensure the JSON is **properly formatted**, with:
            - No extra text, explanations, or preambles.
            - No additional brackets or newline artifacts.
            - A single JSON array containing only the selected items.
            </guidelines> 
            
            Example Output:
            **User Request:** "I need one blanket and two towels for room 851 at 10 AM tomorrow."  
            **Correct JSON Response:**
            ```json
            [
                {{"item": "Blanket", "quantity": "1"}},
                {{"item": "Bath Towel", "quantity": "1"}},
                {{"item": "Air Conditioner", "quantity": "1"}}
            ]

            Here are the possible category options: {items}
            """
        }
    ]





    logger.info(f"{system = }")

    # Your user prompt
    messages = [
        {"role": "user", "content": [{"text":userInput}]},
    ]

    # Configure the inference parameters.
    inf_params = {"maxTokens": 1000, "topP": 0.9, "temperature": 0.0}

    model_response = bedrock_client.converse(
        modelId=MODEL_ID, messages=messages, system=system, inferenceConfig=inf_params
    )

    print(f"{model_response = }")
    return model_response["output"]["message"]["content"][0]['text']


def call_api_endpoint(ticket_data):
    orderUrl = "http://54.175.83.87:33480/robot/order/create"
    http = urllib3.PoolManager(num_pools=1, headers={'Content-Type': 'application/json'})
    dataJson = json.dumps(ticket_data)
    resp = http.request('POST', orderUrl, body=dataJson, timeout=30, retries=5)
    result = json.loads(resp.data)
    return result

def get_request_ticket_api(item, serviceProfile, quantity, userInput, roomNumber, deliveryTime):
    """Generate payload for the api call

    :param item: item requested if any
    :param quantity: how many items requested if applicable
    :param serviceProfile: list of items and corresponding service type and department and request status
    :param userInput: transcription
    """

    ticket = {
              "ticket": {
                  "requests": [
                      {
                          "roomNumber": roomNumber,
                          "robotVer": "chimeInternal_DRAFT",
                          "createBy": "205154476688",
                          "dept": serviceProfile[item]['Department'],  
                          "service": serviceProfile[item]['Service Type'],  
                          "subCategory": item, 
                          "quantity": quantity,
                          "requestTime": str(datetime.datetime.now(datetime.UTC)),
                          "status": serviceProfile[item]['Bot Action'],  
                          "input": userInput,
                          "callIdFull": "99033d55-e034-4e8e-b6fb-d6b17fc122f6",
                          "callStatus": "answer",
                          "callback": "no",
                          "confirmTime": deliveryTime,
                          "botNumber": "+16782030501"
                      }
                  ]
              }
          }
    logger.info(f"{ticket = }")
    api_response = call_api_endpoint(ticket)
    logger.info(f"{api_response = }")
    return json.dumps(api_response)

def s3_retrieve(hotel_number, bucket_name):
    s3_client = boto3.client('s3')
    
    service_info_path = f'{hotel_number}serviceInfo.json'
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=service_info_path)
        data = response['Body'].read().decode('utf-8')
        data = json.loads(data)
        return data
        # available_items = [k for k, v in data.items() if v['Avaliable'] == 'Yes']
        # return available_items
    except Exception as e:
        logger.error(f"Error occurred while retrieving {service_info_path}: {e}")
        return {}

def lambda_handler(event, context):
    logger.info(f"{event = }")
    
    phone_number = event['phoneNumber']
    bucket = os.environ.get('BUCKET', 'us-east-1') # 'botconfig205154476688v2'
    json_service_info = s3_retrieve(phone_number, bucket)
    # available_items = [k for k, v in data.items() if v['Avaliable'] == 'Yes']
    logger.info(f"{json_service_info = }")
    items = json_service_info.keys()

    extracted_items = get_item(event["userInput"], ', '.join(items))
    logger.info(f"{extracted_items = }")
    item_quantity = json.loads(extracted_items)
    logger.info(f"{item_quantity = }")

    for i in range(len(item_quantity)):
        get_request_ticket_api(
            item_quantity[i]['item'], 
            json_service_info, 
            item_quantity[i]['quantity'], 
            event["userInput"], 
            event['roomNumber'], 
            event['confirmTime']
            )
    return True