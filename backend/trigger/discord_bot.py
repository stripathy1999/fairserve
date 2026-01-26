import discord
import aiohttp
import os
import io
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = "http://localhost:8081/visual-incident"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'FairServe Bot connected as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Check for attachments
    if message.attachments:
        for attachment in message.attachments:
            # Simple filter for images
            if any(ext in attachment.filename.lower() for ext in ['png', 'jpg', 'jpeg', 'webp']):
                await message.reply(f"Processing image: {attachment.filename}...")
                
                try:
                    # Download image
                    image_bytes = await attachment.read()
                    
                    # Send to API
                    async with aiohttp.ClientSession() as session:
                        form = aiohttp.FormData()
                        form.add_field('file', image_bytes, filename=attachment.filename)
                        
                        async with session.post(API_URL, data=form) as response:
                            if response.status == 200:
                                result = await response.json()
                                if "incident" in result:
                                    inc = result["incident"]
                                    reply_text = (
                                        f"✅ **Incident Created!**\n"
                                        f"**Category:** {inc.get('service_type')}\n"
                                        f"**Description:** {inc.get('description_redacted')}\n"
                                        f"**ID:** `{inc.get('incident_id')}`"
                                    )
                                else:
                                    reply_text = f"⚠️ No incident created: {result.get('message', 'Unknown error')}"
                            else:
                                reply_text = f"❌ API Error: {response.status}"
                                
                    await message.reply(reply_text)
                    
                except Exception as e:
                    await message.reply(f"❌ Error processing image: {e}")

def run_bot():
    """Entry point for running the bot via thread."""
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment.")
        return
        
    try:
        # Check if we are in a loop already? client.run handles this well usually,
        # but in a thread a new loop is needed.
        client.run(TOKEN)
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    run_bot()
