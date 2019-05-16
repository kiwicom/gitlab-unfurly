# GitLab Unfurly

Serverless Slack bot for unfurling GitLab URLs.

[![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com)
[![Python: 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/kiwicom/gitlab-unfurly/blob/master/LICENSE)

## Example

![GitLab Unfurly example](/docs/gitlab-unfurly.png)

## Usage

### Install serverless and its plugins

> You need [NodeJS](https://nodejs.org/) in order to use it, if you don't have it, head to https://nodejs.org/en/ and download `current` version and install.

> You also need awscli, you can download and install via brew: https://formulae.brew.sh/formula/awscli, or from [official instruction](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)

Install serverless framework

```
> npm install serverless -g
```

Install serverless-python-requirements

```
> sls plugin install -n serverless-python-requirements
```

### Configure and deploy

Configure your aws secrets

> In case you want to generate a new GITLAB_TOKEN, head to `your_repo > Settings > Repository > Deploy Tokens` and create a new read_repository token

> You might also need to create a new slack application and get its token, id and secret.

```
> aws configure
AWS Access Key ID [None]:
AWS Secret Access Key [None]:
Default region name [ap-southeast-2]:
Default output format [None]:
```

Run deploy script and wait the script finish

```
> ./deploy.sh
```

### Remove the service

```
sls remove
```

## Contributing

Bug reports and fixes are always welcome!

Tests are run with [pytest](https://pytest.org). Install into virtual environment
`requirements.txt` and `test-requirements.txt` and run in shell command `pytest`

Code is formatted by [Black](https://github.com/ambv/black).

## License

[MIT](https://github.com/kiwicom/gitlab-unfurly/blob/master/LICENSE)
