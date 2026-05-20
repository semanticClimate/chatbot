"""Compatibility shim for chromadb telemetry with newer posthog versions."""
from __future__ import annotations

import inspect

try:
    import posthog
except ImportError:  # pragma: no cover
    posthog = None


def _patch_posthog_capture() -> None:
    if posthog is None:
        return

    try:
        signature = inspect.signature(posthog.capture)
    except (TypeError, ValueError):
        return

    parameters = list(signature.parameters.values())
    if len(parameters) <= 1:
        return

    original_capture = posthog.capture

    def capture(*args, **kwargs):
        if len(args) == 0:
            return original_capture(**kwargs)
        if len(args) == 1:
            return original_capture(args[0], **kwargs)
        if len(args) == 3:
            user_id, event_name, properties = args
            if getattr(posthog, "disabled", False):
                return None
            if properties is None:
                properties = {}
            return original_capture(event_name, distinct_id=user_id, **{**properties, **kwargs})
        return original_capture(*args, **kwargs)

    posthog.capture = capture

    if hasattr(posthog, "Client"):
        original_client_capture = posthog.Client.capture

        def client_capture(self, *args, **kwargs):
            if len(args) == 3:
                user_id, event_name, properties = args
                if getattr(posthog, "disabled", False):
                    return None
                if properties is None:
                    properties = {}
                return original_client_capture(self, event_name, distinct_id=user_id, **{**properties, **kwargs})
            return original_client_capture(self, *args, **kwargs)

        posthog.Client.capture = client_capture


_patch_posthog_capture()
