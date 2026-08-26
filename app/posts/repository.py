import uuid
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import func, or_, select
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

        # Increment author profile post_count
        author_profile = (await db.execute(select(Profile).where(Profile.user_id == author_id))).scalar_one_or_none()
        if author_profile:
            author_profile.post_count += 1
            db.add(author_profile)

        # Increment community post_count if applicable
        if community_id:
            comm = (await db.execute(select(Community).where(Community.id == community_id))).scalar_one_or_none()
            if comm:
                comm.post_count += 1
                db.add(comm)

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
        author_profile = (await db.execute(select(Profile).where(Profile.user_id == author_id))).scalar_one_or_none()
        if author_profile:
            author_profile.post_count = max(0, author_profile.post_count - 1)
            db.add(author_profile)

        # Decrement community post_count if applicable
        if community_id:
            comm = (await db.execute(select(Community).where(Community.id == community_id))).scalar_one_or_none()
            if comm:
                comm.post_count = max(0, comm.post_count - 1)
                db.add(comm)

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
        post.like_count += 1
        db.add(post)
        await db.commit()
        return True, post.like_count

    async def unlike_post(
        self, db: AsyncSession, user_id: uuid.UUID, post: Post
    ) -> Tuple[bool, int]:
        existing_like = await self.get_like(db, user_id, post.id)
        if not existing_like:
            return False, post.like_count

        await db.delete(existing_like)
        post.like_count = max(0, post.like_count - 1)
        db.add(post)
        await db.commit()
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
        post.save_count += 1
        db.add(post)
        await db.commit()
        return True, post.save_count

    async def unsave_post(
        self, db: AsyncSession, user_id: uuid.UUID, post: Post
    ) -> Tuple[bool, int]:
        existing_saved = await self.get_saved(db, user_id, post.id)
        if not existing_saved:
            return False, post.save_count

        await db.delete(existing_saved)
        post.save_count = max(0, post.save_count - 1)
        db.add(post)
        await db.commit()
        return False, post.save_count

    async def increment_share_count(self, db: AsyncSession, post: Post) -> int:
        post.share_count += 1
        db.add(post)
        await db.commit()
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
