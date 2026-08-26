import re
import uuid
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.models import Community
from app.communities.repository import CommunityRepository, community_repository
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
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.storage import storage_service
from app.interests.repository import InterestRepository, interest_repository
from app.users.models import User


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text).strip("-")


class CommunityService:
    """Service handling community space lifecycle, memberships, and join requests."""

    def __init__(
        self,
        community_repo: CommunityRepository = community_repository,
        interest_repo: InterestRepository = interest_repository,
    ):
        self.community_repo = community_repo
        self.interest_repo = interest_repo

    async def create_community(
        self,
        db: AsyncSession,
        current_user: User,
        payload: CommunityCreateRequest,
    ) -> CommunityResponse:
        # Validate interest if provided
        if payload.interest_id:
            interest = await self.interest_repo.get_by_id(db, payload.interest_id)
            if not interest:
                raise BadRequestException("The specified interest category does not exist.")

        # Generate slug
        base_slug = payload.slug.strip() if payload.slug else slugify(payload.name)
        if not base_slug:
            base_slug = f"community-{uuid.uuid4().hex[:8]}"

        slug = base_slug
        existing = await self.community_repo.get_by_slug(db, slug)
        if existing:
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        community = await self.community_repo.create(
            db,
            owner_id=current_user.id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            interest_id=payload.interest_id,
            cover_image_url=payload.cover_image_url,
            avatar_url=payload.avatar_url,
            is_private=payload.is_private,
        )

        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.index_community(
            {
                "id": str(community.id),
                "name": community.name,
                "slug": community.slug,
                "description": community.description,
                "avatar_url": community.avatar_url,
                "cover_image_url": community.cover_image_url,
                "is_private": community.is_private,
                "owner_id": str(community.owner_id),
                "member_count": community.member_count,
                "post_count": community.post_count,
                "interest_id": str(community.interest_id) if community.interest_id else None,
                "created_at": community.created_at.isoformat() if community.created_at else None,
            }
        )

        return CommunityResponse.model_validate(community)

    async def get_community(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> CommunityDetailResponse:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        is_member = False
        is_owner = False
        membership_role = None
        join_request_status = None

        if current_user:
            is_owner = community.owner_id == current_user.id
            membership = await self.community_repo.get_membership(db, community.id, current_user.id)
            if membership:
                is_member = True
                membership_role = membership.role
            else:
                req = await self.community_repo.get_join_request(db, community.id, current_user.id)
                if req:
                    join_request_status = req.status

        resp = CommunityDetailResponse.model_validate(community)
        resp.is_member = is_member
        resp.is_owner = is_owner
        resp.membership_role = membership_role
        resp.join_request_status = join_request_status
        return resp

    async def update_community(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
        payload: CommunityUpdateRequest,
    ) -> CommunityResponse:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can update community settings.")

        if payload.interest_id is not None:
            interest = await self.interest_repo.get_by_id(db, payload.interest_id)
            if not interest:
                raise BadRequestException("The specified interest category does not exist.")

        updates = payload.model_dump(exclude_unset=True)
        updated_community = await self.community_repo.update(db, community, **updates)

        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.index_community(
            {
                "id": str(updated_community.id),
                "name": updated_community.name,
                "slug": updated_community.slug,
                "description": updated_community.description,
                "avatar_url": updated_community.avatar_url,
                "cover_image_url": updated_community.cover_image_url,
                "is_private": updated_community.is_private,
                "owner_id": str(updated_community.owner_id),
                "member_count": updated_community.member_count,
                "post_count": updated_community.post_count,
                "interest_id": str(updated_community.interest_id) if updated_community.interest_id else None,
                "created_at": updated_community.created_at.isoformat() if updated_community.created_at else None,
            }
        )

        return CommunityResponse.model_validate(updated_community)

    async def delete_community(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can delete the community.")

        # Clean up cover image from MinIO if exists
        if community.cover_image_url:
            storage_service.delete_file_by_url(community.cover_image_url)
        if community.avatar_url:
            storage_service.delete_file_by_url(community.avatar_url)

        await self.community_repo.delete(db, community)

        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.delete_community(community_id)

        return {"message": f"Community '{community.name}' has been deleted."}

    async def list_communities(
        self,
        db: AsyncSession,
        search: Optional[str] = None,
        interest_id: Optional[uuid.UUID] = None,
        is_private: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedCommunitiesResponse:
        communities, total = await self.community_repo.list_communities(
            db,
            search=search,
            interest_id=interest_id,
            is_private=is_private,
            limit=limit,
            offset=offset,
        )
        items = [CommunityResponse.model_validate(c) for c in communities]
        return PaginatedCommunitiesResponse(items=items, total=total, limit=limit, offset=offset)

    async def list_my_communities(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedCommunitiesResponse:
        communities, total = await self.community_repo.list_user_communities(
            db,
            current_user.id,
            limit=limit,
            offset=offset,
        )
        items = [CommunityResponse.model_validate(c) for c in communities]
        return PaginatedCommunitiesResponse(items=items, total=total, limit=limit, offset=offset)

    async def upload_cover_image(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
        file: UploadFile,
    ) -> CommunityResponse:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can update the cover image.")

        raw_bytes = await file.read()
        if len(raw_bytes) > 5 * 1024 * 1024:
            raise BadRequestException("Cover image exceeds maximum size of 5MB.")

        # Convert to WebP (max width 1200px)
        webp_bytes = storage_service.process_and_convert_to_webp(raw_bytes, max_dimension=1200)

        # Remove old cover
        if community.cover_image_url:
            storage_service.delete_file_by_url(community.cover_image_url)

        object_name = f"communities/{community_id}/cover_{uuid.uuid4()}.webp"
        cover_url = storage_service.upload_file(
            file_data=webp_bytes,
            object_name=object_name,
            content_type="image/webp",
        )

        community.cover_image_url = cover_url
        await db.commit()
        await db.refresh(community)
        return CommunityResponse.model_validate(community)

    # --- Memberships & Workflows ---

    async def join_community(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
    ) -> JoinActionResponse:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        # Check if already a member
        existing_membership = await self.community_repo.get_membership(db, community_id, current_user.id)
        if existing_membership:
            raise BadRequestException("You are already a member of this community.")

        # Public community: instant join
        if not community.is_private:
            await self.community_repo.add_member(db, community_id, current_user.id, role="member")
            return JoinActionResponse(
                status="joined",
                message=f"You have joined {community.name}.",
                is_member=True,
            )

        # Private community: submit join request
        existing_req = await self.community_repo.get_join_request(db, community_id, current_user.id)
        if existing_req:
            return JoinActionResponse(
                status="pending",
                message="Your join request is already pending approval by the owner.",
                is_member=False,
            )

        await self.community_repo.create_join_request(db, community_id, current_user.id)
        return JoinActionResponse(
            status="pending",
            message="Join request submitted and waiting for owner approval.",
            is_member=False,
        )

    async def leave_community(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id == current_user.id:
            raise BadRequestException("The community owner cannot leave the community.")

        removed = await self.community_repo.remove_member(db, community_id, current_user.id)
        if not removed:
            raise BadRequestException("You are not a member of this community.")

        return {"message": f"You have left {community.name}."}

    async def list_members(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedMembersResponse:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        memberships, total = await self.community_repo.get_members(db, community_id, limit, offset)
        items = [
            CommunityMemberItem(
                id=m.id,
                user_id=m.user_id,
                username=m.user.username,
                display_name=m.user.profile.display_name if m.user.profile else m.user.username,
                avatar_url=m.user.profile.avatar_url if m.user.profile else None,
                role=m.role,
                joined_at=m.created_at,
            )
            for m in memberships
        ]
        return PaginatedMembersResponse(items=items, total=total, limit=limit, offset=offset)

    async def kick_member(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
        target_user_id: uuid.UUID,
    ) -> dict:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can remove members.")

        if target_user_id == community.owner_id:
            raise BadRequestException("Cannot remove the community owner.")

        removed = await self.community_repo.remove_member(db, community_id, target_user_id)
        if not removed:
            raise NotFoundException("User is not a member of this community.")

        # Publish control event so the WS gateway terminates the kicked user's connection
        try:
            import json as _json
            from app.core.redis import get_redis_client
            r = get_redis_client()
            control_event = _json.dumps({
                "type": "membership.revoked",
                "user_id": str(target_user_id),
                "community_id": str(community_id),
                "reason": "kicked",
            })
            await r.publish(f"pubsub:chat:{community_id}:control", control_event)
        except Exception:
            pass  # Non-critical: DB membership already removed

        return {"message": "Member has been removed from the community."}

    async def list_join_requests(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedJoinRequestsResponse:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can view join requests.")

        requests, total = await self.community_repo.get_pending_requests(db, community_id, limit, offset)
        items = [
            JoinRequestItem(
                id=r.id,
                user_id=r.user_id,
                username=r.user.username,
                display_name=r.user.profile.display_name if r.user.profile else r.user.username,
                avatar_url=r.user.profile.avatar_url if r.user.profile else None,
                status=r.status,
                created_at=r.created_at,
            )
            for r in requests
        ]
        return PaginatedJoinRequestsResponse(items=items, total=total, limit=limit, offset=offset)

    async def approve_join_request(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        request_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can approve join requests.")

        join_req = await self.community_repo.get_join_request_by_id(db, request_id)
        if not join_req or join_req.community_id != community_id:
            raise NotFoundException("Join request not found.")

        # Add member
        await self.community_repo.add_member(db, community_id, join_req.user_id, role="member")
        # Remove join request
        await self.community_repo.delete_join_request(db, join_req)

        from app.notifications.service import notification_service
        await notification_service.notify_user(
            db,
            recipient_id=join_req.user_id,
            actor_id=current_user.id,
            notification_type="community_join_approved",
            title="Join Request Approved",
            message=f"Your request to join {community.name} was approved!",
            entity_type="community",
            entity_id=community.id,
        )

        return {"message": "Join request approved. User is now a member."}

    async def reject_join_request(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        request_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        community = await self.community_repo.get_by_id(db, community_id)
        if not community:
            raise NotFoundException("Community not found.")

        if community.owner_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the community owner can reject join requests.")

        join_req = await self.community_repo.get_join_request_by_id(db, request_id)
        if not join_req or join_req.community_id != community_id:
            raise NotFoundException("Join request not found.")

        await self.community_repo.delete_join_request(db, join_req)
        return {"message": "Join request rejected."}


community_service = CommunityService()
