import asyncio
import datetime
from pathlib import Path
import random
import sys
import uuid
from typing import List, Dict, Any

# Ensure project root is in sys.path and stdout handles utf-8
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.users.models import User, Profile, Follow
from app.posts.models import Post, PostMedia, PostLike, SavedPost
from app.comments.models import Comment
from app.communities.models import Community, CommunityMembership
from app.interests.models import Interest
from app.core.meilisearch import meilisearch_service

# ---------------------------------------------------------
# 20 KHMER USERS DATA
# ---------------------------------------------------------
KHMER_USERS = [
    {
        "username": "dara_kh",
        "email": "dara.sok@genzmedia.app",
        "display_name": "Dara Sok (ដារ៉ា)",
        "bio": "Building Flutter apps by day, playing MLBB by night 📱☕ Phnom Penh vibes.",
        "avatar_url": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "sophea_vibes",
        "email": "sophea.chan@genzmedia.app",
        "display_name": "Sophea Chan (សុភា)",
        "bio": "Café hopper & aesthetic seeker ☕📸 Living between Phnom Penh & Siem Reap.",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "visal_dev",
        "email": "visal.keo@genzmedia.app",
        "display_name": "Visal Keo (វិសាល)",
        "bio": "Fullstack Engineer (FastAPI + Flutter). Tech geek, mechanical keyboard enthusiast 💻⚡",
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "bopha_style",
        "email": "bopha.pich@genzmedia.app",
        "display_name": "Bopha Pich (បុប្ផា)",
        "bio": "Vintage thrift lover 👗 Streetwear KH | Fashion is art you wear ✨",
        "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "rithy_explore",
        "email": "rithy.heng@genzmedia.app",
        "display_name": "Rithy Heng (រិទ្ធី)",
        "bio": "Moto road trips across Cambodia 🏍️ Kampot - Kep - Mondulkiri explorer 🌲",
        "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "sreypov_art",
        "email": "sreypov.meng@genzmedia.app",
        "display_name": "Sreypov Meng (ស្រីពៅ)",
        "bio": "Digital illustrator & 3D artist 🎨 Creating Khmer cyberpunk aesthetics ✨",
        "avatar_url": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "vannak_tech",
        "email": "vannak.long@genzmedia.app",
        "display_name": "Vannak Long (វណ្ណៈ)",
        "bio": "AI & robotics researcher 🤖 Startup life in Toul Kork 🚀",
        "avatar_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "chenda_daily",
        "email": "chenda.nuon@genzmedia.app",
        "display_name": "Chenda Nuon (ចិន្តា)",
        "bio": "Daily life vlogs, matcha lattes & study sessions 🍵📚 Stay mindful 🌸",
        "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "makara_gaming",
        "email": "makara.san@genzmedia.app",
        "display_name": "Makara San (មករា)",
        "bio": "FPS gamer (Valorant & PUBG Mobile) 🎮 Streaming every weekend! 🔥",
        "avatar_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "seyha_photo",
        "email": "seyha.tep@genzmedia.app",
        "display_name": "Seyha Tep (សីហា)",
        "bio": "Street photography in Phnom Penh 📷 Sony A7IV shooter. Capturing shadows & light.",
        "avatar_url": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "pich_design",
        "email": "pich.kim@genzmedia.app",
        "display_name": "Pich Kim (ពេជ្រ)",
        "bio": "UI/UX Designer & Figma wizard 🎨 Making clean mobile experiences ✨",
        "avatar_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "khemera_travel",
        "email": "khemera.ouk@genzmedia.app",
        "display_name": "Khemera Ouk (ខេមរា)",
        "bio": "Chasing waterfalls & mountain peaks in Koh Kong 🏕️ Always outdoors 🌲",
        "avatar_url": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "sovann_beats",
        "email": "sovann.meas@genzmedia.app",
        "display_name": "Sovann Meas (សុវណ្ណ)",
        "bio": "Khmer Hip-Hop producer & beatmaker 🎧 Vinyl collector 🎵",
        "avatar_url": "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "chantrea_food",
        "email": "chantrea.ros@genzmedia.app",
        "display_name": "Chantrea Ros (ចន្ទ្រា)",
        "bio": "Num Banh Chok & Street food hunter in BKK1 🍜 Good food = Good mood 😋",
        "avatar_url": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "kosal_fit",
        "email": "kosal.yin@genzmedia.app",
        "display_name": "Kosal Yin (កុសល)",
        "bio": "Calisthenics & fitness coach 💪 Health is wealth! Let's get fit together 🏋️‍♂️",
        "avatar_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "theara_code",
        "email": "theara.chhum@genzmedia.app",
        "display_name": "Theara Chhum (ធារា)",
        "bio": "Mobile Dev & open source enthusiast 🚀 Always learning something new.",
        "avatar_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "rathana_life",
        "email": "rathana.mao@genzmedia.app",
        "display_name": "Rathana Mao (រតនា)",
        "bio": "Coffee, plants & journal entries 🌿 Quiet moments in a loud world ✨",
        "avatar_url": "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "channtha_chill",
        "email": "channtha.ly@genzmedia.app",
        "display_name": "Channtha Ly (ចាន់ថា)",
        "bio": "Lofi music, sunset watching at riverside, and books 🌅📖",
        "avatar_url": "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "samnang_tech",
        "email": "samnang.seng@genzmedia.app",
        "display_name": "Samnang Seng (សំណាង)",
        "bio": "DevOps & Cloud architecture ☁️ Linux nerd & coffee addict ☕",
        "avatar_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=400&q=80",
    },
    {
        "username": "sokha_explore",
        "email": "sokha.prom@genzmedia.app",
        "display_name": "Sokha Prom (សុខា)",
        "bio": "Exploring hidden gems around Phnom Penh & Kandal 🛵 Camera always ready 📸",
        "avatar_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=400&q=80",
    },
]

