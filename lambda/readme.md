# Hotel Service Virtual Assistant

## Overview
This AWS Lambda-based application serves as a virtual assistant for hotel services, leveraging Amazon Bedrock for natural language processing and interaction. The system handles guest inquiries, manages service requests, and coordinates with different hotel departments based on availability and operating hours.

## Key Features
- Natural language processing using Amazon Bedrock
- Real-time service availability checking
- Hotel-specific configuration management
- Time zone-aware operations
- Front desk transfer capabilities
- Department-specific service routing

## Technical Architecture

### Core Components
1. **AWS Lambda Handler**
   - Entry point for processing all requests
   - Manages session state and conversation flow
   - Handles transcription validation and response generation

2. **Bedrock Agent Integration**
   - Processes natural language queries
   - Generates contextual responses
   - Manages conversation flow and intent recognition

3. **S3-based Configuration**
   - Stores hotel-specific information
   - Manages service availability data
   - Maintains department operating hours

### Key Functions

#### `invoke_agent_helper()`
- Manages communication with Bedrock agent
- Processes response streams
- Handles front desk transfer scenarios

```python
"""
Invokes the Bedrock agent with the given parameters and handles the response stream.

Args:
   query (str): The input text query to send to the agent
   session_id (str): Unique identifier for the session
   agent_id (str): The ID of the Bedrock agent
   alias_id (str): The alias ID of the Bedrock agent
   enable_trace (bool, optional): Whether to enable tracing. Defaults to False
   memory_id (str, optional): ID for memory persistence. Defaults to None
   session_state (dict, optional): State information for the session. Defaults to None
   end_session (bool, optional): Whether to end the session. Defaults to False

Returns:
   tuple: (agent_answer, action_type) where agent_answer is the response text and 
         action_type indicates if a transfer to front desk is needed
    """
```

#### `items_availability()`
- Retrieves and processes service availability from S3
- Categorizes items by department
- Maintains cache for performance optimization

```python
"""
Retrieves and processes item availability information from S3 for a specific hotel.

Args:
   hotel_number (str): The hotel's phone number or identifier

Returns:
   tuple: Contains three elements:
      - list: Unavailable items
      - list: Available items
      - dict: Items grouped by department
"""
```

#### `get_hotel_info_from_s3()`
- Fetches hotel-specific configuration
- Provides fallback defaults
- Implements caching for efficiency

```python
"""
Retrieves hotel information from S3 bucket for a given hotel number.

Args:
   hotel_number (str): The hotel's phone number or identifier

Returns:
   dict: Hotel information including timezone, operating hours, and contact details.
         Returns default values if S3 retrieval fails
"""
```

#### `get_current_timestamp()`
- Handles timezone-specific time calculations
- Formats timestamps for logging and operations
```python
    """
    Gets the current timestamp in a specified timezone.

    Args:
        timezone (str): The timezone to use for the timestamp

    Returns:
        str: Formatted timestamp string in the format "YYYY_MM_DD_HH_MM_SS"
    """
```

#### `lambda_handler()`

```python
"""
Main AWS Lambda handler function that processes incoming requests and generates responses.

Args:
   event (dict): The incoming event data from AWS Lambda
   context (object): AWS Lambda context object

Returns:
   dict: Response containing the session state, messages, and other relevant information
         for the conversation flow
    """
```

## Configuration

### Hotel Information Structure
```json
{
    "timezone": "America/New_York",
    "fd_hour": "Cycle",
    "fd_start_time": "07:00 AM",
    "fd_end_time": "07:00 PM",
    "eng_hour": "Cycle",
    "eng_start_time": "08:00 AM",
    "eng_end_time": "04:00 PM",
    ...
}
```

### Service Classification
Hotels are classified into three categories:
- Luxury & Upper Upscale (class: 0)
- Upscale & Upper Midscale (class: 1)
- Midscale & Economy (class: 2)

## Important Notes
1. **Caching Implementation**
   - Uses LRU cache for hotel information and item availability
   - Cache size limited to 128 entries
   - Optimizes performance for repeated requests

2. **Error Handling**
   - Implements fallback mechanisms for S3 retrieval failures
   - Handles empty transcriptions
   - Manages timezone conversion errors

3. **Session Management**
   - Maintains session state across interactions
   - Stores hotel-specific attributes
   - Tracks conversation context

## Dependencies
- boto3
- datetime
- zoneinfo
- uuid
- json
- logging

## Environment Setup
1. AWS credentials configuration
2. S3 bucket setup with appropriate permissions
3. Bedrock agent configuration
4. Proper IAM roles and policies

## Usage
The Lambda function expects events containing:
- Hotel number/phone number
- Room number
- Transcription data (for voice interactions)
- Session information
























# Hotel Local Advisor Service

