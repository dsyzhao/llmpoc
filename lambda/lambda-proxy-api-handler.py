import boto3
import json
import os

def handler(event, context):
    lex_client = boto3.client('lexv2-runtime')

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

    response = lex_client.recognize_text(
        botId=bot_id,
        botAliasId=bot_alias_id,
        localeId=locale_id,
        sessionId=session_id,
        text=text_input
    )

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(response)
    } 