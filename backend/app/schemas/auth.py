"""Authentication request and response models."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password_strength
from app.data.countries import lookup


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    country_iso: str = Field(min_length=2, max_length=2)
    dial_code: str = Field(min_length=2, max_length=8)
    phone_number: str = Field(min_length=4, max_length=15)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Enter your full name.")
        return cleaned

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("country_iso")
    @classmethod
    def clean_iso(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("dial_code")
    @classmethod
    def clean_dial(cls, value: str) -> str:
        cleaned = value.strip().replace(" ", "")
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned.lstrip('+')}"
        return cleaned

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        return re.sub(r"\D", "", value)

    @model_validator(mode="after")
    def check_password(self) -> "SignupRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        try:
            validate_password_strength(self.password)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        country = lookup(self.country_iso)
        if country is None or country.dial != self.dial_code:
            raise ValueError("Choose a country from the list.")
        if not country.min_length <= len(self.phone_number) <= country.max_length:
            raise ValueError(f"Enter a valid phone number for {country.name}.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_password(self) -> "ResetPasswordRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_strength(self.password)
        return self


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def check_password(self) -> "ChangePasswordRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_strength(self.password)
        return self


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2 or not re.fullmatch(r"[\w .'-]+", cleaned, flags=re.UNICODE):
            raise ValueError("Enter a valid full name.")
        return cleaned


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    is_verified: bool
    country_iso: str | None = None
    dial_code: str | None = None
    phone_number: str | None = None
    phone_e164: str | None = None

    model_config = {"from_attributes": True}


class CountryResponse(BaseModel):
    iso: str
    name: str
    dial: str
    min: int
    max: int


class MessageResponse(BaseModel):
    message: str
    reset_token: str | None = None
    verification_token: str | None = None
