import discord
from discord.ext import commands
from discord import app_commands, ui
import os
import asyncio
import datetime
import random
import string
import json
import io
import chat_exporter
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent.parent))
from modules.utils.db import setup_tickets_database, get_sqlite_connection, get_mysql_connection

log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "tickets.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tickets")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

TICKET_CONFIG = {
    'channel_id': int(os.getenv('TICKET_CHANNEL_ID')),
    'logs_channel_id': int(os.getenv('TICKET_LOGS_CHANNEL_ID')),
    'categories': {
        'general': {
            'name': 'General Support Ticket',
            'category_id': int(os.getenv('GENERAL_CATEGORY_ID')),
            'description': 'Get general help with the server'
        },
        'ban_appeal': {
            'name': 'Ban Appeal',
            'category_id': int(os.getenv('BAN_APPEAL_CATEGORY_ID')),
            'description': 'Appeal a ban or other punishment'
        },
        'tebex': {
            'name': 'Tebex Support',
            'category_id': int(os.getenv('TEBEX_CATEGORY_ID')),
            'description': 'Get help with store purchases'
        },
        'gang': {
            'name': 'Gang Reports',
            'category_id': int(os.getenv('GANG_CATEGORY_ID')),
            'description': 'Report issues related to gangs'
        },
        'staff': {
            'name': 'Staff Report',
            'category_id': int(os.getenv('STAFF_CATEGORY_ID')),
            'description': 'Report a staff member'
        }
    }
}

