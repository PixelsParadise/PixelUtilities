import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class MemberTracking(commands.Cog):
    """Tracks member joins and leaves with invite tracking"""
    
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}  # Store invites for tracking
        self.invite_data_file = 'invite_tracking.json'
        self.invite_tracking = self.load_invite_tracking()
        
    def load_invite_tracking(self):
        """Load invite tracking data from file"""
        if os.path.exists(self.invite_data_file):
            try:
                with open(self.invite_data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_invite_tracking(self):
        """Save invite tracking data to file"""
        try:
            with open(self.invite_data_file, 'w') as f:
                json.dump(self.invite_tracking, f, indent=2)
        except Exception as e:
            print(f"Error saving invite tracking: {e}")
    
    def record_invite(self, guild_id, inviter_id, invited_id):
        """Record who invited whom"""
        guild_key = str(guild_id)
        inviter_key = str(inviter_id)
        invited_key = str(invited_id)
        
        if guild_key not in self.invite_tracking:
            self.invite_tracking[guild_key] = {}
        
        if inviter_key not in self.invite_tracking[guild_key]:
            self.invite_tracking[guild_key][inviter_key] = {
                'total_invites': 0,
                'invited_users': []
            }
        
        self.invite_tracking[guild_key][inviter_key]['total_invites'] += 1
        self.invite_tracking[guild_key][inviter_key]['invited_users'].append({
            'user_id': invited_key,
            'joined_at': datetime.utcnow().isoformat()
        })
        
        self.save_invite_tracking()
    
    def get_inviter_stats(self, guild_id, user_id):
        """Get invite statistics for a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.invite_tracking and user_key in self.invite_tracking[guild_key]:
            return self.invite_tracking[guild_key][user_key]
        return None
    
    def remove_invite(self, guild_id, inviter_id, left_user_id):
        """Remove an invite when someone leaves (for accurate tracking)"""
        guild_key = str(guild_id)
        inviter_key = str(inviter_id)
        left_user_key = str(left_user_id)
        
        if guild_key in self.invite_tracking and inviter_key in self.invite_tracking[guild_key]:
            invited_users = self.invite_tracking[guild_key][inviter_key]['invited_users']
            self.invite_tracking[guild_key][inviter_key]['invited_users'] = [
                u for u in invited_users if u['user_id'] != left_user_key
            ]
            self.invite_tracking[guild_key][inviter_key]['total_invites'] = len(
                self.invite_tracking[guild_key][inviter_key]['invited_users']
            )
            self.save_invite_tracking()
            return True
        return False
    
    def find_who_invited(self, guild_id, user_id):
        """Find who invited a specific user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.invite_tracking:
            for inviter_id, data in self.invite_tracking[guild_key].items():
                for invited in data['invited_users']:
                    if invited['user_id'] == user_key:
                        return inviter_id
        return None
        
    async def load_invites(self):
        """Load all invites from all guilds"""
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except discord.Forbidden:
                print(f"Missing permissions to view invites in {guild.name}")
                self.invites[guild.id] = []
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Load invites when bot is ready"""
        await self.load_invites()
        print("Member tracking loaded - invite tracking enabled")
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Update invite cache when new invite is created"""
        if invite.guild.id not in self.invites:
            self.invites[invite.guild.id] = []
        self.invites[invite.guild.id].append(invite)
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Update invite cache when invite is deleted"""
        if invite.guild.id in self.invites:
            self.invites[invite.guild.id] = [
                inv for inv in self.invites[invite.guild.id] 
                if inv.code != invite.code
            ]
    
    async def find_used_invite(self, member):
        """Find which invite was used by comparing invite uses"""
        try:
            new_invites = await member.guild.invites()
            
            for new_invite in new_invites:
                for old_invite in self.invites.get(member.guild.id, []):
                    if new_invite.code == old_invite.code and new_invite.uses > old_invite.uses:
                        # Update the invite cache
                        self.invites[member.guild.id] = new_invites
                        return new_invite
            
            # Update cache even if we didn't find the invite
            self.invites[member.guild.id] = new_invites
            return None
            
        except discord.Forbidden:
            return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Track when a member joins the server"""
        # Load config to get log channel
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            log_channel_id = config['settings'].get('log_channel_id')
            
            # Calculate account age
            account_created = member.created_at
            account_age = datetime.utcnow() - account_created
            days_old = account_age.days
            
            # Determine if account is new (less than 7 days old)
            is_new_account = days_old < 7
            
            # Find who invited them
            used_invite = await self.find_used_invite(member)
            
            # Record the invite
            if used_invite and used_invite.inviter:
                self.record_invite(member.guild.id, used_invite.inviter.id, member.id)
            
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
                    
                    if used_invite:
                        inviter = used_invite.inviter
                        inviter_stats = self.get_inviter_stats(member.guild.id, inviter.id)
                        total_invites = inviter_stats['total_invites'] if inviter_stats else 1
                        
                        embed.add_field(
                            name="Invited By", 
                            value=f"{inviter.mention} ({inviter})\nInviter ID: `{inviter.id}`\nInvite Code: `{used_invite.code}`\nTotal Invites: **{total_invites}**", 
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="Invited By", 
                            value="Unknown (possibly vanity URL or widget)", 
                            inline=False
                        )
                    
                    embed.set_footer(text=f"Member #{member.guild.member_count}")
                    
                    await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error in member join tracking: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Track when a member leaves the server"""
        # Find who invited them and update their count
        inviter_id = self.find_who_invited(member.guild.id, member.id)
        if inviter_id:
            self.remove_invite(member.guild.id, inviter_id, member.id)
        
        # Load config to get log channel
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            log_channel_id = config['settings'].get('log_channel_id')
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
            
            if inviter_id:
                inviter = member.guild.get_member(int(inviter_id))
                if inviter:
                    embed.add_field(name="Was Invited By", value=f"{inviter.mention} (ID: `{inviter_id}`)", inline=False)
                else:
                    embed.add_field(name="Was Invited By", value=f"User ID: `{inviter_id}` (no longer in server)", inline=False)
            
            if roles:
                embed.add_field(name="Roles", value=", ".join(roles), inline=False)
            
            embed.set_footer(text=f"Member #{member.guild.member_count} remaining")
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error in member leave tracking: {e}")
    
    @commands.command(name='invites')
    async def invites(self, ctx, member: discord.Member = None):
        """Check how many people a user has invited to the server"""
        if member is None:
            member = ctx.author
        
        stats = self.get_inviter_stats(ctx.guild.id, member.id)
        
        if not stats or stats['total_invites'] == 0:
            embed = discord.Embed(
                title=f"📊 Invite Stats for {member.display_name}",
                description=f"{member.mention} hasn't invited anyone to the server yet.",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 Invite Stats for {member.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Total Active Invites", value=f"**{stats['total_invites']}**", inline=False)
        
        # Show invited users (up to 10 most recent)
        if stats['invited_users']:
            invited_list = []
            for invited in stats['invited_users'][-10:]:  # Last 10
                user = ctx.guild.get_member(int(invited['user_id']))
                if user:
                    invited_list.append(f"• {user.mention} (`{invited['user_id']}`)")
                else:
                    invited_list.append(f"• User ID: `{invited['user_id']}` (left server)")
            
            if len(stats['invited_users']) > 10:
                invited_list.append(f"*...and {len(stats['invited_users']) - 10} more*")
            
            embed.add_field(
                name="Recently Invited Users",
                value="\n".join(invited_list) if invited_list else "None currently in server",
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {member.id}")
        await ctx.send(embed=embed)
    
    @commands.command(name='leaderboard')
    async def leaderboard(self, ctx):
        """Show the invite leaderboard for the server"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.invite_tracking or not self.invite_tracking[guild_key]:
            await ctx.send("❌ No invite data available for this server yet!")
            return
        
        # Sort users by total invites
        sorted_inviters = sorted(
            self.invite_tracking[guild_key].items(),
            key=lambda x: x[1]['total_invites'],
            reverse=True
        )
        
        # Create leaderboard embed
        embed = discord.Embed(
            title="🏆 Invite Leaderboard",
            description=f"Top inviters in {ctx.guild.name}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = []
        
        for idx, (user_id, data) in enumerate(sorted_inviters[:10]):
            user = ctx.guild.get_member(int(user_id))
            medal = medals[idx] if idx < 3 else f"`{idx + 1}.`"
            
            if user:
                leaderboard_text.append(
                    f"{medal} **{user.display_name}** - {data['total_invites']} invites"
                )
            else:
                leaderboard_text.append(
                    f"{medal} User ID `{user_id}` - {data['total_invites']} invites"
                )
        
        embed.description = "\n".join(leaderboard_text)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='whoinvited')
    async def whoinvited(self, ctx, member: discord.Member = None):
        """Check who invited a specific user"""
        if member is None:
            member = ctx.author
        
        inviter_id = self.find_who_invited(ctx.guild.id, member.id)
        
        embed = discord.Embed(
            title=f"🔍 Invite Info for {member.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if inviter_id:
            inviter = ctx.guild.get_member(int(inviter_id))
            if inviter:
                embed.add_field(
                    name="Invited By",
                    value=f"{inviter.mention}\nUser ID: `{inviter_id}`",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Invited By",
                    value=f"User ID: `{inviter_id}` (no longer in server)",
                    inline=False
                )
        else:
            embed.add_field(
                name="Invited By",
                value="Unknown (joined before tracking was enabled or via vanity URL)",
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {member.id}")
        await ctx.send(embed=embed)
    
    @commands.command(name='setlogchannel')
    @commands.has_permissions(administrator=True)
    async def setlogchannel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for member join/leave logs"""
        if channel is None:
            channel = ctx.channel
        
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            config['settings']['log_channel_id'] = str(channel.id)
            
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
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
