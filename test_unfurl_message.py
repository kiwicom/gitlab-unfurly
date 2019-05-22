import pytest
import requests

import unfurl_message as uut
from urllib.parse import urljoin



@pytest.mark.parametrize(
    "path, fragment, info",
    [
        ("/platform/zoo", None, uut.PathInfo(uut.PathType.PROJECT, "platform", "zoo")),
        (
            "/dev-ops/crane/issues/6",
            None,
            uut.PathInfo(uut.PathType.ISSUE, "dev-ops", "crane", "6"),
        ),
        (
            "/cia/gun/merge_requests/4",
            None,
            uut.PathInfo(uut.PathType.MERGE_REQUEST, "cia", "gun", "4"),
        ),
        (
            "/ITC/crane/commit/iddqd",
            None,
            uut.PathInfo(uut.PathType.COMMIT, "ITC", "crane", "iddqd"),
        ),
        (
            "/fbi/a/b/c/jail",
            None,
            uut.PathInfo(uut.PathType.PROJECT, "fbi", "jail", None, "a/b/c"),
        ),
        (
            "/planets/solar-system/earth/issues/9",
            None,
            uut.PathInfo(uut.PathType.ISSUE, "planets", "earth", "9", "solar-system"),
        ),
        (
            "/sea/deep/fish/merge_requests/31",
            None,
            uut.PathInfo(uut.PathType.MERGE_REQUEST, "sea", "fish", "31", "deep"),
        ),
        (
            "/kiwi/x/y/com/commit/abcdef",
            None,
            uut.PathInfo(uut.PathType.COMMIT, "kiwi", "com", "abcdef", "x/y"),
        ),
        (
            "/kiwi/com/pipelines/2134",
            None,
            uut.PathInfo(uut.PathType.PIPELINE, "kiwi", "com", "2134"),
        ),
        (
            "/kiwi/x/y/com/pipelines/2134",
            None,
            uut.PathInfo(uut.PathType.PIPELINE, "kiwi", "com", "2134", "x/y"),
        ),
        (
            "/kiwi/com/-/jobs/2134",
            None,
            uut.PathInfo(uut.PathType.JOB, "kiwi", "com", "2134"),
        ),
        (
            "/kiwi/x/y/com/-/jobs/2134",
            None,
            uut.PathInfo(uut.PathType.JOB, "kiwi", "com", "2134", "x/y"),
        ),
        (
            "/kiwi/com/issues/37",
            "note_746624",
            uut.PathInfo(uut.PathType.NOTE_ISSUE, "kiwi", "com", "37", None, "746624"),
        ),
        (
            "/kiwi/x/y/com/issues/37",
            "note_746624",
            uut.PathInfo(uut.PathType.NOTE_ISSUE, "kiwi", "com", "37", "x/y", "746624"),
        ),
        (
            "/kiwi/com/merge_requests/8",
            "note_861109",
            uut.PathInfo(
                uut.PathType.NOTE_MERGE_REQUESTS, "kiwi", "com", "8", None, "861109"
            ),
        ),
        (
            "/kiwi/x/y/com/merge_requests/8",
            "note_861109",
            uut.PathInfo(
                uut.PathType.NOTE_MERGE_REQUESTS, "kiwi", "com", "8", "x/y", "861109"
            ),
        ),
    ],
)
def test_parse_path(path, fragment, info):
    assert uut.parse_path(path, fragment) == info

    if not path.endswith("/"):
        assert uut.parse_path(f"{path}/", fragment) == info


def test_parse_path__wrong():
    with pytest.raises(ValueError):
        uut.parse_path("/mario")


@pytest.mark.parametrize(
    "info, expected",
    [
        (uut.PathInfo(uut.PathType.PROJECT, "games", "doom"), "games%2Fdoom"),
        (
            uut.PathInfo(uut.PathType.PROJECT, "heroes", "pool", subgroups="d/e/a/d"),
            "heroes%2Fd%2Fe%2Fa%2Fd%2Fpool",
        ),
    ],
)
def test_path_info__quoted_id(info, expected):
    assert info.quoted_id == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("foo", "foo"),
        ("has multiple words", "has multiple words"),
        ("has <b>some</b> tags", "has some tags"),
        ("<IMG SRC=j&#X41vascript:alert('test2')>", ""),
        ("has <!-- secret --> comment", "has  comment"),
    ],
)
def test_strip_html_tags(value, expected):
    assert uut.strip_html_tags(value) == expected


