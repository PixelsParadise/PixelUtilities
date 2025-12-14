import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class Warn(commands.Cog):
    """Warning system for moderation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.warns_file = 'warns.json'
        self.warns = self.load_warns()
    
    def load_warns(self):
        """Load warnings from file"""
        if os.path.exists(self.warns_file):
            try:
                with open(self.warns_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_warns(self):
        """Save warnings to file"""
        try:
            with open(self.warns_file, 'w') as f:
                json.dump(self.warns, f, indent=2)
        except Exception as e:
            print(f"Error saving warns: {e}")
    
    def add_warn(self, guild_id, user_id, moderator_id, reason):
        """Add a warning to a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.warns:
            self.warns[guild_key] = {}
        
        if user_key not in self.warns[guild_key]:
            self.warns[guild_key][user_key] = []
        
        warn_data = {
            'reason': reason,
            'moderator_id': str(moderator_id),
            'timestamp': datetime.utcnow().isoformat(),
            'warn_id': len(self.warns[guild_key][user_key]) + 1
        }
        
        self.warns[guild_key][user_key].append(warn_data)
        self.save_warns()
        return warn_data
    
    def get_warns(self, guild_id, user_id):
        """Get all warnings for a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.warns and user_key in self.warns[guild_key]:
            return self.warns[guild_key][user_key]
        return []
    
    def remove_warn(self, guild_id, user_id, warn_id):
        """Remove a specific warning"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.warns and user_key in self.warns[guild_key]:
            warns = self.warns[guild_key][user_key]
            for i, warn in enumerate(warns):
                if warn['warn_id'] == warn_id:
                    del self.warns[guild_key][user_key][i]
                    self.save_warns()
                    return True
        return False
    
    def clear_warns(self, guild_id, user_id):
        """Clear all warnings for a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.warns and user_key in self.warns[guild_key]:
            warn_count = len(self.warns[guild_key][user_key])
            del self.warns[guild_key][user_key]
            self.save_warns()
            return warn_count
        return 0
    
    @commands.command(name='warn')
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member"""
        # Can't warn bots
        if member.bot:
            await ctx.send("❌ You cannot warn bots!")
            return
        
        # Can't warn yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot warn yourself!")
            return
        
        # Can't warn server owner
        if member == ctx.guild.owner:
            await ctx.send("❌ You cannot warn the server owner!")
            return
        
        # Check role hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot warn someone with a higher or equal role!")
            return
        
        # Add the warning
        warn_data = self.add_warn(ctx.guild.id, member.id, ctx.author.id, reason)
        warns = self.get_warns(ctx.guild.id, member.id)
        warn_count = len(warns)
        
        # Create embed for confirmation
        embed = discord.Embed(
            title="⚠️ User Warned",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=f"**{warn_count}**", inline=True)
        embed.set_footer(text=f"Warn ID: {warn_data['warn_id']}")
        
        await ctx.send(embed=embed)
        
        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ You were warned in {ctx.guild.name}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            dm_embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Total Warnings", value=f"{warn_count}", inline=True)
            dm_embed.set_footer(text="Please follow the server rules to avoid further action.")
            
            await member.send(embed=dm_embed)
        except:
            await ctx.send("⚠️ Could not DM the user about their warning.")
    
    @commands.command(name='warnings', aliases=['warns'])
    async def warnings(self, ctx, member: discord.Member = None):
        """View warnings for a user"""
        if member is None:
            member = ctx.author
        
        warns = self.get_warns(ctx.guild.id, member.id)
        
        if not warns:
            embed = discord.Embed(
                title=f"📋 Warnings for {member.display_name}",
                description=f"{member.mention} has no warnings! 🎉",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return
        
        # Create embed with warnings
        embed = discord.Embed(
            title=f"📋 Warnings for {member.display_name}",
            description=f"Total Warnings: **{len(warns)}**",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        for warn in warns:
            moderator = ctx.guild.get_member(int(warn['moderator_id']))
            mod_name = moderator.mention if moderator else f"ID: {warn['moderator_id']}"
            
            timestamp = datetime.fromisoformat(warn['timestamp'])
            
            embed.add_field(
                name=f"⚠️ Warning #{warn['warn_id']}",
                value=f"**Reason:** {warn['reason']}\n**Moderator:** {mod_name}\n**Date:** <t:{int(timestamp.timestamp())}:R>",
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {member.id}")
        await ctx.send(embed=embed)
    
    @commands.command(name='removewarn', aliases=['delwarn', 'unwarn'])
    @commands.has_permissions(kick_members=True)
    async def removewarn(self, ctx, member: discord.Member, warn_id: int):
        """Remove a specific warning from a user"""
        if self.remove_warn(ctx.guild.id, member.id, warn_id):
            embed = discord.Embed(
                title="✅ Warning Removed",
                description=f"Warning #{warn_id} has been removed from {member.mention}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Removed by {ctx.author}")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Could not find warning #{warn_id} for {member.mention}")
    
    @commands.command(name='clearwarns')
    @commands.has_permissions(kick_members=True)
    async def clearwarns(self, ctx, member: discord.Member):
        """Clear all warnings for a user"""
        warn_count = self.clear_warns(ctx.guild.id, member.id)
        
        if warn_count > 0:
            embed = discord.Embed(
                title="✅ Warnings Cleared",
                description=f"Removed **{warn_count}** warning(s) from {member.mention}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Cleared by {ctx.author}")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {member.mention} has no warnings to clear!")
    
    # Error handlers
    @warn.error
    @removewarn.error
    @clearwarns.error
    async def warn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Kick Members' permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Usage: `{ctx.prefix}{ctx.command.name} @member [reason/warn_id]`")

async def setup(bot):
    await bot.add_cog(Warn(bot))
    print('Warn cog loaded successfully!')