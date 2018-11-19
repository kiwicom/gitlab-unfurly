import pytest

import unfurl_message as uut


@pytest.mark.parametrize("trailing_slash", [True, False])
@pytest.mark.parametrize(
    "path, info",
    [
        ("/kiwicom/zoo", uut.PathInfo(uut.PathType.PROJECT, "kiwicom", "zoo")),
        (
            "/dev-ops/crane/issues/6",
            uut.PathInfo(uut.PathType.ISSUE, "dev-ops", "crane", "6"),
        ),
        (
            "/orbit/components/merge_requests/9",
            uut.PathInfo(uut.PathType.MERGE_REQUEST, "orbit", "components", "9"),
        ),
        (
            "/ITC/crane/commit/iddqd",
            uut.PathInfo(uut.PathType.COMMIT, "ITC", "crane", "iddqd"),
        ),
        (
            "/fbi/a/b/c/jail",
            uut.PathInfo(uut.PathType.PROJECT, "fbi", "jail", None, "a/b/c"),
        ),
        (
            "/planets/solar-system/earth/issues/42",
            uut.PathInfo(uut.PathType.ISSUE, "planets", "earth", "42", "solar-system"),
        ),
        (
            "/sea/deep/fish/merge_requests/31",
            uut.PathInfo(uut.PathType.MERGE_REQUEST, "sea", "fish", "31", "deep"),
        ),
        (
            "/kiwi/x/y/com/commit/abcdef",
            uut.PathInfo(uut.PathType.COMMIT, "kiwi", "com", "abcdef", "x/y"),
        ),
    ],
)
def test_parse_path(trailing_slash, path, info):
    if trailing_slash:
        path = f"{path}/"
    assert uut.parse_path(path) == info


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
