import discord
from discord.ext import commands
from datetime import datetime
import math

class Help(commands.Cog):
    """Custom help command with embeds"""
    
    def __init__(self, bot):
        self.bot = bot
        # Remove default help command
        self.bot.remove_command('help')
    
    @commands.command(name='help')
    async def help_command(self, ctx, *, command_name: str = None):
        """Shows help information for commands"""
        
        if command_name:
            # Show help for specific command
            await self.show_command_help(ctx, command_name)
        else:
            # Show general help with categories
            await self.show_general_help(ctx)
    
    async def show_general_help(self, ctx):
        """Show general help with all command categories"""
        
        # Organize commands by cog
        cog_commands = {}
        
        for cog_name, cog in self.bot.cogs.items():
            # Skip help cog itself
            if cog_name == 'Help':
                continue
            
            # Get commands from this cog
            commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            
            if commands_list:
                cog_commands[cog_name] = {
                    'description': cog.description or 'No description',
                    'commands': commands_list
                }
        
        # Create main embed
        embed = discord.Embed(
            title="📚 Bot Commands Help",
            description=f"Use `{ctx.prefix}help <command>` for detailed information about a command.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Add categories
        for cog_name, data in sorted(cog_commands.items()):
            command_list = ', '.join([f"`{cmd.name}`" for cmd in data['commands'][:5]])
            
            if len(data['commands']) > 5:
                command_list += f" *+{len(data['commands']) - 5} more*"
            
            embed.add_field(
                name=f"🔹 {cog_name}",
                value=f"{data['description']}\n{command_list}",
                inline=False
            )
        
        # Add footer with useful info
        embed.set_footer(
            text=f"Prefix: {ctx.prefix} | Total Commands: {len(list(self.bot.commands))}",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)
    
    async def show_command_help(self, ctx, command_name):
        """Show detailed help for a specific command"""
        
        # Find the command
        command = self.bot.get_command(command_name)
        
        if not command:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"No command named `{command_name}` was found.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💡 Tip",
                value=f"Use `{ctx.prefix}help` to see all available commands.",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Create detailed command embed
        embed = discord.Embed(
            title=f"📖 Command: {ctx.prefix}{command.name}",
            description=command.help or "No description available.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        # Command signature
        signature = self.get_command_signature(ctx, command)
        embed.add_field(
            name="📝 Usage",
            value=f"`{signature}`",
            inline=False
        )
        
        # Aliases
        if command.aliases:
            aliases = ', '.join([f"`{alias}`" for alias in command.aliases])
            embed.add_field(
                name="🔄 Aliases",
                value=aliases,
                inline=False
            )
        
        # Permissions required
        if command.checks:
            perms = self.get_command_permissions(command)
            if perms:
                embed.add_field(
                    name="🔒 Required Permissions",
                    value=perms,
                    inline=False
                )
        
        # Cooldown info
        if command._buckets and command._buckets._cooldown:
            cooldown = command._buckets._cooldown
            embed.add_field(
                name="⏱️ Cooldown",
                value=f"{cooldown.rate} use(s) per {cooldown.per} seconds",
                inline=False
            )
        
        # Category (cog)
        if command.cog:
            embed.add_field(
                name="📁 Category",
                value=command.cog.qualified_name,
                inline=True
            )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    def get_command_signature(self, ctx, command):
        """Get the command signature with parameters"""
        signature = f"{ctx.prefix}{command.qualified_name}"
        
        if command.signature:
            signature += f" {command.signature}"
        
        return signature
    
    def get_command_permissions(self, command):
        """Get required permissions for a command"""
        perms = []
        
        for check in command.checks:
            if hasattr(check, '__name__'):
                if 'has_permissions' in check.__name__:
                    # Try to extract permission names from the check
                    perms.append("Requires specific permissions")
                elif 'is_owner' in check.__name__:
                    perms.append("Bot Owner Only")
        
        # Check for permission decorators
        if hasattr(command.callback, '__wrapped__'):
            perms.append("Requires permissions")
        
        return '\n'.join(perms) if perms else None
    
    @commands.command(name='commands', aliases=['cmds'])
    async def list_commands(self, ctx, category: str = None):
        """List all commands or commands in a specific category"""
        
        if category:
            # Show commands for specific category
            cog = self.bot.get_cog(category.title())
            
            if not cog:
                embed = discord.Embed(
                    title="❌ Category Not Found",
                    description=f"No category named `{category}` was found.",
                    color=discord.Color.red()
                )
                
                # List available categories
                categories = ', '.join([f"`{cog_name}`" for cog_name in self.bot.cogs.keys() if cog_name != 'Help'])
                embed.add_field(
                    name="Available Categories",
                    value=categories,
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            # Create embed for category
            embed = discord.Embed(
                title=f"📁 {cog.qualified_name} Commands",
                description=cog.description or "No description",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            
            for command in sorted(commands_list, key=lambda c: c.name):
                embed.add_field(
                    name=f"`{ctx.prefix}{command.name}`",
                    value=command.short_doc or "No description",
                    inline=False
                )
            
            embed.set_footer(text=f"Use {ctx.prefix}help <command> for more info")
            
            await ctx.send(embed=embed)
        else:
            # Show all categories
            embed = discord.Embed(
                title="📚 Command Categories",
                description=f"Use `{ctx.prefix}commands <category>` to see commands in a specific category.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            
            for cog_name, cog in sorted(self.bot.cogs.items()):
                if cog_name == 'Help':
                    continue
                
                commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
                
                if commands_list:
                    embed.add_field(
                        name=f"🔹 {cog_name}",
                        value=f"{len(commands_list)} commands\n{cog.description or 'No description'}",
                        inline=True
                    )
            
            embed.set_footer(text=f"Total: {len(list(self.bot.commands))} commands")
            
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
    print('Custom help command loaded successfully!')