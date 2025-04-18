import discord
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Get channel and category IDs from environment variables
TICKET_CHANNEL_ID = int(os.getenv('TICKET_CHANNEL_ID', '0'))
CATEGORIES = {
    'general': {
        'name': 'General Support Ticket',
        'category_id': int(os.getenv('GENERAL_CATEGORY_ID', '0')),
        'description': 'Get general help with the server'
    },
    'ban_appeal': {
        'name': 'Ban Appeal',
        'category_id': int(os.getenv('BAN_APPEAL_CATEGORY_ID', '0')),
        'description': 'Appeal a ban or other punishment'
    },
    'tebex': {
        'name': 'Tebex Support',
        'category_id': int(os.getenv('TEBEX_CATEGORY_ID', '0')),
        'description': 'Get help with store purchases'
    },
    'gang': {
        'name': 'Gang Reports',
        'category_id': int(os.getenv('GANG_CATEGORY_ID', '0')),
        'description': 'Report issues related to gangs'
    },
    'staff': {
        'name': 'Staff Report',
        'category_id': int(os.getenv('STAFF_CATEGORY_ID', '0')),
        'description': 'Report a staff member'
    }
}

@bot.event
async def on_ready():
    print(f"Setup bot logged in as {bot.user}")
    
    # Get the channel
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        print(f"Could not find channel with ID {TICKET_CHANNEL_ID}")
        await bot.close()
        return
    
    # Create the ticket message embed 
    embed = discord.Embed(
        title="Support Ticket System",
        description="Please select a category below to open a support ticket.",
        color=discord.Color.blue()
    )
    
    select_options = []
    for key, value in CATEGORIES.items():
        select_options.append(
            discord.SelectOption(
                label=value['name'],
                value=key,
                description=value['description']
            )
        )
    
    class TicketView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            select = discord.ui.Select(
                placeholder="Select a ticket type...",
                min_values=1,
                max_values=1,
                options=select_options,
                custom_id="ticket_type_select"
            )
            self.add_item(select)
    
    view = TicketView()
    

    await channel.send(embed=embed, view=view)
    print("Ticket message has been sent!")
    

    await asyncio.sleep(3)
    await bot.close()

# Run the bot
bot.run(TOKEN) 