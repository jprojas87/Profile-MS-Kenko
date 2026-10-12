from typing import ClassVar


class DomainError(Exception):
    code: ClassVar[str] = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ProfileNotFoundError(DomainError):
    code = "PROFILE_NOT_FOUND"


class ProfileAlreadyExistsError(DomainError):
    code = "PROFILE_ALREADY_EXISTS"


class AuthenticationFailedError(DomainError):
    code = "UNAUTHORIZED"
