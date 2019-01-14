#!/usr/bin/env python3

from enum import Enum
import json
import os
import re
import textwrap
from urllib.parse import quote, urljoin, urlparse

import arrow
import attr
import bleach
from kw.structlog_config import configure_structlog
import requests
from slackclient import SlackClient
import structlog


# environment setup
DEBUG = bool(os.getenv("DEBUG"))
GITLAB_URL = os.getenv("GITLAB_URL")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")

# logging setup
configure_structlog(debug=DEBUG)
log = structlog.get_logger()
log.bind(project="gitlab_unfurly")


OK_RESPONSE = {"statusCode": 204, "body": ""}

ISSUE_STATE_COLORS = {"opened": "#1aaa55", "closed": "#1f78d1"}
MR_STATE_COLORS = {"opened": "#1aaa55", "merged": "#1f78d1", "closed": "#db3b21"}


###############################################################################
# GitLab API responses to Slack messages


def strip_html_tags(value):
    return bleach.clean(value, tags=[], strip=True)


def prepare_description(description, *, width=100):
    description = strip_html_tags(description)
    description = description.strip()
    return textwrap.shorten(description, width, placeholder="…")


def get_data_from_api(session, api_path):
    response = session.get(urljoin(GITLAB_URL, api_path))
    response.raise_for_status()
    return response.json()


def get_issue_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/issues/{path_info.identifier}"
    data = get_data_from_api(session, api_path)

    assignee = "_nobody_"
    try:
        title = data["title"].strip()
        description = data["description"] or ""
        due_date = data["due_date"]
        milestone = data["milestone"]
        if data["assignees"]:
            assignee = ", ".join(
                f"@{assignee['username']}" for assignee in data["assignees"]
            )
        author = "@" + data["author"]["username"]
        state = data["state"]
    except IndexError as e:
        log.exception("Error in data from GitLab")
        raise

    if state != "opened":
        title += f" ({state})"

    fields = [
        {"title": "Author", "value": author, "short": "true"},
        {"title": "Assignee", "value": assignee, "short": "true"},
    ]

    if due_date:
        formatted_date = (
            "<!date"
            f"^{arrow.get(due_date).timestamp}"
            "^{date_short_pretty}"
            f"|{due_date}>"
        )
        fields.append({"title": "Due date", "value": formatted_date, "short": "true"})

    if milestone:
        fields.append(
            {
                "title": "Milestone",
                "value": f"<{milestone['web_url']}|{milestone['title']}>",
                "short": "true",
            }
        )

    return {
        "title": title,
        "fields": fields,
        "text": prepare_description(description, width=300),
        "color": ISSUE_STATE_COLORS[state],
    }


def get_mr_info(session, path_info):
    api_path = (
        f"/api/v4/projects/{path_info.quoted_id}/merge_requests/{path_info.identifier}"
    )
    data = get_data_from_api(session, api_path)

    assignee = "_nobody_"
    try:
        title = data["title"].strip()
        description = data["description"] or ""
        if data["assignee"]:
            assignee = "@" + data["assignee"]["username"]
        author = "@" + data["author"]["username"]
        milestone = data["milestone"]
        state = data["state"]
    except IndexError as e:
        log.exception("Error in data from GitLab")
        raise

    if state != "opened":
        title += f" ({state})"

    fields = [
        {"title": "Author", "value": author, "short": "true"},
        {"title": "Assignee", "value": assignee, "short": "true"},
    ]

    if milestone:
        fields.append(
            {
                "title": "Milestone",
                "value": f"<{milestone['web_url']}|{milestone['title']}>",
                "short": "true",
            }
        )

    return {
        "title": title,
        "fields": fields,
        "text": prepare_description(description),
        "color": MR_STATE_COLORS[state],
    }


def get_commit_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/repository/commits/{path_info.identifier}"
    data = get_data_from_api(session, api_path)

    try:
        title = data["title"].strip()
        author_name = data["author_name"].strip()
    except IndexError as e:
        log.exception("Error in data from GitLab")

    attachment = {"title": title, "author_name": author_name}

    return attachment