# ---------------------------------------------------------
# COMMUNITIES
# ---------------------------------------------------------
COMMUNITIES_DATA = [
    {
        "name": "Phnom Penh Tech & Developers",
        "slug": "phnom-penh-tech",
        "description": "The hub for programmers, developers, UI/UX designers, and tech creators in Cambodia 🚀",
        "avatar_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=300&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Cambodia Gamers & Esports",
        "slug": "cambodia-gamers",
        "description": "Valorant, MLBB, PUBG, and PC gaming community in Cambodia 🎮 Join squads and tournaments!",
        "avatar_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=300&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Khmer Food & Coffee Crawl",
        "slug": "khmer-food-coffee",
        "description": "Discover the best street food, specialty cafes, and local cuisine spots across Cambodia 🍜☕",
        "avatar_url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=300&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Siem Reap & Angkor Photographers",
        "slug": "siem-reap-photographers",
        "description": "Sharing breathtaking captures of ancient temples, landscapes, and rural culture 📷✨",
        "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "name": "Gen-Z Streetwear & Aesthetics KH",
        "slug": "genz-streetwear-kh",
        "description": "OOTD, thrift finds, local Cambodian streetwear brands, and creative aesthetic lookbooks 👟✨",
        "avatar_url": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=300&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80",
    },
]

