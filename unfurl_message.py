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
CI_STATE_COLORS = {
    "created": "#1f78d1",
    "pending": "#1f78d1",
    "running": "#1aaa55",
    "failed": "#db3b21",
    "success": "#1aaa55",
    "canceled": "#FDBF2C",
    "skipped": "#1f78d1",
    "manual": "#1f78d1",
}

###############################################################################
# GitLab API responses to Slack messages


def strip_html_tags(value):
    return bleach.clean(value, tags=[], strip=True)


def prepare_description(description, *, width=100):
    description = strip_html_tags(description)
    description = description.strip()
    return textwrap.shorten(description, width, placeholder="…")


def format_user(user, warn_blocked=False):
    if user["state"] == "blocked":
        tag = "(blocked) :warning:" if warn_blocked else "(blocked)"
        return f"{user['username']} {tag}"
    return user["username"]


def slack_formatted_date(raw_datetime):
    return (
        "<!date"
        f"^{arrow.get(raw_datetime).timestamp}"
        "^{date_short_pretty}"
        f"|{raw_datetime}>"
    )


def slack_formatted_datetime(raw_datetime):
    return (
        "<!date"
        f"^{arrow.get(raw_datetime).timestamp}"
        "^{date_short_pretty} - {time_secs}"
        f"|{raw_datetime}>"
    )


def get_data_from_api(session, api_path):
    response = session.get(urljoin(GITLAB_URL, api_path))
    response.raise_for_status()
    return response.json()


def get_issue_data(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/issues/{path_info.identifier}"
    return get_data_from_api(session, api_path)


def get_issues_info(session, path_info):
    data = get_issue_data(session, path_info)

    assignee = "_nobody_"
    try:
        title = data["title"].strip()
        description = data["description"] or ""
        due_date = data["due_date"]
        milestone = data["milestone"]
        if data["assignees"]:
            assignee = ", ".join(
                format_user(assignee, warn_blocked=True)
                for assignee in data["assignees"]
            )
        state = data["state"]
    except IndexError as e:
        log.exception("Error in data from GitLab")
        raise

    if state != "opened":
        title += f" ({state})"

    fields = [{"title": "Assignee", "value": assignee, "short": "true"}]

    if due_date:
        formatted_date = slack_formatted_date(due_date)
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
        "author_name": format_user(data["author"]),
        "author_link": data["author"]["web_url"],
        "author_icon": data["author"]["avatar_url"],
        "title": title,
        "fields": fields,
        "text": prepare_description(description, width=300),
        "color": ISSUE_STATE_COLORS[state],
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Issue",
    }


def get_note_issues_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/issues/{path_info.identifier}/notes/{path_info.note}"
    data = get_data_from_api(session, api_path)
    issue_data = get_issue_data(session, path_info)

    try:
        issue_title = issue_data["title"].strip()
        issue_state = issue_data["state"]
        body = data["body"]
    except IndexError as e:
        log.exception(f"Err in data from GL: {e}")
        raise
    return {
        "author_name": format_user(data['author'], warn_blocked=True),
        "author_link": data["author"]["web_url"],
        "author_icon": data["author"]["avatar_url"],
        "title": f"Comment on issue: {issue_title}",
        "text": prepare_description(body.strip(), width=300),
        "color": ISSUE_STATE_COLORS[issue_state],
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Issue note",
    }


def get_merge_request_data(session, path_info):
    api_path = (
        f"/api/v4/projects/{path_info.quoted_id}/merge_requests/{path_info.identifier}"
    )
    return get_data_from_api(session, api_path)


