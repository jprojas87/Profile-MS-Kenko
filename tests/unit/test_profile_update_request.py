import pytest
from pydantic import ValidationError

from app.api.schemas.profile import ProfileUpdateRequest


def test_empty_body_has_no_changes() -> None:
    assert ProfileUpdateRequest.model_validate({}).to_changes() == {}


def test_only_sent_fields_are_mapped_to_columns() -> None:
    request = ProfileUpdateRequest.model_validate({"phone": "+573109876543"})

    assert request.to_changes() == {"phone": "+573109876543"}


def test_address_maps_to_address_line_and_city() -> None:
    request = ProfileUpdateRequest.model_validate(
        {"address": {"line": "Cra 7 # 45-12 Apto 301", "city": "Bogotá"}}
    )

    assert request.to_changes() == {
        "address_line": "Cra 7 # 45-12 Apto 301",
        "city": "Bogotá",
    }


def test_null_emergency_contact_clears_both_columns() -> None:
    request = ProfileUpdateRequest.model_validate({"emergencyContact": None})

    assert request.to_changes() == {
        "emergency_contact_name": None,
        "emergency_contact_phone": None,
    }


def test_null_department_clears_it() -> None:
    request = ProfileUpdateRequest.model_validate({"department": None})

    assert request.to_changes() == {"department": None}


@pytest.mark.parametrize(
    "field", ["email", "documentNumber", "documentType", "birthDate", "userId"]
)
def test_non_editable_fields_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate({field: "x"})


@pytest.mark.parametrize("phone", ["3001234567", "+57 300 123 4567", "+0123456789", "+57"])
def test_phone_must_be_e164(phone: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate({"phone": phone})


@pytest.mark.parametrize("body", [{"phone": None}, {"address": None}])
def test_required_fields_cannot_be_null(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate(body)


def test_address_requires_city() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate({"address": {"line": "Cra 1"}})


def test_emergency_contact_requires_name_and_phone() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate({"emergencyContact": {"name": "Luis"}})
