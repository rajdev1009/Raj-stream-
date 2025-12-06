import asyncio #raj_dev_01
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import aiohttp 

# --- 1. CONFIGURATION ---
API_ID = 27084955           
API_HASH = "91c88b554ab2a34f8b0c72228f06fc0b" 
BOT_TOKEN = "your_bot_token" #your_bot_token
BIN_CHANNEL = -1002391366258 
OWNER_ID = 5804953849       # Apni Telegram ID yahan daalo (Sirf Owner setting badal payega)
PORT = 8080

# KOYEB URL
ONLINE_URL = "tropical-constantia-dminemraj-a4819015.koyeb.app/" # Deploy ke baad isse Koyeb URL se replace karna

# SHORTENER DETAILS
SHORTENER_DOMAIN = "gplinks.com" 
SHORTENER_API_KEY = "tumhara_api_key"

# --- SYSTEM CONFIG (Default Settings) ---
# Ye system yaad rakhega ki shortener ON hai ya OFF
SYSTEM_CONFIG = {
    "use_shortener": True  # Default ON rakha hai
}

# Pyrogram Client
app = Client("StreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- 2. SHORTENER FUNCTION (With ON/OFF Check) ---
async def get_short_link(link):
    # Sabse pehle check karo ki Setting ON hai ya nahi
    if not SYSTEM_CONFIG["use_shortener"]:
        return link # Agar OFF hai to direct link bhejo
        
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
        print(f"Shortener Error: {e}")
        return link

# --- 3. SETTINGS MENU (ON/OFF BUTTON) ---
@app.on_message(filters.command("settings") & filters.private)
async def settings_menu(client, message):
    # Sirf Owner hi settings khol payega
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Aap Owner nahi hain.")

    status = "✅ ON" if SYSTEM_CONFIG["use_shortener"] else "❌ OFF"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Shortener: {status}", callback_data="toggle_shortener")],
        [InlineKeyboardButton("✖️ Close", callback_data="close_menu")]
    ])
    
    await message.reply_text(
        "⚙️ **Bot Settings Panel**\n\nYahan se aap Shortener ko control kar sakte hain.",
        reply_markup=buttons
    )

@app.on_callback_query(filters.regex("toggle_shortener"))
async def toggle_shortener(client, callback):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Not allowed!", show_alert=True)

    # ON ko OFF, aur OFF ko ON karo
    SYSTEM_CONFIG["use_shortener"] = not SYSTEM_CONFIG["use_shortener"]
    
    # Button Text update karo
    new_status = "✅ ON" if SYSTEM_CONFIG["use_shortener"] else "❌ OFF"
    
    new_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Shortener: {new_status}", callback_data="toggle_shortener")],
        [InlineKeyboardButton("✖️ Close", callback_data="close_menu")]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=new_buttons)
    await callback.answer(f"Shortener ab {new_status} hai!")

@app.on_callback_query(filters.regex("close_menu"))
async def close_menu(client, callback):
    await callback.message.delete()

# --- 4. STREAMING SERVER ---
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
    return web.Response(text="Bot Running")

# --- 5. MAIN HANDLERS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 File bhejo, main link bana dunga!")

@app.on_message(filters.document | filters.video | filters.audio)
async def private_receive_handler(client, message):
    wait_msg = await message.reply_text("🔄 Processing...")
    try:
        log_msg = await message.copy(BIN_CHANNEL)
        original_link = f"{ONLINE_URL}/watch/{log_msg.id}"
        
        # Yahan magic hoga (ON/OFF check karke link banega)
        final_link = await get_short_link(original_link)
        
        # Message decide karo based on Shortener status
        note = "⚠️ _Link open karne ke liye ads skip karein._" if SYSTEM_CONFIG["use_shortener"] else "✅ _Direct Streaming Link_"
        
        await wait_msg.edit_text(
            f"✅ **Link Ready!**\n\n"
            f"📂 **File:** `{message.document.file_name if message.document else 'Video'}`\n"
            f"🔗 **Link:**\n{final_link}\n\n"
            f"{note}"
        )
    except Exception as e:
        await wait_msg.edit_text(f"❌ Error: {e}")

# --- 6. STARTUP ---
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
    print("Bot with Settings Panel Started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
