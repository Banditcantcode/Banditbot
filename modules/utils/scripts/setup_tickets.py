import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio


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
    

    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID {TICKET_CHANNEL_ID}")
        await bot.close()
        return
    

    embed = discord.Embed(
        title="Support Ticket System",
        description="Please select a category below to open a support ticket.",
        color=discord.Color.blue()
    )
    

    categories = {
        'General Support Ticket': 'Get general help with the server',
        'Ban Appeal': 'Appeal a ban or other punishment',
        'Tebex Support': 'Get help with store purchases',
        'Gang Reports': 'Report issues related to gangs',
        'Staff Report': 'Report a staff member'
    }
    
    for name, desc in categories.items():
        embed.add_field(name=name, value=desc, inline=False)
    

    class TicketView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
        
        @discord.ui.select(
            placeholder="Select a ticket type...",
            options=[
                discord.SelectOption(label="General Support Ticket", value="general", description="Get general help with the server"),
                discord.SelectOption(label="Ban Appeal", value="ban_appeal", description="Appeal a ban or other punishment"),
                discord.SelectOption(label="Tebex Support", value="tebex", description="Get help with store purchases"),
                discord.SelectOption(label="Gang Reports", value="gang", description="Report issues related to gangs"),
                discord.SelectOption(label="Staff Report", value="staff", description="Report a staff member")
            ]
        )
        async def select_callback(self, select, interaction):
            await interaction.response.send_message(
                f"This is a setup script. Please use the actual ticket bot to create tickets.", 
                ephemeral=True
            )
    
    view = TicketView()
    
    # Send the message
    await channel.send(embed=embed, view=view)
    print("Ticket setup message has been sent!")
    
    # Close the bot
    await bot.close()

# Run the bot
bot.run(TOKEN) 