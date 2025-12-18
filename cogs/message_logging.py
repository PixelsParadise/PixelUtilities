import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class MessageLogging(commands.Cog):
    """Comprehensive message logging system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'
        
        # Cache for deleted messages (to track bulk deletes better)
        self.message_cache = {}
    
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
    
    def get_message_log_channel(self, guild_id):
        """Get the message log channel ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('message_log_channel_id')
    
    def get_ignored_channels(self, guild_id):
        """Get list of channels to ignore from logging"""
        config = self.load_config()
        return config.get('message_logging', {}).get(str(guild_id), {}).get('ignored_channels', [])
    
    def should_log_channel(self, channel):
        """Check if we should log messages from this channel"""
        if not channel.guild:
            return False
        
        ignored = self.get_ignored_channels(channel.guild.id)
        return str(channel.id) not in ignored
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Cache messages for better logging"""
        # Only cache guild messages
        if message.guild and not message.author.bot:
            # Store message in cache (keep last 1000 messages per guild)
            guild_key = str(message.guild.id)
            if guild_key not in self.message_cache:
                self.message_cache[guild_key] = {}
            
            self.message_cache[guild_key][message.id] = {
                'content': message.content,
                'author': message.author,
                'channel': message.channel,
                'created_at': message.created_at,
                'attachments': [att.url for att in message.attachments] if message.attachments else []
            }
            
            # Keep cache size manageable
            if len(self.message_cache[guild_key]) > 1000:
                # Remove oldest entries
                oldest_keys = sorted(self.message_cache[guild_key].keys())[:100]
                for key in oldest_keys:
                    del self.message_cache[guild_key][key]
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when a message is deleted"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check if we should log this channel
        if not self.should_log_channel(message.channel):
            return
        
        # Get log channel
        log_channel_id = self.get_message_log_channel(message.guild.id)
        if not log_channel_id:
            return
        
        log_channel = message.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        # Create embed
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=f"{message.author} ({message.author.id})",
            icon_url=message.author.display_avatar.url
        )
        
        # Message content
        content = message.content if message.content else "*No text content*"
        if len(content) > 1024:
            content = content[:1021] + "..."
        
        embed.add_field(
            name="📝 Content",
            value=content,
            inline=False
        )
        
        # Channel info
        embed.add_field(
            name="📍 Channel",
            value=f"{message.channel.mention} (`{message.channel.name}`)",
            inline=True
        )
        
        # Message age
        message_age = datetime.utcnow() - message.created_at
        age_str = f"<t:{int(message.created_at.timestamp())}:R>"
        embed.add_field(
            name="⏰ Sent",
            value=age_str,
            inline=True
        )
        
        # Attachments
        if message.attachments:
            attachments_text = "\n".join([f"[{att.filename}]({att.url})" for att in message.attachments[:5]])
            if len(message.attachments) > 5:
                attachments_text += f"\n*+{len(message.attachments) - 5} more*"
            embed.add_field(
                name=f"📎 Attachments ({len(message.attachments)})",
                value=attachments_text,
                inline=False
            )
        
        # Embeds
        if message.embeds:
            embed.add_field(
                name="📋 Embeds",
                value=f"{len(message.embeds)} embed(s) in original message",
                inline=True
            )
        
        embed.set_footer(text=f"Message ID: {message.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permissions to send to message log channel in {message.guild.name}")
        except Exception as e:
            print(f"Error logging deleted message: {e}")
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log when messages are bulk deleted"""
        if not messages or not messages[0].guild:
            return
        
        guild = messages[0].guild
        channel = messages[0].channel
        
        # Check if we should log this channel
        if not self.should_log_channel(channel):
            return
        
        # Get log channel
        log_channel_id = self.get_message_log_channel(guild.id)
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        # Create embed
        embed = discord.Embed(
            title="🗑️ Bulk Message Delete",
            description=f"**{len(messages)}** messages were deleted in {channel.mention}",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow()
        )
        
        # Count messages per author
        author_counts = {}
        for msg in messages:
            author_name = str(msg.author)
            author_counts[author_name] = author_counts.get(author_name, 0) + 1
        
        # Show top authors
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        authors_text = "\n".join([f"**{author}**: {count} messages" for author, count in top_authors])
        
        embed.add_field(
            name="👥 Top Authors",
            value=authors_text,
            inline=False
        )
        
        embed.add_field(
            name="📍 Channel",
            value=f"{channel.mention} (`{channel.name}`)",
            inline=True
        )
        
        embed.add_field(
            name="📊 Total Messages",
            value=str(len(messages)),
            inline=True
        )
        
        # Show a sample of deleted messages (last 5)
        sample_messages = []
        for msg in list(messages)[-5:]:
            content = msg.content[:100] if msg.content else "*No content*"
            if len(msg.content) > 100:
                content += "..."
            sample_messages.append(f"**{msg.author.name}**: {content}")
        
        if sample_messages:
            embed.add_field(
                name="📝 Sample Messages (Last 5)",
                value="\n".join(sample_messages),
                inline=False
            )
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permissions to send to message log channel in {guild.name}")
        except Exception as e:
            print(f"Error logging bulk delete: {e}")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log when a message is edited"""
        # Ignore bot messages, DMs, and if content didn't change
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        # Ignore if no actual text content
        if not before.content and not after.content:
            return
        
        # Check if we should log this channel
        if not self.should_log_channel(before.channel):
            return
        
        # Get log channel
        log_channel_id = self.get_message_log_channel(before.guild.id)
        if not log_channel_id:
            return
        
        log_channel = before.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        # Create embed
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=f"{before.author} ({before.author.id})",
            icon_url=before.author.display_avatar.url
        )
        
        # Before content
        before_content = before.content if before.content else "*No text content*"
        if len(before_content) > 1024:
            before_content = before_content[:1021] + "..."
        
        embed.add_field(
            name="📝 Before",
            value=before_content,
            inline=False
        )
        
        # After content
        after_content = after.content if after.content else "*No text content*"
        if len(after_content) > 1024:
            after_content = after_content[:1021] + "..."
        
        embed.add_field(
            name="✅ After",
            value=after_content,
            inline=False
        )
        
        # Channel and message link
        embed.add_field(
            name="📍 Channel",
            value=f"{before.channel.mention}",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Jump to Message",
            value=f"[Click Here]({after.jump_url})",
            inline=True
        )
        
        # Original timestamp
        embed.add_field(
            name="⏰ Originally Sent",
            value=f"<t:{int(before.created_at.timestamp())}:R>",
            inline=True
        )
        
        embed.set_footer(text=f"Message ID: {before.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permissions to send to message log channel in {before.guild.name}")
        except Exception as e:
            print(f"Error logging edited message: {e}")
    
    @commands.command(name='setupmessagelogs')
    @commands.has_permissions(administrator=True)
    async def setupmessagelogs(self, ctx, channel: discord.TextChannel = None):
        """Set up message logging to a channel
        
        Usage: >setupmessagelogs #channel
               >setupmessagelogs (creates new channel)
        """
        guild = ctx.guild
        
        # Create channel if not provided
        if channel is None:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # Add staff roles
                config = self.load_config()
                staff_roles = config.get('staff_roles', {})
                for role_list in staff_roles.values():
                    for role_id in role_list:
                        role = guild.get_role(int(role_id))
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(read_messages=True)
                
                channel = await guild.create_text_channel(
                    name="message-logs",
                    topic="All message deletions, edits, and bulk deletes are logged here",
                    overwrites=overwrites
                )
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to create channels!")
                return
        
        # Save to config
        config = self.load_config()
        if 'settings' not in config:
            config['settings'] = {}
        
        config['settings']['message_log_channel_id'] = str(channel.id)
        
        # Initialize message logging settings
        if 'message_logging' not in config:
            config['message_logging'] = {}
        if str(guild.id) not in config['message_logging']:
            config['message_logging'][str(guild.id)] = {
                'enabled': True,
                'ignored_channels': []
            }
        
        self.save_config(config)
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Message Logging Enabled",
            description=f"Message logs will be sent to {channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📋 What's Logged",
            value=(
                "✅ Message Deletions\n"
                "✅ Message Edits\n"
                "✅ Bulk Message Deletions\n"
                "✅ Message Content\n"
                "✅ Attachments (with links)\n"
                "✅ Author Information\n"
                "✅ Timestamps"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuration Commands",
            value=(
                f"`{ctx.prefix}ignorechannel #channel` - Ignore a channel from logging\n"
                f"`{ctx.prefix}unignorechannel #channel` - Stop ignoring a channel\n"
                f"`{ctx.prefix}ignoredchannels` - View ignored channels"
            ),
            inline=False
        )
        
        embed.set_footer(text="Message logging is now active!")
        
        await ctx.send(embed=embed)
        
        # Send test message to log channel
        test_embed = discord.Embed(
            title="🎉 Message Logging System Activated",
            description="This channel will now receive all message logs from the server.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        test_embed.set_footer(text=f"Configured by {ctx.author}")
        
        await channel.send(embed=test_embed)
    
    @commands.command(name='ignorechannel')
    @commands.has_permissions(administrator=True)
    async def ignorechannel(self, ctx, channel: discord.TextChannel):
        """Ignore a channel from message logging"""
        config = self.load_config()
        
        if 'message_logging' not in config:
            config['message_logging'] = {}
        if str(ctx.guild.id) not in config['message_logging']:
            config['message_logging'][str(ctx.guild.id)] = {'ignored_channels': []}
        
        ignored = config['message_logging'][str(ctx.guild.id)].get('ignored_channels', [])
        
        if str(channel.id) in ignored:
            await ctx.send(f"❌ {channel.mention} is already being ignored!")
            return
        
        ignored.append(str(channel.id))
        config['message_logging'][str(ctx.guild.id)]['ignored_channels'] = ignored
        self.save_config(config)
        
        embed = discord.Embed(
            title="✅ Channel Ignored",
            description=f"Messages from {channel.mention} will no longer be logged.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='unignorechannel')
    @commands.has_permissions(administrator=True)
    async def unignorechannel(self, ctx, channel: discord.TextChannel):
        """Stop ignoring a channel from message logging"""
        config = self.load_config()
        
        if 'message_logging' not in config:
            config['message_logging'] = {}
        if str(ctx.guild.id) not in config['message_logging']:
            config['message_logging'][str(ctx.guild.id)] = {'ignored_channels': []}
        
        ignored = config['message_logging'][str(ctx.guild.id)].get('ignored_channels', [])
        
        if str(channel.id) not in ignored:
            await ctx.send(f"❌ {channel.mention} is not being ignored!")
            return
        
        ignored.remove(str(channel.id))
        config['message_logging'][str(ctx.guild.id)]['ignored_channels'] = ignored
        self.save_config(config)
        
        embed = discord.Embed(
            title="✅ Channel Unignored",
            description=f"Messages from {channel.mention} will now be logged again.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='ignoredchannels')
    @commands.has_permissions(administrator=True)
    async def ignoredchannels(self, ctx):
        """View all channels ignored from message logging"""
        config = self.load_config()
        
        ignored = config.get('message_logging', {}).get(str(ctx.guild.id), {}).get('ignored_channels', [])
        
        if not ignored:
            await ctx.send("✅ No channels are currently ignored from message logging!")
            return
        
        embed = discord.Embed(
            title="🚫 Ignored Channels",
            description=f"These channels are excluded from message logging:",
            color=discord.Color.blue()
        )
        
        channel_list = []
        for channel_id in ignored:
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                channel_list.append(f"• {channel.mention} (`{channel.name}`)")
            else:
                channel_list.append(f"• Unknown Channel (`{channel_id}`)")
        
        embed.add_field(
            name=f"📋 Ignored ({len(ignored)})",
            value="\n".join(channel_list) if channel_list else "None",
            inline=False
        )
        
        embed.set_footer(text=f"Use {ctx.prefix}unignorechannel to remove from list")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='messagelogstats')
    @commands.has_permissions(administrator=True)
    async def messagelogstats(self, ctx):
        """View message logging statistics and status"""
        config = self.load_config()
        
        log_channel_id = self.get_message_log_channel(ctx.guild.id)
        ignored = self.get_ignored_channels(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Message Logging Status",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Status
        if log_channel_id:
            log_channel = ctx.guild.get_channel(int(log_channel_id))
            if log_channel:
                status = f"✅ **Enabled**\n{log_channel.mention}"
                embed.color = discord.Color.green()
            else:
                status = "⚠️ **Channel Not Found**"
                embed.color = discord.Color.orange()
        else:
            status = "❌ **Disabled**"
            embed.color = discord.Color.red()
        
        embed.add_field(
            name="Status",
            value=status,
            inline=False
        )
        
        # Ignored channels
        embed.add_field(
            name="🚫 Ignored Channels",
            value=f"{len(ignored)} channel(s)",
            inline=True
        )
        
        # Cache size
        guild_key = str(ctx.guild.id)
        cache_size = len(self.message_cache.get(guild_key, {}))
        embed.add_field(
            name="💾 Cached Messages",
            value=f"{cache_size} messages",
            inline=True
        )
        
        # What's logged
        embed.add_field(
            name="📋 Logging Features",
            value=(
                "✅ Message Deletions\n"
                "✅ Message Edits\n"
                "✅ Bulk Deletions\n"
                "✅ Attachments\n"
                "✅ Author Info"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @setupmessagelogs.error
    @ignorechannel.error
    @unignorechannel.error
    @ignoredchannels.error
    @messagelogstats.error
    async def message_log_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("❌ Channel not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{ctx.prefix}help {ctx.command.name}` for usage.")

async def setup(bot):
    await bot.add_cog(MessageLogging(bot))
    print('Message logging system loaded successfully!')