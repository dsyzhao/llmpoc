export interface EnvConfig {
  account: string;
  region: string;
  environment: string;
}

export interface Config {
  application: string;
  environments: {
    [key: string]: EnvConfig;
  };
} 