"""
seed_channels.py — Run once on the VM to seed 35 channels into Oracle DB.
Usage: python3 seed_channels.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

CHANNELS = [
    # ── FORTNITE COMPETITIVE ──────────────────────────────────────────
    {
        "name":        "Fortnite Competitive",
        "category":    "Fortnite Competitive",
        "embed_url":   "https://www.youtube.com/@FortniteCompetitive",
        "description": "Official Fortnite esports — FNCS, majors, Grand Royale events",
    },
    {
        "name":        "Epic Games Fortnite",
        "category":    "Fortnite Competitive",
        "embed_url":   "https://www.youtube.com/@Fortnite",
        "description": "Official Fortnite channel — trailers, events, battle pass reveals",
    },
    {
        "name":        "Fortnite World Cup Archive",
        "category":    "Fortnite Competitive",
        "embed_url":   "https://www.youtube.com/watch?v=pPgBjkZ6WLY",
        "description": "Full broadcast — Fortnite World Cup 2019 Finals replay",
    },
    {
        "name":        "FNCS Highlights 24/7",
        "category":    "Fortnite Competitive",
        "embed_url":   "https://www.youtube.com/watch?v=iToNc9UrA9E",
        "description": "FNCS best plays and highlights on loop",
    },

    # ── GAME DEVELOPERS ──────────────────────────────────────────────
    {
        "name":        "Epic Games",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@EpicGames",
        "description": "Epic Games official — Unreal Engine, Fortnite, dev talks",
    },
    {
        "name":        "Unreal Engine",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@UnrealEngine",
        "description": "Unreal Engine tutorials, State of Unreal, dev showcases",
    },
    {
        "name":        "Unity",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@unity",
        "description": "Unity game engine — tutorials, Unite conference talks, demos",
    },
    {
        "name":        "GDC — Game Developers Conference",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@Gdconf",
        "description": "Thousands of game dev talks — design, art, programming, audio",
    },
    {
        "name":        "Naughty Dog",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@NaughtyDog",
        "description": "Official Naughty Dog — The Last of Us, Uncharted dev content",
    },
    {
        "name":        "Bungie",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@Bungie",
        "description": "Destiny 2 dev channel — trailers, This Week at Bungie, live events",
    },
    {
        "name":        "Riot Games",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@riotgames",
        "description": "Riot dev channel — League, Valorant, TFT, dev updates",
    },
    {
        "name":        "Xbox",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@Xbox",
        "description": "Xbox official — game reveals, Developer_Direct, Game Pass drops",
    },
    {
        "name":        "PlayStation",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@PlayStation",
        "description": "PlayStation official — State of Play, game trailers, dev interviews",
    },
    {
        "name":        "Nintendo",
        "category":    "Game Developers",
        "embed_url":   "https://www.youtube.com/@Nintendo",
        "description": "Nintendo official — Direct broadcasts, game reveals, indie world",
    },

    # ── ESPORTS / COMPETITIVE GAMING ─────────────────────────────────
    {
        "name":        "ESL Counter-Strike",
        "category":    "Esports",
        "embed_url":   "https://www.youtube.com/@ESLCounterStrike",
        "description": "IEM, ESL Pro League CS2 live events and VODs",
    },
    {
        "name":        "PGL Esports",
        "category":    "Esports",
        "embed_url":   "https://www.youtube.com/@PGLesports",
        "description": "PGL — CS2, Dota 2 and more major tournament broadcasts",
    },
    {
        "name":        "LCK — League of Legends Champions Korea",
        "category":    "Esports",
        "embed_url":   "https://www.youtube.com/@lck",
        "description": "Official LCK — Korea's top League of Legends league live and VOD",
    },
    {
        "name":        "Valorant Champions Tour",
        "category":    "Esports",
        "embed_url":   "https://www.youtube.com/@VALORANTesports",
        "description": "Official VCT — Masters, Champions, international Valorant esports",
    },
    {
        "name":        "Rocket League Esports",
        "category":    "Esports",
        "embed_url":   "https://www.youtube.com/@RocketLeagueEsports",
        "description": "RLCS — Rocket League Championship Series official broadcasts",
    },
    {
        "name":        "Overwatch League",
        "category":    "Esports",
        "embed_url":   "https://www.youtube.com/@overwatchleague",
        "description": "Official Overwatch League archive — match VODs and highlights",
    },

    # ── CREATIVE / UEFN ──────────────────────────────────────────────
    {
        "name":        "UEFN & Creative 2.0 Tutorials",
        "category":    "Creative / UEFN",
        "embed_url":   "https://www.youtube.com/results?search_query=UEFN+tutorial+2024",
        "description": "Community UEFN tutorials — island design, verse scripting",
    },
    {
        "name":        "Unreal Sensei",
        "category":    "Creative / UEFN",
        "embed_url":   "https://www.youtube.com/@UnrealSensei",
        "description": "Unreal Engine tutorials for game devs and Fortnite creators",
    },
    {
        "name":        "William Faucher",
        "category":    "Creative / UEFN",
        "embed_url":   "https://www.youtube.com/@WilliamFaucher",
        "description": "Cinematic Unreal Engine — lighting, landscapes, visual design",
    },

    # ── CHILL GAMING / 24-7 ──────────────────────────────────────────
    {
        "name":        "Lofi Gaming Radio 24/7",
        "category":    "Chill Gaming",
        "embed_url":   "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "description": "Lofi hip hop radio — beats to relax and game to, 24/7",
    },
    {
        "name":        "Chillhop Music 24/7",
        "category":    "Chill Gaming",
        "embed_url":   "https://www.youtube.com/watch?v=5yx6BWlEVcY",
        "description": "Chillhop Records — 24/7 lofi beats perfect for gaming sessions",
    },
    {
        "name":        "Video Game Music 24/7",
        "category":    "Chill Gaming",
        "embed_url":   "https://www.youtube.com/watch?v=OhcGNMGQBxU",
        "description": "Non-stop video game OSTs — Zelda, Final Fantasy, Halo and more",
    },
    {
        "name":        "Retro Gaming 24/7",
        "category":    "Chill Gaming",
        "embed_url":   "https://www.youtube.com/watch?v=wREBD2og5iE",
        "description": "Classic retro game music and gameplay on loop",
    },

    # ── GAMING NEWS / REVIEWS ────────────────────────────────────────
    {
        "name":        "IGN",
        "category":    "Gaming News",
        "embed_url":   "https://www.youtube.com/@IGN",
        "description": "IGN — game reviews, trailers, news, live events coverage",
    },
    {
        "name":        "GameSpot",
        "category":    "Gaming News",
        "embed_url":   "https://www.youtube.com/@GameSpot",
        "description": "GameSpot — reviews, features, show coverage, live E3-style events",
    },
    {
        "name":        "Kotaku",
        "category":    "Gaming News",
        "embed_url":   "https://www.youtube.com/@Kotaku",
        "description": "Kotaku — gaming culture, editorials, retrospectives",
    },
    {
        "name":        "Digital Foundry",
        "category":    "Gaming News",
        "embed_url":   "https://www.youtube.com/@DigitalFoundry",
        "description": "Tech analysis — frame rates, resolution, console comparisons",
    },
    {
        "name":        "Gameranx",
        "category":    "Gaming News",
        "embed_url":   "https://www.youtube.com/@gameranxTV",
        "description": "Before You Buy, top 10 lists, gaming news — beginner friendly",
    },

    # ── COMMUNITY PICKS ──────────────────────────────────────────────
    {
        "name":        "Mythpat Gaming",
        "category":    "Community Picks",
        "embed_url":   "https://www.youtube.com/@Mythpat",
        "description": "Fun, lighthearted gaming content — high energy gameplay",
    },
    {
        "name":        "SypherPK",
        "category":    "Community Picks",
        "embed_url":   "https://www.youtube.com/@SypherPK",
        "description": "Fortnite content creator — tips, gameplay, patch reactions",
    },
    {
        "name":        "Lachlan",
        "category":    "Community Picks",
        "embed_url":   "https://www.youtube.com/@Lachlan",
        "description": "Fortnite, gaming challenges — fun community-focused content",
    },
    {
        "name":        "Ali-A",
        "category":    "Community Picks",
        "embed_url":   "https://www.youtube.com/@AliaA",
        "description": "Fortnite & gaming news — one of the OG Fortnite YouTube channels",
    },
]

def main():
    try:
        import oracledb
    except ImportError:
        print("oracledb not installed — run: pip install oracledb --break-system-packages")
        sys.exit(1)

    wallet  = os.environ.get("ORACLE_WALLET", "/home/ubuntu/wallet")
    dsn     = os.environ.get("ORACLE_DSN",    "tiktokdb_high")
    user    = os.environ.get("ORACLE_USER",   "ADMIN")
    pw      = os.environ.get("ORACLE_PASSWORD","")

    print(f"Connecting to {dsn} as {user} (thin mode) ...")
    conn = oracledb.connect(user=user, password=pw, dsn=dsn,
                            config_dir=wallet, wallet_location=wallet,
                            wallet_password="")

    cur = conn.cursor()

    # Ensure table exists
    try:
        cur.execute("""
            CREATE TABLE channels (
                id           NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name         VARCHAR2(128) NOT NULL,
                category     VARCHAR2(64),
                embed_url    VARCHAR2(1024) NOT NULL,
                description  VARCHAR2(512),
                approved     NUMBER(1)     DEFAULT 0,
                suggested_by VARCHAR2(64),
                sort_order   NUMBER        DEFAULT 0,
                created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("Created channels table.")
    except Exception as e:
        if "ORA-00955" in str(e):
            print("channels table already exists.")
        else:
            print(f"Table create warning: {e}")

    inserted = 0
    skipped  = 0
    for i, ch in enumerate(CHANNELS):
        # Check if already exists
        cur.execute("SELECT COUNT(*) FROM channels WHERE name = :n", {"n": ch["name"]})
        if cur.fetchone()[0] > 0:
            print(f"  SKIP  [{ch['category']}] {ch['name']}")
            skipped += 1
            continue
        cur.execute("""
            INSERT INTO channels (name, category, embed_url, description, approved, suggested_by, sort_order)
            VALUES (:name, :category, :embed_url, :description, 1, 'admin', :sort_order)
        """, {
            "name":        ch["name"],
            "category":    ch["category"],
            "embed_url":   ch["embed_url"],
            "description": ch.get("description",""),
            "sort_order":  i,
        })
        print(f"  INSERT [{ch['category']}] {ch['name']}")
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone. {inserted} inserted, {skipped} skipped.")

if __name__ == "__main__":
    main()
