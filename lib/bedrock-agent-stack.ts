import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { CfnAgent, CfnAgentAlias, CfnGuardrail } from 'aws-cdk-lib/aws-bedrock';
import * as fs from 'fs';
import * as path from 'path';
import * as cr from 'aws-cdk-lib/custom-resources';

interface BedrockAgentStackProps extends cdk.StackProps {
  environment: string;
  applicationName: string;
}

export class BedrockAgentStack extends cdk.Stack {
  // Add public properties to expose resources to other stacks
  public readonly agentId: string;
  public readonly agentAliasId: string;
  
  constructor(scope: Construct, id: string, props: BedrockAgentStackProps) {
    super(scope, id, props);

    // Agent configuration (moved from config file)
    const agentConfig = {
      description: "Hotel Front Desk Agent helping guests with their requests",
      instruction: "You are a friendly and helpful AI assistant designed to assist hotel guests with their requests and questions. You will receive three types of inputs: 1. Handling Item or Service Requests. 2. Answer guest inquiries about nearby restaurants, tourist attractions, or local services. 3. request to talk to the front desk",
      foundationModel: "arn:aws:bedrock:us-east-1:205154476688:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0",
      memoryTime: 30,
      actionGroups: {
        ticketBooking: {
          name: "TicketBookingManagerActionGroup",
          description: "Action group to manage ticket booking for item/service request. It allows you to create tickets."
        },
        localAdvisor: {
          name: "LocalAdvisorActionGroup",
          description: "Action group to manage request for info or recommendation about hotel suroundings or local attractions such as restaurant."
        },
        transferToFrontDesk: {
          name: "TransferToFrontDeskActionGroup",
          description: "Action group to transfer the call to front desk if the user asked for"
        }
      }
    };

    // Read orchestration prompt from file
    const promptFilePath = path.join(__dirname, '..', 'config', 'orchestration-prompt.txt');
    const orchestrationPrompt = fs.readFileSync(promptFilePath, 'utf8');

    // Create Lambda functions first
    const ticketFunction = new lambda.Function(this, 'CreateTicket', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-create-ticket`,
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(180),
      handler: 'lambda-create-ticket.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-create-ticket.py']
      }),
      role: new iam.Role(this, 'CreateTicketLambdaRole', {
        roleName: `${props.applicationName}-${props.environment}-stk-iam-role-create-ticket-lambda`,
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
        ]
      })
    });

    const ticketApiCall = new lambda.Function(this, 'CallAPI', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-ticket-api-call`,
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(180),
      handler: 'lambda-ticket-api-call.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-ticket-api-call.py']
      }),
      role: new iam.Role(this, 'TicketApiCallLambdaRole', {
        roleName: `${props.applicationName}-${props.environment}-stk-iam-role-ticket-api-call-lambda`,
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
        ]
      })
    });

    const localAreaInfoFunction = new lambda.Function(this, 'LocalAreaInfo', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-local-area-info`,
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(180),
      handler: 'lambda-local-area-info.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-local-area-info.py']
      }),
      role: new iam.Role(this, 'LocalAreaInfoLambdaRole', {
        roleName: `${props.applicationName}-${props.environment}-stk-iam-role-local-area-info-lambda`,
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
        ]
      })
    });

    // Add resource-based policy statements to allow Bedrock to invoke the Lambda functions
    new lambda.CfnPermission(this, 'BedrockInvokeTicketFunction', {
      action: 'lambda:InvokeFunction',
      functionName: ticketFunction.functionName,
      principal: 'bedrock.amazonaws.com',
      sourceAccount: this.account
    });

    new lambda.CfnPermission(this, 'BedrockInvokeLocalAreaInfoFunction', {
      action: 'lambda:InvokeFunction',
      functionName: localAreaInfoFunction.functionName,
      principal: 'bedrock.amazonaws.com',
      sourceAccount: this.account
    });

    // Then create the IAM role with references to the Lambda functions
    const agentRole = new iam.Role(this, 'BedrockAgentRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      roleName: `${props.applicationName}-${props.environment}-stk-iam-role-bedrock-agent`,
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess')
      ]
    });

    // Now you can reference the Lambda functions in the policy
    agentRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: [
        ticketFunction.functionArn,
        localAreaInfoFunction.functionArn
      ]
    }));

    // Update local-area-info Lambda Bedrock permissions to specific models
    agentRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream'
      ],
      resources: [
        // Allow access to Claude model in all available sonnet v2 regions for cross-region inference feature
        `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`,
        `arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`,
        `arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`,
        // Add Haiku model permissions for all available regions
        `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0`,
        `arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0`,
        `arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0`,
        // Add Nova Micro model permissions for all available regions
        `arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0`,
        `arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-micro-v1:0`,
        `arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-micro-v1:0`,
        // Allow access to inference profiles in all sonnet v2 regions for cross-region inference feature
        `arn:aws:bedrock:us-east-1:${this.account}:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0`,
        `arn:aws:bedrock:us-east-2:${this.account}:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0`,
        `arn:aws:bedrock:us-west-2:${this.account}:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0`,
        // Add Haiku inference profiles for all regions
        `arn:aws:bedrock:us-east-1:${this.account}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0`,
        `arn:aws:bedrock:us-east-2:${this.account}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0`,
        `arn:aws:bedrock:us-west-2:${this.account}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0`,
        // Add Nova Micro inference profiles for all regions
        `arn:aws:bedrock:us-east-1:${this.account}:inference-profile/us.amazon.nova-micro-v1:0`,
        `arn:aws:bedrock:us-east-2:${this.account}:inference-profile/us.amazon.nova-micro-v1:0`,
        `arn:aws:bedrock:us-west-2:${this.account}:inference-profile/us.amazon.nova-micro-v1:0`
      ]
    }));

    // Create guardrail for the agent
    const guardrail = new CfnGuardrail(this, 'HotelGuardrail', {
      name: `${props.applicationName}-${props.environment}-stk-bedrock-guardrail`,
      description: "guardrails for hotel chatbot",
      topicPolicyConfig: {
        topicsConfig: [
          {
            name: 'Inappropriate Services',
            definition: "Requests for adult services or inappropriate entertainment",
            examples: [
              "Are there any adult-only venues nearby?",
              "Can you arrange an escort service for me?",
              "Can you help me find ladies for entertainment?"
            ],
            type: 'DENY'
          }
        ]
      },
      contentPolicyConfig: {
        filtersConfig: [
          {
            type: "SEXUAL",
            inputStrength: "HIGH",
            outputStrength: "HIGH"
          },
          {
            type: "VIOLENCE",
            inputStrength: "HIGH",
            outputStrength: "HIGH"
          },
          {
            type: "HATE",
            inputStrength: "HIGH",
            outputStrength: "HIGH"
          },
          {
            type: "INSULTS",
            inputStrength: "HIGH",
            outputStrength: "HIGH"
          },
          {
            type: "MISCONDUCT",
            inputStrength: "HIGH",
            outputStrength: "HIGH"
          },
          {
            type: "PROMPT_ATTACK",
            inputStrength: "HIGH",
            outputStrength: "NONE"
          }
        ]
      },
      wordPolicyConfig: {
        wordsConfig: [
          {
            text: 'adult services'
          },
          {
            text: 'escort'
          }
        ],
        managedWordListsConfig: [
          {
            type: 'PROFANITY'
          }
        ]
      },
      blockedInputMessaging: "Sorry, I cannot answer this question.",
      blockedOutputsMessaging: "Sorry, I cannot answer this question."
    });

    // Create the Bedrock agent with action groups defined inline
    const agent = new CfnAgent(this, 'HotelFrontDeskAgent', {
      agentName: `${props.applicationName}-${props.environment}-stk-bedrock-agent-guest-care`,
      agentResourceRoleArn: agentRole.roleArn,
      description: agentConfig.description,
      idleSessionTtlInSeconds: 1800,
      foundationModel: agentConfig.foundationModel,
      instruction: agentConfig.instruction,
      customerEncryptionKeyArn: undefined,
      guardrailConfiguration: {
        guardrailIdentifier: guardrail.attrGuardrailId,
        guardrailVersion: 'DRAFT'
      },
      autoPrepare: true,
      promptOverrideConfiguration: {
        promptConfigurations: [
          {
            basePromptTemplate: orchestrationPrompt,
            inferenceConfiguration: {
              maximumLength: 300,
              stopSequences: [
                '</invoke>',
                '</answer>',
                '</error>'
              ],
              temperature: 0,
              topK: 250,
              topP: 1
            },
            parserMode: 'DEFAULT',
            promptCreationMode: 'OVERRIDDEN',
            promptState: 'ENABLED',
            promptType: 'ORCHESTRATION'
          }
        ]
      },
      // Define action groups directly in the agent configuration
      actionGroups: [
        // Ticket booking action group
        {
          actionGroupName: agentConfig.actionGroups.ticketBooking.name,
          actionGroupExecutor: {
            lambda: ticketFunction.functionArn
          },
          description: agentConfig.actionGroups.ticketBooking.description,
          functionSchema: {
            functions: [
              {
                name: "request_ticket_api_tool",
                description: "use this action group to create request ticket for item and/or service",
                parameters: {
                  userInput: {
                    type: "string",
                    description: "The user request (transcription)",
                    required: true
                  },
                  confirmTime: {
                    type: "string",
                    description: "The preferred delivery time for the request.",
                    required: true
                  }
                }
              }
            ]
          }
        },
        // Local advisor action group
        {
          actionGroupName: agentConfig.actionGroups.localAdvisor.name,
          actionGroupExecutor: {
            lambda: localAreaInfoFunction.functionArn
          },
          description: agentConfig.actionGroups.localAdvisor.description,
          functionSchema: {
            functions: [
              {
                name: "get_info_tool",
                description: "use this action group to answer questions about local area attraction near the hotel",
                parameters: {
                  userInput: {
                    type: "string",
                    description: "The user request (transcription)",
                    required: true
                  }
                }
              }
            ]
          }
        },
        // Transfer to front desk action group
        {
          actionGroupName: agentConfig.actionGroups.transferToFrontDesk.name,
          actionGroupExecutor: {
            customControl: 'RETURN_CONTROL'
          },
          description: agentConfig.actionGroups.transferToFrontDesk.description,
          functionSchema: {
            functions: [
              {
                name: "transfer_to_front_desk",
                description: "Action group to transfer the call to front desk if the user asked for",
                parameters: {}
              }
            ]
          }
        }
      ]
    });

    // Add memory configuration using addPropertyOverride
    agent.addPropertyOverride('MemoryConfiguration', {
      EnabledMemoryTypes: ["SESSION_SUMMARY"],
      StorageDays: agentConfig.memoryTime
    });

    // Add Lambda invoke permissions for the create-ticket Lambda
    ticketFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['lambda:InvokeFunction'],
        resources: [ticketApiCall.functionArn]
      })
    );

    // Add S3 read permissions for the ticket-api-call Lambda
    ticketApiCall.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject'],
        resources: [`arn:aws:s3:::botconfig${this.account}v2/*`]
      })
    );

    // Update local-area-info Lambda Bedrock permissions to specific models
    localAreaInfoFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel', 'bedrock:Converse'],
        resources: [
          // Specific models used in the Lambda
          `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0`,
          `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-micro-v1:0`
        ]
      })
    );

    // Create the agent alias with a consistent name
    const agentAlias = new CfnAgentAlias(this, 'HotelFrontDeskAgentAlias', {
      agentId: agent.attrAgentId,
      agentAliasName: `${props.environment}-alias`,
      description: `${props.environment} alias for Hotel Front Desk Agent`
    });

    // Add dependency directly on the agent
    agentAlias.node.addDependency(agent);

    // Store the agent ID and alias ID for reference by other stacks
    this.agentId = agent.attrAgentId;
    this.agentAliasId = agentAlias.attrAgentAliasId;

    // Outputs
    new cdk.CfnOutput(this, 'AgentId', {
      value: agent.attrAgentId,
      description: 'Bedrock Agent ID'
    });

    new cdk.CfnOutput(this, 'AgentAliasId', {
      value: agentAlias.attrAgentAliasId,
      description: 'Bedrock Agent Alias ID'
    });

    new cdk.CfnOutput(this, 'GuardrailId', {
      value: guardrail.attrGuardrailId,
      description: 'Bedrock Guardrail ID'
    });

    // Add new outputs for Lambda functions
    new cdk.CfnOutput(this, 'CreateTicketLambdaArn', {
      value: ticketFunction.functionArn,
      description: 'Create Ticket Lambda Function ARN'
    });

    new cdk.CfnOutput(this, 'LocalAreaInfoLambdaArn', {
      value: localAreaInfoFunction.functionArn,
      description: 'Local Area Info Lambda Function ARN'
    });
  }
} 