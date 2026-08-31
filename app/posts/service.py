import uuid
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.repository import CommunityRepository, community_repository
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.storage import storage_service
from app.posts.models import Post
from app.posts.access import require_post_view
from app.posts.repository import PostRepository, post_repository
from app.posts.schemas import (
    MediaItemResponse,
    MediaUploadResponse,
    PaginatedPostsResponse,
    PaginatedSavedPostsResponse,
    PostAuthorResponse,
    PostCommunityResponse,
    PostCreateRequest,
    PostLikeResponse,
    PostReactionsResponse,
    PostResponse,
    PostSaveResponse,
    PostShareResponse,
    PostUpdateRequest,
    ReactorUserResponse,
)
from app.users.models import User

ALLOWED_POST_TYPES = {"text", "image", "video"}
ALLOWED_VISIBILITY = {"public", "followers_only", "private"}


async def sync_post_search_index(post: Post) -> None:
    """Keep only globally discoverable posts in the external search index."""
    from app.core.meilisearch import meilisearch_service

    is_indexable = post.visibility == "public" and (
        post.community is None or not post.community.is_private
    )
    if not is_indexable:
        await meilisearch_service.delete_post(post.id)
        return

    await meilisearch_service.index_post(
        {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "post_type": post.post_type,
            "visibility": post.visibility,
            "author_id": str(post.author_id),
            "author_username": post.author.username if post.author else None,
            "community_id": str(post.community_id) if post.community_id else None,
            "community_name": post.community.name if post.community else None,
            "like_count": post.like_count,
            "comment_count": post.comment_count,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
    )


def map_post_to_response(
    post: Post,
    *,
    is_liked: bool = False,
    is_saved: bool = False,
) -> PostResponse:
    author = PostAuthorResponse(
        id=post.author.id,
        username=post.author.username,
        display_name=post.author.profile.display_name if post.author.profile else post.author.username,
        avatar_url=post.author.profile.avatar_url if post.author.profile else None,
    )
    community = None
    if post.community:
        community = PostCommunityResponse(
            id=post.community.id,
            name=post.community.name,
            slug=post.community.slug,
            avatar_url=post.community.avatar_url,
        )
    media = [
        MediaItemResponse(
            id=m.id,
            media_type=m.media_type,
            url=storage_service.get_post_media_url(m.url),
            thumbnail_url=storage_service.get_post_media_url(m.thumbnail_url),
            duration=m.duration,
            width=m.width,
            height=m.height,
            order=m.order,
        )
        for m in post.media_items
    ]
    return PostResponse(
        id=post.id,
        author=author,
        community=community,
        post_type=post.post_type,
        title=post.title,
        content=post.content,
        visibility=post.visibility,
        media=media,
        like_count=post.like_count,
        comment_count=post.comment_count,
        share_count=post.share_count,
        save_count=post.save_count,
        is_liked=is_liked,
        is_saved=is_saved,
        created_at=post.created_at,
    )


class PostService:
    """Service handling multi-format post creation, context ownership, feeds, and moderation."""

    def __init__(
        self,
        post_repo: PostRepository = post_repository,
        community_repo: CommunityRepository = community_repository,
    ):
        self.post_repo = post_repo
        self.community_repo = community_repo

    async def create_post(
        self,
        db: AsyncSession,
        current_user: User,
        payload: PostCreateRequest,
    ) -> PostResponse:
        # 1. Validate post type
        if payload.post_type not in ALLOWED_POST_TYPES:
            raise BadRequestException(f"Invalid post type '{payload.post_type}'. Allowed: {', '.join(ALLOWED_POST_TYPES)}")

        # 2. Validate visibility
        if payload.visibility not in ALLOWED_VISIBILITY:
            raise BadRequestException(f"Invalid visibility '{payload.visibility}'. Allowed: {', '.join(ALLOWED_VISIBILITY)}")

        # 3. Community ownership & membership validation
        if payload.community_id:
            community = await self.community_repo.get_by_id(db, payload.community_id)
            if not community:
                raise NotFoundException("The specified community does not exist.")

            membership = await self.community_repo.get_membership(db, payload.community_id, current_user.id)
            if not membership and not current_user.is_superuser:
                raise ForbiddenException("You must be a member of the community to create a community post.")

        # 4. Validate media constraints
        if payload.post_type == "image":
            if not payload.media or len(payload.media) == 0:
                raise BadRequestException("Image post must contain at least one image.")
            if len(payload.media) > 10:
                raise BadRequestException("Image post cannot contain more than 10 images.")

        if payload.post_type == "video":
            if not payload.media or len(payload.media) != 1:
                raise BadRequestException("Video post must contain exactly one video.")

        normalized_media = None
        if payload.media:
            normalized_media = []
            for item in payload.media:
                if item.media_type not in {"image", "video"}:
                    raise BadRequestException("Media type must be image or video.")
                if item.media_type != payload.post_type:
                    raise BadRequestException(
                        "Every media item must match the post type."
                    )
                normalized_media.append(
                    item.model_copy(
                        update={
                            "url": storage_service.normalize_owned_post_media_url(
                                current_user.id, item.url, item.media_type
                            ),
                            "thumbnail_url": (
                                storage_service.normalize_owned_post_media_url(
                                    current_user.id,
                                    item.thumbnail_url,
                                    "image",
                                )
                                if item.thumbnail_url
                                else None
                            ),
                        }
                    )
                )

        # 5. Persist post
        post = await self.post_repo.create(
            db,
            author_id=current_user.id,
            community_id=payload.community_id,
            post_type=payload.post_type,
            title=payload.title,
            content=payload.content,
            visibility=payload.visibility,
            media=normalized_media,
        )

        await sync_post_search_index(post)

        return map_post_to_response(post)

    async def get_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> PostResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)
        is_liked = is_saved = False
        if current_user:
            liked, saved = await self.post_repo.get_viewer_engagement(
                db, current_user.id, [post.id]
            )
            is_liked = post.id in liked
            is_saved = post.id in saved
        return map_post_to_response(post, is_liked=is_liked, is_saved=is_saved)

    async def update_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
        payload: PostUpdateRequest,
    ) -> PostResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")

        if post.author_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the author can edit this post.")

        if payload.visibility and payload.visibility not in ALLOWED_VISIBILITY:
            raise BadRequestException(f"Invalid visibility '{payload.visibility}'.")

        updates = payload.model_dump(exclude_unset=True)
        updated_post = await self.post_repo.update(db, post, **updates)

        await sync_post_search_index(updated_post)

        return map_post_to_response(updated_post)

    async def delete_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")

        # Check authorization: Author, Community Owner, or Superuser
        is_author = post.author_id == current_user.id
        is_comm_owner = post.community and post.community.owner_id == current_user.id
        is_admin = current_user.is_superuser

        if not (is_author or is_comm_owner or is_admin):
            raise ForbiddenException("You do not have permission to delete this post.")

        # Cleanup media files from MinIO
        for item in post.media_items:
            await storage_service.delete_file_by_url(item.url)
            if item.thumbnail_url:
                await storage_service.delete_file_by_url(item.thumbnail_url)

        await self.post_repo.delete(db, post)

        from app.core.meilisearch import meilisearch_service
        await meilisearch_service.delete_post(post_id)

        return {"message": "Post has been deleted successfully."}

    async def list_posts(
        self,
        db: AsyncSession,
        *,
        author_id: Optional[uuid.UUID] = None,
        community_id: Optional[uuid.UUID] = None,
        post_type: Optional[str] = None,
        visibility: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        current_user: Optional[User] = None,
    ) -> PaginatedPostsResponse:
        posts, total = await self.post_repo.list_posts(
            db,
            author_id=author_id,
            community_id=community_id,
            post_type=post_type,
            visibility=visibility,
            search=search,
            viewer_id=current_user.id if current_user else None,
            viewer_is_superuser=bool(current_user and current_user.is_superuser),
            limit=limit,
            offset=offset,
        )
        liked: set[uuid.UUID] = set()
        saved: set[uuid.UUID] = set()
        if current_user:
            liked, saved = await self.post_repo.get_viewer_engagement(
                db, current_user.id, [post.id for post in posts]
            )
        items = [
            map_post_to_response(
                post,
                is_liked=post.id in liked,
                is_saved=post.id in saved,
            )
            for post in posts
        ]
        return PaginatedPostsResponse(items=items, total=total, limit=limit, offset=offset)

    async def upload_media(
        self,
        db: AsyncSession,
        current_user: User,
        file: UploadFile,
    ) -> MediaUploadResponse:
        upload_result = await storage_service.upload_post_media(current_user.id, file)
        return MediaUploadResponse(**upload_result)

    # Engagement service methods
    async def like_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
    ) -> PostLikeResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)

        liked, count = await self.post_repo.like_post(db, current_user.id, post)
        from app.core.cache import cache_service
        await cache_service.set(f"cache:post:{post.id}:like_count", count, ttl=300)

        if liked and post.author_id != current_user.id:
            from app.notifications.service import notification_service
            await notification_service.notify_user(
                db,
                recipient_id=post.author_id,
                actor_id=current_user.id,
                notification_type="post_like",
                title="Post Liked",
                message=f"{current_user.username} liked your post.",
                entity_type="post",
                entity_id=post.id,
            )

        return PostLikeResponse(post_id=post.id, liked=liked, like_count=count)

    async def unlike_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
    ) -> PostLikeResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)

        liked, count = await self.post_repo.unlike_post(db, current_user.id, post)
        from app.core.cache import cache_service
        await cache_service.set(f"cache:post:{post.id}:like_count", count, ttl=300)
        return PostLikeResponse(post_id=post.id, liked=liked, like_count=count)

    async def save_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
    ) -> PostSaveResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)

        saved, count = await self.post_repo.save_post(db, current_user.id, post)
        return PostSaveResponse(post_id=post.id, saved=saved, save_count=count)

    async def unsave_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
    ) -> PostSaveResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)

        saved, count = await self.post_repo.unsave_post(db, current_user.id, post)
        return PostSaveResponse(post_id=post.id, saved=saved, save_count=count)

    async def share_post(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
    ) -> PostShareResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)

        from app.core.cache import cache_service
        await cache_service.incr(f"cache:post:{post.id}:shares")
        count = await self.post_repo.increment_share_count(db, post)
        share_url = f"/posts/{post.id}"
        return PostShareResponse(post_id=post.id, share_count=count, share_url=share_url)

    async def list_saved_posts(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedSavedPostsResponse:
        posts, total = await self.post_repo.list_saved_posts(
            db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            viewer_is_superuser=current_user.is_superuser,
        )
        liked, _ = await self.post_repo.get_viewer_engagement(
            db, current_user.id, [post.id for post in posts]
        )
        items = [
            map_post_to_response(post, is_liked=post.id in liked, is_saved=True)
            for post in posts
        ]
        return PaginatedSavedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def list_post_reactors(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: Optional[User] = None,
        limit: int = 50,
        offset: int = 0,
        query: Optional[str] = None,
    ) -> PostReactionsResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")
        await require_post_view(db, post, current_user)

        users, total = await self.post_repo.list_post_reactors(
            db, post_id=post_id, limit=limit, offset=offset, query=query
        )

        items = []
        for u in users:
            display_name = u.profile.display_name if u.profile else u.username
            avatar_url = u.profile.avatar_url if u.profile else None
            items.append(
                ReactorUserResponse(
                    id=u.id,
                    username=u.username,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    reaction_type="like",
                    mutual_count=0,
                    is_following=False,
                )
            )

        counts = {
            "all": total,
            "like": total,
            "love": 0,
            "care": 0,
            "haha": 0,
            "wow": 0,
            "sad": 0,
            "angry": 0,
        }

        return PostReactionsResponse(
            items=items,
            total=total,
            counts=counts,
            limit=limit,
            offset=offset,
        )


post_service = PostService()
