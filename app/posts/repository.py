import uuid
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.communities.models import Community
from app.posts.models import Post, PostLike, PostMedia, SavedPost
from app.posts.schemas import MediaItemCreate
from app.users.models import Profile, User


class PostRepository:
    """Repository handling database operations for Post, PostMedia, PostLike, and SavedPost entities."""

    async def get_by_id(self, db: AsyncSession, post_id: uuid.UUID) -> Optional[Post]:
        stmt = (
            select(Post)
            .where(Post.id == post_id)
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
                selectinload(Post.media_items),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        author_id: uuid.UUID,
        community_id: Optional[uuid.UUID] = None,
        post_type: str = "text",
        title: Optional[str] = None,
        content: Optional[str] = None,
        visibility: str = "public",
        media: Optional[List[MediaItemCreate]] = None,
    ) -> Post:
        post = Post(
            author_id=author_id,
            community_id=community_id,
            post_type=post_type,
            title=title.strip() if title else None,
            content=content.strip() if content else None,
            visibility=visibility,
            like_count=0,
            comment_count=0,
            share_count=0,
            save_count=0,
        )
        db.add(post)
        await db.flush()  # Generate post.id

        if media:
            for idx, item in enumerate(media):
                media_item = PostMedia(
                    post_id=post.id,
                    media_type=item.media_type,
                    url=item.url,
                    thumbnail_url=item.thumbnail_url,
                    duration=item.duration,
                    width=item.width,
                    height=item.height,
                    order=item.order if item.order is not None else idx,
                )
                db.add(media_item)

        # Increment author profile post_count atomically
        await db.execute(
            update(Profile)
            .where(Profile.user_id == author_id)
            .values(post_count=Profile.post_count + 1)
        )

        # Increment community post_count if applicable atomically
        if community_id:
            await db.execute(
                update(Community)
                .where(Community.id == community_id)
                .values(post_count=Community.post_count + 1)
            )

        await db.commit()
        return await self.get_by_id(db, post.id)  # Returns fully loaded post

    async def update(
        self,
        db: AsyncSession,
        post: Post,
        **kwargs,
    ) -> Post:
        for key, value in kwargs.items():
            if hasattr(post, key) and value is not None:
                setattr(post, key, value)

        db.add(post)
        await db.commit()
        await db.refresh(post)
        return await self.get_by_id(db, post.id)

    async def delete(self, db: AsyncSession, post: Post) -> None:
        author_id = post.author_id
        community_id = post.community_id

        await db.delete(post)

        # Decrement author post_count
        await db.execute(
            update(Profile)
            .where(Profile.user_id == author_id)
            .values(post_count=case((Profile.post_count > 0, Profile.post_count - 1), else_=0))
        )

        # Decrement community post_count if applicable
        if community_id:
            await db.execute(
                update(Community)
                .where(Community.id == community_id)
                .values(post_count=case((Community.post_count > 0, Community.post_count - 1), else_=0))
            )

        await db.commit()

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
    ) -> Tuple[Sequence[Post], int]:
        filters = []
        if author_id is not None:
            filters.append(Post.author_id == author_id)
        if community_id is not None:
            filters.append(Post.community_id == community_id)
        if post_type is not None:
            filters.append(Post.post_type == post_type)
        if visibility is not None:
            filters.append(Post.visibility == visibility)
        if search:
            search_clean = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Post.title).like(search_clean),
                    func.lower(Post.content).like(search_clean),
                )
            )

        count_stmt = select(func.count(Post.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Post)
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
                selectinload(Post.media_items),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return result.scalars().all(), total

    # Engagement operations
    async def get_like(
        self, db: AsyncSession, user_id: uuid.UUID, post_id: uuid.UUID
    ) -> Optional[PostLike]:
        stmt = select(PostLike).where(
            PostLike.user_id == user_id, PostLike.post_id == post_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def like_post(
        self, db: AsyncSession, user_id: uuid.UUID, post: Post
    ) -> Tuple[bool, int]:
        existing_like = await self.get_like(db, user_id, post.id)
        if existing_like:
            return True, post.like_count

        like = PostLike(user_id=user_id, post_id=post.id)
        db.add(like)
        await db.execute(
            update(Post).where(Post.id == post.id).values(like_count=Post.like_count + 1)
        )
        await db.commit()
        await db.refresh(post)
        return True, post.like_count

    async def unlike_post(
        self, db: AsyncSession, user_id: uuid.UUID, post: Post
    ) -> Tuple[bool, int]:
        existing_like = await self.get_like(db, user_id, post.id)
        if not existing_like:
            return False, post.like_count

        await db.delete(existing_like)
        await db.execute(
            update(Post).where(Post.id == post.id).values(like_count=case((Post.like_count > 0, Post.like_count - 1), else_=0))
        )
        await db.commit()
        await db.refresh(post)
        return False, post.like_count

    async def get_saved(
        self, db: AsyncSession, user_id: uuid.UUID, post_id: uuid.UUID
    ) -> Optional[SavedPost]:
        stmt = select(SavedPost).where(
            SavedPost.user_id == user_id, SavedPost.post_id == post_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_post(
        self, db: AsyncSession, user_id: uuid.UUID, post: Post
    ) -> Tuple[bool, int]:
        existing_saved = await self.get_saved(db, user_id, post.id)
        if existing_saved:
            return True, post.save_count

        saved = SavedPost(user_id=user_id, post_id=post.id)
        db.add(saved)
        await db.execute(
            update(Post).where(Post.id == post.id).values(save_count=Post.save_count + 1)
        )
        await db.commit()
        await db.refresh(post)
        return True, post.save_count

    async def unsave_post(
        self, db: AsyncSession, user_id: uuid.UUID, post: Post
    ) -> Tuple[bool, int]:
        existing_saved = await self.get_saved(db, user_id, post.id)
        if not existing_saved:
            return False, post.save_count

        await db.delete(existing_saved)
        await db.execute(
            update(Post).where(Post.id == post.id).values(save_count=case((Post.save_count > 0, Post.save_count - 1), else_=0))
        )
        await db.commit()
        await db.refresh(post)
        return False, post.save_count

    async def increment_share_count(self, db: AsyncSession, post: Post) -> int:
        await db.execute(
            update(Post).where(Post.id == post.id).values(share_count=Post.share_count + 1)
        )
        await db.commit()
        await db.refresh(post)
        return post.share_count

    async def list_saved_posts(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Post], int]:
        count_stmt = (
            select(func.count(SavedPost.id))
            .where(SavedPost.user_id == user_id)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Post)
            .join(SavedPost, SavedPost.post_id == Post.id)
            .where(SavedPost.user_id == user_id)
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
                selectinload(Post.media_items),
            )
            .order_by(SavedPost.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total


post_repository = PostRepository()
