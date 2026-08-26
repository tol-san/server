"""Communities module containing Community, Membership, and JoinRequest models, schemas, services, and routers."""

from app.communities.models import Community, CommunityJoinRequest, CommunityMembership
from app.communities.repository import CommunityRepository, community_repository
from app.communities.router import router as communities_router
from app.communities.schemas import (
    CommunityCreateRequest,
    CommunityDetailResponse,
    CommunityMemberItem,
    CommunityResponse,
    CommunityUpdateRequest,
    JoinActionResponse,
    JoinRequestItem,
    PaginatedCommunitiesResponse,
    PaginatedJoinRequestsResponse,
    PaginatedMembersResponse,
)
from app.communities.service import CommunityService, community_service

__all__ = [
    "Community",
    "CommunityMembership",
    "CommunityJoinRequest",
    "CommunityRepository",
    "community_repository",
    "CommunityService",
    "community_service",
    "CommunityCreateRequest",
    "CommunityUpdateRequest",
    "CommunityResponse",
    "CommunityDetailResponse",
    "PaginatedCommunitiesResponse",
    "CommunityMemberItem",
    "PaginatedMembersResponse",
    "JoinRequestItem",
    "PaginatedJoinRequestsResponse",
    "JoinActionResponse",
    "communities_router",
]
