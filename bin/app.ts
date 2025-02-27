#!/usr/bin/env node
require('source-map-support/register');
import * as cdk from 'aws-cdk-lib';
import { GuestFulfillmentStack } from '../lib/guest-fulfillment-stack';
import * as config from '../config/env-config.json';
import { Config } from '../types/config';
import { BedrockAgentStack } from '../lib/bedrock-agent-stack';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const envName = app.node.tryGetContext('env') || 'dev';
const typedConfig = config as Config;
const envConfig = typedConfig.environments[envName];

if (!envConfig) {
  throw new Error(`Environment ${envName} is not defined in config`);
}

// First, create the Bedrock Agent Stack
const bedrockAgentStack = new BedrockAgentStack(app, `${typedConfig.application}-${envName}-bedrock-agent-stack`, {
  env: {
    account: envConfig.account,
    region: envConfig.region
  },
  environment: envConfig.environment,
  applicationName: typedConfig.application
});

// Then, create the Guest Fulfillment Stack with a reference to the Bedrock Agent Stack
new GuestFulfillmentStack(app, `${typedConfig.application}-${envName}-guest-fulfillment-stack`, {
  env: {
    account: envConfig.account,
    region: envConfig.region
  },
  environment: envConfig.environment,
  applicationName: typedConfig.application,
  bedrockAgentStack: bedrockAgentStack // Pass the reference
});