## Overview
The Hotel Local Advisor Service is an AWS Lambda-based application that provides personalized local recommendations to hotel guests. Using Amazon Bedrock's AI capabilities, it generates contextual suggestions for restaurants, attractions, and other points of interest near the hotel's location.

## Features
- Location-based recommendations
- AI-powered responses using Amazon Bedrock
- Customized suggestions based on user queries
- Concise and structured recommendations including business names, addresses, and distances
- Seamless integration with hotel information systems

## Technical Architecture

### Core Components

1. **Amazon Bedrock Integration**
   - Uses `amazon.nova-micro-v1:0` model
   - Provides natural language understanding and generation
   - Configured for optimal recommendation generation

2. **AWS Lambda Function**
   - Processes incoming requests
   - Handles hotel information management
   - Formats and structures responses

3. **Logging System**
   - Comprehensive logging for monitoring and debugging
   - Tracks request/response flow
   - Records system states and errors

### Key Functions

#### `get_info(userInput: str, hotelAddress: str)`
- Communicates with Amazon Bedrock
- Generates contextual recommendations
- Parameters:
  - `userInput`: User's query or request
  - `hotelAddress`: Reference location for recommendations
- Returns AI-generated recommendations with:
  - Business names
  - Addresses
  - Distances from hotel

```python
"""
Generates location-based recommendations using Amazon Bedrock's AI model.

Args:
    userInput (str): The user's query or request for recommendations
    hotelAddress (str): The hotel's address to use as a reference point

Returns:
    str: AI-generated response containing top 3 recommended places with their names,
            addresses, and distances from the hotel

Note:
    Uses amazon.nova-micro-v1:0 model to generate concise, location-specific recommendations
"""
system = [
    {
        "text" : f"""
You are a Hotel Local Advisor. The user asked: "{userInput}".
Respond to the use with recommendation around the address: {hotelAddress}.
Give top 3 places. Make your recommendations short and concise.
Provide the name of the business, address and distance to the address.
Give only distinct recommendations, do not repeat.
"""     
```

#### `populate_function_response(event, response_body)`
- Structures the response format
- Maintains consistency in response format
- Integrates with Lambda function requirements

```python
"""
Formats the response according to the required structure for the Lambda function.

Args:
    event (dict): The incoming event data containing actionGroup and function information
    response_body (str): The response content to be formatted

Returns:
    dict: Structured response containing the action group, function, and formatted response body
"""
```

#### `lambda_handler(event, context)`
- Main entry point for the service
- Processes incoming requests
- Manages hotel information
- Coordinates recommendation generation

```python
"""
Main AWS Lambda handler function that processes incoming requests for local recommendations.

Args:
    event (dict): The incoming event data containing:
        - inputText: User's query
        - sessionAttributes: Contains hotel information (optional)
    context (object): AWS Lambda context object

Returns:
    dict: Formatted response containing recommendations based on the user's query
            and hotel location

Note:
    If hotel information is not provided in sessionAttributes, uses default values
    for Grapevine location
"""
```

## Configuration

### Model Configuration
```python
MODEL_ID = "amazon.nova-micro-v1:0"
inf_params = {
    "maxTokens": 300,
    "topP": 0.9,
    "temperature": 0.0
}
```

### Default Location
```python
default_address = "2401 Bass Pro Drive"
default_city = "Grapevine"
```

## Input/Output Format

### Input Event Structure
```json
{
    "inputText": "user query",
    "sessionAttributes": {
        "hotel_info": {
            "address": "hotel address",
            "city": "hotel city"
        }
    }
}
```

### Output Response Structure
```json
{
    "response": {
        "actionGroup": "action_group_name",
        "function": "function_name",
        "functionResponse": {
            "responseBody": {
                "TEXT": {
                    "body": "formatted recommendations"
                }
            }
        }
    }
}
```

## Important Notes

1. **Error Handling**
   - Fallback mechanism for missing hotel information
   - Robust logging for debugging
   - Graceful error management

2. **Response Format**
   - Consistent structure
   - Concise recommendations
   - Limited to top 3 places
   - Includes essential business information

3. **Performance**
   - Optimized token usage
   - Efficient response generation
   - Minimal latency

## Dependencies
- boto3
- json
- logging
- datetime
- urllib3

## Setup Requirements
1. AWS account with appropriate permissions
2. Amazon Bedrock access
3. AWS Lambda configuration
4. Proper IAM roles and policies

## Usage Example
```python
event = {
    "inputText": "Find me nearby restaurants",
    "sessionAttributes": {
        "hotel_info": json.dumps({
            "address": "123 Main St",
            "city": "Example City"
        })
    }
}
```

























# Hotel Service Ticket Management System

## Overview
This AWS Lambda-based application manages the creation and processing of hotel service tickets. It serves as a bridge between guest requests and the hotel's service management system, providing automated ticket creation and management capabilities.

