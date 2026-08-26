import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.comments.models import Comment
from app.posts.models import Post
from app.users.models import User


class CommentRepository:
    """Repository handling database operations and counters synchronization for comments & replies."""

    async def get_by_id(self, db: AsyncSession, comment_id: uuid.UUID) -> Optional[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.id == comment_id)
            .options(
                selectinload(Comment.user).selectinload(User.profile),
                selectinload(Comment.post).selectinload(Post.community),
                selectinload(Comment.replies),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        parent_id: Optional[uuid.UUID] = None,
    ) -> Comment:
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content.strip(),
            like_count=0,
            reply_count=0,
            is_edited=False,
        )
        db.add(comment)

        # Increment Post comment_count
        post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if post:
            post.comment_count += 1
            db.add(post)

        # Increment parent comment reply_count if this is a reply
        if parent_id:
            parent = (await db.execute(select(Comment).where(Comment.id == parent_id))).scalar_one_or_none()
            if parent:
                parent.reply_count += 1
                db.add(parent)

        await db.commit()
        return await self.get_by_id(db, comment.id)

    async def update(
        self,
        db: AsyncSession,
        comment: Comment,
        content: str,
    ) -> Comment:
        comment.content = content.strip()
        comment.is_edited = True
        db.add(comment)
        await db.commit()
        return await self.get_by_id(db, comment.id)

    async def delete(self, db: AsyncSession, comment: Comment) -> None:
        post_id = comment.post_id
        parent_id = comment.parent_id

        # Calculate number of child replies to accurately decrement post counter
        reply_count_stmt = select(func.count(Comment.id)).where(Comment.parent_id == comment.id)
        child_replies = (await db.execute(reply_count_stmt)).scalar() or 0
        total_deleted = 1 + child_replies

        await db.delete(comment)

        # Decrement Post comment_count
        post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if post:
            post.comment_count = max(0, post.comment_count - total_deleted)
            db.add(post)

        # Decrement parent reply_count if this was a child reply
        if parent_id:
            parent = (await db.execute(select(Comment).where(Comment.id == parent_id))).scalar_one_or_none()
            if parent:
                parent.reply_count = max(0, parent.reply_count - 1)
                db.add(parent)

        await db.commit()

    async def list_post_comments(
        self,
        db: AsyncSession,
        post_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Comment], int]:
        count_stmt = select(func.count(Comment.id)).where(
            Comment.post_id == post_id,
            Comment.parent_id.is_(None),
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Comment)
            .where(
                Comment.post_id == post_id,
                Comment.parent_id.is_(None),
            )
            .options(selectinload(Comment.user).selectinload(User.profile))
            .order_by(Comment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def list_replies(
        self,
        db: AsyncSession,
        parent_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Comment], int]:
        count_stmt = select(func.count(Comment.id)).where(Comment.parent_id == parent_id)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Comment)
            .where(Comment.parent_id == parent_id)
            .options(selectinload(Comment.user).selectinload(User.profile))
            .order_by(Comment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total


comment_repository = CommentRepository()
