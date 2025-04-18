# 🎮 Discord bot system for QBOX

![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

A Discord bot system for managing qbox server communities. Combines player lookup capabilities with a full-featured ticket support system. I also host this on a seperate linux vps to main server, so you will need to make a read only account in heidi. Unsure if it will work on localhsot did not test it is better to host it on a seperate server in my opinion. Please note its extremely basic and not advanced. hence it runs on 2 different py files

## ✨ Key Features

### 🔍 Finder Bot
- **Detailed Player Lookups** - Find all characters, licenses, and player details
- **Vehicle Inventory Search** - Check trunk and glovebox contents by plate
- **Character Profiles** - View detailed character stats and demographics
- **Reaction Roles** - Automatically assign roles based on reactions

### 🎫 Ticket System
- **Category-Based Tickets** - Different ticket types for different needs
- **Staff Claiming** - Staff can claim tickets to avoid duplicate responses
- **User Data Integration** - Shows FiveM/game data in tickets
- **Transcripts** - Automatically archives closed tickets
- **Customizable Categories** - Easy to configure for your server's needs

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Discord Developer Account
- MySQL Database (for player data)

### Quick Setup
```bash
# Clone the repo
git clone https://github.com/banditcantcode/banditbot.git

# Install dependencies
pip install -r requirements.txt

# Configure your environment
cp .env
# Edit the .env file with your Discord token and database details

# Start the bots
python main.py
```

## 💻 Commands

### Player Commands
| Command | Description |
|---------|-------------|
| `/info @user` | Quick player overview |
| `/character @user` | Detailed character profile |
| `/vehicles @user` | List all player vehicles |
| `/vehicleinfo [plate]` | Check vehicle inventory |

### Ticket Controls
| Button | Function | Access |
|--------|----------|--------|
| 🔵 **Claim Ticket** | Mark as being handled by you | Staff |
| ✏️ **Rename Ticket** | Change the ticket title | Staff |
| 🔒 **Close Ticket** | Close and archive the ticket | Staff & Creator |
| 🗑️ **Delete Ticket** | Remove closed ticket | Staff |

## 🛠️ Configuration

All settings are managed through the `.env` file 

- Discord Token & Bot Settings
- Database Credentials
- Discord IDs (roles, channels, etc.)
- Category IDs for ticket system

## 📂 Project Structure

```
.
├── 📁 logs/                # Log files
├── 📁 modules/
│   ├── 📁 finder/          # Player lookup commands
│   ├── 📁 tickets/         # Ticket system
│   └── 📁 utils/           # Shared utilities
├── 📄 .env                 # Environment variables
├── 📄 main.py              # Main entry point
├── 📄 requirements.txt     # Dependencies
└── 📄 README.md            # You are here!
```

## �� Running the Bots

The system is designed to run both bots together using the main script:

```bash
# Run everything at once (recommended)
python main.py
```

This will start both the Finder bot and the Ticket system in separate threads. The Ticket system will automatically create the ticket dropdown message if one doesn't exist in the ticket channel.

You can also run components individually for testing:

```bash
# Run the Finder bot only
python -c "from modules.finder.bot import run; run()"

# Run the Ticket system only
python -c "from modules.tickets.bot import run; run()"
```

Note: When the Ticket system starts, it will automatically:
1. Check if a ticket message exists in the configured channel
2. If no message exists, it will create a new one with the dropdown menu
3. No manual setup command is required

## 🤝 Contributing

Got ideas or improvements? PRs are welcome! Feel free to fork and contribute.

## 📜 License

This project is available under the MIT License - see the LICENSE file for details.

---

Made with ❤️ for the Nova Gaming community 
