import discord
from discord.ext import commands
from discord import app_commands
import json
import aiohttp
import os
from dotenv import load_dotenv
import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from modules.utils.db import get_mysql_connection, get_player_from_discord, get_characters

log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "finder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("finder")

load_dotenv()

original_request = aiohttp.ClientSession._request
async def _request(self, *args, **kwargs):
    kwargs['ssl'] = False
    return await original_request(self, *args, **kwargs)
aiohttp.ClientSession._request = _request

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

REACTION_ROLE_CONFIG = {
    'message_id': int(os.getenv('REACTION_MESSAGE_ID')),
    'emoji': '✅',
    'role_id': int(os.getenv('REACTION_ROLE_ID'))
}

STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID'))

@bot.event
async def on_ready():
    logger.info(f'Finder Bot is online as {bot.user}')
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
        
        try:
            message_id = REACTION_ROLE_CONFIG['message_id']
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.add_reaction(REACTION_ROLE_CONFIG['emoji'])
                        logger.info(f"Added reaction to message {message_id}")
                        break
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        continue
        except Exception as e:
            logger.error(f"Error setting up reaction: {e}")
            
    except Exception as e:
        logger.error(f'Error syncing commands: {e}')

@bot.event
async def on_raw_reaction_add(payload):
    if (payload.message_id == REACTION_ROLE_CONFIG['message_id'] and 
        str(payload.emoji) == REACTION_ROLE_CONFIG['emoji']):
            
        if payload.user_id == bot.user.id:
            return
            
        try:
            guild = bot.get_guild(payload.guild_id)
            if not guild:
                return
                
            role = guild.get_role(REACTION_ROLE_CONFIG['role_id'])
            if not role:
                logger.error(f"Role {REACTION_ROLE_CONFIG['role_id']} not found")
                return
                
            member = guild.get_member(payload.user_id)
            if not member:
                logger.error(f"Member {payload.user_id} not found")
                return
                
            await member.add_roles(role, reason="Reaction role")
            logger.info(f"Added role {role.name} to {member.display_name}")
            
        except Exception as e:
            logger.error(f"Error adding role: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    if (payload.message_id == REACTION_ROLE_CONFIG['message_id'] and 
        str(payload.emoji) == REACTION_ROLE_CONFIG['emoji']):
        
        try:
            guild = bot.get_guild(payload.guild_id)
            if not guild:
                return
                
            role = guild.get_role(REACTION_ROLE_CONFIG['role_id'])
            if not role:
                return
                
            member = guild.get_member(payload.user_id)
            if not member:
                return
                
            await member.remove_roles(role, reason="Reaction role removed")
            logger.info(f"Removed role {role.name} from {member.display_name}")
            
        except Exception as e:
            logger.error(f"Error removing role: {e}")

