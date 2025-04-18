import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


# Get channel ID from environment variables
TICKET_CHANNEL_ID = int(os.getenv('TICKET_CHANNEL_ID', '0'))


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Setup bot is online as {bot.user}')
    
    # Get the channel
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID {TICKET_CHANNEL_ID}")
        await bot.close()
        return
    

    try:
        print(f"Clearing messages in channel {channel.name}...")
        async for message in channel.history(limit=100):
            await message.delete()
            await asyncio.sleep(0.5)  
        print("Channel cleared")
    except Exception as e:
        print(f"Error clearing channel: {e}")
    
    print("Setup complete! Now run the ticket_system.py script to set up the ticket system.")
    
    # Close the bot
    await bot.close()

# Run the bot
bot.run(TOKEN) 