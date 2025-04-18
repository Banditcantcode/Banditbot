
"""
Main entry point for the Nova Gaming Discord bot system.
This file starts both the Finder bot and the Ticket system.
This is my first time using discord.py and im not sure what the best way of doing this is. i will re do it later.
eventually ill update to command handlers instead of having eveerything in serparate files
and classes.
This is a work in progress and will be updated as I learn more about discord.py.
Copyright (c) 2023 Bandit
"""

import os
import sys
import logging
import threading
import importlib
from pathlib import Path
from dotenv import load_dotenv

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Load environment variables
load_dotenv()

def start_finder():
    """Start the Finder bot in a separate thread"""
    try:
        from modules.finder.bot import run
        logger.info("Starting Finder bot...")
        run()
    except Exception as e:
        logger.error(f"Error starting Finder bot: {e}")
        import traceback
        logger.error(traceback.format_exc())

def start_tickets():
    """Start the Ticket system in a separate thread"""
    try:
        from modules.tickets.bot import run
        logger.info("Starting Ticket system...")
        run()
    except Exception as e:
        logger.error(f"Error starting Ticket system: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Main entry point to start all bots"""
    logger.info("Starting Nova Gaming Discord bot system...")
    
    finder_thread = threading.Thread(target=start_finder, name="FinderBot")
    tickets_thread = threading.Thread(target=start_tickets, name="TicketSystem")
    
    finder_thread.daemon = True
    tickets_thread.daemon = True
    
    finder_thread.start()
    tickets_thread.start()
    
    try:
        finder_thread.join()
        tickets_thread.join()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, closing bots...")
        sys.exit(0)

if __name__ == "__main__":
    main() 