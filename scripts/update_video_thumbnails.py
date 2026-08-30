import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client

THUMBNAIL_UPDATES = [
    ("%oceans.mp4%", "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=600&q=80"),
    ("%sintel%", "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80"),
    ("%bunny%", "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80"),
    ("%BigBuckBunny%", "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80"),
    ("%flower.mp4%", "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=600&q=80"),
    ("%jellyfish%", "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=600&q=80"),
    ("%bicycle%", "https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=600&q=80"),
    ("%detection%", "https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=600&q=80"),
]

async def main():
    async with AsyncSessionLocal() as session:
        for pattern, thumb in THUMBNAIL_UPDATES:
            await session.execute(
                text("UPDATE post_media SET thumbnail_url = :thumb WHERE url LIKE :pattern"),
                {"thumb": thumb, "pattern": pattern}
            )
        await session.commit()
        print("Updated post_media thumbnails in PostgreSQL successfully!")

    try:
        redis = get_redis_client()
        keys = await redis.keys("cache:feed:*")
        if keys:
            await redis.delete(*keys)
            print(f"Flushed {len(keys)} feed cache keys in Redis.")
    except Exception as e:
        print(f"Redis cache flush notice: {e}")

if __name__ == "__main__":
    asyncio.run(main())
