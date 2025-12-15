import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os
import asyncio
import re

class Reminders(commands.Cog):
    """Advanced reminder system with DM notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.reminders_file = 'reminders.json'
        self.reminders = self.load_reminders()
        
        # Start the reminder check loop
        self.check_reminders.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.check_reminders.cancel()
    
    def load_reminders(self):
        """Load reminders from file"""
        if os.path.exists(self.reminders_file):
            try:
                with open(self.reminders_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_reminders(self):
        """Save reminders to file"""
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(self.reminders, f, indent=2)
        except Exception as e:
            print(f"Error saving reminders: {e}")
    
    def parse_time(self, time_str):
        """Parse time string like '1h', '30m', '1d', '2w' into timedelta"""
        time_units = {
            's': 1,           # seconds
            'm': 60,          # minutes
            'h': 3600,        # hours
            'd': 86400,       # days
            'w': 604800,      # weeks
            'mo': 2592000,    # months (30 days)
            'y': 31536000     # years (365 days)
        }
        
        try:
            # Handle compound times like "1d12h30m"
            pattern = r'(\d+)([smhdwy]|mo)'
            matches = re.findall(pattern, time_str.lower())
            
            if not matches:
                return None
            
            total_seconds = 0
            for amount, unit in matches:
                amount = int(amount)
                if unit in time_units:
                    total_seconds += amount * time_units[unit]
            
            if total_seconds > 0:
                return timedelta(seconds=total_seconds)
            
            return None
        except:
            return None
    
    def format_time_remaining(self, time_delta):
        """Format timedelta into human readable string"""
        total_seconds = int(time_delta.total_seconds())
        
        if total_seconds < 0:
            return "Now"
        
        years = total_seconds // 31536000
        total_seconds %= 31536000
        
        months = total_seconds // 2592000
        total_seconds %= 2592000
        
        weeks = total_seconds // 604800
        total_seconds %= 604800
        
        days = total_seconds // 86400
        total_seconds %= 86400
        
        hours = total_seconds // 3600
        total_seconds %= 3600
        
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        parts = []
        if years > 0:
            parts.append(f"{years}y")
        if months > 0:
            parts.append(f"{months}mo")
        if weeks > 0:
            parts.append(f"{weeks}w")
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 and not parts:  # Only show seconds if nothing else
            parts.append(f"{seconds}s")
        
        return " ".join(parts[:2]) if parts else "Now"  # Show max 2 units
    
    def create_reminder(self, user_id, guild_id, channel_id, reminder_text, remind_time, repeat_interval=None):
        """Create a new reminder"""
        user_key = str(user_id)
        
        if user_key not in self.reminders:
            self.reminders[user_key] = []
        
        reminder_id = len(self.reminders[user_key]) + 1
        
        reminder_data = {
            'id': reminder_id,
            'user_id': str(user_id),
            'guild_id': str(guild_id) if guild_id else None,
            'channel_id': str(channel_id),
            'reminder': reminder_text,
            'created_at': datetime.utcnow().isoformat(),
            'remind_at': remind_time.isoformat(),
            'repeat_interval': repeat_interval,
            'active': True,
            'repeat_count': 0
        }
        
        self.reminders[user_key].append(reminder_data)
        self.save_reminders()
        return reminder_data
    
    def get_user_reminders(self, user_id, active_only=True):
        """Get all reminders for a user"""
        user_key = str(user_id)
        
        if user_key not in self.reminders:
            return []
        
        if active_only:
            return [r for r in self.reminders[user_key] if r.get('active', True)]
        
        return self.reminders[user_key]
    
    def delete_reminder(self, user_id, reminder_id):
        """Delete a specific reminder"""
        user_key = str(user_id)
        
        if user_key not in self.reminders:
            return False
        
        for i, reminder in enumerate(self.reminders[user_key]):
            if reminder['id'] == reminder_id:
                del self.reminders[user_key][i]
                self.save_reminders()
                return True
        
        return False
    
    def clear_user_reminders(self, user_id):
        """Clear all reminders for a user"""
        user_key = str(user_id)
        
        if user_key in self.reminders:
            count = len([r for r in self.reminders[user_key] if r.get('active', True)])
            self.reminders[user_key] = []
            self.save_reminders()
            return count
        
        return 0
    
    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def check_reminders(self):
        """Check for reminders that need to be sent"""
        current_time = datetime.utcnow()
        
        for user_key, user_reminders in list(self.reminders.items()):
            for reminder in list(user_reminders):
                if not reminder.get('active', True):
                    continue
                
                remind_time = datetime.fromisoformat(reminder['remind_at'])
                
                # Check if it's time to send the reminder
                if current_time >= remind_time:
                    await self.send_reminder(reminder)
                    
                    # Handle repeating reminders
                    if reminder.get('repeat_interval'):
                        # Schedule next reminder
                        next_remind_time = remind_time + timedelta(seconds=reminder['repeat_interval'])
                        reminder['remind_at'] = next_remind_time.isoformat()
                        reminder['repeat_count'] = reminder.get('repeat_count', 0) + 1
                        self.save_reminders()
                    else:
                        # Mark as inactive (completed)
                        reminder['active'] = False
                        self.save_reminders()
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        """Wait until the bot is ready before starting the loop"""
        await self.bot.wait_until_ready()
    
    async def send_reminder(self, reminder):
        """Send a reminder to the user"""
        user_id = int(reminder['user_id'])
        user = self.bot.get_user(user_id)
        
        if not user:
            try:
                user = await self.bot.fetch_user(user_id)
            except:
                print(f"Could not find user {user_id} for reminder")
                return
        
        # Create reminder embed
        embed = discord.Embed(
            title="⏰ Reminder!",
            description=reminder['reminder'],
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add creation time
        created_at = datetime.fromisoformat(reminder['created_at'])
        embed.add_field(
            name="📅 Set",
            value=f"<t:{int(created_at.timestamp())}:R>",
            inline=True
        )
        
        # Add repeat info if applicable
        if reminder.get('repeat_interval'):
            repeat_time = self.format_time_remaining(timedelta(seconds=reminder['repeat_interval']))
            repeat_count = reminder.get('repeat_count', 0)
            embed.add_field(
                name="🔄 Repeating",
                value=f"Every {repeat_time}\nOccurrence #{repeat_count + 1}",
                inline=True
            )
        
        # Add guild/channel context
        guild_id = reminder.get('guild_id')
        channel_id = reminder.get('channel_id')
        
        if guild_id and channel_id:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    embed.add_field(
                        name="📍 Location",
                        value=f"{guild.name} • {channel.mention}",
                        inline=False
                    )
        
        embed.set_footer(text=f"Reminder ID: {reminder['id']}")
        
        # Try to send DM
        try:
            await user.send(embed=embed)
            print(f"✅ Sent reminder to {user.name} (ID: {user.id})")
        except discord.Forbidden:
            print(f"❌ Could not DM user {user.name} (ID: {user.id}) - DMs disabled")
            
            # Try to send in the original channel as fallback
            if channel_id:
                try:
                    channel = self.bot.get_channel(int(channel_id))
                    if channel:
                        await channel.send(f"{user.mention}", embed=embed)
                except:
                    pass
        except Exception as e:
            print(f"Error sending reminder: {e}")
    
    @commands.command(name='remind', aliases=['reminder', 'remindme'])
    async def remind(self, ctx, time: str, *, reminder: str):
        """Set a reminder that will DM you
        
        Time format: 1s, 30m, 2h, 1d, 1w, 1mo, 1y
        You can combine: 1d12h30m
        
        Examples:
        >remind 30m Take out the trash
        >remind 2h Check the oven
        >remind 1d12h Meeting with John
        >remind 1w Study for exam
        """
        time_delta = self.parse_time(time)
        
        if not time_delta:
            await ctx.send(
                "❌ Invalid time format!\n\n"
                "**Valid formats:**\n"
                "• `1s` - 1 second\n"
                "• `30m` - 30 minutes\n"
                "• `2h` - 2 hours\n"
                "• `1d` - 1 day\n"
                "• `1w` - 1 week\n"
                "• `1mo` - 1 month\n"
                "• `1y` - 1 year\n\n"
                "**Combine them:**\n"
                "• `1d12h` - 1 day and 12 hours\n"
                "• `1w3d` - 1 week and 3 days"
            )
            return
        
        # Check if time is too short
        if time_delta.total_seconds() < 10:
            await ctx.send("❌ Reminder time must be at least 10 seconds!")
            return
        
        # Check if time is too long (1 year max)
        if time_delta.total_seconds() > 31536000:
            await ctx.send("❌ Reminder time cannot exceed 1 year!")
            return
        
        # Calculate reminder time
        remind_time = datetime.utcnow() + time_delta
        
        # Create reminder
        reminder_data = self.create_reminder(
            ctx.author.id,
            ctx.guild.id if ctx.guild else None,
            ctx.channel.id,
            reminder,
            remind_time
        )
        
        # Format time remaining
        time_str = self.format_time_remaining(time_delta)
        
        # Create confirmation embed
        embed = discord.Embed(
            title="⏰ Reminder Set!",
            description=f"I'll remind you about:\n**{reminder}**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="⏱️ Time",
            value=f"In {time_str}",
            inline=True
        )
        
        embed.add_field(
            name="📅 When",
            value=f"<t:{int(remind_time.timestamp())}:F>",
            inline=True
        )
        
        embed.add_field(
            name="🔔 Notification",
            value="You'll receive a DM",
            inline=False
        )
        
        embed.set_footer(text=f"Reminder ID: {reminder_data['id']} | Use >reminders to view all")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='repeatremind', aliases=['repeat', 'repeatreminder'])
    async def repeatremind(self, ctx, interval: str, *, reminder: str):
        """Set a repeating reminder
        
        Examples:
        >repeatremind 1h Drink water
        >repeatremind 1d Take vitamins
        >repeatremind 1w Clean room
        """
        time_delta = self.parse_time(interval)
        
        if not time_delta:
            await ctx.send("❌ Invalid time format! Use formats like: 30m, 2h, 1d, 1w")
            return
        
        # Minimum 1 minute for repeating reminders
        if time_delta.total_seconds() < 60:
            await ctx.send("❌ Repeating reminders must be at least 1 minute apart!")
            return
        
        # Maximum 1 month for repeating
        if time_delta.total_seconds() > 2592000:
            await ctx.send("❌ Repeating interval cannot exceed 1 month!")
            return
        
        # Calculate first reminder time
        remind_time = datetime.utcnow() + time_delta
        
        # Create repeating reminder
        reminder_data = self.create_reminder(
            ctx.author.id,
            ctx.guild.id if ctx.guild else None,
            ctx.channel.id,
            reminder,
            remind_time,
            repeat_interval=int(time_delta.total_seconds())
        )
        
        # Format time
        time_str = self.format_time_remaining(time_delta)
        
        # Create confirmation embed
        embed = discord.Embed(
            title="🔄 Repeating Reminder Set!",
            description=f"I'll remind you about:\n**{reminder}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="⏱️ Interval",
            value=f"Every {time_str}",
            inline=True
        )
        
        embed.add_field(
            name="📅 First Reminder",
            value=f"<t:{int(remind_time.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="🔔 Notification",
            value="You'll receive DMs repeatedly",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Stop Reminder",
            value=f"Use `>delreminder {reminder_data['id']}` to stop",
            inline=False
        )
        
        embed.set_footer(text=f"Reminder ID: {reminder_data['id']}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='reminders', aliases=['myreminders', 'reminderlist'])
    async def reminders(self, ctx):
        """View all your active reminders"""
        user_reminders = self.get_user_reminders(ctx.author.id, active_only=True)
        
        if not user_reminders:
            embed = discord.Embed(
                title="⏰ Your Reminders",
                description="You don't have any active reminders!\n\nCreate one with `>remind <time> <message>`",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Sort by remind time
        user_reminders.sort(key=lambda r: datetime.fromisoformat(r['remind_at']))
        
        # Create embed
        embed = discord.Embed(
            title="⏰ Your Active Reminders",
            description=f"You have **{len(user_reminders)}** active reminder(s)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        current_time = datetime.utcnow()
        
        for reminder in user_reminders[:10]:  # Show max 10
            remind_time = datetime.fromisoformat(reminder['remind_at'])
            time_remaining = remind_time - current_time
            time_str = self.format_time_remaining(time_remaining)
            
            # Build field value
            field_value = f"**Message:** {reminder['reminder'][:100]}\n"
            field_value += f"**Time:** <t:{int(remind_time.timestamp())}:R> ({time_str})\n"
            
            if reminder.get('repeat_interval'):
                repeat_time = self.format_time_remaining(timedelta(seconds=reminder['repeat_interval']))
                repeat_count = reminder.get('repeat_count', 0)
                field_value += f"**Repeats:** Every {repeat_time} (#{repeat_count + 1})\n"
            
            field_value += f"**ID:** `{reminder['id']}`"
            
            # Add emoji based on time remaining
            if time_remaining.total_seconds() < 3600:  # Less than 1 hour
                emoji = "🔴"
            elif time_remaining.total_seconds() < 86400:  # Less than 1 day
                emoji = "🟡"
            else:
                emoji = "🟢"
            
            embed.add_field(
                name=f"{emoji} Reminder #{reminder['id']}" + (" 🔄" if reminder.get('repeat_interval') else ""),
                value=field_value,
                inline=False
            )
        
        if len(user_reminders) > 10:
            embed.set_footer(text=f"Showing 10 of {len(user_reminders)} reminders")
        else:
            embed.set_footer(text="Use >delreminder <id> to delete a reminder")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='delreminder', aliases=['deletereminder', 'rmreminder', 'cancelreminder'])
    async def delreminder(self, ctx, reminder_id: int):
        """Delete a specific reminder
        
        Example: >delreminder 1
        """
        if self.delete_reminder(ctx.author.id, reminder_id):
            embed = discord.Embed(
                title="✅ Reminder Deleted",
                description=f"Reminder #{reminder_id} has been deleted.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Could not find reminder #{reminder_id}!")
    
    @commands.command(name='clearreminders', aliases=['deleteallreminders'])
    async def clearreminders(self, ctx):
        """Clear all your reminders"""
        count = self.clear_user_reminders(ctx.author.id)
        
        if count > 0:
            embed = discord.Embed(
                title="✅ Reminders Cleared",
                description=f"Deleted **{count}** reminder(s).",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ You don't have any active reminders to clear!")
    
    @commands.command(name='reminderinfo', aliases=['remindinfo'])
    async def reminderinfo(self, ctx, reminder_id: int):
        """Get detailed information about a specific reminder"""
        user_reminders = self.get_user_reminders(ctx.author.id, active_only=False)
        
        reminder = None
        for r in user_reminders:
            if r['id'] == reminder_id:
                reminder = r
                break
        
        if not reminder:
            await ctx.send(f"❌ Could not find reminder #{reminder_id}!")
            return
        
        # Create detailed embed
        embed = discord.Embed(
            title=f"⏰ Reminder #{reminder['id']} Details",
            description=reminder['reminder'],
            color=discord.Color.blue() if reminder.get('active', True) else discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        # Created time
        created_at = datetime.fromisoformat(reminder['created_at'])
        embed.add_field(
            name="📅 Created",
            value=f"<t:{int(created_at.timestamp())}:F>\n<t:{int(created_at.timestamp())}:R>",
            inline=True
        )
        
        # Remind time
        remind_at = datetime.fromisoformat(reminder['remind_at'])
        current_time = datetime.utcnow()
        time_remaining = remind_at - current_time
        
        if reminder.get('active', True):
            time_str = self.format_time_remaining(time_remaining)
            embed.add_field(
                name="⏰ Reminder Time",
                value=f"<t:{int(remind_at.timestamp())}:F>\n<t:{int(remind_at.timestamp())}:R> ({time_str})",
                inline=True
            )
        else:
            embed.add_field(
                name="✅ Completed",
                value=f"<t:{int(remind_at.timestamp())}:F>",
                inline=True
            )
        
        # Status
        status = "🟢 Active" if reminder.get('active', True) else "🔴 Completed"
        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )
        
        # Repeat info
        if reminder.get('repeat_interval'):
            repeat_time = self.format_time_remaining(timedelta(seconds=reminder['repeat_interval']))
            repeat_count = reminder.get('repeat_count', 0)
            embed.add_field(
                name="🔄 Repeating",
                value=f"Every {repeat_time}\nOccurred {repeat_count} time(s)",
                inline=True
            )
        
        # Location
        guild_id = reminder.get('guild_id')
        channel_id = reminder.get('channel_id')
        
        if guild_id and channel_id:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                channel = guild.get_channel(int(channel_id))
                location = f"{guild.name}"
                if channel:
                    location += f" • {channel.mention}"
                embed.add_field(
                    name="📍 Set In",
                    value=location,
                    inline=False
                )
        
        embed.set_footer(text=f"Reminder ID: {reminder['id']}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='snooze')
    async def snooze(self, ctx, reminder_id: int, time: str):
        """Snooze a reminder by adding time to it
        
        Example: >snooze 1 30m
        """
        user_key = str(ctx.author.id)
        
        if user_key not in self.reminders:
            await ctx.send("❌ You don't have any reminders!")
            return
        
        # Find the reminder
        reminder = None
        for r in self.reminders[user_key]:
            if r['id'] == reminder_id and r.get('active', True):
                reminder = r
                break
        
        if not reminder:
            await ctx.send(f"❌ Could not find active reminder #{reminder_id}!")
            return
        
        # Parse snooze time
        time_delta = self.parse_time(time)
        
        if not time_delta:
            await ctx.send("❌ Invalid time format! Use formats like: 30m, 2h, 1d")
            return
        
        # Update reminder time
        old_remind_time = datetime.fromisoformat(reminder['remind_at'])
        new_remind_time = old_remind_time + time_delta
        reminder['remind_at'] = new_remind_time.isoformat()
        self.save_reminders()
        
        # Format time
        time_str = self.format_time_remaining(time_delta)
        
        embed = discord.Embed(
            title="😴 Reminder Snoozed",
            description=f"Reminder #{reminder_id} has been snoozed!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⏰ New Time",
            value=f"<t:{int(new_remind_time.timestamp())}:F>\n<t:{int(new_remind_time.timestamp())}:R>",
            inline=False
        )
        
        embed.add_field(
            name="⏱️ Added",
            value=time_str,
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='reminderstats')
    async def reminderstats(self, ctx):
        """View your reminder statistics"""
        user_reminders = self.get_user_reminders(ctx.author.id, active_only=False)
        
        if not user_reminders:
            await ctx.send("❌ You don't have any reminders yet!")
            return
        
        # Calculate stats
        total = len(user_reminders)
        active = len([r for r in user_reminders if r.get('active', True)])
        completed = total - active
        repeating = len([r for r in user_reminders if r.get('repeat_interval') and r.get('active', True)])
        
        # Total repeat count
        total_repeats = sum(r.get('repeat_count', 0) for r in user_reminders if r.get('repeat_interval'))
        
        # Find oldest and newest
        oldest = min(user_reminders, key=lambda r: datetime.fromisoformat(r['created_at']))
        newest = max(user_reminders, key=lambda r: datetime.fromisoformat(r['created_at']))
        
        # Next reminder
        active_reminders = [r for r in user_reminders if r.get('active', True)]
        if active_reminders:
            next_reminder = min(active_reminders, key=lambda r: datetime.fromisoformat(r['remind_at']))
            next_time = datetime.fromisoformat(next_reminder['remind_at'])
            time_until_next = next_time - datetime.utcnow()
        else:
            next_reminder = None
        
        # Create embed
        embed = discord.Embed(
            title="📊 Reminder Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📈 Overview",
            value=(
                f"**Total Created:** {total}\n"
                f"**Active:** {active}\n"
                f"**Completed:** {completed}\n"
                f"**Repeating:** {repeating}"
            ),
            inline=True
        )
        
        if total_repeats > 0:
            embed.add_field(
                name="🔄 Repeat Stats",
                value=f"**Total Repeats:** {total_repeats}",
                inline=True
            )
        
        if next_reminder:
            time_str = self.format_time_remaining(time_until_next)
            embed.add_field(
                name="⏰ Next Reminder",
                value=f"<t:{int(next_time.timestamp())}:R>\n({time_str})",
                inline=True
            )
        
        oldest_time = datetime.fromisoformat(oldest['created_at'])
        newest_time = datetime.fromisoformat(newest['created_at'])
        
        embed.add_field(
            name="📅 First Reminder",
            value=f"<t:{int(oldest_time.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="📅 Latest Reminder",
            value=f"<t:{int(newest_time.timestamp())}:R>",
            inline=True
        )
        
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='remindhelp')
    async def remindhelp(self, ctx):
        """Show detailed help for the reminder system"""
        embed = discord.Embed(
            title="⏰ Reminder System Help",
            description="Set reminders that will DM you!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⏱️ Time Formats",
            value=(
                "`1s` - 1 second\n"
                "`30m` - 30 minutes\n"
                "`2h` - 2 hours\n"
                "`1d` - 1 day\n"
                "`1w` - 1 week\n"
                "`1mo` - 1 month\n"
                "`1y` - 1 year\n\n"
                "**Combine:** `1d12h30m`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Basic Commands",
            value=(
                "`>remind <time> <message>` - Set a reminder\n"
                "`>repeatremind <interval> <message>` - Repeating reminder\n"
                "`>reminders` - View all your reminders\n"
                "`>delreminder <id>` - Delete a reminder\n"
                "`>clearreminders` - Delete all reminders"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔧 Advanced Commands",
            value=(
                "`>reminderinfo <id>` - Detailed reminder info\n"
                "`>snooze <id> <time>` - Postpone a reminder\n"
                "`>reminderstats` - View your statistics"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Examples",
            value=(
                "`>remind 30m Take out trash`\n"
                "`>remind 2h Check the oven`\n"
                "`>remind 1d12h Meeting tomorrow`\n"
                "`>repeatremind 8h Drink water`\n"
                "`>snooze 1 15m`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔔 Notifications",
            value="All reminders are sent via DM! Make sure you have DMs enabled.",
            inline=False
        )
        
        embed.set_footer(text="Reminders are checked every 30 seconds")
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @remind.error
    @repeatremind.error
    @delreminder.error
    @reminderinfo.error
    @snooze.error
    async def reminder_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{ctx.prefix}remindhelp` for usage information.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument! Use `{ctx.prefix}remindhelp` for usage information.")

async def setup(bot):
    await bot.add_cog(Reminders(bot))
    print('Reminder system loaded successfully!')