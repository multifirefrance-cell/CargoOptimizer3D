"""Pruebas de CancellationToken."""

from __future__ import annotations

import threading

from cargo_optimizer.optimization.cancellation import CancellationToken


def test_initial_state_is_not_cancelled() -> None:
    token = CancellationToken()
    assert not token.is_cancelled()


def test_cancel_sets_state() -> None:
    token = CancellationToken()
    token.cancel()
    assert token.is_cancelled()


def test_cancel_from_another_thread_is_visible() -> None:
    token = CancellationToken()

    thread = threading.Thread(target=token.cancel)
    thread.start()
    thread.join()

    assert token.is_cancelled()
