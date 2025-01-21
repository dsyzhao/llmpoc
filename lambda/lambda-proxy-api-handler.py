import boto3
import json
import os
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
from collections import OrderedDict

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    # Configure boto3 client with retries and parameter validation
    config = Config(
        retries = dict(
            max_attempts = 2,
            mode = 'adaptive'
        ),
        parameter_validation = True,  # Enable parameter validation
        connect_timeout = 5,  # Connection timeout in seconds
        read_timeout = 30    # Read timeout in seconds
    )
    
    lex_client = boto3.client('lexv2-runtime', config=config)
    logger.info("Starting proxy Lambda")
    
    try:
        print(event)
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing request body'})
            }
            
        # Extract required parameters
        bot_id = body.get('botId', os.getenv('BOT_ID'))
        bot_alias_id = body.get('botAliasId', os.getenv('BOT_ALIAS_ID'))
        locale_id = body.get('localeId', os.getenv('LOCALE_ID'))
        session_id = body.get('sessionId', 'default-session')
        text_input = body.get('text')
        
        # Extract session attributes
        phone_number = body.get('phone_number', '')
        room_number = body.get('room_number', '')
        hotel_info = body.get('hotel_info', '')
        
        # Get hotel information map from request
        hotel_info_map = body.get('hotel_info_map', {})
        
        # Get hotel-specific information if phone number is provided
        hotel_details = hotel_info_map.get(phone_number, {})
        
        # Create OrderedDict with desired attribute order
        session_attributes = OrderedDict([
            ("phone_number", phone_number),
            ("room_number", room_number),
            ("hotel_info", hotel_info)
        ])
        
        # Add hotel-specific details if available, maintaining order
        if hotel_details:
            hotel_specific_attrs = OrderedDict([
                ("hotel_name", hotel_details.get("name", "")),
                ("hotel_city", hotel_details.get("city", "")),
                ("hotel_timezone", hotel_details.get("timezone", "")),
                ("hotel_address", hotel_details.get("address", "")),
                ("transfer_fo", hotel_details.get("transfer_fo", "")),
                ("fd_hours", f"{hotel_details.get('fd_start_time', '')} - {hotel_details.get('fd_end_time', '')}"),
                ("eng_hours", f"{hotel_details.get('eng_start_time', '')} - {hotel_details.get('eng_end_time', '')}")
            ])
            session_attributes.update(hotel_specific_attrs)

        logger.info(f"Calling Lex: botId={bot_id}, botAliasId={bot_alias_id}, localeId={locale_id}, "
                    f"sessionId={session_id}, text={text_input}")
        logger.info(f"Session attributes (ordered): {json.dumps(session_attributes)}")

        try:
            response = lex_client.recognize_text(
                botId="CLKLPPZYND",#bot_id,
                botAliasId="PTTNQEDRVR",#bot_alias_id,
                localeId=locale_id,
                sessionId=session_id,
                text=text_input,
                sessionState={
                    "sessionAttributes": session_attributes
                }
            )
            
            logger.info(f"Lex response: {json.dumps(response)}")

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response)
            }
            
        except ClientError as e:
            logger.error(f"Error calling Lex: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Error communicating with Lex',
                    'details': str(e)
                })
            }
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        } 