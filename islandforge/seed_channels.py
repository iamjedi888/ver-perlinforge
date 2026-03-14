"""
seed_channels.py - Run on the VM to seed and refresh the curated channels list.
Usage: python3 seed_channels.py

The channels page works best when embed_url is a direct embeddable replay,
playlist, or live feed URL. Official /videos and /streams pages are still
useful when a source should open as a feed instead of an iframe player.
"""

import os
import sys


sys.path.insert(0, os.path.dirname(__file__))


CHANNELS = [
    # Fortnite competitive
    {
        "name": "Fortnite Competitive",
        "category": "Fortnite Competitive",
        "embed_url": "https://www.fortnite.com/competitive/watch",
        "description": "Official Fortnite competitive watch hub for FNCS, majors, and event coverage.",
    },
    {
        "name": "Epic Games Fortnite",
        "category": "Fortnite Competitive",
        "embed_url": "https://www.youtube.com/epicfortnite/videos",
        "description": "Official Fortnite video feed for trailers, events, and season reveals.",
    },
    {
        "name": "Fortnite World Cup Archive",
        "category": "Fortnite Competitive",
        "embed_url": "https://www.youtube.com/watch?v=pPgBjkZ6WLY",
        "description": "Full broadcast replay of the Fortnite World Cup Finals.",
    },
    {
        "name": "FNCS Highlights 24/7",
        "category": "Fortnite Competitive",
        "embed_url": "https://www.youtube.com/@FN_Competitive/streams",
        "description": "Official FN Competitive streams and replay feed for current FNCS coverage.",
    },
    # Game developers
    {
        "name": "Epic Games",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@EpicGames/videos",
        "description": "Official Epic Games feed covering Fortnite, Unreal, and publishing updates.",
    },
    {
        "name": "Unreal Engine",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@UnrealEngine/videos",
        "description": "Official Unreal Engine feed for State of Unreal, tutorials, and showcases.",
    },
    {
        "name": "Unity",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@unity/videos",
        "description": "Official Unity feed for engine updates, Unite sessions, and demos.",
    },
    {
        "name": "GDC \u2014 Game Developers Conference",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@Gdconf/videos",
        "description": "GDC session archive for design, art, programming, and production talks.",
    },
    {
        "name": "Naughty Dog",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@NaughtyDog/videos",
        "description": "Official Naughty Dog studio feed for trailers, panels, and studio updates.",
    },
    {
        "name": "Bungie",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@Bungie/videos",
        "description": "Official Bungie feed with Destiny updates, showcases, and community streams.",
    },
    {
        "name": "Riot Games",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@riotgames/videos",
        "description": "Official Riot Games feed for League, Valorant, TFT, and dev updates.",
    },
    {
        "name": "Xbox",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@Xbox/videos",
        "description": "Official Xbox feed for Developer Direct, reveals, and platform news.",
    },
    {
        "name": "PlayStation",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@PlayStation/videos",
        "description": "Official PlayStation feed for State of Play, reveals, and interviews.",
    },
    {
        "name": "Nintendo",
        "category": "Game Developers",
        "embed_url": "https://www.youtube.com/@Nintendo/videos",
        "description": "Official Nintendo feed for Directs, reveal drops, and event archives.",
    },
    # Esports
    {
        "name": "ESL Counter-Strike",
        "category": "Esports",
        "embed_url": "https://www.youtube.com/@ESLCounterStrike/videos",
        "description": "Official ESL Counter-Strike feed for IEM, Pro League, and VODs.",
    },
    {
        "name": "PGL Esports",
        "category": "Esports",
        "embed_url": "https://www.youtube.com/@PGLesports/videos",
        "description": "Official PGL feed for CS2, Dota, and major event broadcasts.",
    },
    {
        "name": "LCK \u2014 League of Legends Champions Korea",
        "category": "Esports",
        "embed_url": "https://www.youtube.com/@lck/videos",
        "description": "Official LCK feed with match archives, highlights, and desk shows.",
    },
    {
        "name": "Valorant Champions Tour",
        "category": "Esports",
        "embed_url": "https://www.youtube.com/@VALORANTesports/videos",
        "description": "Official VCT feed for Masters, Champions, and global Valorant play.",
    },
    {
        "name": "Rocket League Esports",
        "category": "Esports",
        "embed_url": "https://www.youtube.com/@RocketLeagueEsports/videos",
        "description": "Official Rocket League Esports feed for RLCS broadcasts and recaps.",
    },
    {
        "name": "Overwatch League",
        "category": "Esports",
        "embed_url": "https://www.youtube.com/@overwatchleague/videos",
        "description": "Official Overwatch League archive for match VODs and highlights.",
    },
    # Creative / UEFN
    {
        "name": "UEFN & Creative 2.0 Tutorials",
        "category": "Creative / UEFN",
        "embed_url": "https://www.youtube.com/playlist?list=PL9niUMaDJY710RJ-8L93G9CLbVRXWFFa4",
        "description": "Official Build Your First Island playlist from Fortnite Create.",
    },
    {
        "name": "Unreal Sensei",
        "category": "Creative / UEFN",
        "embed_url": "https://www.youtube.com/@UnrealSensei/videos",
        "description": "Community Unreal tutorials for game devs and Fortnite creators.",
    },
    {
        "name": "William Faucher",
        "category": "Creative / UEFN",
        "embed_url": "https://www.youtube.com/@WilliamFaucher/videos",
        "description": "Cinematic Unreal workflows for lighting, landscapes, and visual polish.",
    },
    # Chill gaming / soundtrack
    {
        "name": "Lofi Gaming Radio 24/7",
        "category": "Chill Gaming",
        "embed_url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "description": "Lofi radio replay feed for long building and grinding sessions.",
    },
    {
        "name": "Chillhop Music 24/7",
        "category": "Chill Gaming",
        "embed_url": "https://www.youtube.com/watch?v=5yx6BWlEVcY",
        "description": "Chillhop stream for background focus while playing or creating.",
    },
    {
        "name": "Video Game Music 24/7",
        "category": "Chill Gaming",
        "embed_url": "https://www.youtube.com/watch?v=OhcGNMGQBxU",
        "description": "Long-form video game soundtrack mix for all-day sessions.",
    },
    {
        "name": "Retro Gaming 24/7",
        "category": "Chill Gaming",
        "embed_url": "https://www.youtube.com/watch?v=wREBD2og5iE",
        "description": "Retro gameplay and soundtrack loop for slower community hours.",
    },
    # Gaming news / reviews
    {
        "name": "IGN",
        "category": "Gaming News",
        "embed_url": "https://www.youtube.com/@IGN/videos",
        "description": "Gaming signal feed for reviews, trailers, and event coverage.",
    },
    {
        "name": "GameSpot",
        "category": "Gaming News",
        "embed_url": "https://www.youtube.com/@GameSpot/videos",
        "description": "GameSpot feed for reviews, features, and major showcase coverage.",
    },
    {
        "name": "Kotaku",
        "category": "Gaming News",
        "embed_url": "https://www.youtube.com/@Kotaku/videos",
        "description": "Gaming culture feed for editorials, commentary, and retrospectives.",
    },
    {
        "name": "Digital Foundry",
        "category": "Gaming News",
        "embed_url": "https://www.youtube.com/@DigitalFoundry/videos",
        "description": "Technical analysis feed for frame rate, visual, and hardware breakdowns.",
    },
    {
        "name": "Gameranx",
        "category": "Gaming News",
        "embed_url": "https://www.youtube.com/@gameranxTV/videos",
        "description": "Accessible gaming news and recommendation feed for broad discovery.",
    },
    # Community picks
    {
        "name": "Mythpat Gaming",
        "category": "Community Picks",
        "embed_url": "https://www.youtube.com/@Mythpat/videos",
        "description": "Light community pick for high-energy gaming sessions and clips.",
    },
    {
        "name": "SypherPK",
        "category": "Community Picks",
        "embed_url": "https://www.youtube.com/@SypherPK/videos",
        "description": "Fortnite creator feed with guides, patch reactions, and gameplay.",
    },
    {
        "name": "Lachlan",
        "category": "Community Picks",
        "embed_url": "https://www.youtube.com/@Lachlan/videos",
        "description": "Community Fortnite and challenge content with a lighter tone.",
    },
    {
        "name": "Ali-A",
        "category": "Community Picks",
        "embed_url": "https://www.youtube.com/@AliA/videos",
        "description": "OG Fortnite creator feed for updates, reactions, and challenge videos.",
    },
]


