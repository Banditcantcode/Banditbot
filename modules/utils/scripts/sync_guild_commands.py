import discord
from discord.ext import commands
import os
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Get guild ID from environment variables
GUILD_ID = int(os.getenv('GUILD_ID', '0'))


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Guild sync bot is online as {bot.user}')
    

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f"Error: Could not find guild with ID {GUILD_ID}")
        await bot.close()
        return
    
    print(f"Found guild: {guild.name} (ID: {guild.id})")
    
    try:
        print(f"Syncing commands to guild {guild.name}...")
        commands = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Successfully synced {len(commands)} commands to {guild.name}:")
        for cmd in commands:
            print(f"- {cmd.name}")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    print("Guild sync complete. Exiting...")
    await bot.close()


@bot.tree.command(name="test", description="A test command to verify slash commands are working")
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("Test command works! Slash commands are functioning correctly.")

# Example of a guild-specific command
@bot.tree.command(
    name="guild_only_test", 
    description="A test command that only works in this guild",
    guild=discord.Object(id=GUILD_ID)
)
async def guild_test_command(interaction: discord.Interaction):
    await interaction.response.send_message("Guild-specific command works!")

# Run the bot
print("Starting guild sync bot...")
bot.run(TOKEN) 