def get_merge_requests_info(session, path_info):
    data = get_merge_request_data(session, path_info)
    assignee = "_nobody_"
    try:
        title = data["title"].strip()
        description = data["description"] or ""
        if data["assignee"]:
            assignee = format_user(data["assignee"], warn_blocked=True)
        milestone = data["milestone"]
        state = data["state"]
        diffs = data["changes_count"]
    except IndexError as e:
        log.exception("Error in data from GitLab")
        raise

    if state != "opened":
        title += f" ({state})"

    fields = [{"title": "Assignee", "value": assignee, "short": "true"}]
    if diffs:
        fields.append(
            {"title": "Diffs", "value": diffs, "short": "true"}
        )

    if milestone:
        fields.append(
            {
                "title": "Milestone",
                "value": f"<{milestone['web_url']}|{milestone['title']}>",
                "short": "true",
            }
        )

    return {
        "author_name": format_user(data["author"]),
        "author_link": data["author"]["web_url"],
        "author_icon": data["author"]["avatar_url"],
        "title": title,
        "fields": fields,
        "text": prepare_description(description),
        "color": MR_STATE_COLORS[state],
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Merge Request",
    }


def get_note_merge_requests_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/merge_requests/{path_info.identifier}/notes/{path_info.note}"
    data = get_data_from_api(session, api_path)
    mr_data = get_merge_request_data(session, path_info)

    try:
        mr_title = mr_data["title"].strip()
        mr_state = mr_data["state"]
        body = data["body"]
    except IndexError as e:
        log.exception(f"Err in data from GL: {e}")
        raise
    return {
        "author_name": format_user(data["author"]),
        "author_link": data["author"]["web_url"],
        "author_icon": data["author"]["avatar_url"],
        "title": f"Comment on merge request: {mr_title}",
        "text": textwrap.shorten(body.strip(), width=300, placeholder="…"),
        "color": MR_STATE_COLORS[mr_state],
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Merge Request Note",
    }


def get_commit_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/repository/commits/{path_info.identifier}"
    data = get_data_from_api(session, api_path)

    try:
        title = data["title"].strip()
        author_name = data["author_name"].strip()
    except IndexError as e:
        log.exception("Error in data from GitLab")

    attachment = {
        "title": title,
        "author_name": author_name,
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Commit",
    }

    return attachment


def get_project_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}"
    data = get_data_from_api(session, api_path)

    try:
        description = data["description"] or ""
    except IndexError as e:
        log.exception("Error in data from GitLab")

    return {
        "author_name": data["namespace"]["name"],
        "author_link": urljoin(GITLAB_URL, data["namespace"]["full_path"]),
        "thumb_url": data["avatar_url"],
        "title": data["name"],
        "text": prepare_description(description),
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Project",
    }


def get_pipelines_info(session, path_info):
    api_path = (
        f"/api/v4/projects/{path_info.quoted_id}/pipelines/{path_info.identifier}"
    )
    data = get_data_from_api(session, api_path)

    try:
        status = data["status"]
        fields = [
            {"title": "Status", "value": status, "short": "true"},
            {"title": "Ref", "value": data["ref"], "short": "true"},
        ]

        started_at = data["started_at"]
        finished_at = data["finished_at"]
        if started_at:
            started_at = slack_formatted_datetime(started_at)
            fields.append({"title": "Started at", "value": started_at, "short": "true"})
        if finished_at:
            finished_at = slack_formatted_datetime(finished_at)
            fields.append(
                {"title": "Finished at", "value": finished_at, "short": "true"}
            )

        pipeline_id = data["id"]
    except IndexError as e:
        log.exception("Err in data from GL")
    return {
        "author_name": format_user(data["user"]),
        "author_link": data["user"]["web_url"],
        "author_icon": data["user"]["avatar_url"],
        "title": f"Pipeline #{pipeline_id}",
        "fields": fields,
        "color": CI_STATE_COLORS.get(status, ""),
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Pipeline",
    }


