# GitHub Actions Deployment Setup

This guide helps you set up automatic deployment of your Drills Creator application to AWS Elastic Beanstalk using GitHub Actions.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS S3 Bucket** for storing deployment packages
3. **AWS Elastic Beanstalk Application and Environment** configured for Docker platform
4. **GitHub repository** with your source code

## AWS Setup

### 1. Create S3 Bucket

```bash
aws s3 mb s3://drills-creator-deployments --region us-east-1
```

### 2. Create Elastic Beanstalk Application

```bash
aws elasticbeanstalk create-application \
    --application-name drills-creator-app \
    --description "Poker Drills Creator Application"
```

### 3. Create Elastic Beanstalk Environment

```bash
aws elasticbeanstalk create-environment \
    --application-name drills-creator-app \
    --environment-name drills-creator-env \
    --solution-stack-name "64bit Amazon Linux 2023 v4.0.11 running Docker" \
    --option-settings \
        Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.micro \
        Namespace=aws:elasticbeanstalk:application:environment,OptionName=PORT,Value=8777
```

### 4. Create IAM User for GitHub Actions

Create an IAM user with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::drills-creator-deployments",
        "arn:aws:s3:::drills-creator-deployments/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticbeanstalk:CreateApplicationVersion",
        "elasticbeanstalk:UpdateEnvironment",
        "elasticbeanstalk:DescribeEnvironments",
        "elasticbeanstalk:DescribeApplicationVersions",
        "elasticbeanstalk:DescribeEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## GitHub Setup

### 1. Add Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add:

- `AWS_ACCESS_KEY_ID`: Your IAM user's access key ID
- `AWS_SECRET_ACCESS_KEY`: Your IAM user's secret access key

### 2. Update Environment Variables

Edit `.github/workflows/deploy.yml` and update these environment variables:

```yaml
env:
  AWS_REGION: us-east-1 # Your AWS region
  EB_APPLICATION_NAME: drills-creator-app # Your EB application name
  EB_ENVIRONMENT_NAME: drills-creator-env # Your EB environment name
  S3_BUCKET: drills-creator-deployments # Your S3 bucket name
```

## Files Created

### 1. `Dockerrun.aws.json`

This file tells Elastic Beanstalk how to run your Docker container:

- Maps container port 8777 to host port 80
- Configures logging

### 2. `.github/workflows/deploy.yml`

This GitHub Action workflow:

- Triggers on pushes to main/master branches
- Creates a deployment package (ZIP file)
- Uploads the package to S3
- Creates a new Elastic Beanstalk application version
- Deploys to your environment
- Waits for deployment completion

## Deployment Process

1. **Automatic**: Push to `main` or `master` branch
2. **Manual**: Go to Actions tab → "Deploy to Elastic Beanstalk" → "Run workflow"

## What Gets Deployed

The deployment package includes:

- `Dockerfile` and `Dockerrun.aws.json`
- Python application files (`hand_image_server.py`, etc.)
- `requirements.txt`
- Static assets (`fonts/`, `cards-images/`, etc.)
- Poker solution data (`poker_solutions/`)

Excluded from deployment:

- Development files (`.git`, `__pycache__`, etc.)
- Local directories (`hand_images/`, `visualizations/`, etc.)
- Documentation files (`.md`)
- Batch scripts

## Monitoring

After deployment, you can:

- Check the GitHub Actions tab for deployment status
- Monitor your Elastic Beanstalk environment in the AWS Console
- Access your application at the provided CNAME URL

## Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure your GitHub secrets are correctly set
2. **Permissions**: Verify IAM user has required permissions
3. **Environment Names**: Check that EB application/environment names match the workflow
4. **S3 Bucket**: Ensure the bucket exists and is accessible
5. **Region**: Verify AWS region is consistent across all resources

### Logs

- GitHub Actions logs: Repository → Actions tab
- EB Environment logs: AWS Console → Elastic Beanstalk → Environment → Logs
- Application logs: Available through EB environment logging

## Customization

You can modify the workflow to:

- Add different triggers (tags, specific branches)
- Include environment-specific configurations
- Add testing steps before deployment
- Set up blue-green deployments
- Add notification steps (Slack, email, etc.)
