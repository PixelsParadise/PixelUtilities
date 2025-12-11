import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
import asyncio

class Mute(commands.Cog):
    """Mute/Timeout system for moderation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mutes_file = 'mutes.json'
        self.mutes = self.load_mutes()
    
    def load_mutes(self):
        """Load mute history from file"""
        if os.path.exists(self.mutes_file):
            try:
                with open(self.mutes_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_mutes(self):
        """Save mute history to file"""
        try:
            with open(self.mutes_file, 'w') as f:
                json.dump(self.mutes, f, indent=2)
        except Exception as e:
            print(f"Error saving mutes: {e}")
    
    def record_mute(self, guild_id, user_id, moderator_id, reason, duration=None):
        """Record a mute action"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.mutes:
            self.mutes[guild_key] = {}
        
        if user_key not in self.mutes[guild_key]:
            self.mutes[guild_key][user_key] = []
        
        mute_data = {
            'reason': reason,
            'moderator_id': str(moderator_id),
            'timestamp': datetime.utcnow().isoformat(),
            'duration': duration,
            'mute_id': len(self.mutes[guild_key][user_key]) + 1
        }
        
        self.mutes[guild_key][user_key].append(mute_data)
        self.save_mutes()
        return mute_data
    
    def parse_time(self, time_str):
        """Parse time string like '1h', '30m', '1d' into timedelta"""
        time_units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        try:
            unit = time_str[-1].lower()
            amount = int(time_str[:-1])
            
            if unit in time_units:
                seconds = amount * time_units[unit]
                return timedelta(seconds=seconds)
            else:
                return None
        except:
            return None
    
    @commands.command(name='mute', aliases=['timeout'])
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "1h", *, reason: str = "No reason provided"):
        """Mute a member using Discord's timeout feature. Duration: 1m, 1h, 1d, 1w"""
        # Can't mute bots
        if member.bot:
            await ctx.send("❌ You cannot mute bots!")
            return
        
        # Can't mute yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot mute yourself!")
            return
        
        # Can't mute server owner
        if member == ctx.guild.owner:
            await ctx.send("❌ You cannot mute the server owner!")
            return
        
        # Check role hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot mute someone with a higher or equal role!")
            return
        
        # Check if bot can mute
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I cannot mute someone with a higher or equal role than me!")
            return
        
        # Parse duration
        time_delta = self.parse_time(duration)
        if not time_delta:
            await ctx.send("❌ Invalid duration! Use format: 1m, 1h, 1d, 1w (max 28 days)")
            return
        
        # Discord timeout max is 28 days
        if time_delta > timedelta(days=28):
            await ctx.send("❌ Maximum mute duration is 28 days!")
            return
        
        if time_delta < timedelta(seconds=1):
            await ctx.send("❌ Minimum mute duration is 1 second!")
            return
        
        try:
            # Apply timeout
            await member.timeout(time_delta, reason=f"{reason} | By {ctx.author}")
            
            # Record the mute
            mute_data = self.record_mute(ctx.guild.id, member.id, ctx.author.id, reason, duration)
            
            # Calculate unmute time
            unmute_time = datetime.utcnow() + time_delta
            
            # Create embed
            embed = discord.Embed(
                title="🔇 User Muted",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Unmute Time", value=f"<t:{int(unmute_time.timestamp())}:R>", inline=False)
            embed.set_footer(text=f"Mute ID: {mute_data['mute_id']}")
            
            await ctx.send(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=f"🔇 You were muted in {ctx.guild.name}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
                dm_embed.add_field(name="Duration", value=duration, inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Unmute Time", value=f"<t:{int(unmute_time.timestamp())}:R>", inline=False)
                dm_embed.set_footer(text="You will be automatically unmuted after the duration.")
                
                await member.send(embed=dm_embed)
            except:
                await ctx.send("⚠️ Could not DM the user about their mute.")
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to timeout this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='unmute', aliases=['untimeout'])
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Unmute a member"""
        # Check if member is actually muted
        if member.timed_out_until is None:
            await ctx.send(f"❌ {member.mention} is not muted!")
            return
        
        try:
            # Remove timeout
            await member.timeout(None, reason=f"{reason} | By {ctx.author}")
            
            # Create embed
            embed = discord.Embed(
                title="🔊 User Unmuted",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await ctx.send(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=f"🔊 You were unmuted in {ctx.guild.name}",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                
                await member.send(embed=dm_embed)
            except:
                pass
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unmute this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='mutes', aliases=['mutehistory'])
    @commands.has_permissions(moderate_members=True)
    async def mutes(self, ctx, member: discord.Member = None):
        """View mute history for a user"""
        if member is None:
            member = ctx.author
        
        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        
        mute_history = []
        if guild_key in self.mutes and user_key in self.mutes[guild_key]:
            mute_history = self.mutes[guild_key][user_key]
        
        # Check current mute status
        is_currently_muted = member.timed_out_until is not None
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 Mute History for {member.display_name}",
            color=discord.Color.red() if is_currently_muted else discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if is_currently_muted:
            unmute_time = member.timed_out_until
            embed.add_field(
                name="🔇 Currently Muted",
                value=f"Unmutes: <t:{int(unmute_time.timestamp())}:R>",
                inline=False
            )
        else:
            embed.add_field(
                name="🔊 Not Currently Muted",
                value="This user is not currently timed out.",
                inline=False
            )
        
        if not mute_history:
            embed.add_field(
                name="📊 Mute History",
                value="No previous mutes recorded.",
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Mute History",
                value=f"Total mutes: **{len(mute_history)}**",
                inline=False
            )
            
            # Show last 5 mutes
            for mute in mute_history[-5:]:
                moderator = ctx.guild.get_member(int(mute['moderator_id']))
                mod_name = moderator.mention if moderator else f"ID: {mute['moderator_id']}"
                
                timestamp = datetime.fromisoformat(mute['timestamp'])
                
                embed.add_field(
                    name=f"🔇 Mute #{mute['mute_id']}",
                    value=f"**Duration:** {mute.get('duration', 'Unknown')}\n**Reason:** {mute['reason']}\n**Moderator:** {mod_name}\n**Date:** <t:{int(timestamp.timestamp())}:R>",
                    inline=False
                )
        
        embed.set_footer(text=f"User ID: {member.id}")
        await ctx.send(embed=embed)
    
    # Error handlers
    @mute.error
    @unmute.error
    @mutes.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Moderate Members' permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Usage: `{ctx.prefix}{ctx.command.name} @member [duration] [reason]`")

async def setup(bot):
    await bot.add_cog(Mute(bot))
    print('Mute cog loaded successfully!')
