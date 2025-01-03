import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lexv2 from 'aws-cdk-lib/aws-lex';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';
import * as path from 'path';
import * as lexConfig from '../config/lex-bot-guest-chat-config.json';
import { CfnBot } from 'aws-cdk-lib/aws-lex';

interface LexbotStackProps extends cdk.StackProps {
  environment: string;
  applicationName: string;
}

export class GuestFulfillmentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LexbotStackProps) {
    super(scope, id, props);

    // Create Lex Bot Role first
    const lexRole = new iam.Role(this, 'LexBotRole', {
      roleName: `${props.applicationName}-${props.environment}-stk-iam-role-lex-bot`,
      assumedBy: new iam.ServicePrincipal('lexv2.amazonaws.com'),
    });

    // Then create bot using the role
    const bot = new lexv2.CfnBot(this, 'LexBotGuestChat', {
      name: `${props.applicationName}-${props.environment}-stk-lex-bot-guest-chat`,
      dataPrivacy: { ChildDirected: false },
      idleSessionTtlInSeconds: 300,
      roleArn: lexRole.roleArn,
      autoBuildBotLocales: true,
      
      botLocales: [{
        localeId: lexConfig.locale.id,
        nluConfidenceThreshold: lexConfig.locale.nluConfidenceThreshold,
        voiceSettings: {
          voiceId: lexConfig.locale.voice.id
        },
        intents: lexConfig.intents as CfnBot.IntentProperty[]
      }]
    });

    // Create Lambda function for bot fulfillment
    const fulfillmentFunction = new lambda.Function(this, 'FulfillmentHandler', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-fulfillment-handler`,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'lambda-fulfillment-handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-fulfillment-handler.py']
      })
    });

    // Create Bot Alias with timestamp to ensure uniqueness
    const uniqueAliasName = `guest-chat-alias-${Date.now()}`;

    const botVersion = new lexv2.CfnBotVersion(this, 'LexBotVersion', {
      botId: bot.attrId,
      botVersionLocaleSpecification: [{
        localeId: 'en_US',
        botVersionLocaleDetails: {
          sourceBotVersion: 'DRAFT'
        }
      }]
    });

    // Add dependency to ensure bot is created first
    botVersion.addDependency(bot);

    const botAlias = new lexv2.CfnBotAlias(this, 'LexBotAlias', {
      botAliasName: uniqueAliasName,
      botId: bot.attrId,
      botVersion: botVersion.attrBotVersion,
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
        localeId: 'en_US'
      }]
    });

    // Add dependency to ensure version is created before alias
    botAlias.addDependency(botVersion);

    // Create Proxy Lambda for API Gateway
    const proxyFunction = new lambda.Function(this, 'ProxyApiHandler', {
      functionName: `${props.applicationName}-${props.environment}-stk-lambda-proxy-api-handler`,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'lambda-proxy-api-handler.handler',
      environment: {
        BOT_ID: bot.attrId,
        BOT_ALIAS_ID: botAlias.attrBotAliasId,
        LOCALE_ID: 'en_US'
      },
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda'), {
        exclude: ['*', '!lambda-proxy-api-handler.py']
      })
    });

    // Grant Lex permissions to invoke the Lambda function
    fulfillmentFunction.addPermission('LexInvocation', {
      principal: new iam.ServicePrincipal('lexv2.amazonaws.com'),
      action: 'lambda:InvokeFunction',
    });

    // Add Lex permissions to proxy Lambda
    proxyFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['lex:RecognizeText'],
        resources: [`arn:aws:lex:${this.region}:${this.account}:bot-alias/${bot.attrId}/${botAlias.attrBotAliasId}`]
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