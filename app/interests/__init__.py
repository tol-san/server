"""Interests module containing Interest and UserInterest models, schemas, services, and routers."""

from app.interests.models import Interest, UserInterest
from app.interests.repository import InterestRepository, interest_repository
from app.interests.router import router as interests_router
from app.interests.schemas import (
    InterestCreateRequest,
    InterestResponse,
    UserInterestsResponse,
    UserInterestsUpdateRequest,
)
from app.interests.service import InterestService, interest_service

__all__ = [
    "Interest",
    "UserInterest",
    "InterestRepository",
    "interest_repository",
    "InterestService",
    "interest_service",
    "InterestResponse",
    "InterestCreateRequest",
    "UserInterestsUpdateRequest",
    "UserInterestsResponse",
    "interests_router",
]
