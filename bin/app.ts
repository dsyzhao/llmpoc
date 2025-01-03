#!/usr/bin/env node
require('source-map-support/register');
import * as cdk from 'aws-cdk-lib';
import { GuestFulfillmentStack } from '../lib/guest-fulfillment-stack';
import * as config from '../config/env-config.json';
import { Config } from '../types/config';

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