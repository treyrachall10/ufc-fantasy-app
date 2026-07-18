"""Tests for canonical UFCStats URL identity."""

from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url


def test_normalize_ufcstats_url_resolves_relative_url() -> None:
    assert (
        normalize_ufcstats_url("/fight-details/abc")
        == "http://ufcstats.com/fight-details/abc"
    )


def test_normalize_ufcstats_url_removes_identity_noise() -> None:
    variants = [
        " HTTP://UFCSTATS.COM/fight-details/abc/ ",
        "http://ufcstats.com/fight-details/abc?source=listing",
        "http://ufcstats.com/fight-details/abc#results",
        "//UFCSTATS.COM/fight-details/abc/?x=1#top",
    ]

    assert {
        normalize_ufcstats_url(value)
        for value in variants
    } == {"http://ufcstats.com/fight-details/abc"}


def test_normalize_ufcstats_url_preserves_root_and_handles_empty() -> None:
    assert normalize_ufcstats_url("http://UFCSTATS.com/") == "http://ufcstats.com/"
    assert normalize_ufcstats_url("  ") == ""
    assert normalize_ufcstats_url(None) == ""
