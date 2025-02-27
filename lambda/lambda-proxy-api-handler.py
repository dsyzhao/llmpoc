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
            
        # Extract required parameters from environment variables or request body
        bot_id = body.get('botId', os.getenv('BOT_ID'))
        bot_alias_id = body.get('botAliasId', os.getenv('BOT_ALIAS_ID'))
        locale_id = body.get('localeId', os.getenv('LOCALE_ID'))
        session_id = body.get('sessionId', 'default-session')
        text_input = body.get('text')
        
        # Log the bot IDs we're using
        logger.info(f"Using bot_id: {bot_id}, bot_alias_id: {bot_alias_id}")
        
        if not bot_id or not bot_alias_id:
            logger.error("Missing bot_id or bot_alias_id. Check environment variables.")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Missing Lex bot configuration'})
            }
        
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
            ("room_number", room_number)
        ])

        logger.info(f"Calling Lex: botId={bot_id}, botAliasId={bot_alias_id}, localeId={locale_id}, "
                    f"sessionId={session_id}, text={text_input}")
        logger.info(f"Session attributes (ordered): {json.dumps(session_attributes)}")

        # Add at the beginning of the handler function
        logger.info(f"Lambda environment variables: BOT_ID={os.getenv('BOT_ID')}, BOT_ALIAS_ID={os.getenv('BOT_ALIAS_ID')}")

        try:
            response = lex_client.recognize_text(
                botId=bot_id,
                botAliasId=bot_alias_id,
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
            error_message = str(e)
            logger.error(f"Error calling Lex: {error_message}")
            
            # Log the ARN being accessed for debugging
            arn = f"arn:aws:lex:{lex_client.meta.region_name}:{context.invoked_function_arn.split(':')[4]}:bot-alias/{bot_id}/{bot_alias_id}"
            logger.error(f"Attempted to access Lex bot ARN: {arn}")
            
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Error communicating with Lex',
                    'details': error_message,
                    'attempted_arn': arn
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