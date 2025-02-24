import boto3
import asyncio, uuid
import logging
import json
import sys
from multi_agent_orchestrator.storage import DynamoDbChatStorage
from multi_agent_orchestrator.orchestrator import MultiAgentOrchestrator, OrchestratorConfig
from multi_agent_orchestrator.types import ConversationMessage
from multi_agent_orchestrator.utils import AgentTools, AgentTool
from multi_agent_orchestrator.agents import BedrockLLMAgent, BedrockLLMAgentOptions, AgentResponse, SupervisorAgent, SupervisorAgentOptions
from multi_agent_orchestrator.classifiers import ClassifierResult, BedrockClassifier, BedrockClassifierOptions
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

model_id_supervisor = ["amazon.nova-pro-v1:0"]

model_id_workers = ["anthropic.claude-3-haiku-20240307-v1:0"]

region_name='us-east-1'
table_name = 'agent_history'

inference_config={
        'maxTokens': 100,
        'temperature': 0,
        'topP': 0.9
    }

session = boto3.Session(region_name=region_name)
bedrock_client = session.client('bedrock-runtime')
lambda_client = session.client('lambda')

memory_storage = DynamoDbChatStorage(
            table_name=table_name,
            region=region_name
        )

def get_request_ticket_api(userInput: str) -> str:
    """receive userinput and create request ticket by invoking lambda funciton

    :param userInput: transcription
    :param serviceProfile: list of items and services in a hotel
    """

    payload = json.dumps({"userInput": userInput})

    response = lambda_client.invoke(
        FunctionName="create_ticket",
        InvocationType='Event',
        LogType='None',
        Payload=payload)

    logger.info(response)
    
    logger.info(payload)
    return "ticket is created successfully"

api_tool = AgentTool(
    name="request_ticket_api_tool",
    description="receive userinput and invoke lambda function to create request ticket",
    properties = {
        "userInput": {
            "type": "string",
            "description": "The user request (transcription)"
        }
    },
    required=["userInput"],
    func=get_request_ticket_api
    
)

tools = AgentTools([api_tool])

service_request_ticket_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
    name='Hotel Service Request Ticket Assistant',
    description="""You are an AI assistant specialized in creating service request tickets for hotel guests.""",
    client=bedrock_client,
    tool_config={
        'tool': tools,
        'toolMaxRecursions': 5,  
    },
    model_id=model_id_workers[0],
    save_chat= True
    ))

get_info_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
    name='Hotel Local Advisor',
    description='An AI assistant that helps hotel guests with their question about hotel surrounding such as nearby restaurant or tourist attractions and etc.',
    client=bedrock_client,
    model_id=model_id_workers[0],
    save_chat= True
    ))

"""You are an AI assistant that leads coordination of support inquirie from a hotel guest. 
            You should always maintain a professional tone in your interactions with the user throughtout the conversation.
            your final respinse to the user should always be similar to this:
            - Your request for the item is successfully placed. Is there any thing else I can help you with please?
            """

supervisor = SupervisorAgent(SupervisorAgentOptions(
    lead_agent=BedrockLLMAgent(BedrockLLMAgentOptions(
        name="Support Team Lead",
        model_id=model_id_supervisor[0],
        inference_config = inference_config,
        description=f"""You are an AI assistant that coordinates hotel guest support inquiries by delegating tasks to specialized agents. 
                    - You must not assume or use any of your knowledge and always use the provided information
                    - Service/item requests are already fulfilled ifpart of the request, you should only handle non-service requests and information queries
                    - You should delegate information requests to the 'Hotel Local Advisor'
                    You should always maintain a professional tone in your interactions with the user throughout the conversation.""",
        client=bedrock_client
    )),
    team=[
        get_info_agent
    ],
    storage=DynamoDbChatStorage(
        table_name=table_name,
        region=region_name
    )
))

custom_bedrock_classifier = BedrockClassifier(BedrockClassifierOptions(
    model_id=model_id_workers[0],
    region=region_name
))

