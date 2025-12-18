import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class JoinLeaveLogging(commands.Cog):
    """Advanced join/leave tracking with role history"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'
        self.role_history_file = 'role_history.json'
        self.role_history = self.load_role_history()
    
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
    
    def load_role_history(self):
        """Load role history from file"""
        if os.path.exists(self.role_history_file):
            try:
                with open(self.role_history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_role_history(self):
        """Save role history to file"""
        try:
            with open(self.role_history_file, 'w') as f:
                json.dump(self.role_history, f, indent=2)
        except Exception as e:
            print(f"Error saving role history: {e}")
    
    def get_join_leave_channel(self, guild_id):
        """Get the join/leave log channel ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('join_leave_channel_id')
    
    def save_member_roles(self, guild_id, user_id, roles):
        """Save member's roles when they leave"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.role_history:
            self.role_history[guild_key] = {}
        
        self.role_history[guild_key][user_key] = {
            'roles': [str(role.id) for role in roles if role.name != "@everyone"],
            'role_names': [role.name for role in roles if role.name != "@everyone"],
            'left_at': datetime.utcnow().isoformat(),
            'join_count': self.role_history.get(guild_key, {}).get(user_key, {}).get('join_count', 0) + 1
        }
        
        self.save_role_history()
    
    def get_previous_roles(self, guild_id, user_id):
        """Get member's previous roles"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.role_history and user_key in self.role_history[guild_key]:
            return self.role_history[guild_key][user_key]
        return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when a member joins the server"""
        # Get log channel
        log_channel_id = self.get_join_leave_channel(member.guild.id)
        if not log_channel_id:
            return
        
        log_channel = member.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        # Calculate account age
        account_created = member.created_at
        account_age = datetime.utcnow() - account_created
        days_old = account_age.days
        
        # Check if this is a rejoin
        previous_data = self.get_previous_roles(member.guild.id, member.id)
        is_rejoin = previous_data is not None
        
        # Determine if account is new (less than 7 days old)
        is_new_account = days_old < 7
        
        # Choose color based on account age
        if is_new_account:
            color = discord.Color.orange()  # Warning for new accounts
        elif is_rejoin:
            color = discord.Color.blue()    # Blue for rejoins
        else:
            color = discord.Color.green()   # Green for normal joins
        
        # Create embed
        embed = discord.Embed(
            title="📥 Member Joined",
            description=f"{member.mention} joined the server",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # User info
        embed.add_field(
            name="👤 User",
            value=f"{member}\n`{member.id}`",
            inline=True
        )
        
        # Account created
        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(account_created.timestamp())}:F>\n<t:{int(account_created.timestamp())}:R>",
            inline=True
        )
        
        # Account age with warning if new
        age_text = f"**{days_old}** days old"
        if is_new_account:
            age_text += " ⚠️"
        
        embed.add_field(
            name="⏳ Account Age",
            value=age_text,
            inline=True
        )
        
        # Member count
        embed.add_field(
            name="📊 Member Count",
            value=f"**{member.guild.member_count}** members",
            inline=True
        )
        
        # Join position (approximation)
        sorted_members = sorted(member.guild.members, key=lambda m: m.joined_at or datetime.utcnow())
        join_position = sorted_members.index(member) + 1 if member in sorted_members else "Unknown"
        
        embed.add_field(
            name="🔢 Join Position",
            value=f"#{join_position}",
            inline=True
        )
        
        # New account warning
        if is_new_account:
            embed.add_field(
                name="⚠️ Warning",
                value="This is a **new account** (less than 7 days old)",
                inline=False
            )
        
        # Rejoin information
        if is_rejoin:
            join_count = previous_data.get('join_count', 1)
            left_at = previous_data.get('left_at')
            previous_roles = previous_data.get('role_names', [])
            
            rejoin_text = f"This user has joined **{join_count}** time(s) before"
            
            if left_at:
                left_timestamp = datetime.fromisoformat(left_at)
                time_away = datetime.utcnow() - left_timestamp
                days_away = time_away.days
                hours_away = time_away.seconds // 3600
                
                if days_away > 0:
                    rejoin_text += f"\nLast left: **{days_away}** days ago"
                elif hours_away > 0:
                    rejoin_text += f"\nLast left: **{hours_away}** hours ago"
                else:
                    rejoin_text += f"\nLast left: Recently"
            
            embed.add_field(
                name="🔄 Rejoin Information",
                value=rejoin_text,
                inline=False
            )
            
            # Show previous roles
            if previous_roles:
                roles_text = ", ".join([f"`{role}`" for role in previous_roles[:10]])
                if len(previous_roles) > 10:
                    roles_text += f" *+{len(previous_roles) - 10} more*"
                
                embed.add_field(
                    name="🎭 Previous Roles",
                    value=roles_text,
                    inline=False
                )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permissions to send to join/leave log channel in {member.guild.name}")
        except Exception as e:
            print(f"Error logging member join: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when a member leaves the server"""
        # Save their roles first
        self.save_member_roles(member.guild.id, member.id, member.roles)
        
        # Get log channel
        log_channel_id = self.get_join_leave_channel(member.guild.id)
        if not log_channel_id:
            return
        
        log_channel = member.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        # Calculate how long they were in the server
        if member.joined_at:
            time_in_server = datetime.utcnow() - member.joined_at
            days = time_in_server.days
            hours = time_in_server.seconds // 3600
            minutes = (time_in_server.seconds % 3600) // 60
        else:
            days = hours = minutes = 0
        
        # Get their roles (excluding @everyone)
        roles = [role for role in member.roles if role.name != "@everyone"]
        
        # Create embed
        embed = discord.Embed(
            title="📤 Member Left",
            description=f"{member.mention} left the server",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # User info
        embed.add_field(
            name="👤 User",
            value=f"{member}\n`{member.id}`",
            inline=True
        )
        
        # When they joined
        if member.joined_at:
            embed.add_field(
                name="📅 Joined Server",
                value=f"<t:{int(member.joined_at.timestamp())}:F>\n<t:{int(member.joined_at.timestamp())}:R>",
                inline=True
            )
        
        # Time in server
        if days > 0:
            time_str = f"**{days}** days, **{hours}** hours"
        elif hours > 0:
            time_str = f"**{hours}** hours, **{minutes}** minutes"
        else:
            time_str = f"**{minutes}** minutes"
        
        embed.add_field(
            name="⏱️ Time in Server",
            value=time_str,
            inline=True
        )
        
        # Member count
        embed.add_field(
            name="📊 Member Count",
            value=f"**{member.guild.member_count}** members remaining",
            inline=True
        )
        
        # Account age
        account_age = datetime.utcnow() - member.created_at
        embed.add_field(
            name="📆 Account Age",
            value=f"**{account_age.days}** days old",
            inline=True
        )
        
        # Roles they had
        if roles:
            # Sort roles by position (highest first)
            sorted_roles = sorted(roles, key=lambda r: r.position, reverse=True)
            
            # Create role list with colors
            role_list = []
            for role in sorted_roles[:15]:  # Show max 15 roles
                role_list.append(role.mention)
            
            roles_text = ", ".join(role_list)
            if len(roles) > 15:
                roles_text += f" *+{len(roles) - 15} more*"
            
            embed.add_field(
                name=f"🎭 Roles ({len(roles)})",
                value=roles_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 Roles",
                value="*No roles*",
                inline=False
            )
        
        # Check if they left shortly after joining (potential raid)
        if days == 0 and hours < 1:
            embed.add_field(
                name="⚠️ Note",
                value="User left within **1 hour** of joining",
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Missing permissions to send to join/leave log channel in {member.guild.name}")
        except Exception as e:
            print(f"Error logging member leave: {e}")
    
    @commands.command(name='setupjoinleavelogs')
    @commands.has_permissions(administrator=True)
    async def setupjoinleavelogs(self, ctx, channel: discord.TextChannel = None):
        """Set up join/leave logging to a channel
        
        Usage: >setupjoinleavelogs #channel
               >setupjoinleavelogs (creates new channel)
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
                    name="join-leave-logs",
                    topic="Member joins and leaves are logged here with role tracking",
                    overwrites=overwrites
                )
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to create channels!")
                return
        
        # Save to config
        config = self.load_config()
        if 'settings' not in config:
            config['settings'] = {}
        
        config['settings']['join_leave_channel_id'] = str(channel.id)
        self.save_config(config)
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Join/Leave Logging Enabled",
            description=f"Join and leave logs will be sent to {channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📋 What's Logged (Joins)",
            value=(
                "✅ Member mention and info\n"
                "✅ Account creation date\n"
                "✅ Account age\n"
                "✅ New account warnings (<7 days)\n"
                "✅ Rejoin detection\n"
                "✅ Previous roles (if rejoining)\n"
                "✅ Join position\n"
                "✅ Member count"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📋 What's Logged (Leaves)",
            value=(
                "✅ Member mention and info\n"
                "✅ All roles they had\n"
                "✅ Time in server\n"
                "✅ When they joined\n"
                "✅ Account age\n"
                "✅ Quick leave warnings\n"
                "✅ Member count"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💾 Role History",
            value=(
                "Roles are automatically saved when members leave.\n"
                "When they rejoin, you'll see what roles they previously had!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistics Commands",
            value=(
                f"`{ctx.prefix}rolehistory @user` - View user's role history\n"
                f"`{ctx.prefix}joinleavestats` - View server statistics\n"
                f"`{ctx.prefix}clearrolehistory @user` - Clear user's role history"
            ),
            inline=False
        )
        
        embed.set_footer(text="Join/Leave logging is now active!")
        
        await ctx.send(embed=embed)
        
        # Send test message to log channel
        test_embed = discord.Embed(
            title="🎉 Join/Leave Logging System Activated",
            description="This channel will now receive all member join and leave logs.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        test_embed.set_footer(text=f"Configured by {ctx.author}")
        
        await channel.send(embed=test_embed)
    
    @commands.command(name='rolehistory', aliases=['previousroles', 'rh'])
    @commands.has_permissions(kick_members=True)
    async def rolehistory(self, ctx, member: discord.Member = None):
        """View a user's role history (shows roles they had when they last left)"""
        if member is None:
            member = ctx.author
        
        previous_data = self.get_previous_roles(ctx.guild.id, member.id)
        
        embed = discord.Embed(
            title=f"🎭 Role History - {member.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Current roles
        current_roles = [role for role in member.roles if role.name != "@everyone"]
        if current_roles:
            current_text = ", ".join([role.mention for role in sorted(current_roles, key=lambda r: r.position, reverse=True)[:15]])
            if len(current_roles) > 15:
                current_text += f" *+{len(current_roles) - 15} more*"
        else:
            current_text = "*No roles*"
        
        embed.add_field(
            name=f"✅ Current Roles ({len(current_roles)})",
            value=current_text,
            inline=False
        )
        
        # Previous roles
        if previous_data:
            previous_roles = previous_data.get('role_names', [])
            left_at = previous_data.get('left_at')
            join_count = previous_data.get('join_count', 1)
            
            if previous_roles:
                previous_text = ", ".join([f"`{role}`" for role in previous_roles[:15]])
                if len(previous_roles) > 15:
                    previous_text += f" *+{len(previous_roles) - 15} more*"
            else:
                previous_text = "*No roles when they left*"
            
            embed.add_field(
                name=f"📋 Previous Roles ({len(previous_roles)})",
                value=previous_text,
                inline=False
            )
            
            # Additional info
            info_text = f"**Join Count:** {join_count} time(s)"
            if left_at:
                left_timestamp = datetime.fromisoformat(left_at)
                info_text += f"\n**Last Left:** <t:{int(left_timestamp.timestamp())}:R>"
            
            embed.add_field(
                name="ℹ️ Information",
                value=info_text,
                inline=False
            )
            
            # Compare roles
            previous_role_names = set(previous_roles)
            current_role_names = set([role.name for role in current_roles])
            
            roles_lost = previous_role_names - current_role_names
            roles_gained = current_role_names - previous_role_names
            
            if roles_lost:
                lost_text = ", ".join([f"`{role}`" for role in list(roles_lost)[:10]])
                if len(roles_lost) > 10:
                    lost_text += f" *+{len(roles_lost) - 10} more*"
                embed.add_field(
                    name=f"❌ Roles Lost ({len(roles_lost)})",
                    value=lost_text,
                    inline=True
                )
            
            if roles_gained:
                gained_text = ", ".join([f"`{role}`" for role in list(roles_gained)[:10]])
                if len(roles_gained) > 10:
                    gained_text += f" *+{len(roles_gained) - 10} more*"
                embed.add_field(
                    name=f"✨ Roles Gained ({len(roles_gained)})",
                    value=gained_text,
                    inline=True
                )
        else:
            embed.add_field(
                name="📋 Previous Roles",
                value="*No previous role data found*\n\nRole history is only recorded when members leave the server.",
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='joinleavestats')
    @commands.has_permissions(kick_members=True)
    async def joinleavestats(self, ctx):
        """View join/leave statistics for the server"""
        config = self.load_config()
        
        log_channel_id = self.get_join_leave_channel(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Join/Leave Statistics",
            description=f"Statistics for **{ctx.guild.name}**",
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
        
        # Member statistics
        total_members = ctx.guild.member_count
        total_bots = sum(1 for m in ctx.guild.members if m.bot)
        total_humans = total_members - total_bots
        
        embed.add_field(
            name="👥 Current Members",
            value=f"**Total:** {total_members}\n**Humans:** {total_humans}\n**Bots:** {total_bots}",
            inline=True
        )
        
        # Role history data
        guild_key = str(ctx.guild.id)
        if guild_key in self.role_history:
            tracked_users = len(self.role_history[guild_key])
            total_joins = sum(data.get('join_count', 1) for data in self.role_history[guild_key].values())
        else:
            tracked_users = 0
            total_joins = 0
        
        embed.add_field(
            name="💾 Tracked Data",
            value=f"**Users with history:** {tracked_users}\n**Total recorded joins:** {total_joins}",
            inline=True
        )
        
        # New accounts (less than 7 days old)
        new_accounts = sum(1 for m in ctx.guild.members if (datetime.utcnow() - m.created_at).days < 7 and not m.bot)
        
        embed.add_field(
            name="⚠️ New Accounts",
            value=f"**{new_accounts}** members with accounts <7 days old",
            inline=True
        )
        
        # Most common rejoiners
        if guild_key in self.role_history:
            rejoiners = sorted(
                self.role_history[guild_key].items(),
                key=lambda x: x[1].get('join_count', 0),
                reverse=True
            )[:5]
            
            if rejoiners:
                rejoiner_text = []
                for user_id, data in rejoiners:
                    if data.get('join_count', 0) > 1:
                        user = ctx.guild.get_member(int(user_id))
                        user_name = user.mention if user else f"User {user_id}"
                        rejoiner_text.append(f"{user_name}: **{data['join_count']}** joins")
                
                if rejoiner_text:
                    embed.add_field(
                        name="🔄 Top Rejoiners",
                        value="\n".join(rejoiner_text),
                        inline=False
                    )
        
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='clearrolehistory')
    @commands.has_permissions(administrator=True)
    async def clearrolehistory(self, ctx, member: discord.Member):
        """Clear role history for a specific user"""
        guild_key = str(ctx.guild.id)
        user_key = str(member.id)
        
        if guild_key in self.role_history and user_key in self.role_history[guild_key]:
            del self.role_history[guild_key][user_key]
            self.save_role_history()
            
            embed = discord.Embed(
                title="✅ Role History Cleared",
                description=f"Role history has been cleared for {member.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ No role history found for {member.mention}")
    
    @commands.command(name='restorerolesfor')
    @commands.has_permissions(administrator=True)
    async def restorerolesfor(self, ctx, member: discord.Member):
        """Restore a member's previous roles (from when they last left)"""
        previous_data = self.get_previous_roles(ctx.guild.id, member.id)
        
        if not previous_data:
            await ctx.send(f"❌ No previous role data found for {member.mention}")
            return
        
        previous_role_ids = previous_data.get('roles', [])
        if not previous_role_ids:
            await ctx.send(f"❌ {member.mention} had no roles when they last left")
            return
        
        # Get roles to restore
        roles_to_add = []
        roles_not_found = []
        
        for role_id in previous_role_ids:
            role = ctx.guild.get_role(int(role_id))
            if role:
                # Check if they already have it
                if role not in member.roles:
                    # Check if bot can assign it
                    if role < ctx.guild.me.top_role:
                        roles_to_add.append(role)
                    else:
                        roles_not_found.append(f"{role.name} (bot role too low)")
            else:
                roles_not_found.append(f"Unknown role (ID: {role_id})")
        
        if not roles_to_add and not roles_not_found:
            await ctx.send(f"✅ {member.mention} already has all their previous roles!")
            return
        
        # Add roles
        success = []
        failed = []
        
        for role in roles_to_add:
            try:
                await member.add_roles(role, reason=f"Role restoration by {ctx.author}")
                success.append(role.name)
            except:
                failed.append(role.name)
        
        # Create result embed
        embed = discord.Embed(
            title="🎭 Role Restoration Complete",
            description=f"Attempted to restore previous roles for {member.mention}",
            color=discord.Color.green() if not failed else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        if success:
            embed.add_field(
                name=f"✅ Restored ({len(success)})",
                value=", ".join([f"`{r}`" for r in success[:15]]),
                inline=False
            )
        
        if failed:
            embed.add_field(
                name=f"❌ Failed ({len(failed)})",
                value=", ".join([f"`{r}`" for r in failed[:10]]),
                inline=False
            )
        
        if roles_not_found:
            embed.add_field(
                name=f"⚠️ Not Found ({len(roles_not_found)})",
                value=", ".join([f"`{r}`" for r in roles_not_found[:10]]),
                inline=False
            )
        
        embed.set_footer(text=f"Restored by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @setupjoinleavelogs.error
    @rolehistory.error
    @joinleavestats.error
    @clearrolehistory.error
    @restorerolesfor.error
    async def joinleave_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("❌ Channel not found!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{ctx.prefix}help {ctx.command.name}` for usage.")

async def setup(bot):
    await bot.add_cog(JoinLeaveLogging(bot))
    print('Join/Leave logging system with role tracking loaded successfully!')