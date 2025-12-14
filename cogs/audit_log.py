import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class AuditLog(commands.Cog):
    """Comprehensive audit logging system for all moderation actions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'
    
    def get_audit_channel(self, guild_id):
        """Get the audit log channel for a guild"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            audit_channel_id = config['settings'].get('audit_channel_id')
            if audit_channel_id:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    return guild.get_channel(int(audit_channel_id))
        except:
            pass
        return None
    
    async def log_action(self, guild_id, action_type, embed):
        """Send an audit log entry to the configured channel"""
        channel = self.get_audit_channel(guild_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Missing permissions to send to audit log channel in guild {guild_id}")
            except Exception as e:
                print(f"Error sending audit log: {e}")
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Log when a member is banned"""
        # Wait a moment for audit log to update
        await asyncio.sleep(1)
        
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    embed = discord.Embed(
                        title="🔨 Member Banned",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.set_thumbnail(url=user.display_avatar.url)
                    embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                    embed.set_footer(text=f"Action ID: {entry.id}")
                    
                    await self.log_action(guild.id, "ban", embed)
                    break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Log when a member is unbanned"""
        await asyncio.sleep(1)
        
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    embed = discord.Embed(
                        title="✅ Member Unbanned",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.set_thumbnail(url=user.display_avatar.url)
                    embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                    embed.set_footer(text=f"Action ID: {entry.id}")
                    
                    await self.log_action(guild.id, "unban", embed)
                    break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when a member is kicked (different from leave)"""
        await asyncio.sleep(1)
        
        try:
            guild = member.guild
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    # Check if this happened recently (within last 5 seconds)
                    time_diff = datetime.utcnow() - entry.created_at
                    if time_diff.total_seconds() < 5:
                        embed = discord.Embed(
                            title="👢 Member Kicked",
                            color=discord.Color.orange(),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
                        embed.add_field(name="Moderator", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                        embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                        embed.set_footer(text=f"Action ID: {entry.id}")
                        
                        await self.log_action(guild.id, "kick", embed)
                        break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log role changes and timeout changes"""
        # Log role changes
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                await asyncio.sleep(1)
                
                try:
                    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                        if entry.target.id == after.id:
                            embed = discord.Embed(
                                title="🎭 Member Roles Updated",
                                color=discord.Color.blue(),
                                timestamp=datetime.utcnow()
                            )
                            embed.set_thumbnail(url=after.display_avatar.url)
                            embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)", inline=False)
                            embed.add_field(name="Moderator", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                            
                            if added_roles:
                                embed.add_field(
                                    name="✅ Roles Added", 
                                    value=", ".join([role.mention for role in added_roles]),
                                    inline=False
                                )
                            
                            if removed_roles:
                                embed.add_field(
                                    name="❌ Roles Removed", 
                                    value=", ".join([role.mention for role in removed_roles]),
                                    inline=False
                                )
                            
                            embed.set_footer(text=f"Action ID: {entry.id}")
                            
                            await self.log_action(after.guild.id, "role_update", embed)
                            break
                except discord.Forbidden:
                    pass
        
        # Log timeout changes (mutes)
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until is not None:
                # Member was muted
                await asyncio.sleep(1)
                
                try:
                    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                        if entry.target.id == after.id:
                            embed = discord.Embed(
                                title="🔇 Member Timed Out",
                                color=discord.Color.red(),
                                timestamp=datetime.utcnow()
                            )
                            embed.set_thumbnail(url=after.display_avatar.url)
                            embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)", inline=False)
                            embed.add_field(name="Moderator", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                            embed.add_field(name="Until", value=f"<t:{int(after.timed_out_until.timestamp())}:F>", inline=True)
                            embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                            embed.set_footer(text=f"Action ID: {entry.id}")
                            
                            await self.log_action(after.guild.id, "timeout", embed)
                            break
                except discord.Forbidden:
                    pass
            else:
                # Member was unmuted
                await asyncio.sleep(1)
                
                try:
                    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                        if entry.target.id == after.id:
                            embed = discord.Embed(
                                title="🔊 Member Timeout Removed",
                                color=discord.Color.green(),
                                timestamp=datetime.utcnow()
                            )
                            embed.set_thumbnail(url=after.display_avatar.url)
                            embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)", inline=False)
                            embed.add_field(name="Moderator", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                            embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                            embed.set_footer(text=f"Action ID: {entry.id}")
                            
                            await self.log_action(after.guild.id, "untimeout", embed)
                            break
                except discord.Forbidden:
                    pass
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when messages are deleted"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        await asyncio.sleep(1)
        
        try:
            async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
                # Check if this is a recent deletion
                time_diff = datetime.utcnow() - entry.created_at
                if time_diff.total_seconds() < 5:
                    embed = discord.Embed(
                        title="🗑️ Message Deleted",
                        color=discord.Color.dark_red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
                    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                    embed.add_field(name="Deleted By", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                    
                    # Add message content (truncate if too long)
                    content = message.content[:1000] if message.content else "*No text content*"
                    if len(message.content) > 1000:
                        content += "... (truncated)"
                    embed.add_field(name="Content", value=content, inline=False)
                    
                    # Add attachments info
                    if message.attachments:
                        attachments_text = "\n".join([f"• {att.filename}" for att in message.attachments])
                        embed.add_field(name="Attachments", value=attachments_text, inline=False)
                    
                    embed.set_footer(text=f"Message ID: {message.id}")
                    
                    await self.log_action(message.guild.id, "message_delete", embed)
                    break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log when messages are bulk deleted"""
        if not messages or not messages[0].guild:
            return
        
        guild = messages[0].guild
        channel = messages[0].channel
        
        embed = discord.Embed(
            title="🗑️ Bulk Message Delete",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Messages Deleted", value=str(len(messages)), inline=True)
        
        # Get moderator from audit log
        await asyncio.sleep(1)
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
                time_diff = datetime.utcnow() - entry.created_at
                if time_diff.total_seconds() < 5:
                    embed.add_field(name="Deleted By", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=False)
                    break
        except discord.Forbidden:
            pass
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await self.log_action(guild.id, "bulk_delete", embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log when a channel is created"""
        await asyncio.sleep(1)
        
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    embed = discord.Embed(
                        title="📝 Channel Created",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Channel", value=f"{channel.mention} (`{channel.id}`)", inline=False)
                    embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
                    embed.add_field(name="Created By", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                    
                    if hasattr(channel, 'category') and channel.category:
                        embed.add_field(name="Category", value=channel.category.name, inline=True)
                    
                    embed.set_footer(text=f"Action ID: {entry.id}")
                    
                    await self.log_action(channel.guild.id, "channel_create", embed)
                    break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log when a channel is deleted"""
        await asyncio.sleep(1)
        
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                embed = discord.Embed(
                    title="🗑️ Channel Deleted",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Channel", value=f"{channel.name} (`{channel.id}`)", inline=False)
                embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
                embed.add_field(name="Deleted By", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                
                embed.set_footer(text=f"Action ID: {entry.id}")
                
                await self.log_action(channel.guild.id, "channel_delete", embed)
                break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log when a role is created"""
        await asyncio.sleep(1)
        
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id:
                    embed = discord.Embed(
                        title="🎭 Role Created",
                        color=role.color if role.color != discord.Color.default() else discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Role", value=f"{role.mention} (`{role.id}`)", inline=False)
                    embed.add_field(name="Created By", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                    embed.add_field(name="Color", value=str(role.color), inline=True)
                    embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
                    embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
                    
                    embed.set_footer(text=f"Action ID: {entry.id}")
                    
                    await self.log_action(role.guild.id, "role_create", embed)
                    break
        except discord.Forbidden:
            pass
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log when a role is deleted"""
        await asyncio.sleep(1)
        
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                embed = discord.Embed(
                    title="🗑️ Role Deleted",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Role", value=f"{role.name} (`{role.id}`)", inline=False)
                embed.add_field(name="Deleted By", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=True)
                
                embed.set_footer(text=f"Action ID: {entry.id}")
                
                await self.log_action(role.guild.id, "role_delete", embed)
                break
        except discord.Forbidden:
            pass
    
    @commands.command(name='setauditchannel')
    @commands.has_permissions(administrator=True)
    async def setauditchannel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for audit logs"""
        if channel is None:
            channel = ctx.channel
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            config['settings']['audit_channel_id'] = str(channel.id)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            embed = discord.Embed(
                title="✅ Audit Log Channel Set",
                description=f"All moderation actions will be logged to {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Logged Actions",
                value=(
                    "• Bans/Unbans\n"
                    "• Kicks\n"
                    "• Timeouts/Mutes\n"
                    "• Role Changes\n"
                    "• Message Deletions\n"
                    "• Channel Creation/Deletion\n"
                    "• Role Creation/Deletion"
                ),
                inline=False
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error setting audit channel: {e}")
    
    @commands.command(name='auditlogs', aliases=['viewaudit'])
    @commands.has_permissions(administrator=True)
    async def auditlogs(self, ctx, limit: int = 10):
        """View recent audit log entries from Discord"""
        if limit < 1 or limit > 50:
            await ctx.send("❌ Limit must be between 1 and 50!")
            return
        
        embed = discord.Embed(
            title=f"📋 Recent Audit Log Entries",
            description=f"Showing last {limit} entries",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        try:
            entries = []
            async for entry in ctx.guild.audit_logs(limit=limit):
                action_name = str(entry.action).replace('AuditLogAction.', '').replace('_', ' ').title()
                time_str = f"<t:{int(entry.created_at.timestamp())}:R>"
                
                entry_text = f"**{action_name}**\n"
                entry_text += f"By: {entry.user.mention}\n"
                entry_text += f"Time: {time_str}"
                
                if entry.target:
                    if hasattr(entry.target, 'mention'):
                        entry_text += f"\nTarget: {entry.target.mention}"
                    else:
                        entry_text += f"\nTarget: {entry.target}"
                
                entries.append(entry_text)
            
            # Split entries into chunks if too long
            if entries:
                embed.description = "\n\n".join(entries[:10])
            else:
                embed.description = "No audit log entries found."
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view audit logs!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @setauditchannel.error
    @auditlogs.error
    async def audit_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")

# Import asyncio at the top
import asyncio

async def setup(bot):
    await bot.add_cog(AuditLog(bot))
    print('Audit log cog loaded successfully!')