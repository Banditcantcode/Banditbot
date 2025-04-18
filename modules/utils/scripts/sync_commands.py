import os
import sys
import asyncio
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


finder_path = os.path.abspath('finder.py')
print(f"Finder path: {finder_path}")


sys.path.append(os.path.dirname(finder_path))

try:

    import finder
    
    async def sync_commands():
        await finder.bot.wait_until_ready()
        print(f'Bot is online as {finder.bot.user}')
        
        try:
            synced = await finder.bot.tree.sync()
            print(f'Synced {len(synced)} command(s)')
            for command in synced:
                print(f'- {command.name}')
        except Exception as e:
            print(f'Error syncing commands: {e}')
        
        print("Command sync complete. Bot will continue running...")
    
    finder.bot.loop.create_task(sync_commands())
    

    print("Starting bot...")
    finder.bot.run(TOKEN)
except Exception as e:
    print(f"Error importing finder module: {e}")
    import traceback
    traceback.print_exc() 