class TicketTypeSelect(ui.Select):
    def __init__(self):
        options = []
        for key, value in TICKET_CONFIG['categories'].items():
            options.append(discord.SelectOption(
                label=value['name'],
                value=key,
                description=value['description']
            ))
        
        super().__init__(
            placeholder="Select a ticket type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_type_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await create_ticket(interaction, self.values[0])

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

class TicketActionsView(ui.View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @ui.button(label="Claim Ticket", style=discord.ButtonStyle.green, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, id=STAFF_ROLE_ID)
        if not staff_role in interaction.user.roles:
            await interaction.response.send_message("You don't have permission to claim this ticket.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, user_id FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            channel_id = result[0]
            channel = interaction.guild.get_channel(channel_id)
            
            if channel:
                embed = discord.Embed(
                    title="Ticket Claimed",
                    description=f"{interaction.user.mention} has claimed this ticket and will be assisting you.",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
                
                try:
                    current_name = channel.name
                    if not "claimed" in current_name:
                        await channel.edit(name=f"{current_name}-claimed")
                except:
                    pass
                
                await interaction.followup.send("You have successfully claimed this ticket.", ephemeral=True)
    
    @ui.button(label="Rename Ticket", style=discord.ButtonStyle.primary, custom_id="rename_ticket")
    async def rename_ticket(self, interaction: discord.Interaction, button: ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, id=STAFF_ROLE_ID)
        if not staff_role in interaction.user.roles:
            await interaction.response.send_message("You don't have permission to rename this ticket.", ephemeral=True)
            return
        
        class RenameModal(ui.Modal, title="Rename Ticket"):
            new_name = ui.TextInput(label="New Name", placeholder="Enter new ticket name...", min_length=1, max_length=100)
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT channel_id FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    channel_id = result[0]
                    channel = modal_interaction.guild.get_channel(channel_id)
                    
                    if channel:
                        try:
                            await channel.edit(name=self.new_name.value)
                            await modal_interaction.response.send_message(f"Ticket has been renamed to: {self.new_name.value}", ephemeral=True)
                        except Exception as e:
                            await modal_interaction.response.send_message(f"Error renaming ticket: {str(e)}", ephemeral=True)
                    else:
                        await modal_interaction.response.send_message("Could not find the ticket channel.", ephemeral=True)
                else:
                    await modal_interaction.response.send_message("Could not find ticket in database.", ephemeral=True)
        
        modal = RenameModal()
        modal.ticket_id = self.ticket_id
        
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, id=STAFF_ROLE_ID)
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
        result = cursor.fetchone()
        conn.close()
        
        is_creator = False
        if result and result[0] == interaction.user.id:
            is_creator = True
            
        if not (staff_role in interaction.user.roles or is_creator):
            await interaction.response.send_message("You don't have permission to close this ticket.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET status = 'closed' WHERE ticket_id = ?", (self.ticket_id,))
        cursor.execute("SELECT channel_id FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
        result = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if result:
            channel_id = result[0]
            channel = interaction.guild.get_channel(channel_id)
            
            if channel:
                if is_creator:
                    await channel.send(f"🔒 This ticket has been closed by the ticket creator {interaction.user.mention}.")
                else:
                    await channel.send(f"🔒 This ticket has been closed by staff member {interaction.user.mention}.")
                
                try:
                    transcript = await chat_exporter.export(channel, bot=bot)
                    
                    if transcript:
                        transcript_file = discord.File(
                            io.BytesIO(transcript.encode()),
                            filename=f"transcript-{self.ticket_id}.html"
                        )
                        
                        try:
                            logs_channel = interaction.guild.get_channel(TICKET_CONFIG['logs_channel_id'])
                            if logs_channel:
                                embed = discord.Embed(
                                    title=f"Ticket Transcript: #{self.ticket_id}",
                                    description=f"Ticket closed by: {interaction.user.mention}\nChannel: {channel.name}",
                                    color=discord.Color.blue(),
                                    timestamp=datetime.datetime.now()
                                )
                                await logs_channel.send(embed=embed, file=transcript_file)
                        except Exception as e:
                            logger.error(f"Error sending transcript to logs channel: {e}")
                             
                        try:
                            conn = get_sqlite_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT user_id FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
                            creator_result = cursor.fetchone()
                            conn.close()
                            
                            if creator_result:
                                creator_id = creator_result[0]
                                creator_user = await bot.fetch_user(creator_id)
                                
                                if creator_user:
                                    user_transcript_file = discord.File(
                                        io.BytesIO(transcript.encode()),
                                        filename=f"transcript-{self.ticket_id}.html"
                                    )
                                    
                                    user_embed = discord.Embed(
                                        title=f"Ticket Transcript: #{self.ticket_id}",
                                        description=f"Your ticket in {interaction.guild.name} has been closed.\nHere is a transcript for your records.",
                                        color=discord.Color.blue(),
                                        timestamp=datetime.datetime.now()
                                    )
                                    
                                    await creator_user.send(embed=user_embed, file=user_transcript_file)
                        except Exception as e:
                            logger.error(f"Error sending transcript to ticket creator: {e}")
                except Exception as e:
                    logger.error(f"Error generating transcript: {e}")
                    
                for permission in channel.overwrites:
                    if isinstance(permission, discord.Member) and not permission.guild_permissions.manage_channels:
                        await channel.set_permissions(permission, send_messages=False, read_messages=True)
                        
                view = DeleteTicketView(self.ticket_id)
                if is_creator:
                    await channel.send("This ticket is now closed. You can delete it when ready.", view=view)
                else:
                    await channel.send("This ticket is now closed. Staff can delete it when ready.", view=view)

class DeleteTicketView(ui.View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, id=STAFF_ROLE_ID)
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, status FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
        result = cursor.fetchone()
        
        is_creator = False
        ticket_closed = False
        if result:
            user_id = result[0]
            if user_id == interaction.user.id:
                is_creator = True
            if result[1] == 'closed':
                ticket_closed = True
            
        if not (staff_role in interaction.user.roles or is_creator):
            await interaction.response.send_message("You don't have permission to delete this ticket.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        cursor.execute("SELECT channel_id, user_id FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
        result = cursor.fetchone()
        
        if result:
            channel_id, user_id = result
            channel = interaction.guild.get_channel(channel_id)
            
            if channel:
                if not ticket_closed:
                    try:
                        transcript = await chat_exporter.export(channel, bot=bot)
                        
                        if transcript:
                            transcript_file = discord.File(
                                io.BytesIO(transcript.encode()),
                                filename=f"transcript-{self.ticket_id}.html"
                            )
                            
                            try:
                                logs_channel = interaction.guild.get_channel(TICKET_CONFIG['logs_channel_id'])
                                if logs_channel:
                                    embed = discord.Embed(
                                        title=f"Ticket Transcript: #{self.ticket_id}",
                                        description=f"Ticket deleted by: {interaction.user.mention}\nChannel: {channel.name}",
                                        color=discord.Color.red(),
                                        timestamp=datetime.datetime.now()
                                    )
                                    await logs_channel.send(embed=embed, file=transcript_file)
                            except Exception as e:
                                logger.error(f"Error sending transcript to logs channel: {e}")
                                
                            try:
                                ticket_user = await bot.fetch_user(user_id)
                                
                                if ticket_user:
                                    user_transcript_file = discord.File(
                                        io.BytesIO(transcript.encode()),
                                        filename=f"transcript-{self.ticket_id}.html"
                                    )
                                    
                                    user_embed = discord.Embed(
                                        title=f"Ticket Transcript: #{self.ticket_id}",
                                        description=f"Your ticket in {interaction.guild.name} has been deleted.\nHere is a transcript for your records.",
                                        color=discord.Color.red(),
                                        timestamp=datetime.datetime.now()
                                    )
                                    
                                    await ticket_user.send(embed=user_embed, file=user_transcript_file)
                            except Exception as e:
                                logger.error(f"Error sending transcript to ticket creator: {e}")
                    except Exception as e:
                        logger.error(f"Error generating transcript before deletion: {e}")
            
            cursor.execute("DELETE FROM tickets WHERE ticket_id = ?", (self.ticket_id,))
            conn.commit()
            
            if channel:
                if is_creator:
                    deletion_reason = f"Ticket {self.ticket_id} deleted by creator {interaction.user.display_name}"
                else:
                    deletion_reason = f"Ticket {self.ticket_id} deleted by staff {interaction.user.display_name}"
                    
                await channel.delete(reason=deletion_reason)
        
        conn.close()

def generate_ticket_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

async def create_ticket(interaction, ticket_type):
    guild = interaction.guild
    user = interaction.user
    
    category_data = TICKET_CONFIG['categories'].get(ticket_type)
    if not category_data:
        await interaction.followup.send("Invalid ticket type selected.", ephemeral=True)
        return
    
    ticket_id = generate_ticket_id()
    
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT channel_id FROM tickets 
    WHERE user_id = ? AND category = ? AND status = 'open'
    """, (user.id, ticket_type))
    existing_ticket = cursor.fetchone()
    conn.close()
    
    if existing_ticket:
        channel = guild.get_channel(existing_ticket[0])
        if channel:
            await interaction.followup.send(
                f"You already have an open ticket in this category. Please use {channel.mention}",
                ephemeral=True
            )
            return
    
    category = guild.get_channel(category_data['category_id'])
    if not category:
        await interaction.followup.send(
            "Could not find the ticket category. Please contact an administrator.",
            ephemeral=True
        )
        return
    
    channel_name = f"{ticket_type}-{user.name}-{ticket_id}".lower()
    channel_name = ''.join(e for e in channel_name if e.isalnum() or e == '-')[:100]
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }
    
    staff_role = discord.utils.get(guild.roles, id=STAFF_ROLE_ID)
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    try:
        channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO tickets (ticket_id, user_id, channel_id, category, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id, user.id, channel.id, ticket_type, datetime.datetime.now(), 'open'))
        conn.commit()
        conn.close()
        
        try:
            conn = get_mysql_connection()
            cursor = conn.cursor(dictionary=True)

            discord_id = str(user.id)
            formatted_discord_id = f"discord:{discord_id}"
            
            user_query = "SELECT userId, username, license, license2, fivem, discord FROM users WHERE discord = %s"
            cursor.execute(user_query, (formatted_discord_id,))
            user_result = cursor.fetchone()

            if user_result:
                user_id = user_result['userId']
                license = user_result['license']
                license2 = user_result.get('license2', '')
                
                char_query = """
                SELECT id, citizenid, cid, name, charinfo
                FROM players 
                WHERE license = %s OR license = %s OR userId = %s
                """
                cursor.execute(char_query, (license, license2, user_id))
                character_results = cursor.fetchall()
                
                embed = discord.Embed(
                    title=f"{category_data['name']} - Ticket #{ticket_id}",
                    description=f"Thank you for creating a ticket, {user.mention}.\nA staff member will assist you shortly.",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now()
                )
                
                embed.set_footer(text=f"Ticket ID: {ticket_id} - Today at {datetime.datetime.now().strftime('%H:%M')}")
                
                user_info = f"Username: {user_result.get('username', 'N/A')}\n"
                user_info += f"Account ID: {user_result.get('userId', 'N/A')}\n"
                user_info += f"{user_result.get('license2', 'N/A')}\n"
                user_info += f"Discord: {user_result.get('discord', 'N/A')}\n"
                user_info += f"FiveM: {user_result.get('fivem', 'N/A')}"
                
                embed.add_field(name="User Info", value=f"```{user_info}```", inline=False)
                
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
                
                view = TicketActionsView(ticket_id)
                await channel.send(embed=embed, view=view)
                
            else:
                embed = discord.Embed(
                    title=f"{category_data['name']} - Ticket #{ticket_id}",
                    description=f"Thank you for creating a ticket, {user.mention}.\nA staff member will assist you shortly.",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="Type", value=category_data['name'], inline=True)
                embed.add_field(name="Created By", value=user.mention, inline=True)
                embed.set_footer(text=f"Ticket ID: {ticket_id}")
                
                view = TicketActionsView(ticket_id)
                await channel.send(embed=embed, view=view)
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error creating combined embed in ticket {ticket_id}: {e}")
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Full error details for ticket {ticket_id}:\n{error_details}")
            
            embed = discord.Embed(
                title=f"{category_data['name']} - Ticket #{ticket_id}",
                description=f"Thank you for creating a ticket, {user.mention}.\nA staff member will assist you shortly.",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Type", value=category_data['name'], inline=True)
            embed.add_field(name="Created By", value=user.mention, inline=True)
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            
            view = TicketActionsView(ticket_id)
            await channel.send(embed=embed, view=view)
        
        await interaction.followup.send(
            f"Your ticket has been created: {channel.mention}",
            ephemeral=True
        )
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        await interaction.followup.send(
            f"An error occurred while creating your ticket: {str(e)}",
            ephemeral=True
        )

@bot.command()
@commands.has_permissions(administrator=True)
async def setuptickets(ctx):
    channel_id = TICKET_CONFIG['channel_id']
    channel = bot.get_channel(channel_id)
    
    if not channel:
        if ctx:
            await ctx.send(f"Could not find channel with ID {channel_id}")
        else:
            logger.error(f"Could not find channel with ID {channel_id}")
        return
    
    embed = discord.Embed(
        title="Support Ticket System",
        description="Please select a category below to open a support ticket.",
        color=discord.Color.blue()
    )
    
    view = TicketView()
    await channel.send(embed=embed, view=view)
    
    if ctx:
        await ctx.send("Ticket system has been set up!")
    else:
        logger.info("Ticket system has been set up!")

@bot.event
async def on_ready():
    logger.info(f'Ticket Bot is online as {bot.user}')
    setup_tickets_database()
    
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logger.error(f'Error syncing commands: {e}')
    
    bot.add_view(TicketView())
    logger.info("Registered ticket view for dropdown menu")
    
    try:
        channel_id = TICKET_CONFIG['channel_id']
        channel = bot.get_channel(channel_id)
        if channel:
            logger.info(f"Found ticket channel: {channel.name}")
            ticket_message_found = False
            async for message in channel.history(limit=10):
                if message.author.id == bot.user.id and message.embeds:
                    embed = message.embeds[0]
                    if embed.title and "Support Ticket System" in embed.title:
                        await message.edit(view=TicketView())
                        logger.info(f"Registered ticket view with existing message ID: {message.id}")
                        ticket_message_found = True
                        break
            
            # If no ticket message was found, create one automatically
            if not ticket_message_found:
                logger.info("No existing ticket message found. Creating new ticket setup...")
                embed = discord.Embed(
                    title="Support Ticket System",
                    description="Please select a category below to open a support ticket.",
                    color=discord.Color.blue()
                )
                
                view = TicketView()
                await channel.send(embed=embed, view=view)
                logger.info("Ticket system setup created automatically")
    except Exception as e:
        logger.error(f"Error setting up ticket system: {e}")
    
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_id FROM tickets WHERE status = 'open'")
    open_tickets = cursor.fetchall()
    
    for ticket_id in open_tickets:
        bot.add_view(TicketActionsView(ticket_id[0]))
    
    conn.close()
    
    logger.info("Ticket system fully initialized and ready")

def run():
    logger.info("Starting Ticket Bot...")
    bot.run(TOKEN)

if __name__ == "__main__":
    run()