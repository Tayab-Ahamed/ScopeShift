import pytest

from scopeshift import approvers


@pytest.fixture(autouse=True)
def configured_approver(monkeypatch):
    monkeypatch.setattr(approvers, "load_approvers", lambda: [
        {"name": "Priya Nair", "email": "priya@example.com", "channel": "email"}
    ])


@pytest.mark.parametrize("sender", [
    "Priya", "a", "Nair", "Mallory Priya Nair", "Priya Nair (Product Owner)",
    "priya@example.com.attacker.test",
    "attacker+priya@example.com", "priya@example", "example.com",
])
def test_partial_or_embedded_identity_cannot_authorize_scope(sender):
    assert not approvers.is_sender_allowlisted(sender, "email")


@pytest.mark.parametrize("sender", ["Priya Nair", " PRIYA NAIR ", "priya@example.com"])
def test_exact_normalized_identity_remains_authorized(sender):
    assert approvers.is_sender_allowlisted(sender, "email")


def test_exact_identity_must_still_match_configured_channel():
    assert not approvers.is_sender_allowlisted("Priya Nair", "slack")
