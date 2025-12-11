import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web
import time
import math

# --- CONFIGURATION (इसे ध्यान से भरें) ---
API_ID = 12345678  # my.telegram.org se milega
API_HASH = "your_api_hash_here" # my.telegram.org se milega
BOT_TOKEN = "7793783847:AAF0QSWnyLjUuaY8NfX-GumX0CY_cS2agCY"
BIN_CHANNEL = -1001234567890  # Private Channel ID jaha files store hongi
APP_URL = "https://your-app-name.koyeb.app" # Koyeb App URL (no slash at end)
# ---------------------------------------

# Client Setup
app = Client(
    "RajStreamBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- WEB SERVER (Streaming Logic) ---
routes = web.RouteTableDef()

@routes.get("/")
async def home(request):
    return web.Response(text="✅ Raj Stream Bot is Alive for Movies!")

@routes.get("/stream/{message_id}")
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        # Log channel se message uthana
        msg = await app.get_messages(BIN_CHANNEL, message_id)
        if not msg or not msg.video and not msg.document:
            return web.Response(text="File not found", status=404)

        file = msg.video or msg.document
        file_size = file.file_size
        file_name = getattr(file, "file_name", "video.mp4")
        mime_type = getattr(file, "mime_type", "video/mp4")

        # Range Header Handling (Seeking ke liye)
        range_header = request.headers.get("Range")
        from_bytes, until_bytes = 0, file_size - 1
        if range_header:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1

        length = until_bytes - from_bytes + 1
        headers = {
            "Content-Type": mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(length),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }

        # Response shuru karna
        response = web.StreamResponse(status=206 if range_header else 200, headers=headers)
        await response.prepare(request)

        # Telegram se chunks lekar user ko bhejna
        async for chunk in app.stream_media(msg, offset=from_bytes, limit=length):
            await response.write(chunk)
        
        return response

    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)

# --- BOT COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "🎬 **Raj Movie Stream Bot**\n\n"
        "Muje koi bhi Movie ya Video bhejo, main uska **High Speed Stream Link** dunga.\n"
        "Ye link MX Player aur VLC mein bhi chalega!"
    )

@app.on_message((filters.document | filters.video) & filters.private)
async def generate_link(client, message: Message):
    status_msg = await message.reply_text("🔄 **Processing Movie...**")
    
    try:
        # File ko Log Channel me forward karna (Permanent Link ke liye)
        log_msg = await message.copy(BIN_CHANNEL)
        stream_link = f"{APP_URL}/stream/{log_msg.id}"
        
        await status_msg.edit_text(
            f"✅ **Link Generated!**\n\n"
            f"📂 **File:** {message.video.file_name if message.video and message.video.file_name else 'Movie'}\n"
            f"🔗 **Stream/Download Link:**\n`{stream_link}`\n\n"
            f"⚠️ *Ye link MX Player me paste karke movie dekh sakte ho.*"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}\nMake sure Bot is Admin in Log Channel.")

# --- RUNNING SERVER & BOT ---

async def start_services():
    # Web Server Start
    server = web.AppRunner(web.Application(client_max_size=30000000)) # 30MB request limit (headers)
    server.app.add_routes(routes)
    await server.setup()
    site = web.TCPSite(server, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Web Server Running...")

    # Bot Start
    print("🤖 Bot Starting...")
    await app.start()
    await asyncio.Event().wait() # Keep running

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
    
