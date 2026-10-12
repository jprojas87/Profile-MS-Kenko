import uuid

import uuid_utils


def new_uuid7() -> uuid.UUID:
    return uuid.UUID(str(uuid_utils.uuid7()))
