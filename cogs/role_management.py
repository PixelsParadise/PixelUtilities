import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class RoleManagement(commands.Cog):
    """Advanced role management with hierarchy checks"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'
    
    def load_config(self):
        """Load config file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def can_manage_role(self, ctx, target_role):
        """Check if user and bot can manage the target role"""
        # Bot must be higher than the role
        if target_role >= ctx.guild.me.top_role:
            return False, f"❌ I cannot manage {target_role.mention} - it's higher than or equal to my highest role ({ctx.guild.me.top_role.mention})!"
        
        # User must be higher than the role (unless they're the owner)
        if ctx.author != ctx.guild.owner:
            if target_role >= ctx.author.top_role:
                return False, f"❌ You cannot manage {target_role.mention} - it's higher than or equal to your highest role ({ctx.author.top_role.mention})!"
        
        # Can't manage @everyone
        if target_role == ctx.guild.default_role:
            return False, "❌ You cannot manage the @everyone role!"
        
        # Can't manage managed roles (bot roles, boosts, etc)
        if target_role.managed:
            return False, f"❌ {target_role.mention} is a managed role (bot/integration role) and cannot be assigned manually!"
        
        return True, None
    
    def get_role_info(self, role):
        """Get detailed information about a role"""
        # Count members with this role
        member_count = len(role.members)
        
        # Get permissions
        perms = role.permissions
        important_perms = []
        
        if perms.administrator:
            important_perms.append("👑 Administrator")
        if perms.manage_guild:
            important_perms.append("⚙️ Manage Server")
        if perms.manage_roles:
            important_perms.append("🎭 Manage Roles")
        if perms.manage_channels:
            important_perms.append("📝 Manage Channels")
        if perms.kick_members:
            important_perms.append("👢 Kick Members")
        if perms.ban_members:
            important_perms.append("🔨 Ban Members")
        if perms.mention_everyone:
            important_perms.append("📢 Mention Everyone")
        
        return {
            'member_count': member_count,
            'important_perms': important_perms,
            'is_hoisted': role.hoist,
            'is_mentionable': role.mentionable,
            'is_managed': role.managed,
            'position': role.position,
            'created_at': role.created_at
        }
    
    @commands.command(name='giverole', aliases=['addrole', 'ar'])
    @commands.has_permissions(manage_roles=True)
    async def giverole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Give a role to a member (with hierarchy checks)
        
        Usage: >giverole @user @role
        """
        # Check if user can manage this role
        can_manage, error = self.can_manage_role(ctx, role)
        if not can_manage:
            await ctx.send(error)
            return
        
        # Check if member already has the role
        if role in member.roles:
            await ctx.send(f"❌ {member.mention} already has {role.mention}!")
            return
        
        # Check if we're trying to give a role to a bot (optional safety)
        if member.bot and not role.managed:
            confirm_embed = discord.Embed(
                title="⚠️ Warning",
                description=f"You're about to give {role.mention} to a bot ({member.mention}).\nAre you sure?",
                color=discord.Color.orange()
            )
            msg = await ctx.send(embed=confirm_embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                if str(reaction.emoji) == "❌":
                    await msg.delete()
                    await ctx.send("❌ Cancelled.")
                    return
            except:
                await msg.delete()
                await ctx.send("⏱️ Timed out. Cancelled.")
                return
        
        try:
            await member.add_roles(role, reason=f"Role given by {ctx.author} ({ctx.author.id})")
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Role Given",
                description=f"Successfully gave {role.mention} to {member.mention}",
                color=role.color if role.color != discord.Color.default() else discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="👤 User", value=member.mention, inline=True)
            embed.add_field(name="🎭 Role", value=role.mention, inline=True)
            embed.add_field(name="👮 By", value=ctx.author.mention, inline=True)
            
            # Show role stats
            role_info = self.get_role_info(role)
            embed.add_field(
                name="📊 Role Stats",
                value=f"**Members:** {role_info['member_count']}\n**Position:** #{role_info['position']}",
                inline=True
            )
            
            embed.set_footer(text=f"Role ID: {role.id}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to give role: {e}")
    
    @commands.command(name='takerole', aliases=['removerole', 'rr'])
    @commands.has_permissions(manage_roles=True)
    async def takerole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Remove a role from a member (with hierarchy checks)
        
        Usage: >takerole @user @role
        """
        # Check if user can manage this role
        can_manage, error = self.can_manage_role(ctx, role)
        if not can_manage:
            await ctx.send(error)
            return
        
        # Check if member has the role
        if role not in member.roles:
            await ctx.send(f"❌ {member.mention} doesn't have {role.mention}!")
            return
        
        try:
            await member.remove_roles(role, reason=f"Role removed by {ctx.author} ({ctx.author.id})")
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Role Removed",
                description=f"Successfully removed {role.mention} from {member.mention}",
                color=role.color if role.color != discord.Color.default() else discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="👤 User", value=member.mention, inline=True)
            embed.add_field(name="🎭 Role", value=role.mention, inline=True)
            embed.add_field(name="👮 By", value=ctx.author.mention, inline=True)
            
            embed.set_footer(text=f"Role ID: {role.id}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to remove role: {e}")
    
    @commands.command(name='roleinfo', aliases=['ri'])
    async def roleinfo(self, ctx, *, role: discord.Role):
        """View detailed information about a role
        
        Usage: >roleinfo @role
        """
        role_info = self.get_role_info(role)
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 Role Information",
            description=f"**{role.name}**",
            color=role.color if role.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Basic info
        embed.add_field(
            name="📋 Basic Info",
            value=(
                f"**Name:** {role.name}\n"
                f"**ID:** `{role.id}`\n"
                f"**Mention:** {role.mention}\n"
                f"**Color:** {str(role.color)}"
            ),
            inline=False
        )
        
        # Position and hierarchy
        total_roles = len(ctx.guild.roles)
        embed.add_field(
            name="📊 Hierarchy",
            value=(
                f"**Position:** #{role.position} / {total_roles}\n"
                f"**Hoisted:** {'✅ Yes' if role_info['is_hoisted'] else '❌ No'}\n"
                f"**Mentionable:** {'✅ Yes' if role_info['is_mentionable'] else '❌ No'}\n"
                f"**Managed:** {'✅ Yes (Bot/Integration)' if role_info['is_managed'] else '❌ No'}"
            ),
            inline=True
        )
        
        # Members
        embed.add_field(
            name="👥 Members",
            value=f"**{role_info['member_count']}** member(s) have this role",
            inline=True
        )
        
        # Important permissions
        if role_info['important_perms']:
            perms_text = "\n".join(role_info['important_perms'])
            embed.add_field(
                name="🔑 Key Permissions",
                value=perms_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🔑 Key Permissions",
                value="*No special permissions*",
                inline=False
            )
        
        # Created date
        embed.add_field(
            name="📅 Created",
            value=f"<t:{int(role_info['created_at'].timestamp())}:F>\n<t:{int(role_info['created_at'].timestamp())}:R>",
            inline=False
        )
        
        # Hierarchy warnings
        warnings = []
        if role >= ctx.guild.me.top_role:
            warnings.append("⚠️ This role is higher than the bot's highest role")
        if not ctx.author == ctx.guild.owner and role >= ctx.author.top_role:
            warnings.append("⚠️ This role is higher than or equal to your highest role")
        if role_info['is_managed']:
            warnings.append("⚠️ This is a managed role and cannot be manually assigned")
        
        if warnings:
            embed.add_field(
                name="⚠️ Warnings",
                value="\n".join(warnings),
                inline=False
            )
        
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='inrole', aliases=['membersinrole', 'whohave'])
    async def inrole(self, ctx, *, role: discord.Role):
        """List all members with a specific role
        
        Usage: >inrole @role
        """
        members = role.members
        
        if not members:
            await ctx.send(f"❌ No members have {role.mention}!")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"👥 Members with {role.name}",
            description=f"**{len(members)}** member(s) have this role",
            color=role.color if role.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Sort members by join date
        sorted_members = sorted(members, key=lambda m: m.joined_at or datetime.utcnow())
        
        # Show first 20 members
        member_list = []
        for member in sorted_members[:20]:
            # Show join date
            joined = f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown"
            member_list.append(f"• {member.mention} - Joined {joined}")
        
        embed.description = "\n".join(member_list)
        
        if len(members) > 20:
            embed.set_footer(text=f"Showing 20 of {len(members)} members | Role ID: {role.id}")
        else:
            embed.set_footer(text=f"Role ID: {role.id}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='roleall', aliases=['giveroleall'])
    @commands.has_permissions(administrator=True)
    async def roleall(self, ctx, *, role: discord.Role):
        """Give a role to ALL members (requires administrator)
        
        Usage: >roleall @role
        """
        # Check if user can manage this role
        can_manage, error = self.can_manage_role(ctx, role)
        if not can_manage:
            await ctx.send(error)
            return
        
        # Get members who don't have the role
        members_without_role = [m for m in ctx.guild.members if role not in m.roles and not m.bot]
        
        if not members_without_role:
            await ctx.send(f"✅ All members already have {role.mention}!")
            return
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚠️ Mass Role Assignment",
            description=(
                f"This will give {role.mention} to **{len(members_without_role)}** member(s).\n\n"
                f"**This action may take a while!**\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=discord.Color.orange()
        )
        
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await msg.edit(embed=discord.Embed(
                    title="❌ Cancelled",
                    description="Mass role assignment cancelled.",
                    color=discord.Color.red()
                ))
                return
            
            # Start assigning roles
            progress_embed = discord.Embed(
                title="⏳ Assigning Roles...",
                description=f"Progress: 0/{len(members_without_role)}",
                color=discord.Color.blue()
            )
            await msg.edit(embed=progress_embed)
            
            success_count = 0
            failed_count = 0
            
            for i, member in enumerate(members_without_role):
                try:
                    await member.add_roles(role, reason=f"Mass role assignment by {ctx.author}")
                    success_count += 1
                except:
                    failed_count += 1
                
                # Update progress every 10 members
                if (i + 1) % 10 == 0 or i == len(members_without_role) - 1:
                    progress_embed.description = f"Progress: {i + 1}/{len(members_without_role)}"
                    await msg.edit(embed=progress_embed)
            
            # Final result
            result_embed = discord.Embed(
                title="✅ Mass Role Assignment Complete",
                description=f"Finished assigning {role.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            result_embed.add_field(name="✅ Success", value=str(success_count), inline=True)
            result_embed.add_field(name="❌ Failed", value=str(failed_count), inline=True)
            result_embed.add_field(name="👥 Total", value=str(len(members_without_role)), inline=True)
            result_embed.set_footer(text=f"Assigned by {ctx.author}")
            
            await msg.edit(embed=result_embed)
            
        except:
            await msg.edit(embed=discord.Embed(
                title="⏱️ Timed Out",
                description="No response received. Mass role assignment cancelled.",
                color=discord.Color.red()
            ))
    
    @commands.command(name='removeroleall', aliases=['takeroleall'])
    @commands.has_permissions(administrator=True)
    async def removeroleall(self, ctx, *, role: discord.Role):
        """Remove a role from ALL members (requires administrator)
        
        Usage: >removeroleall @role
        """
        # Check if user can manage this role
        can_manage, error = self.can_manage_role(ctx, role)
        if not can_manage:
            await ctx.send(error)
            return
        
        # Get members who have the role
        members_with_role = [m for m in role.members if not m.bot]
        
        if not members_with_role:
            await ctx.send(f"✅ No members have {role.mention}!")
            return
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚠️ Mass Role Removal",
            description=(
                f"This will remove {role.mention} from **{len(members_with_role)}** member(s).\n\n"
                f"**This action may take a while!**\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=discord.Color.orange()
        )
        
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await msg.edit(embed=discord.Embed(
                    title="❌ Cancelled",
                    description="Mass role removal cancelled.",
                    color=discord.Color.red()
                ))
                return
            
            # Start removing roles
            progress_embed = discord.Embed(
                title="⏳ Removing Roles...",
                description=f"Progress: 0/{len(members_with_role)}",
                color=discord.Color.blue()
            )
            await msg.edit(embed=progress_embed)
            
            success_count = 0
            failed_count = 0
            
            for i, member in enumerate(members_with_role):
                try:
                    await member.remove_roles(role, reason=f"Mass role removal by {ctx.author}")
                    success_count += 1
                except:
                    failed_count += 1
                
                # Update progress every 10 members
                if (i + 1) % 10 == 0 or i == len(members_with_role) - 1:
                    progress_embed.description = f"Progress: {i + 1}/{len(members_with_role)}"
                    await msg.edit(embed=progress_embed)
            
            # Final result
            result_embed = discord.Embed(
                title="✅ Mass Role Removal Complete",
                description=f"Finished removing {role.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            result_embed.add_field(name="✅ Success", value=str(success_count), inline=True)
            result_embed.add_field(name="❌ Failed", value=str(failed_count), inline=True)
            result_embed.add_field(name="👥 Total", value=str(len(members_with_role)), inline=True)
            result_embed.set_footer(text=f"Removed by {ctx.author}")
            
            await msg.edit(embed=result_embed)
            
        except:
            await msg.edit(embed=discord.Embed(
                title="⏱️ Timed Out",
                description="No response received. Mass role removal cancelled.",
                color=discord.Color.red()
            ))
    
    @commands.command(name='createrole', aliases=['makerole'])
    @commands.has_permissions(manage_roles=True)
    async def createrole(self, ctx, name: str, color: str = None, *, hoist: bool = False):
        """Create a new role
        
        Usage: >createrole "Role Name" #FF5733 True
               >createrole "Role Name"
        
        Color formats: #FF5733, 0xFF5733, FF5733, or red/blue/green
        """
        # Parse color
        role_color = discord.Color.default()
        if color:
            try:
                # Remove # if present
                if color.startswith('#'):
                    color = color[1:]
                
                # Try common color names
                color_map = {
                    'red': discord.Color.red(),
                    'blue': discord.Color.blue(),
                    'green': discord.Color.green(),
                    'yellow': discord.Color.yellow(),
                    'orange': discord.Color.orange(),
                    'purple': discord.Color.purple(),
                    'gold': discord.Color.gold(),
                    'teal': discord.Color.teal(),
                }
                
                if color.lower() in color_map:
                    role_color = color_map[color.lower()]
                else:
                    # Try hex color
                    role_color = discord.Color(int(color, 16))
            except:
                await ctx.send("❌ Invalid color format! Use hex (#FF5733) or color name (red, blue, etc)")
                return
        
        try:
            # Create the role
            role = await ctx.guild.create_role(
                name=name,
                color=role_color,
                hoist=hoist,
                reason=f"Role created by {ctx.author} ({ctx.author.id})"
            )
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Role Created",
                description=f"Successfully created {role.mention}",
                color=role.color if role.color != discord.Color.default() else discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="🎭 Name", value=role.name, inline=True)
            embed.add_field(name="🎨 Color", value=str(role.color), inline=True)
            embed.add_field(name="📊 Hoisted", value="✅ Yes" if hoist else "❌ No", inline=True)
            embed.add_field(name="📍 Position", value=f"#{role.position}", inline=True)
            embed.add_field(name="🆔 ID", value=f"`{role.id}`", inline=True)
            
            embed.set_footer(text=f"Created by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to create role: {e}")
    
    @commands.command(name='deleterole')
    @commands.has_permissions(manage_roles=True)
    async def deleterole(self, ctx, *, role: discord.Role):
        """Delete a role (with confirmation)
        
        Usage: >deleterole @role
        """
        # Check if user can manage this role
        can_manage, error = self.can_manage_role(ctx, role)
        if not can_manage:
            await ctx.send(error)
            return
        
        # Get role info for confirmation
        role_info = self.get_role_info(role)
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚠️ Delete Role",
            description=(
                f"Are you sure you want to delete {role.mention}?\n\n"
                f"**Members with this role:** {role_info['member_count']}\n"
                f"**This action cannot be undone!**\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=discord.Color.red()
        )
        
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await msg.edit(embed=discord.Embed(
                    title="❌ Cancelled",
                    description="Role deletion cancelled.",
                    color=discord.Color.red()
                ))
                return
            
            # Delete the role
            role_name = role.name
            role_id = role.id
            
            await role.delete(reason=f"Role deleted by {ctx.author} ({ctx.author.id})")
            
            # Create success embed
            result_embed = discord.Embed(
                title="✅ Role Deleted",
                description=f"Successfully deleted role: **{role_name}**",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            result_embed.add_field(name="🆔 Role ID", value=f"`{role_id}`", inline=True)
            result_embed.add_field(name="👥 Members Affected", value=str(role_info['member_count']), inline=True)
            result_embed.set_footer(text=f"Deleted by {ctx.author}")
            
            await msg.edit(embed=result_embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to delete role: {e}")
        except:
            await msg.edit(embed=discord.Embed(
                title="⏱️ Timed Out",
                description="No response received. Role deletion cancelled.",
                color=discord.Color.red()
            ))
    
    @commands.command(name='rolelist', aliases=['listroles'])
    async def rolelist(self, ctx):
        """List all roles in the server with hierarchy
        
        Usage: >rolelist
        """
        # Get all roles (excluding @everyone)
        roles = [role for role in ctx.guild.roles if role != ctx.guild.default_role]
        
        # Sort by position (highest first)
        roles.sort(key=lambda r: r.position, reverse=True)
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 Server Roles - {ctx.guild.name}",
            description=f"**{len(roles)}** roles (excluding @everyone)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Build role list
        role_list = []
        for i, role in enumerate(roles[:30]):  # Show max 30
            # Role info
            member_count = len(role.members)
            
            # Indicators
            indicators = []
            if role.managed:
                indicators.append("🤖")
            if role.hoist:
                indicators.append("📌")
            if role.mentionable:
                indicators.append("💬")
            
            indicator_str = "".join(indicators) if indicators else ""
            
            # Position indicator for bot/user roles
            can_manage = role < ctx.guild.me.top_role
            pos_indicator = "✅" if can_manage else "⚠️"
            
            role_list.append(
                f"{pos_indicator} `#{role.position:3d}` {role.mention} {indicator_str}\n"
                f"        └ {member_count} member(s)"
            )
        
        embed.description = "\n".join(role_list)
        
        if len(roles) > 30:
            embed.set_footer(text=f"Showing 30 of {len(roles)} roles | ✅ = Bot can manage, ⚠️ = Bot cannot manage")
        else:
            embed.set_footer(text="✅ = Bot can manage, ⚠️ = Bot cannot manage | 🤖 = Bot role, 📌 = Hoisted, 💬 = Mentionable")
        
        # Add legend
        embed.add_field(
            name="📋 Legend",
            value=(
                "✅ = Bot can manage this role\n"
                "⚠️ = Bot cannot manage (too high)\n"
                "🤖 = Managed by bot/integration\n"
                "📌 = Hoisted (displayed separately)\n"
                "💬 = Mentionable by everyone"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @giverole.error
    @takerole.error
    @roleinfo.error
    @inrole.error
    @createrole.error
    @deleterole.error
    @roleall.error
    @removeroleall.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            permission = "Administrator" if "administrator" in str(error).lower() else "Manage Roles"
            await ctx.send(f"❌ You need '{permission}' permission to use this command!")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send("❌ Role not found! Try mentioning the role or using quotes for role names with spaces.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{ctx.prefix}help {ctx.command.name}` for usage.")

# Import asyncio for mass role operations
import asyncio

async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
    print('Role management system with hierarchy checks loaded successfully!')