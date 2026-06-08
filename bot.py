import os
import logging
import asyncio
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
import battlemetrics as bm

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
PORT = int(os.getenv("PORT", "8080"))

# States for conversations
ADD_SERVER_BM_ID = 1
ADD_PLAYER_STEAM_ID = 2
REMOVE_SERVER_SELECT = 3
REMOVE_PLAYER_SELECT = 4

def is_admin(user_id: int) -> bool:
    if not ADMIN_IDS:
        return True # If no admins specified, everyone is admin
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Привет! Я бот для отслеживания серверов и игроков Rust.\n\n"
        "Команды:\n"
        "/status - статус серверов\n"
        "/players - статус игроков\n"
        "/add_server - добавить сервер\n"
        "/remove_server - удалить сервер\n"
        "/add_player - добавить игрока\n"
        "/remove_player - удалить игрока\n"
    )
    await update.message.reply_text(msg)

# --- Server Management ---
async def add_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Только администраторы могут добавлять серверы.")
        return ConversationHandler.END
    await update.message.reply_text("Введите BattleMetrics ID сервера (например, 1234567):")
    return ADD_SERVER_BM_ID

async def add_server_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bm_id = update.message.text.strip()
    if not bm_id.isdigit():
        await update.message.reply_text("ID должен состоять только из цифр. Попробуйте еще раз или напишите /cancel.")
        return ADD_SERVER_BM_ID
    
    server_info = await bm.get_server_info(bm_id)
    if not server_info:
        await update.message.reply_text("Не удалось найти сервер с таким ID. Проверьте ID и попробуйте снова.")
        return ConversationHandler.END
        
    await db.add_server(update.effective_chat.id, bm_id, server_info["name"])
    await update.message.reply_text(f"Сервер '{server_info['name']}' успешно добавлен!")
    return ConversationHandler.END