# ---------------------------------------------------------
# 20 TEXT POSTS
# ---------------------------------------------------------
TEXT_POSTS_DATA = [
    {
        "title": "Cambodian Iced Coffee (Cafe Teuk Doh Koh Teuk Gok) is literally life fuel",
        "content": "Nothing beats getting an iced condensed milk coffee at 7 AM from the local street cart in Phnom Penh. Instant +100 energy for coding. Who agrees? ☕🔥",
    },
    {
        "title": "Flutter vs React Native in 2026: My experience after 3 years",
        "content": "Honestly, Dart with Riverpod and GoRouter makes UI development feel so smooth. The rendering speed on mobile is unbeatable. What stack is everyone else using for their apps? 📱💻",
    },
    {
        "title": "Late night coding session in Toul Kork 🌙",
        "content": "It's 2:45 AM, lofi beats on repeat, dark mode IDE glowing, bugs getting squashed one by one. The tranquility of late night dev work is truly unmatched.",
    },
    {
        "title": "Best café spots for remote work in BKK1?",
        "content": "Looking for cozy cafes with strong Wi-Fi, good cold brew, and plenty of power outlets. Drop your top 3 recommendations in the comments! 👇",
    },
    {
        "title": "Unpopular opinion on mechanical keyboards",
        "content": "Linear switches (like Gateron Yellows or Oil Kings) are 10x better for typing all day than loud tactile clicky switches. Don't fight me on this 😂⌨️",
    },
    {
        "title": "Siem Reap sunrise at Angkor Wat will always be magical ✨",
        "content": "Woke up at 4:30 AM just to watch the sky turn pink and purple behind the towers. Every Cambodian and traveler needs to experience this at least once in their life. 🌅",
    },
    {
        "title": "Gen-Z thrift shopping tips in Russian Market (Toul Tom Poung)",
        "content": "Go on weekday mornings around 9 AM when new stocks are unpacked! You can find vintage denim jackets and rare streetwear tees for practically under $5. 🛍️",
    },
    {
        "title": "Why FastApi + PostgreSQL is the best backend combo for startups",
        "content": "Type safety with Pydantic v2, async SQLAlchemy, automatic OpenAPI docs, and sub-10ms response times. Building high-performance backends has never been this enjoyable. ⚡",
    },
    {
        "title": "Weekend road trip to Kampot & Kep 🌊",
        "content": "Fresh pepper crab at the Kep crab market followed by sunset chill at the Kampot river. The weekend recharge I desperately needed. Highly recommend! 🦀",
    },
    {
        "title": "Reminder: Drink your water and take a 5-minute posture break! 🧘‍♂️",
        "content": "If you've been sitting in front of your screen for the last 3 hours, this is your sign to stretch your neck, stand up, and hydrate right now. Your spine will thank you.",
    },
    {
        "title": "Mobile Legends rank grind this season is brutal 💀",
        "content": "Reached Mythic rank last night after a 5-game winning streak! Anyone down to squad up for classic or rank matches tonight? Drop your IDs below! 🎮",
    },
    {
        "title": "The aesthetic of Phnom Penh riverside at 6 PM 🌇",
        "content": "Watching the boats on the Tonle Sap river with the cool evening breeze and street food vendors firing up their grills. Such peaceful vibes after a long work day.",
    },
    {
        "title": "Favorite Num Banh Chok in town? 🍜",
        "content": "Samlor Khmer (traditional green fish curry) or Samlor Namya (red curry)? I personally can never say no to fresh herbs and banana blossom with green curry!",
    },
    {
        "title": "AI tools in our daily workflow: what are you actually using?",
        "content": "Beyond code assistance, using LLMs for quick SQL queries, regex generation, and drafting technical documentation saves hours every single sprint. 🤖",
    },
    {
        "title": "Clean desk setup = Clear mind 🖥️",
        "content": "Minimalist wooden desk, monitor arm, cable management tray, and a single green pothos plant. Working in a clutter-free space boosted my productivity by 200%.",
    },
    {
        "title": "Khmer New Year (Sankranta) preparations are starting! 🎉",
        "content": "Who is planning to travel to Siem Reap or Battambang for Sankranta this year? Can't wait for the traditional games, music, and holiday vibes with family!",
    },
    {
        "title": "Favorite music playlist while studying or coding? 🎧",
        "content": "Khmer indie tracks mixed with ambient synthwave and jazzhop. Drop your favorite Spotify / YouTube links below so I can add them to my daily queue!",
    },
    {
        "title": "Starting a 30-day fitness and calisthenics challenge 💪",
        "content": "100 pushups, 50 pullups, and 5km jog every single day. Day 1 starts today! Who wants to join and hold each other accountable?",
    },
    {
        "title": "Photography tip: Master natural golden hour lighting 📸",
        "content": "The 45 minutes before sunset in Cambodia offers the warmest, softest diffused light for portraits. No expensive flash kit needed—just position your subject 45° to the sun.",
    },
    {
        "title": "What was the most impactful book or article you read this year? 📚",
        "content": "Atomic Habits by James Clear completely reshaped how I structure my morning routines and daily coding habits. Small 1% improvements truly compound over time.",
    },
]

# ---------------------------------------------------------
# IMAGE MEDIA POOL (High quality Unsplash curated URLs)
# ---------------------------------------------------------
IMAGE_POOL = [
    # Tech & Setups
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1080&q=80",
    # Coffee & Food
    "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=1080&q=80",
    # Travel, Angkor, Nature
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1569154941061-e231b4725ef1?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1433086966358-54859d0ed716?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1080&q=80",
    # Streetwear & Fashion
    "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1552374196-1ab2a1c593e8?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1080&q=80",
    # Gaming & Cyberpunk
    "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1080&q=80",
    "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=1080&q=80",
]