def get_jobs_info(session, path_info):
    api_path = f"/api/v4/projects/{path_info.quoted_id}/jobs/{path_info.identifier}"
    data = get_data_from_api(session, api_path)

    try:
        status = data["status"]
        fields = [
            {"title": "Status", "value": status, "short": "true"},
            {"title": "Stage", "value": data["stage"], "short": "true"},
        ]

        started_at = data["started_at"]
        finished_at = data["finished_at"]
        duration = data["duration"]
        if started_at:
            started_at = slack_formatted_datetime(started_at)
            fields.append({"title": "Started at", "value": started_at, "short": "true"})
        if finished_at:
            finished_at = slack_formatted_datetime(finished_at)
            fields.append(
                {"title": "Finished at", "value": finished_at, "short": "true"}
            )
        if duration:
            fields.append({"title": "Duration", "value": duration, "short": "true"})

        job_id = data["id"]
        job_name = data["name"]
    except IndexError as e:
        log.exception(f"Err in data from GL: {e}")
    return {
        "author_name": format_user(data["user"]),
        "author_link": data["user"]["web_url"],
        "author_icon": data["user"]["avatar_url"],
        "title": f"Job #{job_id}: {job_name}",
        "fields": fields,
        "color": CI_STATE_COLORS.get(status, ""),
        "ts": arrow.get(data["created_at"]).timestamp,
        "footer": "Pipeline Job",
    }


###############################################################################
# Path parsing utils


class PathType(Enum):
    PROJECT = "project"
    COMMIT = "commit"
    MERGE_REQUEST = "merge_requests"
    ISSUE = "issues"
    PIPELINE = "pipelines"
    JOB = "jobs"
    NOTE_ISSUE = "note_issues"
    NOTE_MERGE_REQUESTS = "note_merge_requests"


@attr.s
class PathInfo:
    type = attr.ib(validator=attr.validators.instance_of(PathType))
    team = attr.ib()
    project = attr.ib()
    identifier = attr.ib(default=None)
    subgroups = attr.ib(default=None)
    note = attr.ib(default=None)

    @property
    def quoted_id(self):
        if self.subgroups:
            return quote(f"{self.team}/{self.subgroups}/{self.project}", safe="")
        return quote(f"{self.team}/{self.project}", safe="")


def parse_path(path, fragment=None):
    # issue, merge request or commit path
    pattern = r"^\/(?P<team>[\w-]+)\/(?P<subgroups>[\w/-]*?)\/?(?P<project>[\w-]+)\/-?\/?(?P<type>issues|merge_requests|commit|pipelines|jobs)\/(?P<identifier>\w+)\/?$"
    m = re.match(pattern, path)
    if m:
        path_type = m.group("type")
        note = None
        if fragment:
            path_type = f"note_{path_type}"
            note = fragment.split("_")[1]

        path_type = PathType(path_type)
        return PathInfo(
            type=path_type,
            team=m.group("team"),
            project=m.group("project"),
            identifier=m.group("identifier"),
            subgroups=m.group("subgroups") or None,
            note=note,
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

HANDLERS = {
    PathType.COMMIT: get_commit_info,
    PathType.ISSUE: get_issues_info,
    PathType.JOB: get_jobs_info,
    PathType.MERGE_REQUEST: get_merge_requests_info,
    PathType.PIPELINE: get_pipelines_info,
    PathType.PROJECT: get_project_info,
    PathType.NOTE_ISSUE: get_note_issues_info,
    PathType.NOTE_MERGE_REQUESTS: get_note_merge_requests_info,
}

def get_handler(path_info):
    handler = HANDLERS.get(path_info.type)
    if not handler:
        raise ValueError(f"No handler for path type '{path_info.type}'")
    return handler


def unfurl(event, context):
    session = requests.Session()
    session.headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "User-Agent": "GitLab Unfurly"}
    slack = SlackClient(SLACK_TOKEN)

    request_json = json.loads(event["body"])

    # handle Slack url verification
    if request_json["type"] == "url_verification":
        return {
            "statusCode": 200,
            "body": request_json["challenge"],
            "headers": {"content-type": "text/plain"},
        }

    # handle unfurl
    for link in request_json["event"]["links"]:
        raw_url = link["url"]
        url = urlparse(raw_url.replace("\\", ""))
        log.bind(url=url)
        if "no_unfurl" in url.query:
            log.info("Skipping URL as requested")
            continue

        try:
            path_info = parse_path(url.path, url.fragment)
        except ValueError as exc:
            log.error("Can't parse path")
            continue

        try:
            handler = get_handler(path_info)
        except ValueError as exc:
            log.error("Can't get handler", error_message=exc)
            continue
        attachment = handler(session, path_info)

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
