import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class UserStats(commands.Cog):
    """User statistics and points system based on moderation actions"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # File paths for different data sources
        self.warns_file = 'warns.json'
        self.mutes_file = 'mutes.json'
        self.bans_file = 'bans.json'
        self.kicks_file = 'kicks.json'
        self.tickets_file = 'tickets.json'
        self.levels_file = 'levels.json'
        
        # Points configuration (negative points for infractions)
        self.points_config = {
            'warn': -2,
            'mute': -3,
            'kick': -4,
            'ban': -5,
            'ticket_created': 2  # Positive points for creating tickets (getting help)
        }
        
        # Level milestone rewards (from levels.py)
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
    
    def load_json_file(self, filename):
        """Load data from a JSON file"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def count_infractions(self, guild_id, user_id):
        """Count all infractions for a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        # Load all data files
        warns_data = self.load_json_file(self.warns_file)
        mutes_data = self.load_json_file(self.mutes_file)
        bans_data = self.load_json_file(self.bans_file)
        kicks_data = self.load_json_file(self.kicks_file)
        tickets_data = self.load_json_file(self.tickets_file)
        levels_data = self.load_json_file(self.levels_file)
        
        # Count each type
        warn_count = len(warns_data.get(guild_key, {}).get(user_key, []))
        mute_count = len(mutes_data.get(guild_key, {}).get(user_key, []))
        ban_count = len(bans_data.get(guild_key, {}).get(user_key, []))
        kick_count = len(kicks_data.get(guild_key, {}).get(user_key, []))
        ticket_count = len(tickets_data.get(guild_key, {}).get(user_key, []))
        
        # Get level data
        level_data = levels_data.get(guild_key, {}).get(user_key, {})
        level = level_data.get('level', 0)
        total_xp = level_data.get('total_xp', 0)
        messages = level_data.get('messages', 0)
        
        return {
            'warns': warn_count,
            'mutes': mute_count,
            'bans': ban_count,
            'kicks': kick_count,
            'tickets': ticket_count,
            'level': level,
            'total_xp': total_xp,
            'messages': messages
        }
    
    def calculate_points(self, infractions):
        """Calculate total points based on infractions and level"""
        total_points = 0
        
        # Negative points for infractions
        total_points += infractions['warns'] * self.points_config['warn']
        total_points += infractions['mutes'] * self.points_config['mute']
        total_points += infractions['kicks'] * self.points_config['kick']
        total_points += infractions['bans'] * self.points_config['ban']
        
        # Positive points for tickets
        total_points += infractions['tickets'] * self.points_config['ticket_created']
        
        # Add level milestone points
        level = infractions.get('level', 0)
        for milestone_level, points in self.level_points.items():
            if level >= milestone_level:
                total_points += points
        
        return total_points
    
    def get_rank(self, points):
        """Get rank based on points"""
        if points >= 100:
            return "🌟 Exemplary", discord.Color.gold()
        elif points >= 50:
            return "✨ Outstanding", discord.Color.green()
        elif points >= 0:
            return "✅ Good Standing", discord.Color.blue()
        elif points >= -50:
            return "⚠️ Caution", discord.Color.orange()
        elif points >= -100:
            return "🚨 Warning", discord.Color.red()
        else:
            return "💀 Critical", discord.Color.dark_red()
    
    @commands.command(name='stats', aliases=['userstats', 'profile'])
    async def stats(self, ctx, member: discord.Member = None):
        """View user statistics and points"""
        if member is None:
            member = ctx.author
        
        # Get infractions
        infractions = self.count_infractions(ctx.guild.id, member.id)
        
        # Calculate points
        total_points = self.calculate_points(infractions)
        
        # Get rank
        rank, color = self.get_rank(total_points)
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 User Statistics for {member.display_name}",
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Points section
        embed.add_field(
            name="📈 Total Points",
            value=f"**{total_points}** points",
            inline=True
        )
        embed.add_field(
            name="🏆 Rank",
            value=rank,
            inline=True
        )
        embed.add_field(
            name="⭐ Level",
            value=f"**{infractions['level']}**",
            inline=True
        )
        
        # Activity stats
        embed.add_field(
            name="💬 Activity",
            value=f"**{infractions['messages']:,}** messages\n**{infractions['total_xp']:,}** total XP",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
        
        # Infractions section
        infractions_text = (
            f"⚠️ Warnings: **{infractions['warns']}** ({infractions['warns'] * self.points_config['warn']} pts)\n"
            f"🔇 Mutes: **{infractions['mutes']}** ({infractions['mutes'] * self.points_config['mute']} pts)\n"
            f"👢 Kicks: **{infractions['kicks']}** ({infractions['kicks'] * self.points_config['kick']} pts)\n"
            f"🔨 Bans: **{infractions['bans']}** ({infractions['bans'] * self.points_config['ban']} pts)\n"
            f"🎫 Tickets Created: **{infractions['tickets']}** (+{infractions['tickets'] * self.points_config['ticket_created']} pts)"
        )
        embed.add_field(
            name="📋 Moderation History",
            value=infractions_text,
            inline=False
        )
        
        # Level bonus points
        level_bonus = 0
        for milestone_level, points in self.level_points.items():
            if infractions['level'] >= milestone_level:
                level_bonus += points
        
        if level_bonus > 0:
            milestones_reached = [str(lvl) for lvl, pts in self.level_points.items() if infractions['level'] >= lvl]
            embed.add_field(
                name="🌟 Level Milestone Bonuses",
                value=f"**+{level_bonus}** points from reaching levels: {', '.join(milestones_reached)}",
                inline=False
            )
        
        # Point breakdown
        embed.add_field(
            name="💡 Point System",
            value=(
                f"**Infractions:** Warn: {self.points_config['warn']} | "
                f"Mute: {self.points_config['mute']} | "
                f"Kick: {self.points_config['kick']} | "
                f"Ban: {self.points_config['ban']}\n"
                f"**Positive:** Ticket: +{self.points_config['ticket_created']} | "
                f"Level Milestones: up to +{sum(self.level_points.values())} pts"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='statslb', aliases=['statsleaderboard', 'slb'])
    async def statslb(self, ctx, mode: str = "points"):
        """View server stats leaderboard (modes: points, warns, mutes, kicks, bans, level)"""
        mode = mode.lower()
        valid_modes = ['points', 'warns', 'mutes', 'kicks', 'bans', 'level']
        
        if mode not in valid_modes:
            await ctx.send(f"❌ Invalid mode! Valid modes: {', '.join(valid_modes)}")
            return
        
        # Get all members and their stats
        member_stats = []
        for member in ctx.guild.members:
            if member.bot:
                continue
            
            infractions = self.count_infractions(ctx.guild.id, member.id)
            points = self.calculate_points(infractions)
            
            member_stats.append({
                'member': member,
                'points': points,
                'infractions': infractions
            })
        
        # Sort based on mode
        if mode == 'points':
            member_stats.sort(key=lambda x: x['points'], reverse=True)
            title = "🏆 Top Users by Points"
        elif mode == 'level':
            member_stats.sort(key=lambda x: x['infractions']['level'], reverse=True)
            title = "⭐ Top Users by Level"
        elif mode == 'warns':
            member_stats.sort(key=lambda x: x['infractions']['warns'], reverse=True)
            title = "⚠️ Most Warnings"
        elif mode == 'mutes':
            member_stats.sort(key=lambda x: x['infractions']['mutes'], reverse=True)
            title = "🔇 Most Mutes"
        elif mode == 'kicks':
            member_stats.sort(key=lambda x: x['infractions']['kicks'], reverse=True)
            title = "👢 Most Kicks"
        elif mode == 'bans':
            member_stats.sort(key=lambda x: x['infractions']['bans'], reverse=True)
            title = "🔨 Most Bans"
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=f"Top users in {ctx.guild.name}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        # Add top 10 users
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = []
        
        for idx, stats in enumerate(member_stats[:10]):
            if idx < len(member_stats):
                medal = medals[idx] if idx < 3 else f"`{idx + 1}.`"
                member = stats['member']
                
                if mode == 'points':
                    value = f"{stats['points']} points (Level {stats['infractions']['level']})"
                elif mode == 'level':
                    value = f"Level {stats['infractions']['level']} ({stats['infractions']['total_xp']:,} XP)"
                else:
                    value = f"{stats['infractions'][mode]} {mode}"
                
                leaderboard_text.append(f"{medal} **{member.display_name}** - {value}")
        
        if leaderboard_text:
            embed.description = "\n".join(leaderboard_text)
        else:
            embed.description = "No data available yet!"
        
        embed.set_footer(text=f"Mode: {mode} | Use >statslb <mode> to change")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='resetstats')
    @commands.has_permissions(administrator=True)
    async def resetstats(self, ctx, member: discord.Member, *, confirmation: str = None):
        """Reset all statistics for a user (requires confirmation)"""
        # Require confirmation
        if confirmation != "confirm":
            infractions = self.count_infractions(ctx.guild.id, member.id)
            points = self.calculate_points(infractions)
            
            embed = discord.Embed(
                title="⚠️ Reset User Statistics",
                description=(
                    f"This will permanently delete ALL records for {member.mention}:\n"
                    f"• All warnings\n"
                    f"• All mutes\n"
                    f"• All kicks\n"
                    f"• All bans\n"
                    f"• All tickets\n"
                    f"• **XP and level data will NOT be reset** (use >resetxp separately)\n\n"
                    f"**Current Stats:**\n"
                    f"Points: {points}\n"
                    f"Level: {infractions['level']}\n"
                    f"Warnings: {infractions['warns']}\n"
                    f"Mutes: {infractions['mutes']}\n"
                    f"Kicks: {infractions['kicks']}\n"
                    f"Bans: {infractions['bans']}\n"
                    f"Tickets: {infractions['tickets']}\n\n"
                    f"**This action cannot be undone!**\n\n"
                    f"To confirm, use: `{ctx.prefix}resetstats {member.mention} confirm`"
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Show current stats before reset
        infractions = self.count_infractions(ctx.guild.id, member.id)
        points = self.calculate_points(infractions)
        
        # Remove user from all data files (except levels)
        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        
        files_to_update = [
            self.warns_file,
            self.mutes_file,
            self.bans_file,
            self.kicks_file,
            self.tickets_file
        ]
        
        for filename in files_to_update:
            data = self.load_json_file(filename)
            if guild_key in data and user_key in data[guild_key]:
                del data[guild_key][user_key]
                
                # Save updated data
                try:
                    with open(filename, 'w') as f:
                        json.dump(data, f, indent=2)
                except Exception as e:
                    await ctx.send(f"❌ Error updating {filename}: {e}")
                    return
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Statistics Reset",
            description=f"Moderation records have been cleared for {member.mention}\n\n*Level and XP data preserved. Use `>resetxp` to reset those separately.*",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(
            name="Previous Statistics",
            value=(
                f"Points: **{points}**\n"
                f"Level: {infractions['level']}\n"
                f"Warnings: {infractions['warns']}\n"
                f"Mutes: {infractions['mutes']}\n"
                f"Kicks: {infractions['kicks']}\n"
                f"Bans: {infractions['bans']}\n"
                f"Tickets: {infractions['tickets']}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Reset By",
            value=f"{ctx.author.mention}",
            inline=True
        )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='pointsconfig')
    @commands.has_permissions(administrator=True)
    async def pointsconfig(self, ctx):
        """View current points configuration"""
        embed = discord.Embed(
            title="⚙️ Points System Configuration",
            description="Current point values for each action:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Negative Actions (Infractions)",
            value=(
                f"⚠️ Warning: **{self.points_config['warn']}** points\n"
                f"🔇 Mute: **{self.points_config['mute']}** points\n"
                f"👢 Kick: **{self.points_config['kick']}** points\n"
                f"🔨 Ban: **{self.points_config['ban']}** points"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Positive Actions",
            value=f"🎫 Ticket Created: **+{self.points_config['ticket_created']}** points",
            inline=False
        )
        
        # Level milestones
        milestones_text = "\n".join([
            f"Level {lvl}: **+{pts}** points"
            for lvl, pts in sorted(self.level_points.items())
        ])
        
        embed.add_field(
            name="🌟 Level Milestone Bonuses",
            value=milestones_text,
            inline=False
        )
        
        embed.add_field(
            name="Rank System",
            value=(
                "🌟 Exemplary: 100+ points\n"
                "✨ Outstanding: 50-99 points\n"
                "✅ Good Standing: 0-49 points\n"
                "⚠️ Caution: -1 to -50 points\n"
                "🚨 Warning: -51 to -100 points\n"
                "💀 Critical: -101+ points"
            ),
            inline=False
        )
        
        embed.set_footer(text="Point values are configured in the bot code")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='compare')
    async def compare(self, ctx, member1: discord.Member, member2: discord.Member):
        """Compare statistics between two users"""
        # Get stats for both members
        infractions1 = self.count_infractions(ctx.guild.id, member1.id)
        points1 = self.calculate_points(infractions1)
        rank1, color1 = self.get_rank(points1)
        
        infractions2 = self.count_infractions(ctx.guild.id, member2.id)
        points2 = self.calculate_points(infractions2)
        rank2, color2 = self.get_rank(points2)
        
        # Determine winner
        if points1 > points2:
            winner = member1
            winner_color = color1
        elif points2 > points1:
            winner = member2
            winner_color = color2
        else:
            winner = None
            winner_color = discord.Color.blue()
        
        # Create embed
        embed = discord.Embed(
            title="⚖️ User Comparison",
            description=f"Comparing {member1.mention} vs {member2.mention}",
            color=winner_color,
            timestamp=datetime.utcnow()
        )
        
        # Member 1 stats
        embed.add_field(
            name=f"👤 {member1.display_name}",
            value=(
                f"**Points:** {points1}\n"
                f"**Rank:** {rank1}\n"
                f"**Level:** {infractions1['level']}\n"
                f"Warns: {infractions1['warns']} | "
                f"Mutes: {infractions1['mutes']} | "
                f"Kicks: {infractions1['kicks']} | "
                f"Bans: {infractions1['bans']}"
            ),
            inline=False
        )
        
        # Member 2 stats
        embed.add_field(
            name=f"👤 {member2.display_name}",
            value=(
                f"**Points:** {points2}\n"
                f"**Rank:** {rank2}\n"
                f"**Level:** {infractions2['level']}\n"
                f"Warns: {infractions2['warns']} | "
                f"Mutes: {infractions2['mutes']} | "
                f"Kicks: {infractions2['kicks']} | "
                f"Bans: {infractions2['bans']}"
            ),
            inline=False
        )
        
        # Winner
        if winner:
            embed.add_field(
                name="🏆 Better Standing",
                value=f"{winner.mention} (+{abs(points1 - points2)} points)",
                inline=False
            )
        else:
            embed.add_field(
                name="🤝 Result",
                value="Both users have equal standing!",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @resetstats.error
    @pointsconfig.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")

async def setup(bot):
    await bot.add_cog(UserStats(bot))
    print('User stats cog loaded successfully!')