def test_prepare_description():
    description = (
        "I'd just like to interject for a moment. <!-- Yes please! --> What you’re "
        "referring to as Linux, is in fact, <b>GNU/Linux</b>, or as I’ve recently "
        "taken to calling it, GNU plus Linux."
    )
    expected = (
        "I'd just like to interject for a moment. What you’re referring to as "
        "Linux, is in fact, GNU/Linux,…"
    )
    assert uut.prepare_description(description) == expected


def test_prepare_description__custom_width():
    description = "Correct Horse Battery Staple"
    expected = "Correct Horse…"
    assert uut.prepare_description(description, width=15) == expected


@pytest.mark.parametrize(
    ("path_info", "handler"),
    [
        (
            uut.PathInfo(uut.PathType.ISSUE, "dev-ops", "crane", "6"),
            uut.get_issues_info,
        ),
        (
            uut.PathInfo(uut.PathType.PIPELINE, "kiwi", "com", "2134", "x/y"),
            uut.get_pipelines_info,
        ),
        (uut.PathInfo(uut.PathType.JOB, "kiwi", "com", "2134"), uut.get_jobs_info),
        (
            uut.PathInfo(uut.PathType.COMMIT, "kiwi", "com", "abcdef", "x/y"),
            uut.get_commit_info,
        ),
        (
            uut.PathInfo(uut.PathType.MERGE_REQUEST, "sea", "fish", "31", "deep"),
            uut.get_merge_requests_info,
        ),
        (
            uut.PathInfo(uut.PathType.PROJECT, "fbi", "jail", None, "a/b/c"),
            uut.get_project_info,
        ),
        (
            uut.PathInfo(uut.PathType.NOTE_ISSUE, "kiwi", "com", "37", "x/y", "746624"),
            uut.get_note_issues_info,
        ),
        (
            uut.PathInfo(
                uut.PathType.NOTE_MERGE_REQUESTS, "kiwi", "com", "8", None, "861109"
            ),
            uut.get_note_merge_requests_info,
        ),
    ],
)
def test_get_handler(path_info, handler):
    assert uut.get_handler(path_info) == handler



