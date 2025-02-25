import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { CfnAgent, CfnAgentAlias, CfnGuardrail } from 'aws-cdk-lib/aws-bedrock';
import * as fs from 'fs';
import * as path from 'path';

interface BedrockAgentStackProps extends cdk.StackProps {
  environment: string;
  applicationName: string;
}

interface CfnAgentActionGroupProps {
  agentId: string;
  agentVersion: string;
  actionGroupName: string;
  actionGroupExecutor: any;
  description: string;
  functionSchema?: any;
}

class CfnAgentActionGroup extends cdk.CfnResource {
  public readonly attrActionGroupId: string;
  
  constructor(scope: Construct, id: string, props: CfnAgentActionGroupProps) {
    super(scope, id, {
      type: 'AWS::Bedrock::AgentActionGroup',
      properties: {
        AgentId: props.agentId,
        AgentVersion: props.agentVersion,
        ActionGroupName: props.actionGroupName,
        ActionGroupExecutor: props.actionGroupExecutor,
        Description: props.description,
        FunctionSchema: props.functionSchema
      }
    });
    
    this.attrActionGroupId = this.getAtt('ActionGroupId').toString();
  }
}

export class BedrockAgentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BedrockAgentStackProps) {
    super(scope, id, props);

    // Agent configuration (moved from config file)
    const agentConfig = {
      description: "Hotel Front Desk Agent helping guests with their requests",
      instruction: "You are a friendly and helpful AI assistant designed to assist hotel guests with their requests and questions. You will receive three types of inputs: 1. Handling Item or Service Requests. 2. Answer guest inquiries about nearby restaurants, tourist attractions, or local services. 3. request to talk to the front desk",
      foundationModel: "anthropic.claude-3-5-sonnet-20241022-v2:0",
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

    // Create the IAM role for the Bedrock agent
    const agentRole = new iam.Role(this, 'BedrockAgentRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      roleName: `${props.applicationName}-${props.environment}-stk-iam-role-bedrock-agent`,
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess')
      ]
    });

    // Add Lambda invoke permissions to the agent role
    agentRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: ['*'] // This should be restricted to specific Lambda functions in production
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

    // Create the Bedrock agent
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
      }
    });

    // Add memory configuration using addPropertyOverride
    agent.addPropertyOverride('MemoryConfiguration', {
      EnabledMemoryTypes: ["SESSION_SUMMARY"],
      StorageDays: agentConfig.memoryTime
    });

    // Reference existing Lambda functions using the naming convention
    const ticketLambda = lambda.Function.fromFunctionArn(
      this, 'TicketLambda', 
      `arn:aws:lambda:${this.region}:${this.account}:function:${props.applicationName}-${props.environment}-stk-lambda-create-ticket`
    );

    const infoLambda = lambda.Function.fromFunctionArn(
      this, 'InfoLambda', 
      `arn:aws:lambda:${this.region}:${this.account}:function:${props.applicationName}-${props.environment}-stk-lambda-local-area-info`
    );

    // Add a dependency to ensure the agent is created before action groups
    const agentCreationDelay = new cdk.CfnWaitCondition(this, 'AgentCreationDelay', {
      count: 1,
      handle: new cdk.CfnWaitConditionHandle(this, 'AgentCreationDelayHandle').ref,
      timeout: '300' // 5 minutes
    });
    agentCreationDelay.node.addDependency(agent);

    // Create ticket booking action group
    const ticketActionGroup = new CfnAgentActionGroup(this, 'TicketBookingActionGroup', {
      agentId: agent.attrAgentId,
      agentVersion: 'DRAFT',
      actionGroupName: agentConfig.actionGroups.ticketBooking.name,
      actionGroupExecutor: {
        lambda: ticketLambda.functionArn
      },
      description: agentConfig.actionGroups.ticketBooking.description,
      functionSchema: {
        functions: [
          {
            name: "request_ticket_api_tool",
            description: "use this action group to create request ticket for item and/or service",
            parameters: {
              type: "OBJECT",
              properties: {
                userInput: {
                  type: "STRING",
                  description: "The user request (transcription)",
                  required: true
                },
                ConfirmTime: {
                  type: "STRING",
                  description: "The preferred delivery time for the request.",
                  required: true
                }
              }
            },
            requireConfirmation: 'ENABLED'
          }
        ]
      }
    });
    ticketActionGroup.node.addDependency(agentCreationDelay);

    // Create local advisor action group
    const infoActionGroup = new CfnAgentActionGroup(this, 'LocalAdvisorActionGroup', {
      agentId: agent.attrAgentId,
      agentVersion: 'DRAFT',
      actionGroupName: agentConfig.actionGroups.localAdvisor.name,
      actionGroupExecutor: {
        lambda: infoLambda.functionArn
      },
      description: agentConfig.actionGroups.localAdvisor.description,
      functionSchema: {
        functions: [
          {
            name: "get_info_tool",
            description: "use this action group to answer questions about local area attraction near the hotel",
            parameters: {
              type: "OBJECT",
              properties: {
                userInput: {
                  type: "STRING",
                  description: "The user request (transcription)",
                  required: true
                }
              }
            }
          }
        ]
      }
    });
    infoActionGroup.node.addDependency(agentCreationDelay);

    // Create transfer to front desk action group
    const transferActionGroup = new CfnAgentActionGroup(this, 'TransferToFrontDeskActionGroup', {
      agentId: agent.attrAgentId,
      agentVersion: 'DRAFT',
      actionGroupName: agentConfig.actionGroups.transferToFrontDesk.name,
      actionGroupExecutor: {
        customControl: 'RETURN_CONTROL'
      },
      description: agentConfig.actionGroups.transferToFrontDesk.description
    });
    transferActionGroup.node.addDependency(agentCreationDelay);

    // Prepare the agent
    const prepareAgent = new cdk.CustomResource(this, 'PrepareAgent', {
      serviceToken: new cdk.custom_resources.Provider(this, 'PrepareAgentProvider', {
        onEventHandler: new lambda.Function(this, 'PrepareAgentFunction', {
          functionName: `${props.applicationName}-${props.environment}-stk-lambda-prepare-agent`,
          runtime: lambda.Runtime.NODEJS_18_X,
          handler: 'index.handler',
          code: lambda.Code.fromInline(`
            const AWS = require('aws-sdk');
            exports.handler = async (event, context) => {
              const bedrockAgent = new AWS.BedrockAgent();
              
              if (event.RequestType === 'Create' || event.RequestType === 'Update') {
                try {
                  await bedrockAgent.prepareAgent({
                    agentId: '${agent.attrAgentId}'
                  }).promise();
                  
                  return {
                    PhysicalResourceId: '${agent.attrAgentId}',
                    Data: { AgentId: '${agent.attrAgentId}' }
                  };
                } catch (error) {
                  console.error('Error preparing agent:', error);
                  throw error;
                }
              }
              
              return {
                PhysicalResourceId: '${agent.attrAgentId}',
                Data: { AgentId: '${agent.attrAgentId}' }
              };
            }
          `),
          timeout: cdk.Duration.minutes(5),
          role: new iam.Role(this, 'PrepareAgentRole', {
            assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
            roleName: `${props.applicationName}-${props.environment}-stk-iam-role-prepare-agent`,
            managedPolicies: [
              iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
            ],
            inlinePolicies: {
              'BedrockAgentAccess': new iam.PolicyDocument({
                statements: [
                  new iam.PolicyStatement({
                    actions: ['bedrock:PrepareAgent'],
                    resources: [`arn:aws:bedrock:${this.region}:${this.account}:agent/${agent.attrAgentId}`]
                  })
                ]
              })
            }
          })
        })
      }).serviceToken,
      properties: {
        AgentId: agent.attrAgentId
      }
    });
    prepareAgent.node.addDependency(ticketActionGroup);
    prepareAgent.node.addDependency(infoActionGroup);
    prepareAgent.node.addDependency(transferActionGroup);

    // Create agent alias
    const agentAlias = new CfnAgentAlias(this, 'HotelFrontDeskAgentAlias', {
      agentId: agent.attrAgentId,
      agentAliasName: `${props.environment}-alias`,
      description: `${props.environment} alias for Hotel Front Desk Agent`
    });
    agentAlias.node.addDependency(prepareAgent);

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
  }
} 