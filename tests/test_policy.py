import pytest

from authority.policy import PolicyViolation, QueryPolicy


def test_allows_aggregate_stars_question():
    QueryPolicy().authorize_question("Show contract-level Stars measure decline")


@pytest.mark.parametrize("term", ["member name", "DOB", "member id", "address"])
def test_denies_phi_requests(term):
    with pytest.raises(PolicyViolation):
        QueryPolicy().authorize_question(f"Show the {term} behind this Stars decline")


def test_enforces_byte_ceiling():
    with pytest.raises(PolicyViolation):
        QueryPolicy(maximum_bytes_billed=10).authorize_dry_run(11)


def test_rejects_identifier_injection():
    with pytest.raises(PolicyViolation):
        QueryPolicy(dataset="safe`; DROP TABLE x; --").validate_identifiers()