IMAGE_POST_TOPICS = [
    ("Specialty Pour-over Coffee Session ☕", "Tasting Ethiopian Yirgacheffe beans roasted right here in Phnom Penh. Floral notes and bright citrus!"),
    ("Minimalist Workspace Setup 🖥️✨", "Finally finished setting up the dual-monitor standing desk. Clean cables and warm bias lighting."),
    ("Angkor Wat at First Light 🌅🇰🇭", "The timeless beauty of our heritage. Captured during sunrise reflection by the lotus pond."),
    ("Streetwear OOTD: Thrifted & Customized 👟", "Vintage oversized bomber jacket paired with wide-leg cargo pants. Sustainable fashion is the vibe."),
    ("Late Night Mechanical Keyboard Build ⌨️", "Lubed Linear switches with custom PBT keycaps. The thock sound is so satisfying!"),
    ("Weekend Cycling around Koh Dach (Silk Island) 🚲", "Ferry ride across the Mekong followed by peaceful cycling through rural villages and weaving houses."),
    ("Phnom Penh Skyline at Golden Hour 🏙️", "Watching the twilight glow over the riverside. Our city is growing so rapidly."),
    ("Fresh Kampot Pepper Crab Feast 🦀", "Crab caught this morning cooked in fresh green pepper from La Plantation. Absolute perfection!"),
    ("Cyberpunk Aesthetic Art Study 🎨✨", "Testing out neon gradients and isometric perspectives for an upcoming game UI concept."),
    ("Monsoon Rain & Warm Matcha Latte 🍵🌧️", "Listening to rain drumming on the cafe glass while reviewing pull requests. Pure comfort."),
    ("Street Photography in Toul Tom Poung 📸", "Every corner of the Russian Market has a story. Authentic moments of daily life."),
    ("Camping under the Stars in Cardamom Mountains 🏕️", "No cellular signal, cool mountain breeze, campfire cooking, and billions of stars."),
    ("Custom Sneaker Art Workshop 👟🎨", "Hand-painting traditional Kbach motifs onto classic white sneakers. Heritage meets streetwear!"),
    ("Matcha & Croissant Morning Routine 🥐", "Starting the productive sprint with a flaky almond croissant and iced ceremonial matcha."),
    ("Retro Gaming Night with the Squad 🎮", "Hooked up classic consoles for an epic Mario Kart and Street Fighter tournament!"),
]

# ---------------------------------------------------------
# VIDEO MEDIA POOL (High speed, reliable public MP4 clips)
# ---------------------------------------------------------
VIDEO_POOL = [
    {
        "url": "https://vjs.zencdn.net/v/oceans.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=600&q=80",
        "duration": 45.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://media.w3.org/2010/05/sintel/trailer.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80",
        "duration": 52.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://media.w3.org/2010/05/bunny/trailer.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80",
        "duration": 33.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=600&q=80",
        "duration": 10.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80",
        "duration": 10.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://test-videos.co.uk/vids/jellyfish/mp4/h264/720/Jellyfish_720_10s_1MB.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=600&q=80",
        "duration": 10.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://test-videos.co.uk/vids/sintel/mp4/h264/720/Sintel_720_10s_1MB.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=600&q=80",
        "duration": 10.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://test-videos.co.uk/vids/jellyfish/mp4/h264/720/Jellyfish_720_10s_1MB.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=80",
        "duration": 10.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://media.w3.org/2010/05/sintel/trailer.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
        "duration": 52.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=600&q=80",
        "duration": 10.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://cdn.jsdelivr.net/gh/intel-iot-devkit/sample-videos@master/person-bicycle-car-detection.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&w=600&q=80",
        "duration": 14.0,
        "width": 1280,
        "height": 720,
    },
    {
        "url": "https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80",
        "duration": 60.0,
        "width": 1280,
        "height": 720,
    },
]

