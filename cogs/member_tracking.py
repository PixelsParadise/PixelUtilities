import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class MemberTracking(commands.Cog):
    """Tracks member joins and leaves"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'
    
    def load_config(self):
        """Load config file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_config(self, config):
        """Save config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot is ready"""
        print("Member tracking loaded")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Track when a member joins the server"""
        # Load config to get log channel
        try:
            config = self.load_config()
            
            log_channel_id = config.get('settings', {}).get('log_channel_id')
            
            # Calculate account age
            account_created = member.created_at
            account_age = datetime.utcnow() - account_created
            days_old = account_age.days
            
            # Determine if account is new (less than 7 days old)
            is_new_account = days_old < 7
            
            # Send log message if channel is set
            if log_channel_id:
                log_channel = member.guild.get_channel(int(log_channel_id))
                if log_channel:
                    # Create embed
                    embed = discord.Embed(
                        title="📥 Member Joined",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.add_field(name="User", value=f"{member.mention} ({member})", inline=False)
                    embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
                    embed.add_field(name="Account Created", value=f"<t:{int(account_created.timestamp())}:R>", inline=True)
                    embed.add_field(name="Account Age", value=f"{days_old} days old", inline=True)
                    
                    if is_new_account:
                        embed.add_field(
                            name="⚠️ Warning", 
                            value="This is a new account (less than 7 days old)", 
                            inline=False
                        )
                    
                    embed.set_footer(text=f"Member #{member.guild.member_count}")
                    
                    await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error in member join tracking: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Track when a member leaves the server"""
        # Load config to get log channel
        try:
            config = self.load_config()
            
            log_channel_id = config.get('settings', {}).get('log_channel_id')
            if not log_channel_id:
                return
            
            log_channel = member.guild.get_channel(int(log_channel_id))
            if not log_channel:
                return
            
            # Calculate how long they were in the server
            if member.joined_at:
                time_in_server = datetime.utcnow() - member.joined_at
                days_in_server = time_in_server.days
                hours = time_in_server.seconds // 3600
                minutes = (time_in_server.seconds % 3600) // 60
            else:
                days_in_server = 0
                hours = 0
                minutes = 0
            
            # Get their roles (excluding @everyone)
            roles = [role.mention for role in member.roles if role.name != "@everyone"]
            
            # Create embed
            embed = discord.Embed(
                title="📤 Member Left",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="User", value=f"{member} ({member.mention})", inline=False)
            embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
            
            if member.joined_at:
                embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
            
            if days_in_server > 0:
                time_str = f"{days_in_server} days, {hours} hours"
            elif hours > 0:
                time_str = f"{hours} hours, {minutes} minutes"
            else:
                time_str = f"{minutes} minutes"
            
            embed.add_field(name="Time in Server", value=time_str, inline=True)
            
            if roles:
                embed.add_field(name="Roles", value=", ".join(roles), inline=False)
            
            embed.set_footer(text=f"Member #{member.guild.member_count} remaining")
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error in member leave tracking: {e}")
    
    @commands.command(name='setlogchannel')
    @commands.has_permissions(administrator=True)
    async def setlogchannel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for member join/leave logs"""
        if channel is None:
            channel = ctx.channel
        
        try:
            config = self.load_config()
            
            if 'settings' not in config:
                config['settings'] = {}
            
            config['settings']['log_channel_id'] = str(channel.id)
            self.save_config(config)
            
            embed = discord.Embed(
                title="✅ Log Channel Set",
                description=f"Member join/leave logs will be sent to {channel.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error setting log channel: {e}")
    
    @setlogchannel.error
    async def setlogchannel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")

async def setup(bot):
    await bot.add_cog(MemberTracking(bot))
    print('Member tracking cog loaded successfully!')