def main():
    # Use the app's own oracle_db pool - same connection that the running app uses
    os.environ.setdefault("ORACLE_DSN", "tiktokdb_high")
    os.environ.setdefault("ORACLE_USER", "ADMIN")
    os.environ.setdefault("ORACLE_WALLET", "/home/ubuntu/wallet")

    pw = os.environ.get("ORACLE_PASSWORD", "")
    if not pw:
        print("ERROR: set ORACLE_PASSWORD env var")
        sys.exit(1)

    try:
        from oracle_db import _get_pool
    except ImportError as exc:
        print(f"Cannot import oracle_db: {exc}")
        print("Run this script from the islandforge/ directory.")
        sys.exit(1)

    print("Getting connection pool ...")
    pool = _get_pool()

    # Create tables if missing (Oracle does not support IF NOT EXISTS)
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            for ddl in [
                """CREATE TABLE posts (
                    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    epic_id      VARCHAR2(64),
                    display_name VARCHAR2(128),
                    skin_img     VARCHAR2(512),
                    caption      VARCHAR2(1000),
                    embed_url    VARCHAR2(1024) NOT NULL,
                    likes        NUMBER        DEFAULT 0,
                    approved     NUMBER(1)     DEFAULT 1,
                    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                )""",
                """CREATE TABLE channels (
                    id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    name         VARCHAR2(128) NOT NULL,
                    category     VARCHAR2(64),
                    embed_url    VARCHAR2(1024) NOT NULL,
                    description  VARCHAR2(512),
                    approved     NUMBER(1)     DEFAULT 0,
                    suggested_by VARCHAR2(64),
                    sort_order   NUMBER        DEFAULT 0,
                    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                )""",
            ]:
                try:
                    cur.execute(ddl)
                    conn.commit()
                    table_name = ddl.split()[2]
                    print(f"Created table: {table_name}")
                except Exception as exc:
                    if "ORA-00955" in str(exc):
                        table_name = ddl.split()[2]
                        print(f"Table already exists: {table_name}")
                    else:
                        print(f"DDL warning: {exc}")

    inserted = 0
    updated = 0

    with pool.acquire() as conn:
        with conn.cursor() as cur:
            for sort_order, channel in enumerate(CHANNELS):
                cur.execute(
                    "SELECT COUNT(*) FROM channels WHERE name = :name",
                    {"name": channel["name"]},
                )
                params = {
                    "name": channel["name"],
                    "category": channel["category"],
                    "embed_url": channel["embed_url"],
                    "description": channel.get("description", ""),
                    "sort_order": sort_order,
                }
                if cur.fetchone()[0] > 0:
                    cur.execute(
                        """
                        UPDATE channels
                           SET category = :category,
                               embed_url = :embed_url,
                               description = :description,
                               approved = 1,
                               sort_order = :sort_order
                         WHERE name = :name
                        """,
                        params,
                    )
                    print(f"  UPDATE [{channel['category']}] {channel['name']}")
                    updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO channels (
                            name,
                            category,
                            embed_url,
                            description,
                            approved,
                            suggested_by,
                            sort_order
                        )
                        VALUES (
                            :name,
                            :category,
                            :embed_url,
                            :description,
                            1,
                            'admin',
                            :sort_order
                        )
                        """,
                        params,
                    )
                    print(f"  INSERT [{channel['category']}] {channel['name']}")
                    inserted += 1
        conn.commit()

    print(f"\nDone. {inserted} inserted, {updated} updated.")


if __name__ == "__main__":
    main()
