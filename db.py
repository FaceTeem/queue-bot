import aiosqlite

import config


async def init():
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS subs(
            user_id INTEGER, city TEXT, service TEXT,
            PRIMARY KEY(user_id, city, service))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS seen(
            key TEXT PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        await db.commit()


async def add_sub(user_id, city, service):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO subs VALUES(?,?,?)", (user_id, city, service))
        await db.commit()


async def remove_all(user_id):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("DELETE FROM subs WHERE user_id=?", (user_id,))
        await db.commit()


async def user_subs(user_id):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT city, service FROM subs WHERE user_id=?", (user_id,))
        return await cur.fetchall()


async def subscribers(city, service):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM subs WHERE city=? AND service=?", (city, service))
        return [r[0] for r in await cur.fetchall()]


async def is_new(key) -> bool:
    """True the first time a slot is seen, so nobody gets the same alert twice."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("INSERT OR IGNORE INTO seen(key) VALUES(?)", (key,))
        await db.execute("DELETE FROM seen WHERE ts < datetime('now','-3 days')")
        await db.commit()
        return cur.rowcount == 1