VIDEO_POST_TOPICS = [
    ("Barista Slow Pour Espresso Shot ☕✨", "Watching the golden crema extract in 4K slow motion. Coffee art perfection!"),
    ("Neon Cyberpunk Phnom Penh Nights 🌃", "Night ride through the glowing streets and bridges of Phnom Penh."),
    ("Skateboarding Session at Riverside Park 🛹", "Landing a clean kickflip right before sunset. Keep grinding!"),
    ("Late Night Mechanical Keyboard Typing ASMR ⌨️🎧", "Testing out 62g tactile switches. Headphones recommended for maximum typing satisfaction!"),
    ("Valorant Clutch 1v4 Ace Gameplay 🎯🔥", "Last round in overtime and pulled off the impossible clutch! Watch till the end!"),
    ("Morning Run along the Chaktomuk Riverfront 🏃‍♂️🌅", "Starting the day with positive energy and 5km morning fresh air."),
    ("Epic Drone Shot of Mondulkiri Pine Hills 🌲🚁", "The green rolling hills of eastern Cambodia look like another world."),
    ("FastAPI Backend Live Benchmark ⚡🚀", "Benchmarking 10,000 requests per second with async SQLAlchemy!"),
    ("Making Authentic Khmer Street Food Pancakes (Banh Chev) 🥞", "Crispy golden turmeric crepe stuffed with herbs and minced pork!"),
    ("Sunset Time-lapse over Angkor Wat ⛅✨", "Watch the clouds dance over ancient stone temples as twilight falls."),
    ("DJ Live Beat Mixing in BKK3 🎧🔥", "Lofi hip-hop blend mixed with traditional Khmer instruments."),
    ("Quick Flutter Animation Tutorial 📱✨", "How to build silky smooth interactive swipe gestures in under 60 seconds!"),
]

# ---------------------------------------------------------
# COMMENTS POOL
# ---------------------------------------------------------
SAMPLE_COMMENTS = [
    "This looks incredible! 🔥",
    "Where is this located? Need to visit this weekend!",
    "Amazing shot! What camera or settings did you use? 📸",
    "Totally agree with this! 100% facts 👏",
    "Lofi vibes are unmatched 🎧✨",
    "So proud of Cambodian tech creators! Keep it up! 🇰🇭🚀",
    "The aesthetics in this post are top tier! ✨",
    "Delicious!! My favorite spot in town 😋",
    "Saved this for my next trip! 🙌",
    "The code structure is so clean! Great explanation 💻",
    "That clutch was insane bro! GG! 🎮🔥",
    "Vibes are immaculate 🌿✨",
    "This made my day! Thanks for sharing ❤️",
    "Can't wait to try this out! 🚀",
]


