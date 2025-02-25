#!/usr/bin/env node
require('source-map-support/register');
import * as cdk from 'aws-cdk-lib';
import { GuestFulfillmentStack } from '../lib/guest-fulfillment-stack';
import * as config from '../config/env-config.json';
import { Config } from '../types/config';
import { CICDStack } from '../lib/ci-cd-stack';
import { BedrockAgentStack } from '../lib/bedrock-agent-stack';

const app = new cdk.App();

// Get environment from context or default to 'dev'
const envName = app.node.tryGetContext('env') || 'dev';
const typedConfig = config as Config;
const envConfig = typedConfig.environments[envName];

if (!envConfig) {
  throw new Error(`Environment ${envName} is not defined in config`);
}

// Initialize the Guest Fulfillment Stack
new GuestFulfillmentStack(app, `${typedConfig.application}-${envName}-guest-fulfillment-stack`, {
  env: {
    account: envConfig.account,
    region: envConfig.region
  },
  environment: envConfig.environment,
  applicationName: typedConfig.application
});

// Add CI/CD stack
new CICDStack(app, `${typedConfig.application}-${envName}-cicd-stack`, {
  env: {
    account: envConfig.account,
    region: envConfig.region
  },
  environment: envConfig.environment,
  applicationName: typedConfig.application,
  workspaceId: '9be73cb9-4aa8-4d81-a92f-e9aa2b628207',
  workspaceName: 'na-dna',
  repositoryName: 'hospitality-voice-tech'
});

// Add Bedrock Agent stack
new BedrockAgentStack(app, `${typedConfig.application}-${envName}-bedrock-agent-stack`, {
  env: {
    account: envConfig.account,
    region: envConfig.region
  },
  environment: envConfig.environment,
  applicationName: typedConfig.application
}); 