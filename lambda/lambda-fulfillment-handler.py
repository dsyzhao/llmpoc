import os
import boto3
from multi_agent_orchestrator.classifiers import BedrockClassifier, BedrockClassifierOptions
from multi_agent_orchestrator.orchestrator import MultiAgentOrchestrator, OrchestratorConfig
from multi_agent_orchestrator.agents import BedrockLLMAgent, BedrockLLMAgentOptions, AgentResponse
from multi_agent_orchestrator.classifiers import ClassifierResult
from multi_agent_orchestrator.types import ConversationMessage
import asyncio, uuid
import datetime
import random

# model_name = 'anthropic.claude-3-sonnet-20240229-v1:0'
model_name = "anthropic.claude-3-5-sonnet-20241022-v2:0"
region_name='us-east-1'
inference_config={
        'maxTokens': 500,
        'temperature': 0,
        'topP': 0.9
    }

bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)

#classifier = BedrockClassifier(BedrockClassifierOptions(
#    model_id=model_name,
#    region=region_name,
#    inference_config=inference_config,
#    client=bedrock_client
#))
order_item_service_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
name='Hotel Service Desk Assistant',
description='An AI assistant that help hotel guests with placing order for their requested items or service in the hotel ticketing system',
client=bedrock_client
))

print(f"{order_item_service_agent.prompt_template = }")

get_info_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
name='Hotel Local Advisor',
description='An AI assistant that help hotel guests with their question about hotel surrounding such as nearby restaurant or tourist attractions and etc.',
client=bedrock_client
))

# greeting_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
# name='Hotel Greeting Agent',
# description='An AI assistant that welcome users, respond to greetings, and provide assistance in navigating the available agents',
# client=bedrock_client
# ))

#orchestrator = MultiAgentOrchestrator(classifier=classifier)
orchestrator = MultiAgentOrchestrator()
orchestrator.add_agent(order_item_service_agent)
orchestrator.add_agent(get_info_agent)


agents = orchestrator.get_all_agents()
agent_list = "\n\n".join([
    f"{index + 1}. **{agent['name']}**: {agent['description']}"
    for index, agent in enumerate(agents.values())
])

GREETING_AGENT_PROMPT = """
You are a friendly and helpful greeting agent. Your primary roles are to welcome users, respond to greetings, and provide assistance in navigating the available agents. Always maintain a warm and professional tone in your interactions.

Core responsibilities:
- Respond warmly to greetings such as "hello", "hi", or similar phrases.
- Provide helpful information when users ask for "help" or guidance.
- Introduce users to the range of specialized agents available to assist them.
- Guide users on how to interact with different agents based on their needs.

When greeting or helping users:
1. Start with a warm welcome or acknowledgment of their greeting.
2. Briefly explain your role as a greeting and help agent.
3. Introduce the list of available agents and their specialties.
4. Encourage the user to ask questions or specify their needs for appropriate agent routing.

Available Agents:
{agentList}

Remember to:
- Be concise yet informative in your responses.
- Tailor your language to be accessible to users of all technical levels.
- Encourage users to be specific about their needs for better assistance.
- Maintain a positive and supportive tone throughout the interaction.

Always respond in markdown format, using the following guidelines:
- Use ## for main headings and ### for subheadings if needed.
- Use bullet points (-) for lists.
- Use **bold** for emphasis on important points or agent names.
- Use *italic* for subtle emphasis or additional details.

By following these guidelines, you'll provide a warm, informative, and well-structured greeting that helps users understand and access the various agents available to them.
""".format(agentList=agent_list)

# print(GREETING_AGENT_PROMPT)

# greeting_agent.set_system_prompt(GREETING_AGENT_PROMPT)
# orchestrator.add_agent(greeting_agent)

async def async_handler(event, context):
    print(event)
    USER_ID = str(uuid.uuid4())
    SESSION_ID = str(uuid.uuid4())
    
    transcription = event['transcriptions'][0].get('transcription', None)
    classifier_result = await orchestrator.classifier.classify(transcription, chat_history="")
    print(classifier_result.selected_agent.name)
    
    response:AgentResponse = await orchestrator.route_request(transcription, USER_ID, SESSION_ID)

    # Print metadata
    print("\nMetadata:")
    print(f"Selected Agent: {response.metadata.agent_name}")
    # Handle regular response
    if isinstance(response.output, str):
        print(response.output)
    elif isinstance(response.output, ConversationMessage):
        print(response.output.content[0].get('text'))
    
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
            "content": response.output.content[0].get('text')
        }]
    }

def lambda_handler(event, context):
    return asyncio.run(async_handler(event, context))