@bot.command()
async def sync(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send("You do not have permission to sync commands.")
        return
    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands globally.")


@bot.tree.command(name="vehicleinfo", description="Lookup vehicle inventory by plate")
@app_commands.describe(plate="Plate number to search for")
async def vehicleinfo(interaction: discord.Interaction, plate: str):
    logger.info(f"Vehicle info command received for plate: {plate}")

    await interaction.response.defer()
    has_role = discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID)

    if not has_role:
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return

    conn = None
    cursor = None

    try:
        logger.info("Connecting to database...")
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT trunk, glovebox FROM player_vehicles WHERE plate = %s"
        cursor.execute(query, (plate.upper(),))
        result = cursor.fetchone()

        if result:
            trunk_data = json.loads(result.get('trunk') or "[]")
            glovebox_data = json.loads(result.get('glovebox') or "[]")

            def format_inventory(items):
                if not items:
                    return "Empty"
                lines = []
                for item in items:
                    name = item.get("name", "Unknown")
                    count = item.get("count", 1)
                    lines.append(f"{name} {count}")
                return "\n".join(lines)

            trunk_formatted = format_inventory(trunk_data)
            glovebox_formatted = format_inventory(glovebox_data)

            embed = discord.Embed(title=f"Inventory for Plate: {plate.upper()}", color=discord.Color.blue())
            embed.add_field(name="🧳 Trunk", value=f"```{trunk_formatted}```", inline=False)
            embed.add_field(name="🧤 Glovebox", value=f"```{glovebox_formatted}```", inline=False)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"No vehicle found with plate `{plate.upper()}`.")

    except Exception as e:
        logger.error(f"Error in vehicleinfo command: {e}")
        await interaction.followup.send(f"An error occurred: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bot.tree.command(name="info", description="Look up characters associated with a Discord user")
@app_commands.describe(user="Mention the Discord user to search for")
async def info(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer()
    has_role = discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID)

    if not has_role:
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return

    try:
        discord_id = str(user.id)
        
        user_result = get_player_from_discord(discord_id)

        if not user_result:
            await interaction.followup.send(f"No player found for Discord user <@{discord_id}>.")
            return
            
        user_id = user_result['userId']
        license = user_result['license']
        license2 = user_result.get('license2', '')
        
        embed = discord.Embed(title="User Information", color=discord.Color.blue())
        
        user_info = f"Username: {user_result.get('username', 'N/A')}\n"
        user_info += f"Account ID: {user_result.get('userId', 'N/A')}\n"
        user_info += f"{user_result.get('license2', 'N/A')}\n"
        user_info += f"Discord: {user_result.get('discord', 'N/A')}\n"
        user_info += f"FiveM: {user_result.get('fivem', 'N/A')}"
        
        embed.add_field(name="User Info", value=f"```{user_info}```", inline=False)
        
        character_results = get_characters(license, license2, user_id)
        
        if character_results:
            characters_overview = ""
            for char in character_results:
                try:
                    charinfo = json.loads(char.get('charinfo', '{}'))
                    first_name = charinfo.get('firstname', 'Unknown')
                    last_name = charinfo.get('lastname', 'Unknown')
                    characters_overview += f"ID: {char.get('citizenid')} | {first_name} {last_name}\n"
                except json.JSONDecodeError:
                    characters_overview += f"ID: {char.get('citizenid')} | Name: {char.get('name', 'Unknown')}\n"
            
            embed.add_field(
                name="All Characters", 
                value=f"```{characters_overview}```", 
                inline=False
            )
        else:
            embed.add_field(name="Characters", value="```No characters found for this user.```", inline=False)
        
        embed.add_field(
            name="Detailed Info",
            value="Use `/character @user` or `/character [citizenid]` to view detailed character information.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error in info command: {e}")
        await interaction.followup.send(f"An error occurred: {e}")


@bot.tree.command(name="character", description="Look up detailed information about a character")
@app_commands.describe(
    user="Mention the Discord user to search for (optional)",
    citizenid="Citizen ID to look up (optional)"
)
async def character(
    interaction: discord.Interaction, 
    user: discord.User = None, 
    citizenid: str = None
):
    await interaction.response.defer()
    has_role = discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID)

    if not has_role:
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return
    
    if not user and not citizenid:
        await interaction.followup.send("You must provide either a user mention or a citizen ID.")
        return
        
    conn = None
    cursor = None
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        if citizenid:
            char_query = "SELECT * FROM players WHERE citizenid = %s"
            cursor.execute(char_query, (citizenid,))
            character = cursor.fetchone()
            
            if not character:
                await interaction.followup.send(f"No character found with citizen ID: {citizenid}")
                return
                
            embed = create_character_embed(character)
            await interaction.followup.send(embed=embed)
                
        elif user:
            discord_id = str(user.id)
            user_result = get_player_from_discord(discord_id)
            
            if not user_result:
                await interaction.followup.send(f"No player found for Discord user <@{discord_id}>.")
                return
                
            user_id = user_result['userId']
            license = user_result['license']
            license2 = user_result.get('license2', '')
            
            characters = get_characters(license, license2, user_id)
            
            if not characters:
                await interaction.followup.send(f"No characters found for user <@{discord_id}>.")
                return
                
            embed = discord.Embed(title=f"Characters for {user.display_name}", color=discord.Color.blue())
            
            for character in characters:
                try:
                    charinfo = json.loads(character.get('charinfo', '{}'))
                    first_name = charinfo.get('firstname', 'Unknown')
                    last_name = charinfo.get('lastname', 'Unknown')
                    
                    char_title = f"{first_name} {last_name} (ID: {character.get('citizenid', 'XXX')})"
                    
                    char_details = f"Character ID: {character.get('citizenid', 'N/A')}\n"
                    char_details += f"CID: {character.get('cid', 'N/A')}\n"
                    char_details += f"Database ID: {character.get('id', 'N/A')}\n"
                    char_details += f"Name: {character.get('name', 'N/A')}\n"
                    char_details += f"First Name: {first_name}\n"
                    char_details += f"Last Name: {last_name}\n"
                    
                    if 'birthdate' in charinfo:
                        char_details += f"Birthdate: {charinfo.get('birthdate', 'N/A')}\n"
                    
                    if 'gender' in charinfo:
                        char_details += f"Gender: {charinfo.get('gender', 'N/A')}\n"
                    
                    if 'nationality' in charinfo:
                        char_details += f"Nationality: {charinfo.get('nationality', 'N/A')}"
                    
                    embed.add_field(name=f"{char_title}", value=f"```{char_details}```", inline=False)
                    
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Error parsing character info: {e}")
                    char_info = f"Character ID: {character.get('citizenid', 'N/A')}\n"
                    char_info += f"Error parsing character data: {str(e)}"
                    embed.add_field(name=f"Character {character.get('citizenid', 'Unknown')}", value=f"```{char_info}```", inline=False)
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error in character command: {e}")
        await interaction.followup.send(f"An error occurred: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_character_embed(character):
    try:
        charinfo = json.loads(character.get('charinfo', '{}'))
        first_name = charinfo.get('firstname', 'Unknown')
        last_name = charinfo.get('lastname', 'Unknown')
        
        embed = discord.Embed(
            title=f"Character: {first_name} {last_name}",
            color=discord.Color.blue()
        )
        
        char_details = f"Character ID: {character.get('citizenid', 'N/A')}\n"
        char_details += f"CID: {character.get('cid', 'N/A')}\n"
        char_details += f"Database ID: {character.get('id', 'N/A')}\n"
        char_details += f"Name: {character.get('name', 'N/A')}\n"
        char_details += f"First Name: {first_name}\n"
        char_details += f"Last Name: {last_name}\n"
        
        if 'birthdate' in charinfo:
            char_details += f"Birthdate: {charinfo.get('birthdate', 'N/A')}\n"
        
        if 'gender' in charinfo:
            char_details += f"Gender: {charinfo.get('gender', 'N/A')}\n"
        
        if 'nationality' in charinfo:
            char_details += f"Nationality: {charinfo.get('nationality', 'N/A')}"
        
        embed.add_field(name="Character Details", value=f"```{char_details}```", inline=False)
        
        return embed
    except Exception as e:
        logger.error(f"Error creating character embed: {e}")
        embed = discord.Embed(title="Character Information", color=discord.Color.red())
        embed.add_field(name="Error", value=f"Error parsing character data: {str(e)}", inline=False)
        return embed


@bot.tree.command(name="vehicles", description="Look up vehicles owned by a Discord user")
@app_commands.describe(user="Mention the Discord user to search for")
async def vehicles(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer()
    has_role = discord.utils.get(interaction.user.roles, id=STAFF_ROLE_ID)

    if not has_role:
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return

    conn = None
    cursor = None

    try:
        discord_id = str(user.id)
        user_result = get_player_from_discord(discord_id)
        
        if not user_result:
            await interaction.followup.send(f"No player found for Discord user <@{discord_id}>.")
            return

        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        user_id = user_result['userId']
        license = user_result['license']
        license2 = user_result.get('license2', '')
        
        char_query = "SELECT citizenid FROM players WHERE license = %s OR license = %s OR userId = %s"
        cursor.execute(char_query, (license, license2, user_id))
        characters = cursor.fetchall()
        
        if not characters:
            await interaction.followup.send(f"No characters found for user <@{discord_id}>.")
            return
            
        citizenids = [char['citizenid'] for char in characters]
        
        placeholders = ', '.join(['%s'] * len(citizenids))
        vehicle_query = f"""
        SELECT plate, vehicle, hash, garage, state, depotprice, drivingdistance, status, fuel, engine, body
        FROM player_vehicles 
        WHERE citizenid IN ({placeholders})
        """
        
        cursor.execute(vehicle_query, citizenids)
        vehicles = cursor.fetchall()
        
        if not vehicles:
            await interaction.followup.send(f"No vehicles found for user <@{discord_id}>.")
            return
            
        embed = discord.Embed(
            title=f"Vehicles owned by {user.display_name}",
            color=discord.Color.blue(),
            description=f"Found {len(vehicles)} vehicles across {len(citizenids)} characters."
        )
        
        by_garage = {}
        for vehicle in vehicles:
            location = vehicle.get('garage', 'Unknown')
            if vehicle.get('state') == 0:
                location = "Impound"
                
            if location not in by_garage:
                by_garage[location] = []
                
            by_garage[location].append(vehicle)
        
        for location, loc_vehicles in by_garage.items():
            vehicle_list = ""
            for v in loc_vehicles:
                status_emoji = "🟢" if v.get('state', 0) == 1 else "🔴"
                vehicle_list += f"{status_emoji} {v.get('vehicle', 'Unknown')} ({v.get('plate', 'No Plate')})\n"
                
            embed.add_field(
                name=f"Location: {location} ({len(loc_vehicles)})",
                value=f"```{vehicle_list}```",
                inline=False
            )
            
        embed.set_footer(text="Use /vehicleinfo [plate] to view a vehicle's inventory")
            
        await interaction.followup.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error in vehicles command: {e}")
        await interaction.followup.send(f"An error occurred: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bot.tree.command(name="help", description="Display information about available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands for this bot:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="`/info @user`",
        value="Look up characters associated with a Discord user.",
        inline=False
    )
    
    embed.add_field(
        name="`/character @user` or `/character [citizenid]`",
        value="Look up detailed information about a character.",
        inline=False
    )
    
    embed.add_field(
        name="`/vehicles @user`",
        value="Look up vehicles owned by a Discord user.",
        inline=False
    )
    
    embed.add_field(
        name="`/vehicleinfo [plate]`",
        value="Look up a vehicle's inventory by plate number.",
        inline=False
    )
    
    embed.add_field(
        name="`/help`",
        value="Shows this help message.",
        inline=False
    )
    
    embed.add_field(
        name="Requirements",
        value="Most commands require specific Discord permissions to use.",
        inline=False
    )
    
    embed.set_footer(text="For more help, contact your server administrator.")
    
    await interaction.response.send_message(embed=embed)


def run():
    logger.info("Starting Finder Bot...")
    bot.run(os.getenv('DISCORD_TOKEN'))


if __name__ == "__main__":
    run()