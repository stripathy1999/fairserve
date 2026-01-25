import discord
import aiohttp
import os
import io
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

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment.")
    else:
        try:
            client.run(TOKEN)
        except discord.errors.PrivilegedIntentsRequired:
            print("\n❌ ERROR: Privileged Intents are missing!")
            print("To fix this:")
            print("1. Go to https://discord.com/developers/applications")
            print("2. Click on your Bot application")
            print("3. Go to the 'Bot' tab (left sidebar)")
            print("4. Scroll down to 'Privileged Gateway Intents'")
            print("5. ENABLE 'Message Content Intent'")
            print("6. Save Changes and restart this script.\n")
        except Exception as e:
            print(f"Error running bot: {e}")
