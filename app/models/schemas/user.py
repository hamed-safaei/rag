from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    username: str


class UserRead(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)



class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserRefreshToken(BaseModel):
    token: str