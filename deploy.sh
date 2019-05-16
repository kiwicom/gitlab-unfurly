#!/bin/bash

set -e

printf "GITLAB_URL[${GITLAB_URL:-"-"}]:"
read gitlab_url
export GITLAB_URL=$gitlab_url
printf "$gitlab_url\n"

printf "GITLAB_TOKEN[${GITLAB_TOKEN:-"-"}]:"
read gitlab_token
export GITLAB_TOKEN=$gitlab_token
printf "$gitlab_token\n"

printf "SLACK_TOKEN[${SLACK_TOKEN:-"-"}]:"
read slack_token
export SLACK_TOKEN=$slack_token
printf "$slack_token\n"

printf "SLACK_CLIENT_ID[${SLACK_CLIENT_ID:-"-"}]:"
read slack_client_id
export SLACK_CLIENT_ID=$slack_client_id
printf "$slack_client_id\n"

printf "SLACK_CLIENT_SECRET[${SLACK_CLIENT_SECRET:-"-"}]:"
read slack_client_secret
export SLACK_CLIENT_SECRET=$slack_client_secret
printf "$slack_client_secret\n"

printf "AWS_REGION[${AWS_REGION:-UNSET}]:"
read aws_region
export AWS_REGION=$aws_region
printf "$aws_region\n"

printf "Deployment start...\n"

sls deploy