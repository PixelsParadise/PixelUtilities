import discord
from discord.ext import commands
from datetime import datetime
import json
import os
import random
import string
import asyncio

class VerificationView(discord.ui.View):
    """Persistent view for verification button"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="✅ Verify", style=discord.ButtonStyle.green, custom_id="verify_button", emoji="🔐")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Verification')
        if cog:
            await cog.start_verification(interaction)

class CaptchaModal(discord.ui.Modal, title="Verification Captcha"):
    """Modal for captcha verification"""
    def __init__(self, correct_code):
        super().__init__()
        self.correct_code = correct_code
        
    captcha_input = discord.ui.TextInput(
        label="Enter the code shown above",
        placeholder="Enter the verification code...",
        required=True,
        max_length=6,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('Verification')
        if cog:
            await cog.verify_captcha(interaction, self.captcha_input.value, self.correct_code)

class RulesModal(discord.ui.Modal, title="Server Rules Agreement"):
    """Modal for rules verification"""
    def __init__(self):
        super().__init__()
        
    agreement = discord.ui.TextInput(
        label="Type 'I agree' to accept the rules",
        placeholder="I agree",
        required=True,
        max_length=20,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('Verification')
        if cog:
            await cog.verify_rules(interaction, self.agreement.value)

class Verification(commands.Cog):
    """Advanced verification system with multiple methods"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'
        self.verification_file = 'verification.json'
        self.verification_data = self.load_verification_data()
        self.pending_verifications = {}  # Store temporary verification data
        
        # Add persistent view
        self.bot.add_view(VerificationView())
    
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
    
    def load_verification_data(self):
        """Load verification data"""
        if os.path.exists(self.verification_file):
            try:
                with open(self.verification_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_verification_data(self):
        """Save verification data"""
        try:
            with open(self.verification_file, 'w') as f:
                json.dump(self.verification_data, f, indent=2)
        except Exception as e:
            print(f"Error saving verification data: {e}")
    
    def get_verification_settings(self, guild_id):
        """Get verification settings for a guild"""
        config = self.load_config()
        return config.get('verification', {}).get(str(guild_id), {})
    
    def record_verification(self, guild_id, user_id, method):
        """Record a successful verification"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.verification_data:
            self.verification_data[guild_key] = {}
        
        self.verification_data[guild_key][user_key] = {
            'verified_at': datetime.utcnow().isoformat(),
            'method': method
        }
        self.save_verification_data()
    
    def is_verified(self, guild_id, user_id):
        """Check if a user is verified"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        return guild_key in self.verification_data and user_key in self.verification_data[guild_key]
    
    def generate_captcha_code(self):
        """Generate a random captcha code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    async def start_verification(self, interaction: discord.Interaction):
        """Start the verification process"""
        settings = self.get_verification_settings(interaction.guild.id)
        
        if not settings:
            await interaction.response.send_message(
                "❌ Verification system is not set up! Ask an administrator to run `>setupverification`",
                ephemeral=True
            )
            return
        
        # Check if already verified
        verified_role_id = settings.get('verified_role_id')
        if verified_role_id:
            verified_role = interaction.guild.get_role(int(verified_role_id))
            if verified_role and verified_role in interaction.user.roles:
                await interaction.response.send_message(
                    "✅ You are already verified!",
                    ephemeral=True
                )
                return
        
        # Get verification method
        method = settings.get('method', 'button')
        
        if method == 'button':
            await self.verify_button_method(interaction, settings)
        elif method == 'captcha':
            await self.verify_captcha_method(interaction, settings)
        elif method == 'rules':
            await self.verify_rules_method(interaction, settings)
        elif method == 'reaction':
            await interaction.response.send_message(
                "❌ Reaction verification must be done in the verification channel!",
                ephemeral=True
            )
    
    async def verify_button_method(self, interaction: discord.Interaction, settings):
        """Simple button verification"""
        verified_role_id = settings.get('verified_role_id')
        if not verified_role_id:
            await interaction.response.send_message(
                "❌ Verification role not configured!",
                ephemeral=True
            )
            return
        
        verified_role = interaction.guild.get_role(int(verified_role_id))
        if not verified_role:
            await interaction.response.send_message(
                "❌ Verification role not found!",
                ephemeral=True
            )
            return
        
        try:
            await interaction.user.add_roles(verified_role, reason="Verification completed")
            self.record_verification(interaction.guild.id, interaction.user.id, 'button')
            
            # Remove unverified role if configured
            unverified_role_id = settings.get('unverified_role_id')
            if unverified_role_id:
                unverified_role = interaction.guild.get_role(int(unverified_role_id))
                if unverified_role and unverified_role in interaction.user.roles:
                    await interaction.user.remove_roles(unverified_role)
            
            embed = discord.Embed(
                title="✅ Verification Complete!",
                description=f"Welcome to **{interaction.guild.name}**!\n\nYou now have access to all channels.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Send welcome message in welcome channel if configured
            welcome_channel_id = settings.get('welcome_channel_id')
            if welcome_channel_id:
                welcome_channel = interaction.guild.get_channel(int(welcome_channel_id))
                if welcome_channel:
                    welcome_msg = settings.get('welcome_message', f'Welcome {interaction.user.mention}!')
                    welcome_msg = welcome_msg.replace('{user}', interaction.user.mention)
                    welcome_msg = welcome_msg.replace('{server}', interaction.guild.name)
                    await welcome_channel.send(welcome_msg)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to assign roles!",
                ephemeral=True
            )
    
    async def verify_captcha_method(self, interaction: discord.Interaction, settings):
        """Captcha verification"""
        # Generate captcha code
        captcha_code = self.generate_captcha_code()
        
        # Store in pending verifications
        self.pending_verifications[interaction.user.id] = {
            'code': captcha_code,
            'guild_id': interaction.guild.id,
            'timestamp': datetime.utcnow()
        }
        
        # Create captcha embed
        embed = discord.Embed(
            title="🔐 Captcha Verification",
            description=f"Please enter the following code to verify:\n\n```\n{captcha_code}\n```",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Enter the code exactly as shown (case-sensitive)")
        
        # Send modal
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.followup.send("Click the button below to enter the code:", 
                                       view=CaptchaButtonView(captcha_code), ephemeral=True)
    
    async def verify_captcha(self, interaction: discord.Interaction, user_input, correct_code):
        """Verify captcha input"""
        if user_input.strip() == correct_code:
            settings = self.get_verification_settings(interaction.guild.id)
            verified_role_id = settings.get('verified_role_id')
            
            if verified_role_id:
                verified_role = interaction.guild.get_role(int(verified_role_id))
                if verified_role:
                    try:
                        await interaction.user.add_roles(verified_role, reason="Captcha verification completed")
                        self.record_verification(interaction.guild.id, interaction.user.id, 'captcha')
                        
                        # Remove unverified role
                        unverified_role_id = settings.get('unverified_role_id')
                        if unverified_role_id:
                            unverified_role = interaction.guild.get_role(int(unverified_role_id))
                            if unverified_role and unverified_role in interaction.user.roles:
                                await interaction.user.remove_roles(unverified_role)
                        
                        # Clean up pending verification
                        if interaction.user.id in self.pending_verifications:
                            del self.pending_verifications[interaction.user.id]
                        
                        embed = discord.Embed(
                            title="✅ Verification Complete!",
                            description=f"Welcome to **{interaction.guild.name}**!\n\nYou now have access to all channels.",
                            color=discord.Color.green()
                        )
                        
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        # Send welcome message
                        welcome_channel_id = settings.get('welcome_channel_id')
                        if welcome_channel_id:
                            welcome_channel = interaction.guild.get_channel(int(welcome_channel_id))
                            if welcome_channel:
                                welcome_msg = settings.get('welcome_message', f'Welcome {interaction.user.mention}!')
                                welcome_msg = welcome_msg.replace('{user}', interaction.user.mention)
                                welcome_msg = welcome_msg.replace('{server}', interaction.guild.name)
                                await welcome_channel.send(welcome_msg)
                        
                        return
                    except discord.Forbidden:
                        await interaction.response.send_message("❌ I don't have permission to assign roles!", ephemeral=True)
                        return
        
        await interaction.response.send_message(
            "❌ Incorrect code! Please try again.",
            ephemeral=True
        )
    
    async def verify_rules_method(self, interaction: discord.Interaction, settings):
        """Rules agreement verification"""
        rules_text = settings.get('rules_text', 'Please read and accept the server rules.')
        
        embed = discord.Embed(
            title="📜 Server Rules",
            description=rules_text,
            color=discord.Color.blue()
        )
        embed.set_footer(text="You must agree to the rules to gain access")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.followup.send(
            "Click the button below to accept the rules:",
            view=RulesButtonView(),
            ephemeral=True
        )
    
    async def verify_rules(self, interaction: discord.Interaction, agreement_text):
        """Verify rules agreement"""
        if agreement_text.lower().strip() in ['i agree', 'agree', 'yes']:
            settings = self.get_verification_settings(interaction.guild.id)
            verified_role_id = settings.get('verified_role_id')
            
            if verified_role_id:
                verified_role = interaction.guild.get_role(int(verified_role_id))
                if verified_role:
                    try:
                        await interaction.user.add_roles(verified_role, reason="Rules agreement completed")
                        self.record_verification(interaction.guild.id, interaction.user.id, 'rules')
                        
                        # Remove unverified role
                        unverified_role_id = settings.get('unverified_role_id')
                        if unverified_role_id:
                            unverified_role = interaction.guild.get_role(int(unverified_role_id))
                            if unverified_role and unverified_role in interaction.user.roles:
                                await interaction.user.remove_roles(unverified_role)
                        
                        embed = discord.Embed(
                            title="✅ Verification Complete!",
                            description=f"Thank you for agreeing to the rules!\n\nWelcome to **{interaction.guild.name}**!",
                            color=discord.Color.green()
                        )
                        
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        # Send welcome message
                        welcome_channel_id = settings.get('welcome_channel_id')
                        if welcome_channel_id:
                            welcome_channel = interaction.guild.get_channel(int(welcome_channel_id))
                            if welcome_channel:
                                welcome_msg = settings.get('welcome_message', f'Welcome {interaction.user.mention}!')
                                welcome_msg = welcome_msg.replace('{user}', interaction.user.mention)
                                welcome_msg = welcome_msg.replace('{server}', interaction.guild.name)
                                await welcome_channel.send(welcome_msg)
                        
                        return
                    except discord.Forbidden:
                        await interaction.response.send_message("❌ I don't have permission to assign roles!", ephemeral=True)
                        return
        
        await interaction.response.send_message(
            "❌ You must type 'I agree' to accept the rules!",
            ephemeral=True
        )
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle new member joins"""
        settings = self.get_verification_settings(member.guild.id)
        
        if not settings.get('enabled', False):
            return
        
        # Assign unverified role if configured
        unverified_role_id = settings.get('unverified_role_id')
        if unverified_role_id:
            unverified_role = member.guild.get_role(int(unverified_role_id))
            if unverified_role:
                try:
                    await member.add_roles(unverified_role, reason="Auto-assigned on join (unverified)")
                except discord.Forbidden:
                    print(f"Missing permissions to assign unverified role in {member.guild.name}")
        
        # Send DM with verification instructions if enabled
        if settings.get('dm_on_join', True):
            try:
                verification_channel_id = settings.get('verification_channel_id')
                verification_channel = member.guild.get_channel(int(verification_channel_id)) if verification_channel_id else None
                
                embed = discord.Embed(
                    title=f"👋 Welcome to {member.guild.name}!",
                    description=f"To gain access to the server, please verify yourself.",
                    color=discord.Color.blue()
                )
                
                if verification_channel:
                    embed.add_field(
                        name="How to Verify",
                        value=f"Go to {verification_channel.mention} and click the verify button!",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="How to Verify",
                        value="Look for the verification channel and follow the instructions!",
                        inline=False
                    )
                
                embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
                embed.set_footer(text="We hope you enjoy your stay!")
                
                await member.send(embed=embed)
            except:
                pass  # User has DMs disabled
    
    @commands.command(name='setupverification')
    @commands.has_permissions(administrator=True)
    async def setupverification(self, ctx, method: str = "button"):
        """Set up the verification system
        
        Methods: button, captcha, rules, reaction
        Usage: >setupverification button
        """
        method = method.lower()
        valid_methods = ['button', 'captcha', 'rules', 'reaction']
        
        if method not in valid_methods:
            await ctx.send(f"❌ Invalid method! Valid methods: {', '.join(valid_methods)}")
            return
        
        guild = ctx.guild
        
        try:
            # Create verification category
            category = await guild.create_category("🔐 Verification")
            
            # Create verification channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    add_reactions=False
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }
            
            verification_channel = await category.create_text_channel(
                name="verify-here",
                overwrites=overwrites
            )
            
            # Create verified role
            verified_role = await guild.create_role(
                name="✅ Verified",
                color=discord.Color.green(),
                reason="Verification system setup"
            )
            
            # Create unverified role
            unverified_role = await guild.create_role(
                name="⏳ Unverified",
                color=discord.Color.greyple(),
                reason="Verification system setup"
            )
            
            # Save configuration
            config = self.load_config()
            if 'verification' not in config:
                config['verification'] = {}
            
            config['verification'][str(guild.id)] = {
                'enabled': True,
                'method': method,
                'verification_channel_id': str(verification_channel.id),
                'verified_role_id': str(verified_role.id),
                'unverified_role_id': str(unverified_role.id),
                'dm_on_join': True,
                'welcome_message': 'Welcome {user} to {server}! 🎉'
            }
            
            self.save_config(config)
            
            # Send verification panel based on method
            if method == 'button':
                panel_embed = discord.Embed(
                    title="🔐 Verification Required",
                    description=(
                        f"Welcome to **{guild.name}**!\n\n"
                        "To gain access to the server, click the **Verify** button below.\n\n"
                        "This helps us ensure all members are legitimate users."
                    ),
                    color=discord.Color.blue()
                )
                panel_embed.set_footer(text="Click the button to get started!")
                
                await verification_channel.send(embed=panel_embed, view=VerificationView())
            
            elif method == 'captcha':
                panel_embed = discord.Embed(
                    title="🔐 Captcha Verification",
                    description=(
                        f"Welcome to **{guild.name}**!\n\n"
                        "To verify, click the button below and enter the captcha code.\n\n"
                        "This helps prevent bots and ensures server security."
                    ),
                    color=discord.Color.blue()
                )
                panel_embed.set_footer(text="Click the button to start verification!")
                
                await verification_channel.send(embed=panel_embed, view=VerificationView())
            
            elif method == 'rules':
                panel_embed = discord.Embed(
                    title="📜 Rules Verification",
                    description=(
                        f"Welcome to **{guild.name}**!\n\n"
                        "Please read and agree to our server rules to gain access.\n\n"
                        "Click the button below to view and accept the rules."
                    ),
                    color=discord.Color.blue()
                )
                panel_embed.set_footer(text="Click the button to continue!")
                
                await verification_channel.send(embed=panel_embed, view=VerificationView())
            
            elif method == 'reaction':
                panel_embed = discord.Embed(
                    title="✅ Reaction Verification",
                    description=(
                        f"Welcome to **{guild.name}**!\n\n"
                        "React with ✅ below to verify and gain access to the server."
                    ),
                    color=discord.Color.blue()
                )
                
                msg = await verification_channel.send(embed=panel_embed)
                await msg.add_reaction("✅")
                
                # Store message ID for reaction verification
                config['verification'][str(guild.id)]['reaction_message_id'] = str(msg.id)
                self.save_config(config)
            
            # Send setup confirmation
            setup_embed = discord.Embed(
                title="✅ Verification System Set Up!",
                description=(
                    f"Verification system configured with **{method}** method.\n\n"
                    f"**Verification Channel:** {verification_channel.mention}\n"
                    f"**Verified Role:** {verified_role.mention}\n"
                    f"**Unverified Role:** {unverified_role.mention}\n\n"
                    "**Next Steps:**\n"
                    f"• Set welcome channel: `>setwelcomechannel #channel`\n"
                    f"• Customize welcome message: `>setwelcomemsg message`\n"
                    f"• Set rules (if using rules method): `>setverificationrules rules`\n"
                    f"• Update channel permissions to require verified role"
                ),
                color=discord.Color.green()
            )
            
            await ctx.send(embed=setup_embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create channels/roles!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction-based verification"""
        if payload.user_id == self.bot.user.id:
            return
        
        settings = self.get_verification_settings(payload.guild_id)
        
        if not settings or settings.get('method') != 'reaction':
            return
        
        reaction_message_id = settings.get('reaction_message_id')
        if not reaction_message_id or str(payload.message_id) != reaction_message_id:
            return
        
        if str(payload.emoji) != '✅':
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Check if already verified
        verified_role_id = settings.get('verified_role_id')
        if verified_role_id:
            verified_role = guild.get_role(int(verified_role_id))
            if verified_role and verified_role in member.roles:
                return
            
            # Assign verified role
            try:
                await member.add_roles(verified_role, reason="Reaction verification completed")
                self.record_verification(guild.id, member.id, 'reaction')
                
                # Remove unverified role
                unverified_role_id = settings.get('unverified_role_id')
                if unverified_role_id:
                    unverified_role = guild.get_role(int(unverified_role_id))
                    if unverified_role and unverified_role in member.roles:
                        await member.remove_roles(unverified_role)
                
                # Send DM
                try:
                    embed = discord.Embed(
                        title="✅ Verification Complete!",
                        description=f"Welcome to **{guild.name}**!\n\nYou now have access to all channels.",
                        color=discord.Color.green()
                    )
                    await member.send(embed=embed)
                except:
                    pass
                
                # Send welcome message
                welcome_channel_id = settings.get('welcome_channel_id')
                if welcome_channel_id:
                    welcome_channel = guild.get_channel(int(welcome_channel_id))
                    if welcome_channel:
                        welcome_msg = settings.get('welcome_message', f'Welcome {member.mention}!')
                        welcome_msg = welcome_msg.replace('{user}', member.mention)
                        welcome_msg = welcome_msg.replace('{server}', guild.name)
                        await welcome_channel.send(welcome_msg)
                
            except discord.Forbidden:
                print(f"Missing permissions to assign verified role in {guild.name}")
    
    @commands.command(name='setwelcomechannel')
    @commands.has_permissions(administrator=True)
    async def setwelcomechannel(self, ctx, channel: discord.TextChannel = None):
        """Set the welcome channel for verified users"""
        if channel is None:
            channel = ctx.channel
        
        config = self.load_config()
        if 'verification' not in config:
            config['verification'] = {}
        if str(ctx.guild.id) not in config['verification']:
            config['verification'][str(ctx.guild.id)] = {}
        
        config['verification'][str(ctx.guild.id)]['welcome_channel_id'] = str(channel.id)
        self.save_config(config)
        
        await ctx.send(f"✅ Welcome channel set to {channel.mention}")
    
    @commands.command(name='setwelcomemsg')
    @commands.has_permissions(administrator=True)
    async def setwelcomemsg(self, ctx, *, message: str):
        """Set the welcome message (use {user} for mention, {server} for server name)"""
        config = self.load_config()
        if 'verification' not in config:
            config['verification'] = {}
        if str(ctx.guild.id) not in config['verification']:
            config['verification'][str(ctx.guild.id)] = {}
        
        config['verification'][str(ctx.guild.id)]['welcome_message'] = message
        self.save_config(config)
        
        preview = message.replace('{user}', ctx.author.mention).replace('{server}', ctx.guild.name)
        await ctx.send(f"✅ Welcome message updated!\n\n**Preview:**\n{preview}")
    
    @commands.command(name='setverificationrules')
    @commands.has_permissions(administrator=True)
    async def setverificationrules(self, ctx, *, rules: str):
        """Set the rules text for rules-based verification"""
        config = self.load_config()
        if 'verification' not in config:
            config['verification'] = {}
        if str(ctx.guild.id) not in config['verification']:
            config['verification'][str(ctx.guild.id)] = {}
        
        config['verification'][str(ctx.guild.id)]['rules_text'] = rules
        self.save_config(config)
        
        await ctx.send("✅ Verification rules updated!")
    
    @commands.command(name='verify')
    @commands.has_permissions(kick_members=True)
    async def manual_verify(self, ctx, member: discord.Member):
        """Manually verify a user (staff only)"""
        settings = self.get_verification_settings(ctx.guild.id)
        
        if not settings:
            await ctx.send("❌ Verification system is not set up!")
            return
        
        verified_role_id = settings.get('verified_role_id')
        if not verified_role_id:
            await ctx.send("❌ Verification role not configured!")
            return
        
        verified_role = ctx.guild.get_role(int(verified_role_id))
        if not verified_role:
            await ctx.send("❌ Verification role not found!")
            return
        
        try:
            await member.add_roles(verified_role, reason=f"Manually verified by {ctx.author}")
            self.record_verification(ctx.guild.id, member.id, 'manual')
            
            # Remove unverified role
            unverified_role_id = settings.get('unverified_role_id')
            if unverified_role_id:
                unverified_role = ctx.guild.get_role(int(unverified_role_id))
                if unverified_role and unverified_role in member.roles:
                    await member.remove_roles(unverified_role)
            
            await ctx.send(f"✅ {member.mention} has been manually verified!")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to assign roles!")
    
    @commands.command(name='unverify')
    @commands.has_permissions(kick_members=True)
    async def unverify(self, ctx, member: discord.Member):
        """Remove verification from a user (staff only)"""
        settings = self.get_verification_settings(ctx.guild.id)
        
        if not settings:
            await ctx.send("❌ Verification system is not set up!")
            return
        
        verified_role_id = settings.get('verified_role_id')
        unverified_role_id = settings.get('unverified_role_id')
        
        try:
            # Remove verified role
            if verified_role_id:
                verified_role = ctx.guild.get_role(int(verified_role_id))
                if verified_role and verified_role in member.roles:
                    await member.remove_roles(verified_role)
            
            # Add unverified role
            if unverified_role_id:
                unverified_role = ctx.guild.get_role(int(unverified_role_id))
                if unverified_role:
                    await member.add_roles(unverified_role)
            
            # Remove from verification data
            guild_key = str(ctx.guild.id)
            user_key = str(member.id)
            if guild_key in self.verification_data and user_key in self.verification_data[guild_key]:
                del self.verification_data[guild_key][user_key]
                self.save_verification_data()
            
            await ctx.send(f"✅ {member.mention} has been unverified!")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles!")
    
    @commands.command(name='verificationstats')
    @commands.has_permissions(kick_members=True)
    async def verificationstats(self, ctx):
        """View verification statistics"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.verification_data:
            await ctx.send("❌ No verification data available!")
            return
        
        verified_users = self.verification_data[guild_key]
        total_verified = len(verified_users)
        
        # Count by method
        methods = {}
        for user_data in verified_users.values():
            method = user_data.get('method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        
        # Get settings
        settings = self.get_verification_settings(ctx.guild.id)
        current_method = settings.get('method', 'Not configured')
        
        embed = discord.Embed(
            title="📊 Verification Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Total Verified Users", value=str(total_verified), inline=True)
        embed.add_field(name="Current Method", value=current_method.title(), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        # Method breakdown
        method_text = "\n".join([f"{m.title()}: **{c}**" for m, c in methods.items()])
        embed.add_field(name="Verification Methods Used", value=method_text or "None", inline=False)
        
        # Get role stats
        verified_role_id = settings.get('verified_role_id')
        if verified_role_id:
            verified_role = ctx.guild.get_role(int(verified_role_id))
            if verified_role:
                embed.add_field(
                    name="Verified Role Members",
                    value=f"{len(verified_role.members)} members",
                    inline=True
                )
        
        unverified_role_id = settings.get('unverified_role_id')
        if unverified_role_id:
            unverified_role = ctx.guild.get_role(int(unverified_role_id))
            if unverified_role:
                embed.add_field(
                    name="Unverified Role Members",
                    value=f"{len(unverified_role.members)} members",
                    inline=True
                )
        
        await ctx.send(embed=embed)
    
    @setupverification.error
    @setwelcomechannel.error
    @setwelcomemsg.error
    @setverificationrules.error
    async def verification_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command!")

# Additional view classes for captcha and rules
class CaptchaButtonView(discord.ui.View):
    def __init__(self, correct_code):
        super().__init__(timeout=300)
        self.correct_code = correct_code
    
    @discord.ui.button(label="Enter Code", style=discord.ButtonStyle.primary, emoji="🔑")
    async def enter_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CaptchaModal(self.correct_code))

class RulesButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="Accept Rules", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RulesModal())

async def setup(bot):
    await bot.add_cog(Verification(bot))
    print('Verification system loaded successfully!')