## Features
- Automated ticket creation
- Asynchronous request processing
- Robust error handling
- Performance monitoring
- Integration with external API endpoints
- Session management

## Technical Architecture

### Core Components

1. **AWS Lambda Function**
   - Processes incoming service requests
   - Manages ticket creation workflow
   - Handles session attributes
   - Monitors performance metrics

2. **External API Integration**
   - Communicates with ticket management system
   - Implements retry logic
   - Handles timeout scenarios

3. **Logging System**
   - Comprehensive request/response logging
   - Performance metrics tracking
   - Error tracking and debugging support

### Key Functions

#### `call_api_endpoint(ticket_data)`
- Makes HTTP POST requests to external ticket system
- Features:
  - Configurable timeout (30 seconds)
  - Retry mechanism (5 attempts)
  - JSON payload handling
  - Error handling

```python
"""
Makes a POST request to create a ticket order through an external API endpoint.

Args:
    ticket_data (dict): The ticket information to be sent to the API

Returns:
    dict: The JSON response from the API endpoint

Note:
    - Uses urllib3 for HTTP requests
    - Includes retry logic (5 attempts)
    - 30-second timeout for requests
"""
```

#### `get_request_ticket_api(userInput, phoneNumber, confirmTime, roomNumber)`
- Creates service tickets via Lambda function
- Handles:
  - Asynchronous ticket creation
  - Payload formatting
  - Response management
  - Logging

```python
"""
Creates a request ticket by invoking an AWS Lambda function asynchronously.

Args:
    userInput (str): The user's transcribed request or message
    phoneNumber (str): Contact phone number for the ticket
    confirmTime (str): The time for the request confirmation
    roomNumber (str): The hotel room number

Returns:
    str: Confirmation message indicating ticket creation status

Note:
    Uses asynchronous Lambda invocation (Event type)
    Logs the payload for debugging purposes
    """
```

#### `lambda_handler(event, context)`
- Main entry point for the service
- Processes:
  - Request validation
  - Parameter extraction
  - Session management
  - Response formatting

```python
"""
Main AWS Lambda handler function that processes incoming requests and creates service tickets.

Args:
    event (dict): The incoming event data containing:
        - agent: Agent information
        - actionGroup: Action group identifier
        - function: Function name
        - parameters: List of parameter dictionaries
        - sessionAttributes: Session information (optional)
    context (object): AWS Lambda context object

Returns:
    dict: Response containing:
        - Action response details
        - Message version
        - Function execution status

Note:
    - Includes performance monitoring (execution time logging)
    - Has fallback values for phone and room numbers
    - Formats response according to required structure
"""
```

## Configuration

### AWS Configuration
```python
region_name = 'us-east-1'
lambda_function_name = "hotel-help-desk-assistant-api-us-east-1-205154476688"
```

### API Configuration
```python
orderUrl = "http://54.175.83.87:33480/robot/order/create"
timeout = 30
retries = 5
```

## Input/Output Format

### Input Event Structure
```json
{
    "agent": "agent_info",
    "actionGroup": "action_group_id",
    "function": "function_name",
    "parameters": [
        {
            "name": "parameter_name",
            "value": "parameter_value"
        }
    ],
    "sessionAttributes": {
        "hotel_phone_number": "phone_number",
        "room_number": "room_number"
    }
}
```

### Output Response Structure
```json
{
    "response": {
        "actionGroup": "action_group_id",
        "function": "function_name",
        "functionResponse": {
            "responseBody": {
                "TEXT": {
                    "body": "success_message"
                }
            }
        }
    },
    "messageVersion": "version_number"
}
```

## Important Notes

1. **Error Handling**
   - Fallback values for missing session attributes
   - API request retry logic
   - Comprehensive error logging

2. **Performance Monitoring**
   - Execution time tracking
   - API response monitoring
   - Resource usage logging

3. **Security**
   - Session attribute validation
   - API endpoint security
   - AWS IAM role management

## Dependencies
- boto3
- urllib3
- json
- logging
- datetime
- time

## Setup Requirements
1. AWS account with appropriate permissions
2. Configured AWS Lambda environment
3. Access to external API endpoint
4. Proper IAM roles and policies

## Best Practices
1. Monitor API response times
2. Review error logs regularly
3. Maintain fallback mechanisms
4. Update security configurations
5. Monitor resource usage


























# AI-Powered Hotel Service Request Processor

## Overview
This system provides an intelligent service request handling solution for hotels, leveraging AWS services and AI to process guest requests, identify required items, and create service tickets automatically. The system uses Amazon Bedrock's Claude 3 Haiku model for natural language understanding and integrates with external ticket management systems.
 
## Features
- AI-powered request analysis
- Automatic item categorization
- Multi-item request handling
- Hotel-specific service configuration
- Automated ticket creation
- Comprehensive logging

## Technical Architecture

### Core Components

