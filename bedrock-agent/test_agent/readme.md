# Agent Testing Documentation

## Overview
This code provides a framework for testing Amazon Bedrock Agents by executing queries, measuring performance, and storing execution traces. It allows users to test agents with different queries, manage session states, and analyze response latency.

## Main Components

### 1. Process Response Function
```python
def process_response(query, session_state, trial_id, query_id, resp)
```
Processes the response from an agent's invoke_model API call.

**Parameters:**
- `query`: User query string
- `session_state`: Dictionary containing session state
- `trial_id`: Integer identifying the trial
- `query_id`: Integer identifying the query within a conversation
- `resp`: JSON response from the invokeModel API

**Returns:** Agent answer, execution time, JSON trace, and invocation ID

### 2. Add File to Session State Function
```python
def add_file_to_session_state(local_file_name, file_url, use_case, session_state)
```
Adds files to the session state for CHAT or CODE_INTERPRETER capabilities.

**Parameters:**
- `local_file_name`: Local file path
- `file_url`: S3 URL for the file
- `use_case`: Either "CHAT" or "CODE_INTERPRETER"
- `session_state`: Current session state dictionary

### 3. Invoke Agent Helper Function
```python
def invoke_agent_helper(query, trial_id, query_id, session_id, agent_id, alias_id, memory_id, session_state, end_session)
```
Supports agent invocation with specified parameters.

### 4. Test Query Function
```python
def test_query(show_code_use, queries_list, agent_id, alias_id, number_trials, memory_id, session_id, session_state, file_prefix, sleep_time)
```
Main testing function that executes queries and records results.

## Key Features

1. **File Handling**
   - Supports multiple file types (CSV, XLS, XLSX)
   - Handles both local files and S3 URLs

2. **Session Management**
   - Maintains session state across queries
   - Supports session continuation with memory_id

3. **Performance Tracking**
   - Records execution time for each query
   - Stores detailed traces in JSON format
   - Generates performance summaries in Excel format

4. **Output Management**
   - Creates organized output directory structure
   - Saves traces and summaries with timestamps
   - Supports custom file prefixes

## Usage

Run the script using command line arguments:
```bash
python script.py --test_file test.json --agent_id AGENT_ID --agent_alias_id ALIAS_ID
```

For example,

Run the script using command line arguments:
```bash
python3 test_agent.py --test_file "test1.json" --agent_id "HYCYYD7WKC" --agent_alias_id "7MIUBN4U6T" --memory_id "123" --session_id "123"
```

Required parameters:
- `test_file`: JSON file containing test queries
- `agent_id`: Bedrock agent ID
- `agent_alias_id`: Agent alias ID

Optional parameters:
- `region`: AWS region (default: us-east-1)
- `number_trials`: Number of test iterations
- `sleep_time`: Delay between queries
- `memory_id`: Memory ID for conversation continuation
- `session_id`: Session ID for conversation continuation
- `output`: Output directory path

## Important Notes
- Requires appropriate AWS credentials and permissions
- JSON test file must follow the expected format
- Supports both single-query and multi-query conversations
- Handles error cases and provides detailed logging

### Important Note on Session Management
⚠️ To prevent data leakage between different test runs and ensure clean test environments:
- The `memory_id` and `session_id` should be updated with unique values for each new test run
- You can either:
  - Generate new UUIDs for each run
  - Use timestamp-based IDs
  - Use incremental numbers
- Reusing the same `memory_id` or `session_id` across different test runs may result in:
  - Contaminated test results
  - Unexpected agent behavior
  - Carried-over context from previous conversations
