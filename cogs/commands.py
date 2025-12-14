import discord
from discord.ext import commands
from datetime import datetime
import random
import aiohttp

class Commands(commands.Cog):
    """Basic commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx):
        """Responds with Pong and shows bot latency"""
        latency = round(self.bot.latency * 1000)  # Convert to milliseconds
        await ctx.send(f'🏓 Pong! 🏓 Latency: {latency}ms')

    @commands.command(name='hello')
    async def hello(self, ctx):
        """Says hello to the user"""
        await ctx.send(f'Hello {ctx.author.mention}!')

    @commands.command(name='echo')
    async def echo(self, ctx, *, message):
        """Repeats what you say"""
        await ctx.send(message)

    @commands.command(name='avatar', aliases=['av', 'pfp'])
    async def avatar(self, ctx, *, user: discord.User = None):
        """Get the avatar/profile picture of a user"""
        # If no user specified, use command author
        if user is None:
            user = ctx.author
        
        # Create embed
        embed = discord.Embed(
            title=f"🖼️ {user.display_name}'s Avatar",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Get avatar URL
        avatar_url = user.display_avatar.url
        
        # Set the image
        embed.set_image(url=avatar_url)
        
        # Add download links for different formats
        avatar_links = []
        
        # PNG format (always available)
        png_url = user.display_avatar.replace(format='png', size=4096).url
        avatar_links.append(f"[PNG]({png_url})")
        
        # JPG format
        jpg_url = user.display_avatar.replace(format='jpg', size=4096).url
        avatar_links.append(f"[JPG]({jpg_url})")
        
        # WEBP format
        webp_url = user.display_avatar.replace(format='webp', size=4096).url
        avatar_links.append(f"[WEBP]({webp_url})")
        
        # GIF format (only if animated)
        if user.display_avatar.is_animated():
            gif_url = user.display_avatar.replace(format='gif', size=4096).url
            avatar_links.append(f"[GIF]({gif_url})")
            embed.description = "🎬 Animated Avatar"
        
        embed.add_field(
            name="📥 Download Links (4096x4096)",
            value=" • ".join(avatar_links),
            inline=False
        )
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await ctx.send(embed=embed)

    @commands.command(name='serveravatar', aliases=['sav', 'servericon'])
    async def serveravatar(self, ctx):
        """Get the server's icon/avatar"""
        if ctx.guild.icon is None:
            await ctx.send("❌ This server doesn't have an icon!")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"🖼️ {ctx.guild.name}'s Icon",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Set the image
        embed.set_image(url=ctx.guild.icon.url)
        
        # Add download links for different formats
        icon_links = []
        
        # PNG format
        png_url = ctx.guild.icon.replace(format='png', size=4096).url
        icon_links.append(f"[PNG]({png_url})")
        
        # JPG format
        jpg_url = ctx.guild.icon.replace(format='jpg', size=4096).url
        icon_links.append(f"[JPG]({jpg_url})")
        
        # WEBP format
        webp_url = ctx.guild.icon.replace(format='webp', size=4096).url
        icon_links.append(f"[WEBP]({webp_url})")
        
        # GIF format (only if animated)
        if ctx.guild.icon.is_animated():
            gif_url = ctx.guild.icon.replace(format='gif', size=4096).url
            icon_links.append(f"[GIF]({gif_url})")
            embed.description = "🎬 Animated Icon"
        
        embed.add_field(
            name="📥 Download Links (4096x4096)",
            value=" • ".join(icon_links),
            inline=False
        )
        
        embed.set_footer(text=f"Server ID: {ctx.guild.id}")
        
        await ctx.send(embed=embed)

    @commands.command(name='banner')
    async def banner(self, ctx, *, user: discord.User = None):
        """Get the banner of a user (if they have one)"""
        if user is None:
            user = ctx.author
        
        # Fetch full user to get banner info
        user = await self.bot.fetch_user(user.id)
        
        if user.banner is None:
            await ctx.send(f"❌ {user.display_name} doesn't have a banner!")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"🎨 {user.display_name}'s Banner",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Set the image
        embed.set_image(url=user.banner.url)
        
        # Add download links
        banner_links = []
        
        # PNG format
        png_url = user.banner.replace(format='png', size=4096).url
        banner_links.append(f"[PNG]({png_url})")
        
        # JPG format
        jpg_url = user.banner.replace(format='jpg', size=4096).url
        banner_links.append(f"[JPG]({jpg_url})")
        
        # WEBP format
        webp_url = user.banner.replace(format='webp', size=4096).url
        banner_links.append(f"[WEBP]({webp_url})")
        
        # GIF format (only if animated)
        if user.banner.is_animated():
            gif_url = user.banner.replace(format='gif', size=4096).url
            banner_links.append(f"[GIF]({gif_url})")
            embed.description = "🎬 Animated Banner"
        
        embed.add_field(
            name="📥 Download Links (4096x4096)",
            value=" • ".join(banner_links),
            inline=False
        )
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await ctx.send(embed=embed)

    @commands.command(name='roles')
    async def roles(self, ctx, member: discord.Member = None):
        """Shows all roles for a user (defaults to yourself)"""
        # If no member specified, use the command author
        if member is None:
            member = ctx.author
        
        # Get all roles except @everyone
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        
        # Create embed for better formatting
        embed = discord.Embed(
            title=f"Roles for {member.display_name}",
            color=member.color,
            description=", ".join(roles) if roles else "No roles"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Total roles: {len(roles)}")
        
        await ctx.send(embed=embed)

    @commands.command(name='addrole')
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Add a role to a member (requires Manage Roles permission)"""
        # Check if bot can manage this role
        if role >= ctx.guild.me.top_role:
            await ctx.send(f"❌ I cannot manage {role.mention} - it's higher than or equal to my highest role!")
            return
        
        # Check if member already has the role
        if role in member.roles:
            await ctx.send(f"❌ {member.mention} already has {role.mention}!")
            return
        
        try:
            await member.add_roles(role)
            await ctx.send(f"✅ Added {role.mention} to {member.mention}!")
        except discord.Forbidden:
            await ctx.send(f"❌ I don't have permission to manage roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to add role: {e}")

    @commands.command(name='removerole')
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Remove role from member (requires Manage Roles permission)"""
        # Check if bot can manage this role
        if role >= ctx.guild.me.top_role:
            await ctx.send(f"❌ I cannot manage {role.mention} - it's higher than or equal to my highest role!")
            return
        
        # Check if member has the role
        if role not in member.roles:
            await ctx.send(f"❌ {member.mention} doesn't have {role.mention}!")
            return
        
        try:
            await member.remove_roles(role)
            await ctx.send(f"✅ Removed {role.mention} from {member.mention}!")
        except discord.Forbidden:
            await ctx.send(f"❌ I don't have permission to manage roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to remove role: {e}")

    # FUN COMMANDS START HERE

    @commands.command(name='poll')
    async def poll(self, ctx, question, *options):
        """Create a poll with up to 10 options. Usage: !poll "question" "option1" "option2" ..."""
        if len(options) < 2:
            await ctx.send("❌ You need at least 2 options for a poll!")
            return
        
        if len(options) > 10:
            await ctx.send("❌ You can only have up to 10 options!")
            return
        
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        description = "\n".join([f"{emojis[i]} {options[i]}" for i in range(len(options))])
        
        embed = discord.Embed(
            title=f"📊 {question}",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        
        message = await ctx.send(embed=embed)
        
        for i in range(len(options)):
            await message.add_reaction(emojis[i])

    @commands.command(name='8ball')
    async def eightball(self, ctx, *, question):
        """Ask the magic 8-ball a question"""
        responses = [
            # Affirmative responses
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            # Non-committal responses
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            # Negative responses
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        
        response = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        embed.set_footer(text=f"Asked by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

    @commands.command(name='roll')
    async def roll(self, ctx, dice: str = "1d6"):
        """Roll dice (e.g., 2d6 for two 6-sided dice)"""
        try:
            # Parse dice notation (e.g., "2d6" = 2 dice with 6 sides)
            dice = dice.lower().strip()
            
            if 'd' not in dice:
                await ctx.send("❌ Invalid format! Use format like `1d6` or `2d20`")
                return
            
            num_dice, num_sides = dice.split('d')
            num_dice = int(num_dice) if num_dice else 1
            num_sides = int(num_sides)
            
            # Validate input
            if num_dice < 1 or num_dice > 100:
                await ctx.send("❌ Number of dice must be between 1 and 100!")
                return
            
            if num_sides < 2 or num_sides > 1000:
                await ctx.send("❌ Number of sides must be between 2 and 1000!")
                return
            
            # Roll the dice
            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Create embed
            embed = discord.Embed(
                title=f"🎲 Rolling {num_dice}d{num_sides}",
                color=discord.Color.green()
            )
            
            if num_dice <= 20:
                rolls_str = ", ".join(str(r) for r in rolls)
                embed.add_field(name="Rolls", value=rolls_str, inline=False)
            
            embed.add_field(name="Total", value=f"**{total}**", inline=False)
            embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send("❌ Invalid dice format! Use format like `1d6` or `2d20`")

    @commands.command(name='meme')
    async def meme(self, ctx):
        """Get a random meme from Reddit"""
        subreddits = ["memes", "dankmemes", "wholesomememes", "me_irl", "AdviceAnimals"]
        subreddit = random.choice(subreddits)
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"https://meme-api.com/gimme/{subreddit}") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if post is not NSFW
                        if data.get("nsfw", False):
                            await ctx.send("Got an NSFW meme, fetching another one...")
                            async with session.get(f"https://meme-api.com/gimme/{subreddit}") as retry_response:
                                if retry_response.status == 200:
                                    data = await retry_response.json()
                        
                        embed = discord.Embed(
                            title=data["title"],
                            color=discord.Color.orange(),
                            url=data["postLink"]
                        )
                        embed.set_image(url=data["url"])
                        embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']} | Requested by {ctx.author.display_name}")
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("❌ Failed to fetch meme. Try again!")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.command(name='quote')
    async def quote(self, ctx, *, author: str = None):
        """Get a random inspirational quote, optionally by a specific author"""
        async with aiohttp.ClientSession() as session:
            try:
                if author:
                    # Search for quotes by author
                    async with session.get(f"https://api.quotable.io/quotes?author={author}") as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data['count'] == 0:
                                await ctx.send(f"❌ No quotes found for author: {author}")
                                return
                            
                            quote_data = data['results'][0]
                        else:
                            await ctx.send("❌ Failed to fetch quote. Try again!")
                            return
                else:
                    # Get random quote
                    async with session.get("https://api.quotable.io/random") as response:
                        if response.status == 200:
                            quote_data = await response.json()
                        else:
                            await ctx.send("❌ Failed to fetch quote. Try again!")
                            return
                
                embed = discord.Embed(
                    description=f"*\"{quote_data['content']}\"*",
                    color=discord.Color.gold()
                )
                embed.set_author(name=quote_data['author'])
                embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {str(e)}")

    # Error handlers for role commands
    @addrole.error
    @removerole.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need the 'Manage Roles' permission to use this command!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send("❌ Role not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Usage: `{ctx.prefix}{ctx.command.name} @member @role`")

# Setup function to add this cog to the bot
async def setup(bot):
    await bot.add_cog(Commands(bot))
    print('Commands cog loaded successfully!')