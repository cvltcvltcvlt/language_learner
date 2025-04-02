from pydantic import BaseModel, Field


class Requests:

    class Complete(BaseModel):
        login: str = (Field(alias="login", min_length=4, max_length=16))
        password: str = (Field(alias="password", min_length=4, max_length=16))


class Errors:

    class UserNotFound(BaseModel):
        detail: str = "Invalid login or password."