def s3_retrieve(hotel_number, bucket_name = 'botconfig205154476688v2'):
    s3_client = boto3.client('s3')
    
    hotel_hours_path = 'hotel_number.json'
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=hotel_hours_path)
        file_content = response['Body'].read().decode('utf-8')
        hotel_info = json.loads(file_content)[hotel_number]
        #logger.info(f"{hotel_info = }")
    except Exception as e:
        logger.error(f"Error occurred while retrieving {hotel_hours_path}: {e}")
        hotel_info = {}

    return hotel_info

def update_prompts(hotel_info):
    ORDER_ITEM_SERVICE_AGENT_PROMPT = f"""
    You are an AI assisstant that its primary role is to invoke a lambda function to create a ticket for the user requested item.
    Your only response is "Success, ServiceRequestOnly" or "Success, IncludesServiceRequest" or "NoServiceRequest" or "Failure"

    - Use the `request_ticket_api_tool` to create a service request ticket whenever a user requests items or services.
    - Your primary role is to **invoke the ticket API tool** and return a response indicating success or failure.
    - Do not directly handle the request outside the tool. Always use the tool.
    
    Here are the tools you can use:
    <tools>
    request_ticket_api_tool:create a ticket for each guest request.
    </tools>
    """
    service_request_ticket_agent.set_system_prompt(ORDER_ITEM_SERVICE_AGENT_PROMPT)

    GET_INFO_AGENT_PROMPT = f"""
    You are a helpful AI assistant that help hotel guests with their question about hotel surrounding such as nearby restaurant or tourist attractions and etc.
    Your primary role is to answer user question. Provide information in the vicinity of the hotel address located at: {hotel_info['address']}.
    """
    get_info_agent.set_system_prompt(GET_INFO_AGENT_PROMPT)

async def direct_agent_request(agent, user_input: str, user_id: str, session_id: str) -> AgentResponse:
    """
    Direct routing to agent bypassing supervisor for simple requests
    Maintains conversation history in DynamoDB but skips supervisor orchestration
    """
    try:
        # Get existing chat history
        chat_history = await memory_storage.get_chat_history(user_id, session_id)
        
        # Direct call to agent
        start_time = time.time()
        response = await agent.process_request(
            user_input,
            user_id,
            session_id,
            chat_history or []
        )
        print(f"--- Direct agent processing time: {time.time() - start_time} seconds ---")
        
        return response
    except Exception as e:
        logger.error(f"Direct routing failed: {e}")
        # Fallback to supervisor if direct routing fails
        return None

async def get_routing_decision(user_input: str) -> tuple[ClassifierResult, bool]:
    """
    Uses service request agent to classify if request is purely for service.
    Returns tuple of (ClassifierResult, can_bypass_supervisor)
    """
    try:
        # Get classification from service agent
        response = await service_request_ticket_agent.process_request(
            user_input,
            "classifier",  # special user_id for classification
            "classifier",  # special session_id for classification
            []  # empty chat history for clean classification
        )
        
        # Check response
        if response.output.content[0].get('text') == "Success, ServiceRequestOnly":
            return ClassifierResult(
                selected_agent=service_request_ticket_agent,
                confidence=0.95
            ), True
            
        # All other responses go through supervisor
        return ClassifierResult(selected_agent=supervisor, confidence=1.0), False
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        # On any error, default to supervisor
        return ClassifierResult(selected_agent=supervisor, confidence=1.0), False

