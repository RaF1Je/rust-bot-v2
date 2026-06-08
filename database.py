import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_NAME = "rust_tracker.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                bm_id TEXT,
                rcon_host TEXT,
                rcon_port INTEGER,
                rcon_password TEXT,
                name TEXT,
                last_status TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                steam_id TEXT,
                bm_id TEXT,
                alias TEXT,
                last_online_state TEXT,
                last_server_id TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS online_peaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                chat_id INTEGER,
                server_bm_id TEXT,
                peak_online INTEGER
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS player_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                steam_id TEXT,
                server_bm_id TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                left_at TIMESTAMP
            )
        ''')
        await db.commit()

async def add_server(chat_id: int, bm_id: str, name: str, rcon_host: str = None, rcon_port: int = None, rcon_password: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO servers (chat_id, bm_id, name, rcon_host, rcon_port, rcon_password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (chat_id, bm_id, name, rcon_host, rcon_port, rcon_password))
        await db.commit()

async def remove_server(chat_id: int, bm_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM servers WHERE chat_id = ? AND bm_id = ?', (chat_id, bm_id))
        await db.commit()

async def get_servers(chat_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if chat_id:
            async with db.execute('SELECT * FROM servers WHERE chat_id = ?', (chat_id,)) as cursor:
                return await cursor.fetchall()
        else:
            async with db.execute('SELECT * FROM servers') as cursor:
                return await cursor.fetchall()

async def update_server_status(chat_id: int, bm_id: str, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE servers SET last_status = ? WHERE chat_id = ? AND bm_id = ?', (status, chat_id, bm_id))
        await db.commit()

async def add_player(chat_id: int, steam_id: str, bm_id: str, alias: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO players (chat_id, steam_id, bm_id, alias, last_online_state)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, steam_id, bm_id, alias, "offline"))
        await db.commit()

async def remove_player(chat_id: int, steam_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM players WHERE chat_id = ? AND steam_id = ?', (chat_id, steam_id))
        await db.commit()

async def get_players(chat_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if chat_id:
            async with db.execute('SELECT * FROM players WHERE chat_id = ?', (chat_id,)) as cursor:
                return await cursor.fetchall()
        else:
            async with db.execute('SELECT * FROM players') as cursor:
                return await cursor.fetchall()

async def update_player_state(chat_id: int, steam_id: str, state: str, server_id: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE players 
            SET last_online_state = ?, last_server_id = ? 
            WHERE chat_id = ? AND steam_id = ?
        ''', (state, server_id, chat_id, steam_id))
        await db.commit()

async def update_peak_online(chat_id: int, server_bm_id: str, current_online: int, date: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT peak_online FROM online_peaks WHERE chat_id = ? AND server_bm_id = ? AND date = ?', 
                              (chat_id, server_bm_id, date)) as cursor:
            row = await cursor.fetchone()
            if row:
                if current_online > row['peak_online']:
                    await db.execute('''
                        UPDATE online_peaks 
                        SET peak_online = ? 
                        WHERE chat_id = ? AND server_bm_id = ? AND date = ?
                    ''', (current_online, chat_id, server_bm_id, date))
            else:
                await db.execute('''
                    INSERT INTO online_peaks (date, chat_id, server_bm_id, peak_online) 
                    VALUES (?, ?, ?, ?)
                ''', (date, chat_id, server_bm_id, current_online))
        await db.commit()

async def get_daily_peaks(date: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM online_peaks WHERE date = ?', (date,)) as cursor:
            return await cursor.fetchall()