async def remove_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Только администраторы могут удалять серверы.")
        return ConversationHandler.END
        
    servers = await db.get_servers(update.effective_chat.id)
    if not servers:
        await update.message.reply_text("Список серверов пуст.")
        return ConversationHandler.END
        
    keyboard = []
    for srv in servers:
        keyboard.append([InlineKeyboardButton(srv['name'], callback_data=f"del_srv_{srv['bm_id']}")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    
    await update.message.reply_text("Выберите сервер для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    return REMOVE_SERVER_SELECT

async def remove_server_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("Отменено.")
        return ConversationHandler.END
        
    bm_id = query.data.replace("del_srv_", "")
    await db.remove_server(update.effective_chat.id, bm_id)
    await query.edit_message_text("Сервер удален.")
    return ConversationHandler.END

# --- Player Management ---
async def add_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите SteamID64 игрока (17 цифр):")
    return ADD_PLAYER_STEAM_ID

async def add_player_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    steam_id = update.message.text.strip()
    if not steam_id.isdigit() or len(steam_id) != 17:
        await update.message.reply_text("Неверный формат SteamID64. Введите 17 цифр или /cancel.")
        return ADD_PLAYER_STEAM_ID
        
    msg = await update.message.reply_text("Ищу игрока в BattleMetrics...")
    bm_id, alias = await bm.search_player_by_steamid(steam_id)
    
    if not bm_id:
        await msg.edit_text("Не удалось найти игрока. Возможно, он никогда не играл на серверах Rust, отслеживаемых BM.")
        return ConversationHandler.END
        
    await db.add_player(update.effective_chat.id, steam_id, bm_id, alias)
    await msg.edit_text(f"Игрок '{alias}' (SteamID: {steam_id}) добавлен в список отслеживания!")
    return ConversationHandler.END

async def remove_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = await db.get_players(update.effective_chat.id)
    if not players:
        await update.message.reply_text("Список игроков пуст.")
        return ConversationHandler.END
        
    keyboard = []
    for p in players:
        keyboard.append([InlineKeyboardButton(p['alias'], callback_data=f"del_plr_{p['steam_id']}")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
    
    await update.message.reply_text("Выберите игрока для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    return REMOVE_PLAYER_SELECT

async def remove_player_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("Отменено.")
        return ConversationHandler.END
        
    steam_id = query.data.replace("del_plr_", "")
    await db.remove_player(update.effective_chat.id, steam_id)
    await query.edit_message_text("Игрок удален.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# --- Status Commands ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    servers = await db.get_servers(update.effective_chat.id)
    if not servers:
        await update.message.reply_text("Список серверов пуст. Добавьте сервер командой /add_server.")
        return

    lines = ["📊 Статус серверов:"]
    for srv in servers:
        info = await bm.get_server_info(srv['bm_id'])
        if info:
            status_emoji = "🟢" if info["status"] == "online" else "🔴"
            lines.append(f"{status_emoji} {info['name']}: {info['players']}/{info['max_players']}")
        else:
            lines.append(f"❓ {srv['name']}: Недоступен")
            
    await update.message.reply_text("\n".join(lines))

async def players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = await db.get_players(update.effective_chat.id)
    if not players:
        await update.message.reply_text("Список игроков пуст. Добавьте игрока командой /add_player.")
        return

    lines = ["👥 Статус игроков:"]
    for p in players:
        is_online, srv_id, srv_name = await bm.get_player_status(p['bm_id'])
        if is_online:
            lines.append(f"🟢 {p['alias']}: Играет на '{srv_name}'")
        else:
            lines.append(f"🔴 {p['alias']}: Офлайн")
            
    await update.message.reply_text("\n".join(lines))

# --- Background Tasks ---
async def send_daily_summary(app):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    peaks = await db.get_daily_peaks(today)
    
    chat_summaries = {}
    for peak in peaks:
        chat_id = peak['chat_id']
        if chat_id not in chat_summaries:
            chat_summaries[chat_id] = []
        chat_summaries[chat_id].append(peak)
        
    for chat_id, chat_peaks in chat_summaries.items():
        if not chat_peaks:
            continue
            
        lines = [f"📈 Ежедневная сводка онлайна ({today}):"]
        for p in chat_peaks:
            info = await bm.get_server_info(p['server_bm_id'])
            name = info['name'] if info else f"ID:{p['server_bm_id']}"
            lines.append(f"- {name}: Пик {p['peak_online']} игроков")
            
        try:
            await app.bot.send_message(chat_id=chat_id, text="\n".join(lines))
        except Exception as e:
            logger.error(f"Failed to send summary to {chat_id}: {e}")

async def check_updates_loop(app):
    while True:
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # 1. Check Servers
            all_servers = await db.get_servers()
            for srv in all_servers:
                chat_id = srv['chat_id']
                bm_id = srv['bm_id']
                old_status = srv['last_status']
                
                info = await bm.get_server_info(bm_id)
                if not info:
                    continue
                    
                new_status = info['status']
                if old_status != new_status and old_status is not None:
                    if new_status == "online":
                        await app.bot.send_message(chat_id, f"✅ Сервер '{info['name']}' поднялся!")
                    elif new_status == "offline" or new_status == "dead":
                        await app.bot.send_message(chat_id, f"❌ Сервер '{info['name']}' упал!")
                
                if old_status != new_status:
                    await db.update_server_status(chat_id, bm_id, new_status)
                    
                if new_status == "online":
                    await db.update_peak_online(chat_id, bm_id, info['players'], today)

            # 2. Check Players
            all_players = await db.get_players()
            for p in all_players:
                chat_id = p['chat_id']
                steam_id = p['steam_id']
                old_state = p['last_online_state']
                
                is_online, srv_id, srv_name = await bm.get_player_status(p['bm_id'])
                new_state = "online" if is_online else "offline"
                
                if old_state != new_state and old_state is not None:
                    if new_state == "online":
                        await app.bot.send_message(chat_id, f"🎮 Игрок {p['alias']} зашел на сервер: {srv_name}")
                    else:
                        await app.bot.send_message(chat_id, f"🚪 Игрок {p['alias']} вышел с сервера")
                
                if old_state != new_state:
                    await db.update_player_state(chat_id, steam_id, new_state, srv_id)

        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            
        await asyncio.sleep(CHECK_INTERVAL)

async def post_init(application):
    await db.init_db()
    
    # Keep-alive HTTP server for Render
    async def handle_request(reader, writer):
        # We don't really care about the request content
        request = await reader.read(1024)
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nBot is running!"
        writer.write(response)
        await writer.drain()
        writer.close()
        
    try:
        server = await asyncio.start_server(handle_request, '0.0.0.0', PORT)
        logger.info(f"Keep-alive server started on port {PORT}")
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        
    # Start polling loop
    asyncio.create_task(check_updates_loop(application))

    # Scheduler for daily summary
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_summary, 'cron', hour=20, minute=0, timezone=timezone.utc, args=[application])
    scheduler.start()

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("players", players))

    # Add Server Conversation
    conv_add_server = ConversationHandler(
        entry_points=[CommandHandler('add_server', add_server_start)],
        states={
            ADD_SERVER_BM_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_add_server)

    # Remove Server Conversation
    conv_remove_server = ConversationHandler(
        entry_points=[CommandHandler('remove_server', remove_server_start)],
        states={
            REMOVE_SERVER_SELECT: [CallbackQueryHandler(remove_server_finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_remove_server)

    # Add Player Conversation
    conv_add_player = ConversationHandler(
        entry_points=[CommandHandler('add_player', add_player_start)],
        states={
            ADD_PLAYER_STEAM_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_player_finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_add_player)

    # Remove Player Conversation
    conv_remove_player = ConversationHandler(
        entry_points=[CommandHandler('remove_player', remove_player_start)],
        states={
            REMOVE_PLAYER_SELECT: [CallbackQueryHandler(remove_player_finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_remove_player)

    logger.info("Bot started polling...")
    app.run_polling()

if __name__ == '__main__':
    main()
