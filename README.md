## Project Structure

```
├── bin/
│   └── app.ts                 # CDK app entry point
├── config/
│   ├── env-config.json        # AWS/CDK Environment configuration
│   ├── lex-bot-guest-chat-config.json # Lex bot configuration
│   └── orchestration-prompt.txt # Bedrock agent prompts
├── lambda/
│   ├── lambda-ticket-api-call.py
│   ├── lambda-fulfillment-handler.py
│   ├── lambda-create-ticket.py
│   ├── lambda-local-area-info.py
│   ├── lambda-proxy-api-handler.py
│   └── readme.md .............# Lambda documentation
├── lib/
│   ├── bedrock-agent-stack.ts # Bedrock agent infrastructure
│   └── guest-fulfillment-stack.ts # Guest fulfillment 
├── cdk.json                 # CDK configuration
├── tsconfig.json           # TypeScript configuration
├── package.json            # Project dependencies
```

## Resource Naming Convention

All resources follow the naming convention:
`{application}-{environment}-stk-{resource-type}-{purpose}`

Example:
- `hvt-dev-stk-bedrock-agent-guest-care`
- `hvt-dev-stk-lambda-fulfillment-handler`
- `hvt-dev-stk-lex-bot-guest-fulfillment`

The application name ('hvt') and environment ('dev') are configured in `config/env-config.json`:
```json
{
  "application": "hvt",
  "environments": {
    "dev": {
      "account": "205154476688",
      "region": "us-east-1",
      "environment": "dev"
    }...
```
This allows easy deployment to different environments by modifying these values.

## Prerequisites

- Node.js and npm installed
- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Setup

# Configure AWS CLI with SSO

1. Run the following command to configure `aws configure sso`
2. Url: `https://changethis.awsapps.com/start/#`
3. Region: `us-east-1`
4. Profile Name: `hvt-dev`
5. Select your account
6. Test: `aws s3 ls  --profile hvt-dev`

# Login process

1. `aws --profile hvt-dev sso login`

# Install AWS Cli and ssm-session-manager-plugin

1. Download the AWS CLI installer

    https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html#getting-started-install-instructions

# CDK Deployment Process

1. Install dependencies:
```bash
npm install
```

2. Bootstrap CDK (first time only):
```bash
cdk bootstrap --profile hvt-dev
```

3. Synthesize the CloudFormation template:
```bash
cdk synth --profile hvt-dev
```

4. Review changes before deployment:
```bash
cdk diff --profile hvt-dev
```
Always run `cdk diff` before deploying to review what changes will be made to your infrastructure.

5. Deploy the stack:
```bash
cdk deploy --profile hvt-dev
```

Note: You should always run `cdk diff` before `cdk deploy` to review the changes that will be made to your infrastructure. This is a crucial step to prevent unintended changes.