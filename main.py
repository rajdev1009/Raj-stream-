import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import aiohttp 

# --- 1. CONFIGURATION (Ise Dhyan se Bharo) ---
# NOTE: Numbers bina quotes "" ke hone chahiye.

API_ID = 27084955            # Apna API ID yahan daalo (Integer)
API_HASH = "91c88b554ab2a34f8b0c72228f06fc0b" # Apna Hash yahan daalo
BOT_TOKEN = "7777252416:AAG1D8PvNoISnvOkpxc8t8yY1mP8Wf-Opq4" # Bot Token yahan

# Log Channel ID (Bot yahan Admin hona chahiye)
BIN_CHANNEL = -1002391366258  

# Maalik ki ID (Sirf tum settings khol paoge)
OWNER_ID = 5804953849       

# Koyeb URL (Pehli baar deploy karne ke baad yahan update karna)
# Example: "https://my-bot.koyeb.app"
ONLINE_URL = "https://tropical-constantia-dminemraj-a4819015.koyeb.app/" 
PORT = 8080

# --- SHORTENER CONFIGURATION ---
SHORTENER_DOMAIN = "gplinks.com" 
SHORTENER_API_KEY = "tumhara_api_key"

# --- SYSTEM SETTINGS ---
SYSTEM_CONFIG = {
    "use_shortener": False  # Default ON (Shortener use karega)
}

# Pyrogram Client Setup
app = Client(
    "StreamBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- 2. SHORTENER FUNCTION ---
async def get_short_link(link):
    if not SYSTEM_CONFIG["use_shortener"]:
        return link 
        
    try:
        api_url = f"https://{SHORTENER_DOMAIN}/api?api={SHORTENER_API_KEY}&url={link}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                if "shortenedUrl" in data:
                    return data["shortenedUrl"]
                else:
                    return link
    except Exception as e:
        print(f"⚠️ Shortener Error: {e}")
        return link

# --- 3. SETTINGS PANEL (Owner Only) ---
@app.on_message(filters.command("settings") & filters.private)
async def settings_menu(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Aap Owner nahi hain.")

    status = "✅ ON" if SYSTEM_CONFIG["use_shortener"] else "❌ OFF"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Shortener: {status}", callback_data="toggle_shortener")],
        [InlineKeyboardButton("✖️ Close", callback_data="close_menu")]
    ])
    await message.reply_text("⚙️ **Settings Panel**", reply_markup=buttons)

@app.on_callback_query(filters.regex("toggle_shortener"))
async def toggle_shortener(client, callback):
    if callback.from_user.id != OWNER_ID: return
    SYSTEM_CONFIG["use_shortener"] = not SYSTEM_CONFIG["use_shortener"]
    new_status = "✅ ON" if SYSTEM_CONFIG["use_shortener"] else "❌ OFF"
    new_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Shortener: {new_status}", callback_data="toggle_shortener")],
        [InlineKeyboardButton("✖️ Close", callback_data="close_menu")]
    ])
    await callback.message.edit_reply_markup(reply_markup=new_buttons)

@app.on_callback_query(filters.regex("close_menu"))
async def close_menu(client, callback):
    await callback.message.delete()

# --- 4. STREAMING ENGINE ---
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
        return web.Response(text=f"Server Error: {e}", status=500)

async def status_check(request):
    return web.Response(text="Bot is Online & Running")

# --- 5. MAIN HANDLERS (With Debugging Prints) ---

@app.on_message(filters.command("start"))
async def start(client, message):
    # 👇 Ye Logs mein dikhega agar bot message receive karega
    print(f"📩 DEBUG: Command /start received from {message.from_user.id}")
    
    await message.reply_text(
        "👋 **Hello!**\n"
        "Mujhe koi bhi File ya Video bhejo, main uska Stream Link bana dunga."
    )

@app.on_message(filters.document | filters.video | filters.audio)
async def private_receive_handler(client, message):
    print(f"📩 DEBUG: File received from {message.from_user.id}")
    wait_msg = await message.reply_text("🔄 Processing...")
    
    try:
        # File ko Log Channel mein bhej rahe hain
        log_msg = await message.copy(BIN_CHANNEL)
        print(f"✅ DEBUG: File copied to Channel {BIN_CHANNEL} (Msg ID: {log_msg.id})")
        
        original_link = f"{ONLINE_URL}/watch/{log_msg.id}"
        final_link = await get_short_link(original_link)
        
        note = "⚠️ _Ads skip karein dekhne ke liye_" if SYSTEM_CONFIG["use_shortener"] else "✅ _Direct Link_"
        
        await wait_msg.edit_text(
            f"✅ **Link Ready!**\n\n"
            f"📂 **File:** `{message.document.file_name if message.document else 'Video'}`\n"
            f"🔗 **Link:**\n{final_link}\n\n"
            f"{note}"
        )
    except Exception as e:
        print(f"❌ ERROR: {e}")
        await wait_msg.edit_text(
            f"❌ **Error:** {e}\n\n"
            "**Possible Reasons:**\n"
            "1. Bot Log Channel mein Admin nahi hai.\n"
            "2. BIN_CHANNEL ID galat hai."
        )

# --- 6. STARTUP ---
async def start_server():
    server = web.Application()
    server.router.add_get('/', status_check)
    server.router.add_get('/watch/{message_id}', stream_handler)
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

async def main():
    print("🤖 Bot Starting...")
    await app.start()
    print("✅ Pyrogram Client Started!")
    await start_server()
    print("🌍 Web Server Started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
