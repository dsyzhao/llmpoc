import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

interface CICDStackProps extends cdk.StackProps {
  environment: string;
  applicationName: string;
  workspaceId: string;
  workspaceName: string;
  repositoryName: string;
}

export class CICDStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: CICDStackProps) {
    super(scope, id, props);

    // Create OIDC Provider for Bitbucket
    const provider = new iam.OpenIdConnectProvider(this, 'BitbucketOIDCProvider', {
      url: 'https://api.bitbucket.org/2.0/openid-connect',
      clientIds: ['ari:cloud:bitbucket::workspace/9be73cb9-4aa8-4d81-a92f-e9aa2b628207'],
      thumbprints: ['a031c46782e6e6c662c2c87c76da9aa62ccabd8e']
    });

    // Create deployment role that Bitbucket can assume
    const deploymentRole = new iam.Role(this, 'BitbucketDeploymentRole', {
      roleName: `${props.applicationName}-${props.environment}-stk-iam-role-bitbucket-deployment`,
      assumedBy: new iam.WebIdentityPrincipal(provider.openIdConnectProviderArn, {
        StringEquals: {
          'api.bitbucket.org/2.0/openid-connect:aud': 'ari:cloud:bitbucket::workspace/9be73cb9-4aa8-4d81-a92f-e9aa2b628207'
        },
        StringLike: {
          // Match the repository UUID from environment variables
          'api.bitbucket.org/2.0/openid-connect:sub': 'repository:na-dna/hospitality-voice-tech:*'
        }
      })
    });

    // Add required permissions for CDK deployment
    deploymentRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudformation:*',
        'iam:*',
        'lambda:*',
        'apigateway:*',
        'lex:*',
        's3:*',
        'logs:*'
      ],
      resources: ['*']
    }));

    // Output the role ARN for reference
    new cdk.CfnOutput(this, 'DeploymentRoleArn', {
      value: deploymentRole.roleArn,
      description: 'ARN of the deployment role for Bitbucket pipelines'
    });
  }
} 