async def seed_database():
    print("🚀 Starting Gen-Z Media Seeding Script...")
    
    async with AsyncSessionLocal() as db:
        # 1. Fetch existing interests
        result = await db.execute(select(Interest))
        interests = result.scalars().all()
        interest_ids = [i.id for i in interests] if interests else []
        print(f"✅ Found {len(interests)} existing interests.")

        # 2. Create or Get 20 Khmer Users
        password_hash_val = get_password_hash("Password123!")
        created_users: List[User] = []

        for u_data in KHMER_USERS:
            # Check if user exists
            stmt = select(User).where(User.username == u_data["username"])
            existing = (await db.execute(stmt)).scalars().first()
            if not existing:
                user = User(
                    id=uuid.uuid4(),
                    username=u_data["username"],
                    email=u_data["email"],
                    hashed_password=password_hash_val,
                    is_active=True,
                    is_superuser=False,
                )
                db.add(user)
                await db.flush()

                profile = Profile(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    display_name=u_data["display_name"],
                    bio=u_data["bio"],
                    avatar_url=u_data["avatar_url"],
                    follower_count=0,
                    following_count=0,
                    post_count=0,
                )
                db.add(profile)
                created_users.append(user)
            else:
                created_users.append(existing)

        await db.commit()
        print(f"✅ 20 Khmer Users verified/created in database.")

        # Re-fetch users with profiles
        stmt = select(User)
        all_users = (await db.execute(stmt)).scalars().all()

        # 3. Create Communities if none exist
        created_communities: List[Community] = []
        for idx, c_data in enumerate(COMMUNITIES_DATA):
            stmt = select(Community).where(Community.slug == c_data["slug"])
            comm = (await db.execute(stmt)).scalars().first()
            if not comm:
                comm = Community(
                    id=uuid.uuid4(),
                    owner_id=created_users[idx % len(created_users)].id,
                    interest_id=interest_ids[idx % len(interest_ids)] if interest_ids else None,
                    name=c_data["name"],
                    slug=c_data["slug"],
                    description=c_data["description"],
                    avatar_url=c_data["avatar_url"],
                    cover_image_url=c_data["cover_image_url"],
                    is_private=False,
                    member_count=len(all_users),
                    post_count=0,
                )
                db.add(comm)
                await db.flush()

                # Add all users to community
                for u in all_users:
                    membership = CommunityMembership(
                        id=uuid.uuid4(),
                        community_id=comm.id,
                        user_id=u.id,
                        role="admin" if u.id == comm.owner_id else "member",
                    )
                    db.add(membership)
                created_communities.append(comm)
            else:
                created_communities.append(comm)

        await db.commit()
        print(f"✅ {len(created_communities)} Communities verified/created.")

        # 4. Generate Follows between users
        for u in all_users:
            potential_targets = [target for target in all_users if target.id != u.id]
            follow_count = random.randint(4, min(12, len(potential_targets)))
            targets = random.sample(potential_targets, follow_count)
            for target in targets:
                # Check if follow exists
                stmt = select(Follow).where(Follow.follower_id == u.id, Follow.following_id == target.id)
                exists = (await db.execute(stmt)).scalars().first()
                if not exists:
                    db.add(Follow(id=uuid.uuid4(), follower_id=u.id, following_id=target.id))
        await db.commit()
        print("✅ Follow network initialized.")

        # 5. Create 200 Posts:
        # - 20 Text posts
        # - 90 Image posts
        # - 90 Video posts
        print("📝 Generating 200 posts (20 Text, 90 Image, 90 Short Video)...")
        now = datetime.datetime.now(datetime.timezone.utc)
        posts_to_index: List[Dict[str, Any]] = []
        all_created_posts: List[Post] = []

        # A. 20 TEXT POSTS
        for i in range(20):
            t_data = TEXT_POSTS_DATA[i % len(TEXT_POSTS_DATA)]
            author = random.choice(all_users)
            community = random.choice(created_communities) if random.random() < 0.4 else None
            created_at = now - datetime.timedelta(days=random.randint(0, 25), hours=random.randint(0, 23), minutes=random.randint(0, 59))

            post = Post(
                id=uuid.uuid4(),
                author_id=author.id,
                community_id=community.id if community else None,
                post_type="text",
                title=t_data["title"],
                content=t_data["content"],
                visibility="public",
                like_count=0,
                comment_count=0,
                share_count=random.randint(0, 25),
                save_count=0,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(post)
            all_created_posts.append(post)

        # B. 90 IMAGE POSTS
        for i in range(90):
            topic_title, topic_caption = random.choice(IMAGE_POST_TOPICS)
            author = random.choice(all_users)
            community = random.choice(created_communities) if random.random() < 0.45 else None
            created_at = now - datetime.timedelta(days=random.randint(0, 28), hours=random.randint(0, 23), minutes=random.randint(0, 59))

            post = Post(
                id=uuid.uuid4(),
                author_id=author.id,
                community_id=community.id if community else None,
                post_type="image",
                title=f"{topic_title} #{i+1}",
                content=topic_caption,
                visibility="public",
                like_count=0,
                comment_count=0,
                share_count=random.randint(0, 40),
                save_count=0,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(post)
            await db.flush()

            # Add 1 to 3 images
            num_images = random.choices([1, 2, 3], weights=[0.6, 0.25, 0.15])[0]
            sampled_images = random.sample(IMAGE_POOL, min(num_images, len(IMAGE_POOL)))
            for order_idx, img_url in enumerate(sampled_images):
                media_item = PostMedia(
                    id=uuid.uuid4(),
                    post_id=post.id,
                    media_type="image",
                    url=img_url,
                    thumbnail_url=None,
                    width=1080,
                    height=1080,
                    duration=None,
                    order=order_idx,
                    created_at=created_at,
                    updated_at=created_at,
                )
                db.add(media_item)

            all_created_posts.append(post)

        # C. 90 VIDEO POSTS
        for i in range(90):
            v_data = random.choice(VIDEO_POOL)
            topic_title, topic_caption = random.choice(VIDEO_POST_TOPICS)
            author = random.choice(all_users)
            community = random.choice(created_communities) if random.random() < 0.5 else None
            created_at = now - datetime.timedelta(days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59))

            post = Post(
                id=uuid.uuid4(),
                author_id=author.id,
                community_id=community.id if community else None,
                post_type="video",
                title=f"{topic_title} #{i+1}",
                content=topic_caption,
                visibility="public",
                like_count=0,
                comment_count=0,
                share_count=random.randint(2, 65),
                save_count=0,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(post)
            await db.flush()

            media_item = PostMedia(
                id=uuid.uuid4(),
                post_id=post.id,
                media_type="video",
                url=v_data["url"],
                thumbnail_url=v_data["thumbnail"],
                width=v_data.get("width", 1280),
                height=v_data.get("height", 720),
                duration=v_data["duration"],
                order=0,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(media_item)
            all_created_posts.append(post)

        await db.commit()
        print(f"✅ Successfully inserted 200 posts into database.")

        # 6. Add Likes, Comments, and Saves for realistic interaction
        print("❤️ Generating likes, comments, and saves...")
        for post in all_created_posts:
            # Likes
            num_likes = random.randint(3, min(18, len(all_users)))
            likers = random.sample(all_users, num_likes)
            for liker in likers:
                db.add(PostLike(id=uuid.uuid4(), post_id=post.id, user_id=liker.id))
            post.like_count = num_likes

            # Saves
            num_saves = random.randint(0, min(8, len(all_users)))
            savers = random.sample(all_users, num_saves)
            for saver in savers:
                db.add(SavedPost(id=uuid.uuid4(), post_id=post.id, user_id=saver.id))
            post.save_count = num_saves

            # Comments
            num_comments = random.randint(1, 6)
            for _ in range(num_comments):
                c_user = random.choice(all_users)
                c_text = random.choice(SAMPLE_COMMENTS)
                comment = Comment(
                    id=uuid.uuid4(),
                    post_id=post.id,
                    user_id=c_user.id,
                    parent_id=None,
                    content=c_text,
                    like_count=random.randint(0, 5),
                    reply_count=0,
                    is_edited=False,
                )
                db.add(comment)
            post.comment_count = num_comments

        await db.commit()

        # 7. Update User Profile counts (post_count, follower_count, following_count)
        print("📊 Updating profile metrics...")
        for u in all_users:
            p_stmt = select(func.count(Post.id)).where(Post.author_id == u.id)
            post_cnt = (await db.execute(p_stmt)).scalar() or 0

            f_stmt = select(func.count(Follow.id)).where(Follow.following_id == u.id)
            follower_cnt = (await db.execute(f_stmt)).scalar() or 0

            fg_stmt = select(func.count(Follow.id)).where(Follow.follower_id == u.id)
            following_cnt = (await db.execute(fg_stmt)).scalar() or 0

            prof_stmt = select(Profile).where(Profile.user_id == u.id)
            prof = (await db.execute(prof_stmt)).scalars().first()
            if prof:
                prof.post_count = post_cnt
                prof.follower_count = follower_cnt
                prof.following_count = following_cnt

        await db.commit()
        print("✅ Profile counts updated.")

        # 8. Index into Meilisearch
        print("🔍 Syncing posts to Meilisearch index...")
        try:
            posts_for_meili = []
            for p in all_created_posts:
                # Find author username
                author = next((u for u in all_users if u.id == p.author_id), None)
                posts_for_meili.append({
                    "id": str(p.id),
                    "title": p.title,
                    "content": p.content,
                    "post_type": p.post_type,
                    "visibility": p.visibility,
                    "author_id": str(p.author_id),
                    "author_username": author.username if author else "user",
                    "community_id": str(p.community_id) if p.community_id else None,
                    "community_name": None,
                    "like_count": p.like_count,
                    "comment_count": p.comment_count,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                })
            
            for chunk_start in range(0, len(posts_for_meili), 50):
                chunk = posts_for_meili[chunk_start:chunk_start+50]
                for doc in chunk:
                    await meilisearch_service.index_post(doc)
            print("✅ All posts successfully indexed into Meilisearch!")
        except Exception as e:
            print(f"⚠️ Note on Meilisearch indexing: {e}")

    print("\n🎉 SEEDING COMPLETE!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"👥 Users: 20 Khmer Users (Password: Password123!)")
    print(f"📄 Posts: 200 Total (20 Text, 90 Image, 90 Video)")
    print(f"🏛️ Communities: 5 Cambodian Hubs")
    print(f"❤️ Engagement: Thousands of realistic likes, comments, follows, saves")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    asyncio.run(seed_database())