@pytest.mark.parametrize(
    ("name", "api_resp", "want", "want_error"),
    [
        (
                "should return nothing for empty api response",
                '{}',
                None,
                KeyError
        ),
        (
            "happy path",
            """
            {
               "id":1,
               "iid":1,
               "project_id":3,
               "title":"test1",
               "description":"fixed login page css paddings",
               "state":"merged",
               "created_at":"2017-04-29T08:46:00Z",
               "updated_at":"2017-04-29T08:46:00Z",
               "target_branch":"master",
               "source_branch":"test1",
               "upvotes":0,
               "downvotes":0,
               "author":{
                  "id":1,
                  "name":"Administrator",
                  "username":"admin",
                  "state":"active",
                  "avatar_url":null,
                  "web_url":"https://gitlab.example.com/admin"
               },
               "user":{
                  "can_merge":false
               },
               "assignee":{
                  "id":1,
                  "name":"Administrator",
                  "username":"admin",
                  "state":"active",
                  "avatar_url":null,
                  "web_url":"https://gitlab.example.com/admin"
               },
               "assignees":[
                  {
                     "name":"Miss Monserrate Beier",
                     "username":"axel.block",
                     "id":12,
                     "state":"active",
                     "avatar_url":"http://www.gravatar.com/avatar/46f6f7dc858ada7be1853f7fb96e81da?s=80&d=identicon",
                     "web_url":"https://gitlab.example.com/axel.block"
                  }
               ],
               "source_project_id":2,
               "target_project_id":3,
               "labels":[
                  "Community contribution",
                  "Manage"
               ],
               "work_in_progress":false,
               "milestone":{
                  "id":5,
                  "iid":1,
                  "project_id":3,
                  "title":"v2.0",
                  "description":"Assumenda aut placeat expedita exercitationem labore sunt enim earum.",
                  "state":"closed",
                  "created_at":"2015-02-02T19:49:26.013Z",
                  "updated_at":"2015-02-02T19:49:26.013Z",
                  "due_date":"2018-09-22",
                  "start_date":"2018-08-08",
                  "web_url":"https://gitlab.example.com/my-group/my-project/milestones/1"
               },
               "merge_when_pipeline_succeeds":true,
               "merge_status":"can_be_merged",
               "merge_error":null,
               "sha":"8888888888888888888888888888888888888888",
               "merge_commit_sha":null,
               "user_notes_count":1,
               "discussion_locked":null,
               "should_remove_source_branch":true,
               "force_remove_source_branch":false,
               "allow_collaboration":false,
               "allow_maintainer_to_push":false,
               "web_url":"http://gitlab.example.com/my-group/my-project/merge_requests/1",
               "time_stats":{
                  "time_estimate":0,
                  "total_time_spent":0,
                  "human_time_estimate":null,
                  "human_total_time_spent":null
               },
               "squash":false,
               "subscribed":false,
               "changes_count":"1",
               "merged_by":{
                  "id":87854,
                  "name":"Douwe Maan",
                  "username":"DouweM",
                  "state":"active",
                  "avatar_url":"https://gitlab.example.com/uploads/-/system/user/avatar/87854/avatar.png",
                  "web_url":"https://gitlab.com/DouweM"
               },
               "merged_at":"2018-09-07T11:16:17.520Z",
               "closed_by":null,
               "closed_at":null,
               "latest_build_started_at":"2018-09-07T07:27:38.472Z",
               "latest_build_finished_at":"2018-09-07T08:07:06.012Z",
               "first_deployed_to_production_at":null,
               "pipeline":{
                  "id":29626725,
                  "sha":"2be7ddb704c7b6b83732fdd5b9f09d5a397b5f8f",
                  "ref":"patch-28",
                  "status":"success",
                  "web_url":"https://gitlab.example.com/my-group/my-project/pipelines/29626725"
               },
               "diff_refs":{
                  "base_sha":"c380d3acebd181f13629a25d2e2acca46ffe1e00",
                  "head_sha":"2be7ddb704c7b6b83732fdd5b9f09d5a397b5f8f",
                  "start_sha":"c380d3acebd181f13629a25d2e2acca46ffe1e00"
               },
               "diverged_commits_count":2,
               "rebase_in_progress":false,
               "approvals_before_merge":null
            }
            """,
            {
                "author_name": 'admin',
                "author_link": 'https://gitlab.example.com/admin',
                "author_icon": None,
                "title": 'test1 (merged)',
                "fields": [
                    {"title": "Assignee", "value": "admin", "short": "true"},
                    {"title": "Diffs", "value": '1', "short": "true"},
                    {
                        "title": "Milestone",
                        "value": '<https://gitlab.example.com/my-group/my-project/milestones/1|v2.0>',
                        "short": "true",
                    }
                ],
                "text": "fixed login page css paddings",
                "color": '#1f78d1',
                "ts": 1493455560,
                "footer": "Merge Request",
            },
            None
        )
    ],
)
def test_get_merge_requests_info(requests_mock, name, api_resp, want, want_error):
    pi = uut.PathInfo(uut.PathType.MERGE_REQUEST, "test_team","test_project","test_id", "test_subgroup")
    api_path =  f"/api/v4/projects/{pi.quoted_id}/merge_requests/{pi.identifier}"
    uut.GITLAB_URL = 'http://192.0.2.1:1234'

    requests_mock.get(urljoin(uut.GITLAB_URL, api_path), text=api_resp)
    s = requests.Session()

    if want_error:
        with pytest.raises(want_error):
            uut.get_merge_requests_info(s, pi)
        return
    got = uut.get_merge_requests_info(s, pi)

    assert want == got
