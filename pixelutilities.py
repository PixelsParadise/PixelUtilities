import discord
from discord.ext import commands
import os
import asyncio
import json

with open('config.json', 'r') as f:
    config = json.load(f)

# Check if user has admin role
def is_admin(member):
    admin_roles = config['staff_roles']['admin']
    return any(str(role.id) in admin_roles for role in member.roles)

# Or use as a check in commands
@commands.check(lambda ctx: is_admin(ctx.author))
async def admin_command(self, ctx):
    # Only users with admin roles can use this
    pass

# Load config file
def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found!")
        print("Please create a config.json file with your bot settings")
        exit(1)
    except json.JSONDecodeError:
        print("Error: config.json is not valid JSON!")
        exit(1)

config = load_config()

# Set up intents (permissions for what events the bot can receive)
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

# Create bot instance with config prefix
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

# Store config in bot for access in cogs
bot.config = config

# Event: Bot is ready and connected
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} server(s)')
    
    # Set bot activity from config
    activity_type = config['activity']['type'].lower()
    activity_name = config['activity']['name']
    
    if activity_type == 'playing':
        activity = discord.Game(name=activity_name)
    elif activity_type == 'watching':
        activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
    elif activity_type == 'listening':
        activity = discord.Activity(type=discord.ActivityType.listening, name=activity_name)
    else:
        activity = discord.Game(name=activity_name)
    
    await bot.change_presence(activity=activity)

# Event: When a message is sent
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands and get the context
    ctx = await bot.get_context(message)
    
    # Only delete if it was a valid command
    if ctx.valid and ctx.command is not None:
        try:
            await message.delete()
        except discord.Forbidden:
            pass  # Bot doesn't have permission to delete messages
        except discord.HTTPException:
            pass  # Message already deleted or other error
    
    # Continue processing commands
    await bot.process_commands(message)

# Load all cogs (command files)
async def load_cogs():
    """Load all cog files from the cogs folder"""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'Loaded cog: {filename}')

# Main function to run the bot
async def main():
    async with bot:
        await load_cogs()
        
        # Use token from config or environment variable (env takes priority)
        TOKEN = os.getenv('DISCORD_BOT_TOKEN') or config.get('token')
        
        if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("Error: No valid bot token found!")
            print("Either set DISCORD_BOT_TOKEN environment variable")
            print("or add your token to config.json")
            return
        
        await bot.start(TOKEN)

# Run the bot
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutting down...")
    except Exception as e:
        print(f"Error running bot: {e}")