import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment
from app.comments.repository import CommentRepository, comment_repository
from app.comments.schemas import (
    CommentAuthorResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    PaginatedCommentsResponse,
)
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.posts.repository import PostRepository, post_repository
from app.users.models import User


def map_comment_to_response(comment: Comment) -> CommentResponse:
    author = CommentAuthorResponse(
        id=comment.user.id,
        username=comment.user.username,
        display_name=comment.user.profile.display_name if comment.user.profile else comment.user.username,
        avatar_url=comment.user.profile.avatar_url if comment.user.profile else None,
    )
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        author=author,
        content=comment.content,
        like_count=comment.like_count,
        reply_count=comment.reply_count,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


class CommentService:
    """Service handling discussions, nested replies, counters, and moderation rules."""

    def __init__(
        self,
        comment_repo: CommentRepository = comment_repository,
        post_repo: PostRepository = post_repository,
    ):
        self.comment_repo = comment_repo
        self.post_repo = post_repo

    async def create_comment(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User,
        payload: CommentCreateRequest,
    ) -> CommentResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")

        # Validate parent comment if this is a nested reply
        if payload.parent_id:
            parent_comment = await self.comment_repo.get_by_id(db, payload.parent_id)
            if not parent_comment:
                raise NotFoundException("Parent comment not found.")
            if parent_comment.post_id != post_id:
                raise BadRequestException("Parent comment does not belong to this post.")

        comment = await self.comment_repo.create(
            db,
            post_id=post_id,
            user_id=current_user.id,
            content=payload.content,
            parent_id=payload.parent_id,
        )

        return map_comment_to_response(comment)

    async def get_comment(
        self,
        db: AsyncSession,
        comment_id: uuid.UUID,
    ) -> CommentResponse:
        comment = await self.comment_repo.get_by_id(db, comment_id)
        if not comment:
            raise NotFoundException("Comment not found.")
        return map_comment_to_response(comment)

    async def update_comment(
        self,
        db: AsyncSession,
        comment_id: uuid.UUID,
        current_user: User,
        payload: CommentUpdateRequest,
    ) -> CommentResponse:
        comment = await self.comment_repo.get_by_id(db, comment_id)
        if not comment:
            raise NotFoundException("Comment not found.")

        if comment.user_id != current_user.id and not current_user.is_superuser:
            raise ForbiddenException("Only the author can edit this comment.")

        updated = await self.comment_repo.update(db, comment, payload.content)
        return map_comment_to_response(updated)

    async def delete_comment(
        self,
        db: AsyncSession,
        comment_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        comment = await self.comment_repo.get_by_id(db, comment_id)
        if not comment:
            raise NotFoundException("Comment not found.")

        # 4-tier moderation check: Comment Author, Post Author, Community Owner, Platform Admin
        is_comment_author = comment.user_id == current_user.id
        is_post_author = comment.post and comment.post.author_id == current_user.id
        is_comm_owner = (
            comment.post
            and comment.post.community
            and comment.post.community.owner_id == current_user.id
        )
        is_admin = current_user.is_superuser

        if not (is_comment_author or is_post_author or is_comm_owner or is_admin):
            raise ForbiddenException("You do not have permission to delete this comment.")

        await self.comment_repo.delete(db, comment)
        return {"message": "Comment has been deleted successfully."}

    async def list_post_comments(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedCommentsResponse:
        post = await self.post_repo.get_by_id(db, post_id)
        if not post:
            raise NotFoundException("Post not found.")

        comments, total = await self.comment_repo.list_post_comments(db, post_id, limit, offset)
        items = [map_comment_to_response(c) for c in comments]
        return PaginatedCommentsResponse(items=items, total=total, limit=limit, offset=offset)

    async def list_replies(
        self,
        db: AsyncSession,
        parent_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedCommentsResponse:
        parent = await self.comment_repo.get_by_id(db, parent_id)
        if not parent:
            raise NotFoundException("Parent comment not found.")

        replies, total = await self.comment_repo.list_replies(db, parent_id, limit, offset)
        items = [map_comment_to_response(r) for r in replies]
        return PaginatedCommentsResponse(items=items, total=total, limit=limit, offset=offset)


comment_service = CommentService()
