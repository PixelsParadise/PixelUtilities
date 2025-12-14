import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
import math
import random

class Levels(commands.Cog):
    """Level and XP system with leaderboard integration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.levels_file = 'levels.json'
        self.levels = self.load_levels()
        self.cooldowns = {}  # Track message cooldowns to prevent spam
        
        # XP Configuration
        self.xp_per_message = (15, 25)  # Random XP range per message
        self.xp_cooldown = 60  # Seconds between XP gains
        self.base_xp = 100  # XP needed for level 1
        self.xp_multiplier = 1.5  # XP multiplier per level
        
        # Level rewards (points added to user stats)
        self.level_points = {
            5: 10,
            10: 25,
            15: 50,
            20: 75,
            25: 100,
            30: 150,
            40: 200,
            50: 300
        }
    
    def load_levels(self):
        """Load level data from file"""
        if os.path.exists(self.levels_file):
            try:
                with open(self.levels_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_levels(self):
        """Save level data to file"""
        try:
            with open(self.levels_file, 'w') as f:
                json.dump(self.levels, f, indent=2)
        except Exception as e:
            print(f"Error saving levels: {e}")
    
    def calculate_level(self, xp):
        """Calculate level from total XP"""
        level = 0
        xp_needed = self.base_xp
        
        while xp >= xp_needed:
            xp -= xp_needed
            level += 1
            xp_needed = int(self.base_xp * (self.xp_multiplier ** level))
        
        return level
    
    def xp_for_next_level(self, level):
        """Calculate XP needed for next level"""
        return int(self.base_xp * (self.xp_multiplier ** level))
    
    def get_user_data(self, guild_id, user_id):
        """Get user level data"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.levels:
            self.levels[guild_key] = {}
        
        if user_key not in self.levels[guild_key]:
            self.levels[guild_key][user_key] = {
                'xp': 0,
                'level': 0,
                'total_xp': 0,
                'messages': 0,
                'last_xp_time': None
            }
        
        return self.levels[guild_key][user_key]
    
    def add_xp(self, guild_id, user_id, amount):
        """Add XP to a user and check for level up"""
        user_data = self.get_user_data(guild_id, user_id)
        
        old_level = user_data['level']
        user_data['xp'] += amount
        user_data['total_xp'] += amount
        user_data['messages'] += 1
        
        # Calculate new level
        new_level = self.calculate_level(user_data['total_xp'])
        user_data['level'] = new_level
        
        self.save_levels()
        
        # Return level up info
        if new_level > old_level:
            return {
                'leveled_up': True,
                'old_level': old_level,
                'new_level': new_level,
                'xp_gained': amount
            }
        
        return {
            'leveled_up': False,
            'xp_gained': amount
        }
    
    def get_level_role_rewards(self, guild):
        """Get role rewards configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            return config.get('level_roles', {})
        except:
            return {}
    
    async def give_level_rewards(self, member, level):
        """Give rewards for reaching a level"""
        # Check for role rewards
        level_roles = self.get_level_role_rewards(member.guild)
        
        for level_threshold, role_id in level_roles.items():
            if level == int(level_threshold):
                role = member.guild.get_role(int(role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except discord.Forbidden:
                        pass
    
    def get_rank_card_color(self, level):
        """Get color based on level"""
        if level >= 50:
            return discord.Color.gold()
        elif level >= 40:
            return discord.Color.purple()
        elif level >= 30:
            return discord.Color.blue()
        elif level >= 20:
            return discord.Color.green()
        elif level >= 10:
            return discord.Color.orange()
        else:
            return discord.Color.light_gray()
    
    def calculate_progress_bar(self, current_xp, needed_xp, length=10):
        """Create a progress bar"""
        progress = current_xp / needed_xp
        filled = int(progress * length)
        empty = length - filled
        return f"{'█' * filled}{'░' * empty}"
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Award XP for messages"""
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check cooldown
        user_key = f"{message.guild.id}_{message.author.id}"
        current_time = datetime.utcnow()
        
        if user_key in self.cooldowns:
            time_diff = (current_time - self.cooldowns[user_key]).total_seconds()
            if time_diff < self.xp_cooldown:
                return
        
        # Update cooldown
        self.cooldowns[user_key] = current_time
        
        # Award random XP
        xp_gain = random.randint(*self.xp_per_message)
        result = self.add_xp(message.guild.id, message.author.id, xp_gain)
        
        # Check for level up
        if result['leveled_up']:
            user_data = self.get_user_data(message.guild.id, message.author.id)
            new_level = result['new_level']
            
            # Create level up embed
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"{message.author.mention} has reached **Level {new_level}**!",
                color=self.get_rank_card_color(new_level),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            
            # Check for point rewards
            if new_level in self.level_points:
                points_earned = self.level_points[new_level]
                embed.add_field(
                    name="🎁 Milestone Reward",
                    value=f"+{points_earned} points added to your stats!",
                    inline=False
                )
            
            # XP for next level
            xp_needed = self.xp_for_next_level(new_level)
            embed.add_field(
                name="Next Level",
                value=f"{xp_needed:,} XP needed for Level {new_level + 1}",
                inline=False
            )
            
            embed.set_footer(text=f"Total XP: {user_data['total_xp']:,}")
            
            try:
                await message.channel.send(embed=embed, delete_after=30)
            except:
                pass
            
            # Give rewards
            await self.give_level_rewards(message.author, new_level)
    
    @commands.command(name='rank', aliases=['level', 'xp'])
    async def rank(self, ctx, member: discord.Member = None):
        """View your or someone else's rank card"""
        if member is None:
            member = ctx.author
        
        user_data = self.get_user_data(ctx.guild.id, member.id)
        
        # Calculate current level progress
        level = user_data['level']
        total_xp = user_data['total_xp']
        
        # Calculate XP for current level
        xp_for_current = sum(self.xp_for_next_level(i) for i in range(level))
        current_level_xp = total_xp - xp_for_current
        xp_needed = self.xp_for_next_level(level)
        
        # Calculate server rank
        guild_key = str(ctx.guild.id)
        if guild_key in self.levels:
            sorted_users = sorted(
                self.levels[guild_key].items(),
                key=lambda x: x[1]['total_xp'],
                reverse=True
            )
            rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == str(member.id)), 0)
        else:
            rank = 0
        
        # Create rank card embed
        embed = discord.Embed(
            title=f"📊 Rank Card - {member.display_name}",
            color=self.get_rank_card_color(level),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Level info
        embed.add_field(
            name="📈 Level",
            value=f"**{level}**",
            inline=True
        )
        embed.add_field(
            name="🏆 Server Rank",
            value=f"**#{rank}**",
            inline=True
        )
        embed.add_field(
            name="💬 Messages",
            value=f"**{user_data['messages']:,}**",
            inline=True
        )
        
        # XP Progress
        progress_bar = self.calculate_progress_bar(current_level_xp, xp_needed, 15)
        progress_percentage = (current_level_xp / xp_needed) * 100
        
        embed.add_field(
            name="⭐ XP Progress",
            value=(
                f"{progress_bar}\n"
                f"**{current_level_xp:,}** / **{xp_needed:,}** XP ({progress_percentage:.1f}%)"
            ),
            inline=False
        )
        
        # Total XP
        embed.add_field(
            name="🌟 Total XP",
            value=f"**{total_xp:,}** XP",
            inline=True
        )
        
        # XP to next level
        xp_remaining = xp_needed - current_level_xp
        embed.add_field(
            name="🎯 Next Level",
            value=f"**{xp_remaining:,}** XP needed",
            inline=True
        )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='xpleaderboard', aliases=['xlb', 'xptop'])
    async def xpleaderboard(self, ctx, page: int = 1):
        """View the server XP leaderboard"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.levels or not self.levels[guild_key]:
            await ctx.send("❌ No level data available yet!")
            return
        
        # Sort users by total XP
        sorted_users = sorted(
            self.levels[guild_key].items(),
            key=lambda x: x[1]['total_xp'],
            reverse=True
        )
        
        # Pagination
        per_page = 10
        total_pages = math.ceil(len(sorted_users) / per_page)
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_users = sorted_users[start_idx:end_idx]
        
        # Create leaderboard embed
        embed = discord.Embed(
            title=f"🏆 XP Leaderboard - {ctx.guild.name}",
            description=f"Top members by total XP (Page {page}/{total_pages})",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = []
        
        for idx, (user_id, data) in enumerate(page_users):
            global_idx = start_idx + idx
            medal = medals[global_idx] if global_idx < 3 else f"`{global_idx + 1}.`"
            
            member = ctx.guild.get_member(int(user_id))
            if member:
                name = member.display_name
            else:
                name = f"User {user_id}"
            
            level = data['level']
            total_xp = data['total_xp']
            messages = data['messages']
            
            leaderboard_text.append(
                f"{medal} **{name}**\n"
                f"    Level {level} • {total_xp:,} XP • {messages:,} msgs"
            )
        
        embed.description = "\n\n".join(leaderboard_text)
        
        # Show user's rank if not on current page
        user_rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == str(ctx.author.id)), 0)
        if user_rank > 0:
            user_data = self.levels[guild_key][str(ctx.author.id)]
            embed.set_footer(
                text=f"Your rank: #{user_rank} • Level {user_data['level']} • {user_data['total_xp']:,} XP"
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='setxp')
    @commands.has_permissions(administrator=True)
    async def setxp(self, ctx, member: discord.Member, xp: int):
        """Set a user's XP (admin only)"""
        if xp < 0:
            await ctx.send("❌ XP cannot be negative!")
            return
        
        user_data = self.get_user_data(ctx.guild.id, member.id)
        old_level = user_data['level']
        
        user_data['total_xp'] = xp
        user_data['xp'] = xp
        user_data['level'] = self.calculate_level(xp)
        
        self.save_levels()
        
        embed = discord.Embed(
            title="✅ XP Updated",
            description=f"Set {member.mention}'s XP to **{xp:,}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Old Level", value=str(old_level), inline=True)
        embed.add_field(name="New Level", value=str(user_data['level']), inline=True)
        embed.set_footer(text=f"Updated by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='addxp')
    @commands.has_permissions(administrator=True)
    async def addxp(self, ctx, member: discord.Member, xp: int):
        """Add XP to a user (admin only)"""
        if xp == 0:
            await ctx.send("❌ XP amount cannot be zero!")
            return
        
        result = self.add_xp(ctx.guild.id, member.id, xp)
        user_data = self.get_user_data(ctx.guild.id, member.id)
        
        embed = discord.Embed(
            title="✅ XP Added" if xp > 0 else "✅ XP Removed",
            description=f"{'Added' if xp > 0 else 'Removed'} **{abs(xp):,}** XP {'to' if xp > 0 else 'from'} {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Current Level", value=str(user_data['level']), inline=True)
        embed.add_field(name="Total XP", value=f"{user_data['total_xp']:,}", inline=True)
        
        if result['leveled_up']:
            embed.add_field(
                name="🎉 Level Up!",
                value=f"Level {result['old_level']} → {result['new_level']}",
                inline=False
            )
        
        embed.set_footer(text=f"Updated by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='resetxp')
    @commands.has_permissions(administrator=True)
    async def resetxp(self, ctx, member: discord.Member, *, confirmation: str = None):
        """Reset a user's XP (requires confirmation)"""
        if confirmation != "confirm":
            user_data = self.get_user_data(ctx.guild.id, member.id)
            
            embed = discord.Embed(
                title="⚠️ Reset User XP",
                description=(
                    f"This will reset ALL XP data for {member.mention}:\n"
                    f"• Current Level: **{user_data['level']}**\n"
                    f"• Total XP: **{user_data['total_xp']:,}**\n"
                    f"• Messages: **{user_data['messages']:,}**\n\n"
                    f"**This action cannot be undone!**\n\n"
                    f"To confirm, use: `{ctx.prefix}resetxp {member.mention} confirm`"
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Reset user data
        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        
        if guild_key in self.levels and user_key in self.levels[guild_key]:
            del self.levels[guild_key][user_key]
            self.save_levels()
        
        embed = discord.Embed(
            title="✅ XP Reset",
            description=f"All XP data has been reset for {member.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Reset by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='xpconfig')
    @commands.has_permissions(administrator=True)
    async def xpconfig(self, ctx):
        """View XP system configuration"""
        embed = discord.Embed(
            title="⚙️ XP System Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💬 Message XP",
            value=f"**{self.xp_per_message[0]}-{self.xp_per_message[1]}** XP per message",
            inline=False
        )
        
        embed.add_field(
            name="⏱️ Cooldown",
            value=f"**{self.xp_cooldown}** seconds between XP gains",
            inline=False
        )
        
        embed.add_field(
            name="📊 Level Formula",
            value=f"Base XP: **{self.base_xp}** • Multiplier: **{self.xp_multiplier}x**",
            inline=False
        )
        
        # Show level milestones
        milestones = "\n".join([
            f"Level {lvl}: **+{pts}** points"
            for lvl, pts in sorted(self.level_points.items())
        ])
        
        embed.add_field(
            name="🎁 Level Milestone Rewards",
            value=milestones,
            inline=False
        )
        
        embed.set_footer(text="These points are added to user stats")
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @setxp.error
    @addxp.error
    @resetxp.error
    @xpconfig.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Check `{ctx.prefix}help {ctx.command.name}`")

async def setup(bot):
    await bot.add_cog(Levels(bot))
    print('Level system loaded successfully!')