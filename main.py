import asyncio
from pyrogram import Client, filters
from aiohttp import web
import aiohttp # Shortener API call karne ke liye

# --- 1. CONFIGURATION ---
API_ID = 1234567           
API_HASH = "your_api_hash" 
BOT_TOKEN = "your_bot_token"
BIN_CHANNEL = -100xxxxxxxxx 
PORT = 8080

# 👇 KOYEB KA PUBLIC URL (Deploy hone ke baad yahan dalna)
ONLINE_URL = "http://0.0.0.0:8080" 

# 👇 SHORTENER CONFIGURATION (Yahan apni details daalo)
USE_SHORTENER = True  # Agar shortener nahi chahiye to False kar dena
SHORTENER_DOMAIN = "gplinks.com"  # Example: gplinks.com, droplink.co
SHORTENER_API_KEY = "tumhara_api_key_yahan_daalo"

# Pyrogram Client
app = Client("MyStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- 2. SHORTENER FUNCTION (New Feature) ---
async def get_short_link(link):
    if not USE_SHORTENER:
        return link
        
    try:
        # Zyadatar shorteners ka format yahi hota hai
        api_url = f"https://{SHORTENER_DOMAIN}/api?api={SHORTENER_API_KEY}&url={link}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                
                # Agar success hai to short link return karo
                if "shortenedUrl" in data:
                    return data["shortenedUrl"]
                else:
                    # Agar error aaye to original link hi bhej do
                    return link
    except Exception as e:
        print(f"Shortener Error: {e}")
        return link

# --- 3. STREAMING LOGIC ---
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        msg = await app.get_messages(BIN_CHANNEL, message_id)
        file = msg.document or msg.video or msg.audio
        
        if not file: return web.Response(text="File not found", status=404)

        headers = {
            'Content-Type': file.mime_type,
            'Content-Disposition': f'attachment; filename="{file.file_name}"',
            'Content-Length': str(file.file_size),
        }

        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)

        async for chunk in app.download_media(msg, in_memory=True):
            await response.write(chunk)

        return response
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)

async def status_check(request):
    return web.Response(text="Bot is Online")

# --- 4. TELEGRAM HANDLERS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 File bhejo, main short link bana dunga!")

@app.on_message(filters.document | filters.video | filters.audio)
async def private_receive_handler(client, message):
    wait_msg = await message.reply_text("🔄 Processing & Shortening...")
    
    try:
        log_msg = await message.copy(BIN_CHANNEL)
        
        # Original Stream Link
        original_link = f"{ONLINE_URL}/watch/{log_msg.id}"
        
        # 👇 Short Link Generate kar rahe hain
        final_link = await get_short_link(original_link)
        
        await wait_msg.edit_text(
            f"✅ **Link Ready!**\n\n"
            f"📂 **File:** `{message.document.file_name if message.document else 'Video'}`\n"
            f"🔗 **Watch/Download:**\n{final_link}\n\n"
            f"⚠️ _Note: Link open karne ke liye ads skip karein._"
        )
    except Exception as e:
        await wait_msg.edit_text(f"❌ Error: {e}")

# --- 5. SERVER STARTUP ---
async def start_server():
    server = web.Application()
    server.router.add_get('/', status_check)
    server.router.add_get('/watch/{message_id}', stream_handler)
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

async def main():
    await app.start()
    await start_server()
    print("Bot with Shortener Started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
