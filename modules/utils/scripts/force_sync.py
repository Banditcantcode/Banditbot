import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Force sync bot is online as {bot.user}')
    try:
        print("Attempting to sync commands globally...")
        await bot.tree.sync(guild=None)
        print("Global sync complete!")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    print("Attempting to sync commands to all guilds individually...")
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
            print(f"Synced commands to guild: {guild.name} (ID: {guild.id})")
        except Exception as e:
            print(f"Error syncing to guild {guild.name}: {e}")
    
    print("Force sync complete. Exiting...")
    await bot.close()

@bot.tree.command(name="test", description="A test command to verify slash commands are working")
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("Test command works! Slash commands are functioning correctly.")

# Run the bot
bot.run(TOKEN) 