async def async_handler(_intent_name, _user_input, _orchestrator, _user_id, _session_id):
    start_time = time.time()
    
    try:
        # First call to service agent for classification and potential ticket creation
        initial_response = await service_request_ticket_agent.process_request(
            _user_input,
            _user_id,
            _session_id,
            []  # Start fresh for this request
        )
        
        response_text = initial_response.output.content[0].get('text')
        print(f"Initial agent response: {response_text}")
        
        # Handle each response type specifically
        if response_text == "Success, ServiceRequestOnly":
            # Pure service request - use the response we already have
            print(f"--- Direct service request time: {time.time() - start_time} seconds ---")
            response = initial_response
            
        elif response_text == "Success, IncludesServiceRequest":
            # Mixed request - service part handled, pass context to supervisor
            print("Mixed request - service portion handled, routing to supervisor")
            context_message = (
                "Note: The service/item portion of this request has been successfully "
                "processed and a ticket has been created. Please handle the remaining "
                "information or other requests only."
            )
            enhanced_input = f"{context_message}\nUser request: {_user_input}"
            
            response = await _orchestrator.agent_process_request(
                enhanced_input,
                _user_id,
                _session_id,
                ClassifierResult(selected_agent=supervisor, confidence=1.0)
            )
            
        elif response_text == "NoServiceRequest":
            # Pure information request - route directly to supervisor
            print("Information request - routing to supervisor")
            context_message = (
                "Note: This request has been verified to contain no service/item requests. "
                "Please proceed with handling the information request."
            )
            enhanced_input = f"{context_message}\nUser request: {_user_input}"
            
            response = await _orchestrator.agent_process_request(
                enhanced_input,
                _user_id,
                _session_id,
                ClassifierResult(selected_agent=supervisor, confidence=1.0)
            )
            
        else:  # "Failure" or unexpected response
            # Classification failed - let supervisor handle everything
            print("Classification unclear - routing to supervisor for full processing")
            context_message = (
                "Note: Request classification was unclear. Please analyze the full request "
                "and handle any information queries. If you detect any service/item requests, "
                "note in your response that those should be made as separate requests."
            )
            enhanced_input = f"{context_message}\nUser request: {_user_input}"
            
            response = await _orchestrator.agent_process_request(
                enhanced_input,
                _user_id,
                _session_id,
                ClassifierResult(selected_agent=supervisor, confidence=1.0)
            )
    
    except Exception as e:
        logger.error(f"Handler error: {e}")
        # Fallback to supervisor on any error
        response = await _orchestrator.agent_process_request(
            _user_input, 
            _user_id, 
            _session_id,
            ClassifierResult(selected_agent=supervisor, confidence=1.0)
        )
    
    print(f"--- Total processing time: {time.time() - start_time} seconds ---")
    
    # Print metadata
    logger.info("\nMetadata:")
    logger.info(f"Selected Agent: {response.metadata.agent_name}")
    
    # Handle response
    if isinstance(response.output, str):
        logger.info(response.output)
    elif isinstance(response.output, ConversationMessage):
        logger.info(response.output.content[0].get('text'))

    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": _intent_name,
                "state": "Fulfilled"
            }
        },
        "messages": [{
            "contentType": "PlainText",
            "content": response.output.content[0].get('text')
        }]
    }


def lambda_handler(event, context):

    print("EVENT: -----", event)

    transcription = event['transcriptions'][0].get('transcription', None)
    intent_name = event["sessionState"]["intent"]["name"]

    print("transcription", transcription)

    #session_attributes = event["sessionState"]["sessionAttributes"]
    #{'hotel_city': 'Grapevine', 'eng_hours': '08:00 AM - 04:00 PM', 'hotel_timezone': 'America/New_York', 'room_number': '301', 'transfer_fo': '+16784336186', 'phone_number': '+16782030501', 'hotel_address': '2401 Bass Pro Drive', 'hotel_info': '', 'fd_hours': '07:00 AM - 07:00 PM', 'hotel_name': 'Embassy Suites by Hilton - DFW Airport North'}

    hotel_number = '+16782030501'
    hotel_info = s3_retrieve(hotel_number)
    update_prompts(hotel_info)

    USER_ID = event['sessionId']
    SESSION_ID = hotel_number

    print("USER_ID: -----", USER_ID)
    print("SESSION_ID: -----", SESSION_ID)

    orchestrator = MultiAgentOrchestrator(storage=memory_storage
        )
    
    return asyncio.run(async_handler(intent_name, transcription, orchestrator, USER_ID, SESSION_ID))