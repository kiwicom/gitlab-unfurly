import pytest

import unfurl_message as uut


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
