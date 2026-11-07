"""Authentication routes."""

from fastapi import APIRouter, Request, Response, status

from app.core.deps import CurrentUser, DbSession
from app.data.countries import as_public
from app.schemas.auth import (
    ChangePasswordRequest,
    CountryResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ProfileUpdate,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/countries", response_model=list[CountryResponse])
def countries() -> list[dict[str, str | int]]:
    return as_public()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, response: Response, db: DbSession) -> UserResponse:
    return auth_service.signup(db, payload, response)


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: DbSession) -> UserResponse:
    return auth_service.login(db, payload, response, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> Response:
    auth_service.logout(db, request, response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
def update_me(payload: ProfileUpdate, user: CurrentUser, db: DbSession) -> UserResponse:
    return auth_service.update_profile(db, user, payload)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    response: Response,
    request: Request,
    db: DbSession,
) -> MessageResponse:
    return auth_service.change_password(db, user, payload, response, request)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: DbSession) -> MessageResponse:
    return auth_service.forgot_password(db, payload, request)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    return auth_service.reset_password(db, payload)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: DbSession) -> MessageResponse:
    return auth_service.verify_email(db, payload)
