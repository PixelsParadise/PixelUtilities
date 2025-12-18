import discord
from discord.ext import commands
from datetime import datetime

class Slowmode(commands.Cog):
    """Channel slowmode management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def format_time(self, seconds):
        """Format seconds into human readable time"""
        if seconds == 0:
            return "Disabled"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0:
            parts.append(f"{secs}s")
        
        return " ".join(parts)
    
    def parse_time(self, time_str):
        """Parse time string like '5s', '1m', '2h' into seconds"""
        time_str = time_str.lower().strip()
        
        # If it's just a number, treat it as seconds
        if time_str.isdigit():
            return int(time_str)
        
        # Parse with unit
        try:
            if time_str.endswith('s'):
                return int(time_str[:-1])
            elif time_str.endswith('m'):
                return int(time_str[:-1]) * 60
            elif time_str.endswith('h'):
                return int(time_str[:-1]) * 3600
            else:
                return int(time_str)
        except:
            return None
    
    @commands.command(name='slowmode', aliases=['sm', 'slow'])
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, delay: str = None):
        """Set slowmode delay for the current channel
        
        Usage:
        >slowmode 5s - 5 seconds
        >slowmode 1m - 1 minute
        >slowmode 2h - 2 hours
        >slowmode 30 - 30 seconds
        >slowmode 0 - Disable slowmode
        >slowmode off - Disable slowmode
        >slowmode - Show current slowmode
        
        Max: 6 hours (21600 seconds)
        """
        
        # If no delay specified, show current slowmode
        if delay is None:
            current_delay = ctx.channel.slowmode_delay
            
            embed = discord.Embed(
                title=f"â±ï¸ Slowmode Status - #{ctx.channel.name}",
                color=discord.Color.blue()
            )
            
            if current_delay == 0:
                embed.description = "**Slowmode is currently disabled**"
                embed.color = discord.Color.green()
            else:
                embed.description = f"**Current slowmode:** {self.format_time(current_delay)}"
                embed.add_field(
                    name="Delay",
                    value=f"{current_delay} seconds",
                    inline=True
                )
            
            embed.set_footer(text=f"Use {ctx.prefix}slowmode <time> to change")
            await ctx.send(embed=embed)
            return
        
        # Handle "off" or "disable"
        if delay.lower() in ['off', 'disable', 'disabled', 'none']:
            delay_seconds = 0
        else:
            # Parse the time
            delay_seconds = self.parse_time(delay)
            
            if delay_seconds is None:
                await ctx.send(
                    "âŒ Invalid time format!\n\n"
                    "**Valid formats:**\n"
                    "• `5s` - 5 seconds\n"
                    "• `1m` - 1 minute\n"
                    "• `2h` - 2 hours\n"
                    "• `30` - 30 seconds\n"
                    "• `0` or `off` - Disable slowmode"
                )
                return
        
        # Validate delay
        if delay_seconds < 0:
            await ctx.send("âŒ Slowmode delay cannot be negative!")
            return
        
        if delay_seconds > 21600:  # Discord's max is 6 hours
            await ctx.send("âŒ Slowmode delay cannot exceed 6 hours (21600 seconds)!")
            return
        
        # Get old slowmode for comparison
        old_delay = ctx.channel.slowmode_delay
        
        try:
            # Set the slowmode
            await ctx.channel.edit(
                slowmode_delay=delay_seconds,
                reason=f"Slowmode changed by {ctx.author} ({ctx.author.id})"
            )
            
            # Create success embed
            if delay_seconds == 0:
                embed = discord.Embed(
                    title="âœ… Slowmode Disabled",
                    description=f"Slowmode has been disabled in {ctx.channel.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                if old_delay > 0:
                    embed.add_field(
                        name="Previous Delay",
                        value=self.format_time(old_delay),
                        inline=True
                    )
            else:
                embed = discord.Embed(
                    title="â±ï¸ Slowmode Updated",
                    description=f"Slowmode has been set in {ctx.channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="New Delay",
                    value=f"{self.format_time(delay_seconds)}\n({delay_seconds} seconds)",
                    inline=True
                )
                
                if old_delay > 0:
                    embed.add_field(
                        name="Previous Delay",
                        value=self.format_time(old_delay),
                        inline=True
                    )
                
                embed.add_field(
                    name="ℹ️ Info",
                    value=f"Users can send 1 message every {self.format_time(delay_seconds)}",
                    inline=False
                )
            
            embed.set_footer(text=f"Changed by {ctx.author}")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("âŒ I don't have permission to edit this channel!")
        except discord.HTTPException as e:
            await ctx.send(f"âŒ Failed to set slowmode: {e}")
    
    @commands.command(name='slowmodeall', aliases=['small'])
    @commands.has_permissions(manage_channels=True)
    async def slowmodeall(self, ctx, delay: str, category: discord.CategoryChannel = None):
        """Set slowmode for all channels in a category or server
        
        Usage:
        >slowmodeall 5s - Set 5s slowmode in all text channels
        >slowmodeall 1m CategoryName - Set 1m slowmode in all channels in a category
        """
        # Parse time
        if delay.lower() in ['off', 'disable', 'disabled', 'none']:
            delay_seconds = 0
        else:
            delay_seconds = self.parse_time(delay)
            
            if delay_seconds is None:
                await ctx.send("âŒ Invalid time format!")
                return
        
        if delay_seconds < 0 or delay_seconds > 21600:
            await ctx.send("âŒ Slowmode delay must be between 0 and 21600 seconds!")
            return
        
        # Get channels to update
        if category:
            channels = category.text_channels
            location = f"category **{category.name}**"
        else:
            channels = ctx.guild.text_channels
            location = "**all text channels**"
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="âš ï¸ Bulk Slowmode Change",
            description=f"This will set slowmode to **{self.format_time(delay_seconds)}** in {location}.\n\n**Channels affected:** {len(channels)}\n\nReact with âœ… to confirm or âŒ to cancel.",
            color=discord.Color.orange()
        )
        
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("âœ…")
        await msg.add_reaction("âŒ")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["âœ…", "âŒ"] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "âŒ":
                await msg.edit(embed=discord.Embed(
                    title="âŒ Cancelled",
                    description="Bulk slowmode change cancelled.",
                    color=discord.Color.red()
                ))
                return
            
            # Apply slowmode to all channels
            success_count = 0
            failed_count = 0
            
            progress_embed = discord.Embed(
                title="â³ Updating Channels...",
                description=f"Progress: 0/{len(channels)}",
                color=discord.Color.blue()
            )
            await msg.edit(embed=progress_embed)
            
            for i, channel in enumerate(channels):
                try:
                    await channel.edit(
                        slowmode_delay=delay_seconds,
                        reason=f"Bulk slowmode by {ctx.author}"
                    )
                    success_count += 1
                except:
                    failed_count += 1
                
                # Update progress every 5 channels
                if (i + 1) % 5 == 0 or i == len(channels) - 1:
                    progress_embed.description = f"Progress: {i + 1}/{len(channels)}"
                    await msg.edit(embed=progress_embed)
            
            # Final result
            result_embed = discord.Embed(
                title="âœ… Bulk Slowmode Complete",
                description=f"Slowmode set to **{self.format_time(delay_seconds)}** in {location}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            result_embed.add_field(name="âœ… Success", value=str(success_count), inline=True)
            result_embed.add_field(name="âŒ Failed", value=str(failed_count), inline=True)
            result_embed.set_footer(text=f"Changed by {ctx.author}")
            
            await msg.edit(embed=result_embed)
            
        except asyncio.TimeoutError:
            await msg.edit(embed=discord.Embed(
                title="â±ï¸ Timed Out",
                description="No response received. Bulk slowmode change cancelled.",
                color=discord.Color.red()
            ))
    
    # Error handlers
    @slowmode.error
    @slowmodeall.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("âŒ You need 'Manage Channels' permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"âŒ Missing required argument! Use `{ctx.prefix}help {ctx.command.name}` for usage.")

# Import asyncio for slowmodeall
import asyncio

async def setup(bot):
    await bot.add_cog(Slowmode(bot))
    print('Slowmode cog loaded successfully!')