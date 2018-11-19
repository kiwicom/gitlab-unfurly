# GitLab Unfurly

Serverless Slack bot for unfurling GitLab URLs.

[![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com) 
[![Python: 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://python.org) 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) 
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/kiwicom/gitlab-unfurly/blob/master/LICENSE)

## Example

![GitLab Unfurly example](/docs/gitlab-unfurly.png)

## Usage

Deploy on [AWS](https://aws.amazon.com/) using [Serverless](https://serverless.com) 
framework.

Provide these environment variables:

- `GITLAB_URL`
- `GITLAB_TOKEN`
- `SLACK_TOKEN`
- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `AWS_REGION`

## Contributing

Bug reports and fixes are always welcome!

Tests are run with [pytest](https://pytest.org). Install into virtual environment 
`requirements.txt` and `test-requirements.txt` and run in shell command `pytest`

Code is formatted by [Black](https://github.com/ambv/black).

## License

[MIT](https://github.com/kiwicom/gitlab-unfurly/blob/master/LICENSE)
