import discord
from discord.ext import commands
import sys
import os
import asyncio

class Reboot(commands.Cog):
    """Bot restart/reboot system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='reboot', aliases=['restart'])
    @commands.has_permissions(administrator=True)
    async def reboot(self, ctx):
        """Restart the entire bot (Administrator only)"""
        
        # Create confirmation embed
        embed = discord.Embed(
            title="🔄 Bot Restart",
            description="Are you sure you want to restart the bot?\n\nThis will:\n• Disconnect the bot\n• Reload all cogs\n• Reconnect to Discord\n\n**The bot will be offline for a few seconds.**",
            color=discord.Color.orange()
        )
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
        
        msg = await ctx.send(embed=embed)
        
        # Add reactions
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == msg.id
            )
        
        try:
            # Wait for reaction (30 second timeout)
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # User confirmed restart
                restart_embed = discord.Embed(
                    title="🔄 Restarting Bot...",
                    description="The bot is restarting. Please wait...",
                    color=discord.Color.blue()
                )
                await msg.edit(embed=restart_embed)
                
                # Log the restart
                print(f"\n{'='*50}")
                print(f"Bot restart initiated by {ctx.author} ({ctx.author.id})")
                print(f"Time: {discord.utils.utcnow()}")
                print(f"{'='*50}\n")
                
                # Close the bot and restart
                await asyncio.sleep(1)
                await self.bot.close()
                
                # Restart the bot process
                os.execv(sys.executable, ['python'] + sys.argv)
            
            else:
                # User cancelled
                cancel_embed = discord.Embed(
                    title="❌ Restart Cancelled",
                    description="Bot restart has been cancelled.",
                    color=discord.Color.red()
                )
                await msg.edit(embed=cancel_embed)
        
        except asyncio.TimeoutError:
            # Timeout - no reaction received
            timeout_embed = discord.Embed(
                title="⏱️ Restart Timed Out",
                description="No response received. Restart cancelled.",
                color=discord.Color.red()
            )
            await msg.edit(embed=timeout_embed)
    
    @commands.command(name='shutdown')
    @commands.has_permissions(administrator=True)
    async def shutdown(self, ctx):
        """Shutdown the bot completely (Administrator only)"""
        
        # Create confirmation embed
        embed = discord.Embed(
            title="⚠️ Bot Shutdown",
            description="Are you sure you want to shutdown the bot?\n\n**This will completely stop the bot until manually restarted.**",
            color=discord.Color.red()
        )
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
        
        msg = await ctx.send(embed=embed)
        
        # Add reactions
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author 
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == msg.id
            )
        
        try:
            # Wait for reaction (30 second timeout)
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # User confirmed shutdown
                shutdown_embed = discord.Embed(
                    title="🛑 Shutting Down...",
                    description="Bot is shutting down. Goodbye! 👋",
                    color=discord.Color.dark_red()
                )
                await msg.edit(embed=shutdown_embed)
                
                # Log the shutdown
                print(f"\n{'='*50}")
                print(f"Bot shutdown initiated by {ctx.author} ({ctx.author.id})")
                print(f"Time: {discord.utils.utcnow()}")
                print(f"{'='*50}\n")
                
                await asyncio.sleep(1)
                await self.bot.close()
                sys.exit(0)
            
            else:
                # User cancelled
                cancel_embed = discord.Embed(
                    title="❌ Shutdown Cancelled",
                    description="Bot shutdown has been cancelled.",
                    color=discord.Color.green()
                )
                await msg.edit(embed=cancel_embed)
        
        except asyncio.TimeoutError:
            # Timeout - no reaction received
            timeout_embed = discord.Embed(
                title="⏱️ Shutdown Timed Out",
                description="No response received. Shutdown cancelled.",
                color=discord.Color.red()
            )
            await msg.edit(embed=timeout_embed)
    
    @commands.command(name='reload')
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx, *, cog: str = None):
        """Reload a specific cog or all cogs (Administrator only)
        
        Usage: 
        >reload commands - Reload the commands cog
        >reload all - Reload all cogs
        >reload - Shows list of cogs
        """
        
        if cog is None:
            # Show list of available cogs
            cog_list = []
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and not filename.startswith('__'):
                    cog_list.append(f"`{filename[:-3]}`")
            
            embed = discord.Embed(
                title="🔄 Reload Cogs",
                description="Use `>reload <cog>` to reload a specific cog\nUse `>reload all` to reload all cogs",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Available Cogs",
                value=", ".join(cog_list) if cog_list else "No cogs found",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        if cog.lower() == 'all':
            # Reload all cogs
            reloaded = []
            failed = []
            
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and not filename.startswith('__'):
                    cog_name = filename[:-3]
                    try:
                        await self.bot.reload_extension(f'cogs.{cog_name}')
                        reloaded.append(cog_name)
                    except Exception as e:
                        failed.append(f"{cog_name}: {str(e)[:50]}")
            
            embed = discord.Embed(
                title="🔄 Reload All Cogs",
                color=discord.Color.green() if not failed else discord.Color.orange()
            )
            
            if reloaded:
                embed.add_field(
                    name="✅ Successfully Reloaded",
                    value=", ".join([f"`{c}`" for c in reloaded]),
                    inline=False
                )
            
            if failed:
                embed.add_field(
                    name="❌ Failed to Reload",
                    value="\n".join(failed),
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        else:
            # Reload specific cog
            try:
                await self.bot.reload_extension(f'cogs.{cog}')
                
                embed = discord.Embed(
                    title="✅ Cog Reloaded",
                    description=f"Successfully reloaded `{cog}` cog!",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            
            except commands.ExtensionNotFound:
                await ctx.send(f"❌ Cog `{cog}` not found!")
            except commands.ExtensionNotLoaded:
                await ctx.send(f"❌ Cog `{cog}` is not loaded!")
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Reload Failed",
                    description=f"Failed to reload `{cog}`",
                    color=discord.Color.red()
                )
                embed.add_field(name="Error", value=f"```{str(e)[:500]}```", inline=False)
                await ctx.send(embed=embed)
    
    @commands.command(name='load')
    @commands.has_permissions(administrator=True)
    async def load(self, ctx, *, cog: str):
        """Load a cog (Administrator only)"""
        try:
            await self.bot.load_extension(f'cogs.{cog}')
            
            embed = discord.Embed(
                title="✅ Cog Loaded",
                description=f"Successfully loaded `{cog}` cog!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"❌ Cog `{cog}` is already loaded!")
        except commands.ExtensionNotFound:
            await ctx.send(f"❌ Cog `{cog}` not found!")
        except Exception as e:
            embed = discord.Embed(
                title="❌ Load Failed",
                description=f"Failed to load `{cog}`",
                color=discord.Color.red()
            )
            embed.add_field(name="Error", value=f"```{str(e)[:500]}```", inline=False)
            await ctx.send(embed=embed)
    
    @commands.command(name='unload')
    @commands.has_permissions(administrator=True)
    async def unload(self, ctx, *, cog: str):
        """Unload a cog (Administrator only)"""
        # Don't allow unloading the reboot cog
        if cog.lower() == 'reboot':
            await ctx.send("❌ Cannot unload the reboot cog!")
            return
        
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
            
            embed = discord.Embed(
                title="✅ Cog Unloaded",
                description=f"Successfully unloaded `{cog}` cog!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        
        except commands.ExtensionNotLoaded:
            await ctx.send(f"❌ Cog `{cog}` is not loaded!")
        except Exception as e:
            embed = discord.Embed(
                title="❌ Unload Failed",
                description=f"Failed to unload `{cog}`",
                color=discord.Color.red()
            )
            embed.add_field(name="Error", value=f"```{str(e)[:500]}```", inline=False)
            await ctx.send(embed=embed)
    
    @commands.command(name='cogs')
    @commands.has_permissions(administrator=True)
    async def cogs_list(self, ctx):
        """List all loaded cogs (Administrator only)"""
        
        loaded_cogs = [cog for cog in self.bot.cogs.keys()]
        
        # Get all available cogs in the folder
        available_cogs = []
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                available_cogs.append(filename[:-3])
        
        # Find unloaded cogs
        unloaded_cogs = [cog for cog in available_cogs if cog.title() not in loaded_cogs]
        
        embed = discord.Embed(
            title="📦 Bot Cogs",
            color=discord.Color.blue()
        )
        
        if loaded_cogs:
            embed.add_field(
                name=f"✅ Loaded Cogs ({len(loaded_cogs)})",
                value=", ".join([f"`{cog}`" for cog in sorted(loaded_cogs)]),
                inline=False
            )
        
        if unloaded_cogs:
            embed.add_field(
                name=f"❌ Unloaded Cogs ({len(unloaded_cogs)})",
                value=", ".join([f"`{cog}`" for cog in sorted(unloaded_cogs)]),
                inline=False
            )
        
        embed.set_footer(text="Use >load/unload/reload to manage cogs")
        
        await ctx.send(embed=embed)
    
    # Error handlers
    @reboot.error
    @shutdown.error
    @reload.error
    @load.error
    @unload.error
    @cogs_list.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")

async def setup(bot):
    await bot.add_cog(Reboot(bot))
    print('Reboot/reload system loaded successfully!')