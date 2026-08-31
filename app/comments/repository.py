import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy import case, func, select, update
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
        await db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(comment_count=Post.comment_count + 1)
        )

        # Increment parent comment reply_count if this is a reply
        if parent_id:
            await db.execute(
                update(Comment)
                .where(Comment.id == parent_id)
                .values(reply_count=Comment.reply_count + 1)
            )

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

        descendants = select(Comment.id).where(Comment.id == comment.id).cte(
            name="comment_descendants", recursive=True
        )
        descendants = descendants.union_all(
            select(Comment.id).join(
                descendants, Comment.parent_id == descendants.c.id
            )
        )
        total_deleted = (
            await db.execute(select(func.count()).select_from(descendants))
        ).scalar_one()

        await db.delete(comment)

        # Decrement Post comment_count
        await db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(
                comment_count=case(
                    (Post.comment_count >= total_deleted, Post.comment_count - total_deleted),
                    else_=0,
                )
            )
        )

        # Decrement parent reply_count if this was a child reply
        if parent_id:
            await db.execute(
                update(Comment)
                .where(Comment.id == parent_id)
                .values(
                    reply_count=case(
                        (Comment.reply_count > 0, Comment.reply_count - 1),
                        else_=0,
                    )
                )
            )

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
