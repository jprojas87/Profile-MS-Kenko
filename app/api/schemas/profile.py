import uuid
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator
from pydantic.alias_generators import to_camel

from app.core.time import UtcDatetime
from app.db.models.profile import Profile
from app.domain.enums import DocumentType

E164_PATTERN = r"^\+[1-9]\d{7,14}$"
PhoneNumber = Annotated[str, StringConstraints(pattern=E164_PATTERN)]
AddressLine = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
CityName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
DepartmentName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StrictCamelModel(CamelModel):
    model_config = ConfigDict(extra="forbid")


class AddressSchema(CamelModel):
    line: str
    city: str


class EmergencyContactSchema(CamelModel):
    name: str | None
    phone: str | None


class ProfileResponse(CamelModel):
    profile_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    document_type: DocumentType
    document_number: str
    birth_date: date
    gender: str
    phone: str
    address: AddressSchema
    department: str | None
    emergency_contact: EmergencyContactSchema | None
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @classmethod
    def from_model(cls, profile: Profile) -> "ProfileResponse":
        has_emergency_contact = (
            profile.emergency_contact_name is not None
            or profile.emergency_contact_phone is not None
        )
        emergency_contact = (
            EmergencyContactSchema(
                name=profile.emergency_contact_name,
                phone=profile.emergency_contact_phone,
            )
            if has_emergency_contact
            else None
        )
        return cls(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            email=profile.email,
            first_name=profile.first_name,
            last_name=profile.last_name,
            document_type=profile.document_type,
            document_number=profile.document_number,
            birth_date=profile.birth_date,
            gender=profile.gender,
            phone=profile.phone,
            address=AddressSchema(line=profile.address_line, city=profile.city),
            department=profile.department,
            emergency_contact=emergency_contact,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )


class AddressUpdate(StrictCamelModel):
    line: AddressLine
    city: CityName


class EmergencyContactUpdate(StrictCamelModel):
    name: PersonName
    phone: PhoneNumber


class ProfileUpdateRequest(StrictCamelModel):
    """Campos editables. Los omitidos no cambian; `null` borra department o emergencyContact."""

    phone: PhoneNumber | None = None
    address: AddressUpdate | None = None
    department: DepartmentName | None = None
    emergency_contact: EmergencyContactUpdate | None = None

    @field_validator("phone", "address", mode="after")
    @classmethod
    def _reject_null_for_required(cls, value: object) -> object:
        if value is None:
            raise ValueError("no puede ser nulo")
        return value

    def to_changes(self) -> dict[str, str | None]:
        sent = self.model_fields_set
        changes: dict[str, str | None] = {}
        if "phone" in sent:
            changes["phone"] = self.phone
        if "address" in sent and self.address is not None:
            changes["address_line"] = self.address.line
            changes["city"] = self.address.city
        if "department" in sent:
            changes["department"] = self.department
        if "emergency_contact" in sent:
            if self.emergency_contact is None:
                changes["emergency_contact_name"] = None
                changes["emergency_contact_phone"] = None
            else:
                changes["emergency_contact_name"] = self.emergency_contact.name
                changes["emergency_contact_phone"] = self.emergency_contact.phone
        return changes
