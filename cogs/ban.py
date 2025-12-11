import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class Ban(commands.Cog):
    """Ban/Kick system for moderation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bans_file = 'bans.json'
        self.kicks_file = 'kicks.json'
        self.bans = self.load_data(self.bans_file)
        self.kicks = self.load_data(self.kicks_file)
    
    def load_data(self, filename):
        """Load data from file"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_data(self, data, filename):
        """Save data to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving {filename}: {e}")
    
    def record_ban(self, guild_id, user_id, moderator_id, reason):
        """Record a ban action"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.bans:
            self.bans[guild_key] = {}
        
        if user_key not in self.bans[guild_key]:
            self.bans[guild_key][user_key] = []
        
        ban_data = {
            'reason': reason,
            'moderator_id': str(moderator_id),
            'timestamp': datetime.utcnow().isoformat(),
            'ban_id': len(self.bans[guild_key][user_key]) + 1
        }
        
        self.bans[guild_key][user_key].append(ban_data)
        self.save_data(self.bans, self.bans_file)
        return ban_data
    
    def record_kick(self, guild_id, user_id, moderator_id, reason):
        """Record a kick action"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.kicks:
            self.kicks[guild_key] = {}
        
        if user_key not in self.kicks[guild_key]:
            self.kicks[guild_key][user_key] = []
        
        kick_data = {
            'reason': reason,
            'moderator_id': str(moderator_id),
            'timestamp': datetime.utcnow().isoformat(),
            'kick_id': len(self.kicks[guild_key][user_key]) + 1
        }
        
        self.kicks[guild_key][user_key].append(kick_data)
        self.save_data(self.kicks, self.kicks_file)
        return kick_data
    
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        # Can't kick bots
        if member.bot:
            await ctx.send("❌ You cannot kick bots!")
            return
        
        # Can't kick yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot kick yourself!")
            return
        
        # Can't kick server owner
        if member == ctx.guild.owner:
            await ctx.send("❌ You cannot kick the server owner!")
            return
        
        # Check role hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot kick someone with a higher or equal role!")
            return
        
        # Check if bot can kick
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I cannot kick someone with a higher or equal role than me!")
            return
        
        try:
            # Try to DM the user before kicking
            try:
                dm_embed = discord.Embed(
                    title=f"👢 You were kicked from {ctx.guild.name}",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.set_footer(text="You can rejoin with a new invite link.")
                
                await member.send(embed=dm_embed)
            except:
                pass
            
            # Kick the member
            await member.kick(reason=f"{reason} | By {ctx.author}")
            
            # Record the kick
            kick_data = self.record_kick(ctx.guild.id, member.id, ctx.author.id, reason)
            
            # Create embed
            embed = discord.Embed(
                title="👢 User Kicked",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Kick ID: {kick_data['kick_id']}")
            
            await ctx.send(embed=embed)
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        # Can't ban bots
        if member.bot:
            await ctx.send("❌ You cannot ban bots!")
            return
        
        # Can't ban yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot ban yourself!")
            return
        
        # Can't ban server owner
        if member == ctx.guild.owner:
            await ctx.send("❌ You cannot ban the server owner!")
            return
        
        # Check role hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot ban someone with a higher or equal role!")
            return
        
        # Check if bot can ban
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I cannot ban someone with a higher or equal role than me!")
            return
        
        try:
            # Try to DM the user before banning
            try:
                dm_embed = discord.Embed(
                    title=f"🔨 You were banned from {ctx.guild.name}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.set_footer(text="You may appeal this ban by contacting the server administrators.")
                
                await member.send(embed=dm_embed)
            except:
                pass
            
            # Ban the member
            await member.ban(reason=f"{reason} | By {ctx.author}", delete_message_days=1)
            
            # Record the ban
            ban_data = self.record_ban(ctx.guild.id, member.id, ctx.author.id, reason)
            
            # Create embed
            embed = discord.Embed(
                title="🔨 User Banned",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Ban ID: {ban_data['ban_id']}")
            
            await ctx.send(embed=embed)
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str, *, reason: str = "No reason provided"):
        """Unban a user by their ID"""
        try:
            user_id = int(user_id)
        except:
            await ctx.send("❌ Invalid user ID! Please provide a valid Discord user ID.")
            return
        
        try:
            # Get the user object
            user = await self.bot.fetch_user(user_id)
            
            # Try to unban
            await ctx.guild.unban(user, reason=f"{reason} | By {ctx.author}")
            
            # Create embed
            embed = discord.Embed(
                title="✅ User Unbanned",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await ctx.send(embed=embed)
        
        except discord.NotFound:
            await ctx.send("❌ This user is not banned!")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban users!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='bans', aliases=['banlist'])
    @commands.has_permissions(ban_members=True)
    async def bans(self, ctx):
        """List all banned users"""
        try:
            bans = [entry async for entry in ctx.guild.bans(limit=None)]
            
            if not bans:
                await ctx.send("✅ No users are currently banned!")
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"🔨 Ban List for {ctx.guild.name}",
                description=f"Total bans: **{len(bans)}**",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            # Show first 10 bans
            ban_list = []
            for i, ban_entry in enumerate(bans[:10]):
                user = ban_entry.user
                reason = ban_entry.reason or "No reason provided"
                ban_list.append(f"**{i+1}.** {user} (`{user.id}`)\n└ Reason: {reason}")
            
            embed.description = "\n\n".join(ban_list)
            
            if len(bans) > 10:
                embed.set_footer(text=f"Showing 10 of {len(bans)} bans")
            
            await ctx.send(embed=embed)
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view the ban list!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='softban')
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Softban a user (ban and immediately unban to delete messages)"""
        # Can't softban bots
        if member.bot:
            await ctx.send("❌ You cannot softban bots!")
            return
        
        # Can't softban yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot softban yourself!")
            return
        
        # Can't softban server owner
        if member == ctx.guild.owner:
            await ctx.send("❌ You cannot softban the server owner!")
            return
        
        # Check role hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot softban someone with a higher or equal role!")
            return
        
        # Check if bot can ban
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I cannot softban someone with a higher or equal role than me!")
            return
        
        try:
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=f"⚠️ You were softbanned from {ctx.guild.name}",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.set_footer(text="Your messages were deleted but you can rejoin with a new invite.")
                
                await member.send(embed=dm_embed)
            except:
                pass
            
            # Ban and immediately unban
            await member.ban(reason=f"Softban: {reason} | By {ctx.author}", delete_message_days=7)
            await ctx.guild.unban(member, reason=f"Softban (auto-unban) | By {ctx.author}")
            
            # Create embed
            embed = discord.Embed(
                title="⚡ User Softbanned",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text="Messages deleted • User can rejoin")
            
            await ctx.send(embed=embed)
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to softban this user!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='kicks', aliases=['kickhistory'])
    @commands.has_permissions(kick_members=True)
    async def kickhistory(self, ctx, *, user_id: str = None):
        """View kick history for a user"""
        if user_id is None:
            await ctx.send("❌ Please provide a user ID! Usage: `>kicks <user_id>`")
            return
        
        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
        except:
            await ctx.send("❌ Invalid user ID!")
            return
        
        guild_key = str(ctx.guild.id)
        user_key = str(user_id)
        
        kick_history = []
        if guild_key in self.kicks and user_key in self.kicks[guild_key]:
            kick_history = self.kicks[guild_key][user_key]
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 Kick History for {user}",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        if not kick_history:
            embed.description = "No kicks recorded for this user."
        else:
            embed.description = f"Total kicks: **{len(kick_history)}**"
            
            # Show last 5 kicks
            for kick in kick_history[-5:]:
                moderator = ctx.guild.get_member(int(kick['moderator_id']))
                mod_name = moderator.mention if moderator else f"ID: {kick['moderator_id']}"
                
                timestamp = datetime.fromisoformat(kick['timestamp'])
                
                embed.add_field(
                    name=f"👢 Kick #{kick['kick_id']}",
                    value=f"**Reason:** {kick['reason']}\n**Moderator:** {mod_name}\n**Date:** <t:{int(timestamp.timestamp())}:R>",
                    inline=False
                )
        
        embed.set_footer(text=f"User ID: {user_id}")
        await ctx.send(embed=embed)
    
    # Error handlers
    @kick.error
    @ban.error
    @unban.error
    @softban.error
    async def ban_kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            perm_name = "Ban Members" if "ban" in ctx.command.name else "Kick Members"
            await ctx.send(f"❌ You need '{perm_name}' permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Usage: `{ctx.prefix}{ctx.command.name} @member [reason]`")

async def setup(bot):
    await bot.add_cog(Ban(bot))
    print('Ban cog loaded successfully!')
