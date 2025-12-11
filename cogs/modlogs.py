import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class ModLogs(commands.Cog):
    """Unified moderation logs viewer"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # File paths for all moderation data
        self.warns_file = 'warns.json'
        self.mutes_file = 'mutes.json'
        self.bans_file = 'bans.json'
        self.kicks_file = 'kicks.json'
    
    def load_json_file(self, filename):
        """Load data from a JSON file"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def get_all_logs(self, guild_id, user_id):
        """Get all moderation logs for a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        # Load all data
        warns_data = self.load_json_file(self.warns_file)
        mutes_data = self.load_json_file(self.mutes_file)
        bans_data = self.load_json_file(self.bans_file)
        kicks_data = self.load_json_file(self.kicks_file)
        
        # Collect all logs with type
        all_logs = []
        
        # Add warnings
        if guild_key in warns_data and user_key in warns_data[guild_key]:
            for warn in warns_data[guild_key][user_key]:
                all_logs.append({
                    'type': 'warn',
                    'emoji': '⚠️',
                    'color': discord.Color.orange(),
                    'id': warn['warn_id'],
                    'reason': warn['reason'],
                    'moderator_id': warn['moderator_id'],
                    'timestamp': warn['timestamp']
                })
        
        # Add mutes
        if guild_key in mutes_data and user_key in mutes_data[guild_key]:
            for mute in mutes_data[guild_key][user_key]:
                all_logs.append({
                    'type': 'mute',
                    'emoji': '🔇',
                    'color': discord.Color.red(),
                    'id': mute['mute_id'],
                    'reason': mute['reason'],
                    'moderator_id': mute['moderator_id'],
                    'timestamp': mute['timestamp'],
                    'duration': mute.get('duration', 'Unknown')
                })
        
        # Add kicks
        if guild_key in kicks_data and user_key in kicks_data[guild_key]:
            for kick in kicks_data[guild_key][user_key]:
                all_logs.append({
                    'type': 'kick',
                    'emoji': '👢',
                    'color': discord.Color.orange(),
                    'id': kick['kick_id'],
                    'reason': kick['reason'],
                    'moderator_id': kick['moderator_id'],
                    'timestamp': kick['timestamp']
                })
        
        # Add bans
        if guild_key in bans_data and user_key in bans_data[guild_key]:
            for ban in bans_data[guild_key][user_key]:
                all_logs.append({
                    'type': 'ban',
                    'emoji': '🔨',
                    'color': discord.Color.dark_red(),
                    'id': ban['ban_id'],
                    'reason': ban['reason'],
                    'moderator_id': ban['moderator_id'],
                    'timestamp': ban['timestamp']
                })
        
        # Sort by timestamp (newest first)
        all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_logs
    
    def get_log_summary(self, guild_id, user_id):
        """Get summary counts of all infractions"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        warns_data = self.load_json_file(self.warns_file)
        mutes_data = self.load_json_file(self.mutes_file)
        bans_data = self.load_json_file(self.bans_file)
        kicks_data = self.load_json_file(self.kicks_file)
        
        return {
            'warns': len(warns_data.get(guild_key, {}).get(user_key, [])),
            'mutes': len(mutes_data.get(guild_key, {}).get(user_key, [])),
            'kicks': len(kicks_data.get(guild_key, {}).get(user_key, [])),
            'bans': len(bans_data.get(guild_key, {}).get(user_key, []))
        }
    
    @commands.command(name='modlogs', aliases=['mlogs', 'infractions', 'history'])
    @commands.has_permissions(kick_members=True)
    async def modlogs(self, ctx, member: discord.Member = None, page: int = 1):
        """View all moderation logs for a user"""
        if member is None:
            member = ctx.author
        
        # Get all logs
        all_logs = self.get_all_logs(ctx.guild.id, member.id)
        summary = self.get_log_summary(ctx.guild.id, member.id)
        
        # Calculate total infractions
        total = summary['warns'] + summary['mutes'] + summary['kicks'] + summary['bans']
        
        if total == 0:
            embed = discord.Embed(
                title=f"📋 Moderation Logs - {member.display_name}",
                description=f"{member.mention} has a clean record! 🎉",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            await ctx.send(embed=embed)
            return
        
        # Pagination
        logs_per_page = 5
        total_pages = (total + logs_per_page - 1) // logs_per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * logs_per_page
        end_idx = start_idx + logs_per_page
        page_logs = all_logs[start_idx:end_idx]
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 Moderation Logs - {member.display_name}",
            description=f"Showing {len(page_logs)} of {total} total infractions",
            color=discord.Color.red() if total >= 5 else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Summary section
        summary_text = (
            f"⚠️ Warnings: **{summary['warns']}** | "
            f"🔇 Mutes: **{summary['mutes']}**\n"
            f"👢 Kicks: **{summary['kicks']}** | "
            f"🔨 Bans: **{summary['bans']}**"
        )
        embed.add_field(name="📊 Summary", value=summary_text, inline=False)
        
        # Add each log entry
        for log in page_logs:
            # Get moderator
            moderator = ctx.guild.get_member(int(log['moderator_id']))
            mod_name = moderator.mention if moderator else f"<@{log['moderator_id']}>"
            
            # Format timestamp
            timestamp = datetime.fromisoformat(log['timestamp'])
            time_str = f"<t:{int(timestamp.timestamp())}:R>"
            
            # Build field value
            field_value = f"**Reason:** {log['reason']}\n**Moderator:** {mod_name}\n**Date:** {time_str}"
            
            # Add duration for mutes
            if log['type'] == 'mute' and 'duration' in log:
                field_value += f"\n**Duration:** {log['duration']}"
            
            # Add field
            embed.add_field(
                name=f"{log['emoji']} {log['type'].title()} #{log['id']}",
                value=field_value,
                inline=False
            )
        
        # Pagination info
        if total_pages > 1:
            embed.set_footer(text=f"Page {page}/{total_pages} | User ID: {member.id} | Use >modlogs @user {page+1} for next page")
        else:
            embed.set_footer(text=f"User ID: {member.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='modstats')
    @commands.has_permissions(kick_members=True)
    async def modstats(self, ctx):
        """View moderation statistics for the entire server"""
        guild_key = str(ctx.guild.id)
        
        # Load all data
        warns_data = self.load_json_file(self.warns_file)
        mutes_data = self.load_json_file(self.mutes_file)
        bans_data = self.load_json_file(self.bans_file)
        kicks_data = self.load_json_file(self.kicks_file)
        
        # Count totals
        total_warns = sum(len(warns_data.get(guild_key, {}).get(user, [])) 
                         for user in warns_data.get(guild_key, {}))
        total_mutes = sum(len(mutes_data.get(guild_key, {}).get(user, [])) 
                         for user in mutes_data.get(guild_key, {}))
        total_kicks = sum(len(kicks_data.get(guild_key, {}).get(user, [])) 
                         for user in kicks_data.get(guild_key, {}))
        total_bans = sum(len(bans_data.get(guild_key, {}).get(user, [])) 
                        for user in bans_data.get(guild_key, {}))
        
        total_actions = total_warns + total_mutes + total_kicks + total_bans
        
        # Count unique users with infractions
        unique_users = set()
        for data in [warns_data, mutes_data, kicks_data, bans_data]:
            if guild_key in data:
                unique_users.update(data[guild_key].keys())
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 Server Moderation Statistics",
            description=f"Statistics for **{ctx.guild.name}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📈 Total Actions",
            value=f"**{total_actions:,}** moderation actions",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Warnings",
            value=f"**{total_warns:,}**",
            inline=True
        )
        embed.add_field(
            name="🔇 Mutes",
            value=f"**{total_mutes:,}**",
            inline=True
        )
        embed.add_field(
            name="👢 Kicks",
            value=f"**{total_kicks:,}**",
            inline=True
        )
        embed.add_field(
            name="🔨 Bans",
            value=f"**{total_bans:,}**",
            inline=True
        )
        embed.add_field(
            name="👥 Users with Infractions",
            value=f"**{len(unique_users):,}**",
            inline=True
        )
        
        # Calculate percentages
        if total_actions > 0:
            percentages = (
                f"Warns: {(total_warns/total_actions*100):.1f}% | "
                f"Mutes: {(total_mutes/total_actions*100):.1f}%\n"
                f"Kicks: {(total_kicks/total_actions*100):.1f}% | "
                f"Bans: {(total_bans/total_actions*100):.1f}%"
            )
            embed.add_field(
                name="📊 Distribution",
                value=percentages,
                inline=False
            )
        
        embed.set_footer(text=f"Server ID: {ctx.guild.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='modlog')
    @commands.has_permissions(kick_members=True)
    async def modlog(self, ctx, member: discord.Member, log_type: str, log_id: int):
        """View details of a specific moderation log entry
        
        Usage: >modlog @user warn 1
               >modlog @user mute 2
               >modlog @user kick 1
               >modlog @user ban 1
        """
        log_type = log_type.lower()
        valid_types = ['warn', 'mute', 'kick', 'ban']
        
        if log_type not in valid_types:
            await ctx.send(f"❌ Invalid log type! Valid types: {', '.join(valid_types)}")
            return
        
        # Load appropriate file
        file_map = {
            'warn': self.warns_file,
            'mute': self.mutes_file,
            'kick': self.kicks_file,
            'ban': self.bans_file
        }
        
        data = self.load_json_file(file_map[log_type])
        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        
        # Find the log entry
        if guild_key not in data or user_key not in data[guild_key]:
            await ctx.send(f"❌ No {log_type} logs found for {member.mention}!")
            return
        
        logs = data[guild_key][user_key]
        log_entry = None
        
        for log in logs:
            if log.get(f'{log_type}_id') == log_id:
                log_entry = log
                break
        
        if not log_entry:
            await ctx.send(f"❌ {log_type.title()} #{log_id} not found for {member.mention}!")
            return
        
        # Create detailed embed
        emoji_map = {'warn': '⚠️', 'mute': '🔇', 'kick': '👢', 'ban': '🔨'}
        color_map = {
            'warn': discord.Color.orange(),
            'mute': discord.Color.red(),
            'kick': discord.Color.orange(),
            'ban': discord.Color.dark_red()
        }
        
        embed = discord.Embed(
            title=f"{emoji_map[log_type]} {log_type.title()} Details - #{log_id}",
            color=color_map[log_type],
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # User info
        embed.add_field(
            name="👤 User",
            value=f"{member.mention}\n`{member.id}`",
            inline=True
        )
        
        # Moderator info
        moderator = ctx.guild.get_member(int(log_entry['moderator_id']))
        if moderator:
            mod_text = f"{moderator.mention}\n`{moderator.id}`"
        else:
            mod_text = f"<@{log_entry['moderator_id']}>\n`{log_entry['moderator_id']}`"
        
        embed.add_field(
            name="👮 Moderator",
            value=mod_text,
            inline=True
        )
        
        # Timestamp
        timestamp = datetime.fromisoformat(log_entry['timestamp'])
        embed.add_field(
            name="📅 Date",
            value=f"<t:{int(timestamp.timestamp())}:F>\n<t:{int(timestamp.timestamp())}:R>",
            inline=True
        )
        
        # Reason
        embed.add_field(
            name="📝 Reason",
            value=log_entry['reason'],
            inline=False
        )
        
        # Duration (for mutes)
        if log_type == 'mute' and 'duration' in log_entry:
            embed.add_field(
                name="⏱️ Duration",
                value=log_entry['duration'],
                inline=True
            )
        
        embed.set_footer(text=f"Log ID: {log_id} | Type: {log_type}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='recent')
    @commands.has_permissions(kick_members=True)
    async def recent(self, ctx, limit: int = 10):
        """View the most recent moderation actions in the server"""
        if limit < 1 or limit > 50:
            await ctx.send("❌ Limit must be between 1 and 50!")
            return
        
        guild_key = str(ctx.guild.id)
        
        # Collect all logs from all users
        all_logs = []
        
        for file_name, log_type, emoji in [
            (self.warns_file, 'warn', '⚠️'),
            (self.mutes_file, 'mute', '🔇'),
            (self.kicks_file, 'kick', '👢'),
            (self.bans_file, 'ban', '🔨')
        ]:
            data = self.load_json_file(file_name)
            if guild_key in data:
                for user_id, logs in data[guild_key].items():
                    for log in logs:
                        all_logs.append({
                            'type': log_type,
                            'emoji': emoji,
                            'user_id': user_id,
                            'timestamp': log['timestamp'],
                            'reason': log['reason'][:50] + '...' if len(log['reason']) > 50 else log['reason'],
                            'moderator_id': log['moderator_id']
                        })
        
        # Sort by timestamp (newest first)
        all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        if not all_logs:
            await ctx.send("✅ No moderation actions recorded yet!")
            return
        
        # Get recent logs
        recent_logs = all_logs[:limit]
        
        # Create embed
        embed = discord.Embed(
            title=f"🕒 Recent Moderation Actions",
            description=f"Showing {len(recent_logs)} most recent actions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for log in recent_logs:
            user = ctx.guild.get_member(int(log['user_id']))
            user_text = user.mention if user else f"<@{log['user_id']}>"
            
            moderator = ctx.guild.get_member(int(log['moderator_id']))
            mod_text = moderator.display_name if moderator else f"ID: {log['moderator_id']}"
            
            timestamp = datetime.fromisoformat(log['timestamp'])
            time_str = f"<t:{int(timestamp.timestamp())}:R>"
            
            embed.add_field(
                name=f"{log['emoji']} {log['type'].title()} - {time_str}",
                value=f"**User:** {user_text}\n**Mod:** {mod_text}\n**Reason:** {log['reason']}",
                inline=False
            )
        
        embed.set_footer(text=f"Total actions: {len(all_logs)}")
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @modlogs.error
    @modstats.error
    @modlog.error
    @recent.error
    async def modlogs_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Kick Members' permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{ctx.prefix}help {ctx.command.name}` for usage.")

async def setup(bot):
    await bot.add_cog(ModLogs(bot))
    print('ModLogs cog loaded successfully!')