1. **AI Request Analyzer**
   - Uses Claude 3 Haiku model
   - Processes natural language requests
   - Identifies items and quantities
   - Matches against available services

2. **Configuration Management**
   - S3-based configuration storage
   - Hotel-specific service profiles
   - Dynamic service catalog

3. **Ticket Management**
   - External API integration
   - Automated ticket creation
   - Request status tracking
   - Multiple item handling

### Key Functions

#### `get_item(userInput, items)`
- Analyzes user requests using AI
- Features:
  - Natural language processing
  - Exact and semantic matching
  - Structured JSON output
  - Multiple item identification

```python
"""
Analyzes user requests using AI to identify and categorize requested service items.

Args:
    userInput (str): The user's transcribed request or message
    items (str): Comma-separated list of available service items/categories

Returns:
    str: JSON-formatted string containing identified items and their quantities
    Format: [{"item": "category_name", "quantity": "requested_quantity"}]

Note:
    - Uses Claude 3 Haiku model for analysis
    - Implements exact and semantic matching
    - Returns properly formatted JSON array
    - Handles multiple item requests
"""
```

#### `s3_retrieve(hotel_number)`
- Manages hotel configurations
- Features:
  - Dynamic configuration retrieval
  - Error handling
  - Hotel-specific service catalogs

```python
"""
Retrieves hotel service configuration from S3 bucket.

Args:
    hotel_number (str): Hotel identifier (typically phone number)
    bucket_name (str, optional): S3 bucket name. Defaults to 'botconfig205154476688v2'

Returns:
    dict: Hotel service configuration data
          Empty dict if retrieval fails

Note:
    - Handles S3 access errors
    - Logs retrieval issues
"""
```

#### `get_request_ticket_api()`
- Creates service tickets
- Features:
  - Department routing
  - Service categorization
  - Request tracking
  - Delivery scheduling

```python
"""
Generates and submits service ticket requests to external API.

Args:
    item (str): Requested service item name
    serviceProfile (dict): Service configuration details
    quantity (str): Number of items requested
    userInput (str): Original user request
    roomNumber (str): Hotel room number
    deliveryTime (str): Requested delivery time

Returns:
    str: JSON string containing API response

Note:
    - Formats request according to service profile
    - Includes metadata like department and service type
    - Handles request status and callback settings
"""
```

#### `call_api_endpoint()`
- Handles external API communication
- Features:
  - Reliable HTTP requests
  - Retry mechanism
  - Timeout handling
  - Response validation

```python
"""
Makes HTTP POST request to create service tickets in external system.

Args:
    ticket_data (dict): Complete ticket information including all request details

Returns:
    dict: API response containing ticket creation status

Note:
    - 30 second timeout
    - 5 retry attempts
    - JSON content type
"""
```

#### `lambda_handler(event, context)`

```python
"""
Main AWS Lambda handler for processing service item requests.

Args:
    event (dict): Event data containing:
        - phoneNumber: Hotel identifier
        - userInput: User's request
        - roomNumber: Room number
        - confirmTime: Delivery time
    context (object): Lambda context object

Returns:
    bool: True if processing successful

Note:
    - Coordinates entire request workflow
    - Handles multiple item requests
    - Creates separate tickets for each item
"""
```

## Configuration

### AI Model Configuration
```python
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
inf_params = {
    "maxTokens": 1000,
    "topP": 0.9,
    "temperature": 0.0
}
```

### API Configuration
```python
orderUrl = "http://54.175.83.87:33480/robot/order/create"
timeout = 30
retries = 5
```

## Input/Output Format

### Input Event Structure
```json
{
    "phoneNumber": "hotel_identifier",
    "userInput": "guest_request",
    "roomNumber": "room_number",
    "confirmTime": "delivery_time"
}
```

### Service Item Response Format
```json
[
    {
        "item": "service_category",
        "quantity": "requested_quantity"
    }
]
```

## Important Notes

1. **AI Processing**
   - Prioritizes exact matches
   - Falls back to semantic matching
   - Handles multiple items
   - Maintains formatting standards

2. **Error Handling**
   - S3 retrieval failures
   - API communication issues
   - Invalid request formats
   - Configuration errors

3. **Performance**
   - Optimized AI token usage
   - Efficient request processing
   - Reliable ticket creation

## Dependencies
- boto3
- urllib3
- json
- datetime
- logging

## Setup Requirements
1. AWS account with appropriate permissions
2. S3 bucket for configuration storage
3. Access to Amazon Bedrock
4. External API endpoint access

## Best Practices
1. Regular configuration updates
2. Monitor AI response quality
3. Track API performance
4. Maintain error logs
5. Update service catalogs

## Service Configuration Structure
```json
{
    "item_name": {
        "Department": "department_name",
        "Service Type": "service_category",
        "Bot Action": "action_type"
    }
}
```
