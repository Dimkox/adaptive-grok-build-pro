from __future__ import annotations

import inspect
import socket
import subprocess
import unittest
from unittest.mock import patch

from adaptive_delivery.landing_publisher import (
    LandingPublicationUnavailable,
    LandingPublisher,
    UnavailableLandingPublisher,
)


class LandingPublisherTests(unittest.TestCase):
    def test_unavailable_publisher_denies_before_any_transport_or_artifact_access(self):
        class UnreadableArtifact:
            def __getattribute__(self, _name):
                raise AssertionError("unavailable publisher inspected artifact")

        publisher = UnavailableLandingPublisher()
        with patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("publisher opened a socket"),
        ), patch.object(
            subprocess,
            "Popen",
            side_effect=AssertionError("publisher spawned a process"),
        ), self.assertRaisesRegex(
            LandingPublicationUnavailable, "publication_unavailable"
        ):
            publisher.publish(UnreadableArtifact())

    def test_publisher_surface_has_no_destination_credential_or_success_override(self):
        self.assertTrue(isinstance(UnavailableLandingPublisher(), LandingPublisher))
        self.assertEqual(
            ("self", "artifact"),
            tuple(inspect.signature(UnavailableLandingPublisher.publish).parameters),
        )
        self.assertEqual(
            (), tuple(inspect.signature(UnavailableLandingPublisher).parameters)
        )


if __name__ == "__main__":
    unittest.main()
