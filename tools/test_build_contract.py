"""Unit coverage for the offline container/build contract checker."""

from check_build_contract import assert_build_contract


def test_container_and_workspace_build_contract() -> None:
    assert_build_contract()
