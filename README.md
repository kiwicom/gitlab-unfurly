# GitLab Unfurly

Serverless Slack bot for unfurling GitLab URLs.

[![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com) 
[![Python: 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://python.org) 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) 
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/kiwicom/gitlab-unfurly/blob/master/LICENSE)

## Example

![GitLab Unfurly example](/docs/gitlab-unfurly.png)

## Installation

Deploy on [AWS](https://aws.amazon.com/) using [Serverless](https://serverless.com) 
framework.

### Create Slack App
1. Go to https://api.slack.com/apps?new_app=1 and log in to your workspace
2. Name and create your app for your workspace
3. Scroll down to App Credentials
   1. Copy the Client Id and Client Secret, or just remember that they are right here for later use
4. Add features and functionality
   1. Event Subscriptions
   2. App unfurl domains
   3. Add your GitLab domain
   4. You'll come back here and fill in your Request URL once you've deployed the app using serverless
5. Go back to Settings > Basic Information
6. Add features and functionality
   1. Permissions
   2. Scopes > Add an OAuth scope
   3. links:write
7. Reinstall the app as requested
8. Copy the OAuth Access Token. That is your SLACK_TOKEN referenced later.

### Get AWS Credentials
You will need AWS Access keys. If you do not know your keys or don't have them, you can retrieve your personal access keys from the following url:
https://console.aws.amazon.com/iam/home?region=us-west-2#/security_credentials

For more information about creating an AWS account, or using an appropriately scoped service account, follow [these directions from serverless](https://serverless.com/framework/docs/providers/aws/guide/credentials/)

### Get GitLab Token
1. In GitLab, go to your user settings, which are found in the upper right corner of the Website.
2. Open the access tokens section found in the left menu
3. Add a personal Access Token with api scope
4. The token presented is your GITLAB_TOKEN referenced later

### Deploy Using GitLab-CI
The easiest way to deploy this lambda function is to use the provided .gitlab-ci.yml. This requires that you have a shared GitLab runner configured.

Setup:
1. Go into your gitlab instance and create a project named gitlab-unfurly
2. Copy the clone link from the project repo page
3. Add the repo as a remote for this git repo  
   `git remote add gitlab {your gitlab clone link}.git`
4. In GitLab, go to Settings > CI/CD
5. Expand the Variables section
6. Add the following variables:  
   - `GITLAB_URL` - The base url to your GitLab instance
   - `GITLAB_TOKEN` - Your personal Access Token generated earlier
   - `SLACK_TOKEN` - OAuth Access Token generated earlier
   - `SLACK_CLIENT_ID`
   - `SLACK_CLIENT_SECRET`
   - `AWS_REGION` - The AWS region you will deploy to. `us-west-2` is 100% renewable energy
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
7. Save
8. Push this repo to the gitlab project
   `git push -u gitlab master`
9. Wait for the deploy job to run to completion in GitLab Pipelines
10. Open the job output to find the POST endpoint; it will be near the bottom of the build output.
11. Go back to the slack app website you were using earlier
12. Go to Features > Event Subscriptions
13. Paste the POST endpoint url into the Request Url field
14. Try sharing a gitlab link with yourself in slack to see if it works

### Deploy Using Your Machine
If for some reason you do not want to use GitLab CI to deploy this lambda, then you can deploy it using the serverless cli on your own machine.

Deployment environment requirements:
1. Linux:
   1. Python 3.8
   2. set dockerizePip to false in the serverless.yml.
2. Windows
   1. Docker
3. node.js
4. serverless  
   `npm install -g serverless`
5. serverless-python-requirements
   `serverless plugin install -n serverless-python-requirements`

Set the following environment variables:
- `GITLAB_URL` - The base url to your GitLab instance
- `GITLAB_TOKEN` - Your personal Access Token generated earlier
- `SLACK_TOKEN` - OAuth Access Token generated earlier
- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `AWS_REGION` - The AWS region you will deploy to. `us-west-2` is 100% renewable energy
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

After that's all taken care of, you just run the following command: `serverless deploy`

### Troubleshooting
The first step to troubleshooting is to open the AWS Console and navigate to the CloudWatch logs. You will find the logs for this lambda in the log group named something like gitlab-unfurly-dev-unfurl.

#### Common Issues
1. SSL failure while contacting your GitLab instance
   1. This is likely caused by your GitLab instance using an untrusted Certificate Authority (CA)
   2. Use [this StackOverflow answer](https://stackoverflow.com/a/59638101/576153) to resolve the issue
1. auth_failure while contacting slack
   1. This is likely caused by you skipping step #6 in the [Create Slack App](#Create-Slack-App) section above

## Contributing

Bug reports and fixes are always welcome!

Tests are run with [pytest](https://pytest.org). Install into virtual environment 
`requirements.txt` and `test-requirements.txt` and run in shell command `pytest`

Code is formatted by [Black](https://github.com/ambv/black).

## License

[MIT](https://github.com/kiwicom/gitlab-unfurly/blob/master/LICENSE)

## FAQ

1. **How to make unfurly ignore my urls (= not create previews)?**  
Append `?no_unfurl` to the url.

2. **Is there a way to disable unfurly for the whole post?**  
Unfortunately no. Unfurly receives links from slack 1-by-1. Therefore it has no knowledge about
links being part of the same post.
