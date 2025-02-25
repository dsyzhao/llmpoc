import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lexv2 from 'aws-cdk-lib/aws-lex';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';
import * as path from 'path';
import * as lexConfig from '../config/lex-bot-guest-chat-config.json';
import { CfnBot } from 'aws-cdk-lib/aws-lex';
import { BedrockAgentStack } from './bedrock-agent-stack';

interface LexbotStackProps extends cdk.StackProps {
  environment: string;
  applicationName: string;
  bedrockAgentStack?: BedrockAgentStack; // Optional reference to the Bedrock agent stack
}

export class GuestFulfillmentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LexbotStackProps) {
    super(scope, id, props);

    // Create Lex Bot Role first
    const lexRole = new iam.Role(this, 'LexBotRole', {
      roleName: `${props.applicationName}-${props.environment}-stk-iam-role-lex-bot`,
      assumedBy: new iam.ServicePrincipal('lexv2.amazonaws.com'),
    });

    // 1. Create bot first
    const bot = new lexv2.CfnBot(this, 'LexBotGuestFulfillment', {
      name: `${props.applicationName}-${props.environment}-stk-lex-bot-guest-fulfillment`,
      dataPrivacy: { ChildDirected: false },
      idleSessionTtlInSeconds: 300,
      roleArn: lexRole.roleArn,
      autoBuildBotLocales: true,
      
      botLocales: [{
        localeId: lexConfig.identifier,
        nluConfidenceThreshold: lexConfig.nluConfidenceThreshold,
        voiceSettings: {
          engine: 'standard',
          voiceId: lexConfig.voiceSettings.voiceId
        } as CfnBot.VoiceSettingsProperty,
        generativeAISettings: lexConfig.generativeAISettings,
        intents: lexConfig.intents as CfnBot.IntentProperty[]
      } as CfnBot.BotLocaleProperty]
    });

    // 2. Create fulfillment Lambda with environment variables for Bedrock agent
    const fulfillmentFunction = new lambda.Function(this, 'FulfillmentHandler', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-fulfillment-handler`,
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(180),
      handler: 'lambda-fulfillment-handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-fulfillment-handler.py']
      }),
      environment: props.bedrockAgentStack ? {
        // Add environment variables for the Bedrock agent if available
        AGENT_ID: props.bedrockAgentStack.agentId,
        AGENT_ALIAS_ID: props.bedrockAgentStack.agentAliasId
      } : {},
      role: new iam.Role(this, 'FulfillmentLambdaRole', {
        roleName: `${props.applicationName}-${props.environment}-stk-iam-role-fulfillment-lambda`,
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
        ]
      })
    });

    // 3. Create bot version with proper reference
    const botVersion = new lexv2.CfnBotVersion(this, 'LexBotVersion', {
      botId: bot.attrId,
      botVersionLocaleSpecification: [{
        localeId: lexConfig.identifier,
        botVersionLocaleDetails: {
          sourceBotVersion: 'DRAFT'
        }
      }]
    });
    botVersion.addDependency(bot);

    // 4. Create alias with proper references
    const botAlias = new lexv2.CfnBotAlias(this, 'LexBotAlias', {
      botAliasName: `guest-chat-alias-${props.environment}`,
      botId: bot.attrId,
      botVersion: '1',
      botAliasLocaleSettings: [{
        botAliasLocaleSetting: {
          enabled: true,
          codeHookSpecification: {
            lambdaCodeHook: {
              codeHookInterfaceVersion: '1.0',
              lambdaArn: fulfillmentFunction.functionArn
            }
          }
        },
        localeId: lexConfig.identifier
      }]
    });
    botAlias.addDependency(botVersion);

    // Create Proxy Lambda for API Gateway
    const proxyFunction = new lambda.Function(this, 'ProxyApiHandler', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-proxy-api-handler`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'lambda-proxy-api-handler.lambda_handler',
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        BOT_ID: bot.attrId,
        BOT_ALIAS_ID: botAlias.attrBotAliasId,
        LOCALE_ID: 'en_US'
      },
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-proxy-api-handler.py']
      })
    });

    // Add specific Lambda permission for this bot/alias
    fulfillmentFunction.addPermission('LexInvocation', {
      principal: new iam.ServicePrincipal('lexv2.amazonaws.com'),
      action: 'lambda:InvokeFunction',
      sourceArn: `arn:aws:lex:${this.region}:${this.account}:bot-alias/${bot.ref}/*`
    });

    // Add Lex role permissions
    lexRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: [fulfillmentFunction.functionArn]
    }));

    // Add Lex permissions to proxy Lambda
    proxyFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['lex:RecognizeText'],
        resources: [
          `arn:aws:lex:${this.region}:${this.account}:bot-alias/${bot.ref}/${botAlias.ref}`,
          `arn:aws:lex:${this.region}:${this.account}:bot-alias/CLKLPPZYND/PYRKBGNF98`
        ]
      })
    );

    // Add S3 read permissions for the fulfillment Lambda
    fulfillmentFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject'],
        resources: [`arn:aws:s3:::botconfig${this.account}v2/*`]
      })
    );

    // Add Bedrock permissions for the fulfillment Lambda - restrict to specific agents
    fulfillmentFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeAgent'],
        resources: [
          // The agent created in our CDK stack
          props.bedrockAgentStack ? 
            `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/${props.bedrockAgentStack.agentId}/*` : 
            `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/*`,
          // The hardcoded agent in the Lambda (QPUIAGLFMO/FN2KWQFPLG)
          `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/QPUIAGLFMO/*`
        ]
      })
    );

    // Create API Gateway Logging Role
    const apiGatewayLoggingRole = new iam.Role(this, 'ApiGatewayLoggingRole', {
      roleName: `${props.applicationName}-${props.environment}-stk-iam-role-api-gtwy-logging`,
      assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonAPIGatewayPushToCloudWatchLogs')
      ]
    });

    // Associate the role with API Gateway Account
    new apigateway.CfnAccount(this, 'ApiGatewayLoggingAccount', {
      cloudWatchRoleArn: apiGatewayLoggingRole.roleArn
    });

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'ApiGateway', {
      restApiName: `${props.applicationName}-${props.environment}-stk-api-gateway-integration`,
      description: 'API Gateway Integration for Lex Bot Transcription of other channels',
      deployOptions: {
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true
      },
      defaultMethodOptions: {
        authorizationType: apigateway.AuthorizationType.IAM
      }
    });

    // Create Lambda integration for API Gateway
    const lambdaIntegration = new apigateway.LambdaIntegration(
      proxyFunction,
      { proxy: true }
    );

    // Add POST method to API Gateway
    api.root.addMethod('POST', lambdaIntegration, {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigateway.Model.EMPTY_MODEL
          }
        }
      ]
    });

    // Add outputs
    new cdk.CfnOutput(this, 'ApiGatewayEndpointUrl', {
      value: api.url,
      description: 'API Gateway URL'
    });

    new cdk.CfnOutput(this, 'LexBotId', {
      value: bot.attrId,
      description: 'Lex Bot ID'
    });

  }
} 