from fastapi import APIRouter

from app.api.deps import CorrelationId, CurrentUserId, DbSession, EventPublisherDep
from app.api.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    user_id: CurrentUserId,
    session: DbSession,
    publisher: EventPublisherDep,
) -> ProfileResponse:
    profile = ProfileService(session, publisher).get_my_profile(user_id)
    return ProfileResponse.from_model(profile)


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    body: ProfileUpdateRequest,
    user_id: CurrentUserId,
    session: DbSession,
    publisher: EventPublisherDep,
    correlation_id: CorrelationId,
) -> ProfileResponse:
    profile = ProfileService(session, publisher).update_my_profile(
        user_id, body.to_changes(), correlation_id
    )
    return ProfileResponse.from_model(profile)
