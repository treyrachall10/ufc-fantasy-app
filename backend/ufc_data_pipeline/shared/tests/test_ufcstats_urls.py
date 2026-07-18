"""Tests for canonical UFCStats URL identity."""

from django.test import SimpleTestCase

from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url


class NormalizeUfcstatsUrlTests(SimpleTestCase):
    def test_resolves_relative_url(self) -> None:
        assert (
            normalize_ufcstats_url("/fight-details/abc")
            == "http://ufcstats.com/fight-details/abc"
        )

    def test_removes_identity_noise(self) -> None:
        variants = [
            " HTTP://UFCSTATS.COM/fight-details/abc/ ",
            "http://ufcstats.com/fight-details/abc?source=listing",
            "http://ufcstats.com/fight-details/abc#results",
            "//UFCSTATS.COM/fight-details/abc/?x=1#top",
        ]

        assert {normalize_ufcstats_url(value) for value in variants} == {
            "http://ufcstats.com/fight-details/abc"
        }

    def test_preserves_root_and_handles_empty(self) -> None:
        assert normalize_ufcstats_url("http://UFCSTATS.com/") == "http://ufcstats.com/"
        assert normalize_ufcstats_url("  ") == ""
        assert normalize_ufcstats_url(None) == ""