def get_project_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}"
    data = get_data_from_api(session, api_path)

    try:
        name = data["name_with_namespace"]
        description = data["description"] or ""
    except IndexError as e:
        log.exception("Error in data from GitLab")

    return {"title": name, "text": prepare_description(description)}


###############################################################################
# Path parsing utils


class PathType(Enum):
    PROJECT = "project"
    COMMIT = "commit"
    MERGE_REQUEST = "merge_requests"
    ISSUE = "issues"


@attr.s
class PathInfo:
    type = attr.ib(validator=attr.validators.instance_of(PathType))
    team = attr.ib()
    project = attr.ib()
    identifier = attr.ib(default=None)
    subgroups = attr.ib(default=None)

    @property
    def quoted_id(self):
        if self.subgroups:
            return quote(f"{self.team}/{self.subgroups}/{self.project}", safe="")
        return quote(f"{self.team}/{self.project}", safe="")


def parse_path(path):
    # issue, merge request or commit path
    pattern = r"^\/(?P<team>[\w-]+)\/(?P<subgroups>[\w/-]*?)\/?(?P<project>[\w-]+)\/(?P<type>issues|merge_requests|commit)\/(?P<identifier>\w+).*$"
    m = re.match(pattern, path)
    if m:
        return PathInfo(
            type=PathType(m.group("type")),
            team=m.group("team"),
            project=m.group("project"),
            identifier=m.group("identifier"),
            subgroups=m.group("subgroups") or None,
        )

    # project path
    pattern = r"^\/(?P<team>[\w-]+)\/(?P<subgroups>[\w/-]*?)\/?(?P<project>[\w-]+)\/?$"
    m = re.match(pattern, path)
    if m:
        return PathInfo(
            type=PathType.PROJECT,
            team=m.group("team"),
            project=m.group("project"),
            subgroups=m.group("subgroups") or None,
        )

    raise ValueError(f"Can't parse path: {path}")


###############################################################################
# Serverless handlers


def unfurl(event, context):
    session = requests.Session()
    session.headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "User-Agent": "GitLab Unfurly"}
    slack = SlackClient(SLACK_TOKEN)

    request_json = json.loads(event["body"])
    raw_url = request_json["event"]["links"][0]["url"]
    url = urlparse(raw_url.replace("\\", ""))
    log.bind(url=url)
    if "no_unfurl" in url.query:
        log.info("Skipping URL as requested")
        return OK_RESPONSE

    try:
        path_info = parse_path(url.path)
    except ValueError as exc:
        log.error("Can't parse path")
        return OK_RESPONSE

    if path_info.type == PathType.ISSUE:
        attachment = get_issue_info(session, path_info)
    elif path_info.type == PathType.MERGE_REQUEST:
        attachment = get_mr_info(session, path_info)
    elif path_info.type == PathType.COMMIT:
        attachment = get_commit_info(session, path_info)
    elif path_info.type == PathType.PROJECT:
        attachment = get_project_info(session, path_info)
    else:
        log.error(f"Unhandled path type: {path_info.type}")
        return OK_RESPONSE

    attachment["title_link"] = raw_url
    r = slack.api_call(
        "chat.unfurl",
        channel=request_json["event"]["channel"],
        ts=request_json["event"]["message_ts"],
        unfurls={raw_url: attachment},
    )
    log.info("Slack API call", response=r)
    return OK_RESPONSE


def start_login(event, context):
    return {
        "statusCode": 200,
        "body": f"""
            <a href="https://slack.com/oauth/authorize?scope=links:read,links:write&client_id={SLACK_CLIENT_ID}">
                Add to Slack
            </a>
        """,
        "headers": {"content-type": "text/html; charset=utf-8"},
    }


def finish_login(event, context):
    slack = SlackClient(SLACK_TOKEN)
    auth_code = event["queryStringParameters"]["code"]
    slack.api_call(
        "oauth.access",
        client_id=SLACK_CLIENT_ID,
        client_secret=SLACK_CLIENT_SECRET,
        code=auth_code,
    )

    return {
        "statusCode": 200,
        "body": "<meta charset='utf-8'> <h1>👌</h1>",
        "headers": {"content-type": "text/html; charset=utf-8"},
    }
