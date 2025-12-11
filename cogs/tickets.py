import discord
from discord.ext import commands
from datetime import datetime
import json
import os
import io

class TicketView(discord.ui.View):
    """Persistent view for ticket panel buttons"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📩 Support", style=discord.ButtonStyle.green, custom_id="ticket_support")
    async def support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.create_ticket(interaction, "support")
    
    @discord.ui.button(label="🚩 Report", style=discord.ButtonStyle.red, custom_id="ticket_report")
    async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.create_ticket(interaction, "report")
    
    @discord.ui.button(label="⚖️ Appeal", style=discord.ButtonStyle.blurple, custom_id="ticket_appeal")
    async def appeal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.create_ticket(interaction, "appeal")
    
    @discord.ui.button(label="❓ Other", style=discord.ButtonStyle.gray, custom_id="ticket_other")
    async def other_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.create_ticket(interaction, "other")

class TicketControlView(discord.ui.View):
    """View for ticket control buttons (claim, close, etc.)"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="✋ Claim", style=discord.ButtonStyle.green, custom_id="ticket_claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.claim_ticket(interaction)
    
    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.red, custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.close_ticket(interaction)
    
    @discord.ui.button(label="📋 Transcript", style=discord.ButtonStyle.blurple, custom_id="ticket_transcript")
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.save_transcript(interaction)

class RatingView(discord.ui.View):
    """View for ticket rating"""
    def __init__(self, ticket_id, staff_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.ticket_id = ticket_id
        self.staff_id = staff_id
        self.rating = None
    
    @discord.ui.button(label="⭐", style=discord.ButtonStyle.gray, custom_id="rating_1")
    async def rating_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 1)
    
    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.gray, custom_id="rating_2")
    async def rating_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 2)
    
    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.gray, custom_id="rating_3")
    async def rating_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 3)
    
    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.gray, custom_id="rating_4")
    async def rating_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 4)
    
    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.green, custom_id="rating_5")
    async def rating_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 5)
    
    async def process_rating(self, interaction: discord.Interaction, rating: int):
        self.rating = rating
        cog = interaction.client.get_cog('Tickets')
        if cog:
            await cog.save_rating(interaction, self.ticket_id, self.staff_id, rating)
        self.stop()

class Tickets(commands.Cog):
    """Enhanced ticket system with categories, claiming, and transcripts"""
    
    def __init__(self, bot):
        self.bot = bot
        self.tickets_file = 'tickets.json'
        self.config_file = 'config.json'
        self.tickets = self.load_tickets()
        
        # Add persistent views
        self.bot.add_view(TicketView())
        self.bot.add_view(TicketControlView())
    
    def load_tickets(self):
        """Load ticket data from file"""
        if os.path.exists(self.tickets_file):
            try:
                with open(self.tickets_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_tickets(self):
        """Save ticket data to file"""
        try:
            with open(self.tickets_file, 'w') as f:
                json.dump(self.tickets, f, indent=2)
        except Exception as e:
            print(f"Error saving tickets: {e}")
    
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
    
    def get_ticket_category(self, guild_id):
        """Get the ticket category ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('ticket_category_id')
    
    def get_transcript_channel(self, guild_id):
        """Get the transcript channel ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('transcript_channel_id')
    
    def get_staff_roles(self, guild):
        """Get all staff role IDs from config"""
        config = self.load_config()
        staff_roles = config.get('staff_roles', {})
        role_ids = []
        for roles in staff_roles.values():
            role_ids.extend(roles)
        return role_ids
    
    def is_staff(self, member):
        """Check if member has a staff role"""
        staff_role_ids = self.get_staff_roles(member.guild)
        return any(role.id in staff_role_ids for role in member.roles)
    
    async def create_ticket(self, interaction: discord.Interaction, category: str):
        """Create a new ticket"""
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has an open ticket
        guild_key = str(guild.id)
        user_key = str(user.id)
        
        if guild_key in self.tickets:
            for ticket_id, ticket_data in self.tickets[guild_key].items():
                if ticket_data.get('user_id') == user_key and ticket_data.get('status') == 'open':
                    await interaction.response.send_message(
                        f"❌ You already have an open ticket: <#{ticket_data['channel_id']}>",
                        ephemeral=True
                    )
                    return
        
        # Get ticket category
        category_id = self.get_ticket_category(guild.id)
        ticket_category = None
        
        if category_id:
            ticket_category = guild.get_channel(int(category_id))
        
        if not ticket_category:
            await interaction.response.send_message(
                "❌ Ticket system is not set up! An administrator needs to run `>setuptickets`",
                ephemeral=True
            )
            return
        
        # Create ticket counter
        if guild_key not in self.tickets:
            self.tickets[guild_key] = {}
        
        # Get highest ticket number to avoid duplicates
        existing_numbers = [t.get('ticket_number', 0) for t in self.tickets[guild_key].values()]
        ticket_number = max(existing_numbers, default=0) + 1
        
        # Category emojis
        category_emojis = {
            "support": "📩",
            "report": "🚩",
            "appeal": "⚖️",
            "other": "❓"
        }
        
        # Create ticket channel
        channel_name = f"ticket-{ticket_number:04d}"
        
        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add staff roles to overwrites
        staff_role_ids = self.get_staff_roles(guild)
        for role_id in staff_role_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        try:
            ticket_channel = await ticket_category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_number} | {category.title()} | User: {user.name}"
            )
            
            # Store ticket data
            ticket_id = str(ticket_channel.id)
            self.tickets[guild_key][ticket_id] = {
                'ticket_number': ticket_number,
                'user_id': user_key,
                'category': category,
                'status': 'open',
                'claimed_by': None,
                'channel_id': ticket_channel.id,
                'created_at': datetime.utcnow().isoformat(),
                'closed_at': None,
                'rating': None
            }
            self.save_tickets()
            
            # Create welcome embed
            embed = discord.Embed(
                title=f"{category_emojis.get(category, '🎫')} {category.title()} Ticket #{ticket_number}",
                description=f"Hello {user.mention}! Thanks for creating a ticket.\n\nA staff member will be with you shortly. Please describe your issue in detail.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Category", value=category.title(), inline=True)
            embed.add_field(name="Status", value="🟢 Open", inline=True)
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            
            # Send welcome message with control buttons
            await ticket_channel.send(
                content=f"{user.mention}",
                embed=embed,
                view=TicketControlView()
            )
            
            await interaction.response.send_message(
                f"✅ Ticket created! {ticket_channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create channels!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )
    
    async def claim_ticket(self, interaction: discord.Interaction):
        """Claim a ticket"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Only staff members can claim tickets!",
                ephemeral=True
            )
            return
        
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.tickets or channel_id not in self.tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid ticket channel!",
                ephemeral=True
            )
            return
        
        ticket = self.tickets[guild_key][channel_id]
        
        if ticket['claimed_by']:
            claimer = interaction.guild.get_member(int(ticket['claimed_by']))
            await interaction.response.send_message(
                f"❌ This ticket is already claimed by {claimer.mention if claimer else 'a staff member'}!",
                ephemeral=True
            )
            return
        
        # Claim the ticket
        ticket['claimed_by'] = str(interaction.user.id)
        self.save_tickets()
        
        embed = discord.Embed(
            title="✋ Ticket Claimed",
            description=f"{interaction.user.mention} is now handling this ticket.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def close_ticket(self, interaction: discord.Interaction):
        """Close a ticket"""
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.tickets or channel_id not in self.tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid ticket channel!",
                ephemeral=True
            )
            return
        
        ticket = self.tickets[guild_key][channel_id]
        
        # Check if user is ticket owner or staff
        is_owner = str(interaction.user.id) == ticket['user_id']
        is_staff_member = self.is_staff(interaction.user)
        
        if not (is_owner or is_staff_member):
            await interaction.response.send_message(
                "❌ Only the ticket owner or staff can close tickets!",
                ephemeral=True
            )
            return
        
        # Update ticket status
        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.utcnow().isoformat()
        ticket['closed_by'] = str(interaction.user.id)
        self.save_tickets()
        
        # Send closing message
        embed = discord.Embed(
            title="🔒 Ticket Closing",
            description=f"This ticket is being closed by {interaction.user.mention}.\n\nGenerating transcript and the channel will be deleted in 10 seconds.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Ask for rating if staff helped
        if ticket['claimed_by'] and str(interaction.user.id) == ticket['user_id']:
            rating_embed = discord.Embed(
                title="⭐ Rate Your Experience",
                description="Please rate the support you received:",
                color=discord.Color.gold()
            )
            
            try:
                user = interaction.guild.get_member(int(ticket['user_id']))
                if user:
                    await interaction.channel.send(
                        content=user.mention,
                        embed=rating_embed,
                        view=RatingView(channel_id, ticket['claimed_by'])
                    )
            except:
                pass
        
        # Generate and send transcript to transcript channel
        await self.send_transcript_to_channel(interaction.channel, ticket)
        
        # Wait and delete channel
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete()
        except:
            pass
    
    async def save_transcript(self, interaction: discord.Interaction):
        """Save ticket transcript"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Only staff members can save transcripts!",
                ephemeral=True
            )
            return
        
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.tickets or channel_id not in self.tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid ticket channel!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        ticket = self.tickets[guild_key][channel_id]
        transcript = await self.generate_transcript_text(interaction.channel, ticket)
        
        # Send transcript as file
        file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"ticket-{ticket['ticket_number']}-transcript.txt"
        )
        
        await interaction.followup.send(
            "✅ Transcript saved!",
            file=file,
            ephemeral=True
        )
    
    async def generate_transcript_text(self, channel, ticket):
        """Generate a text transcript of the ticket"""
        transcript = f"╔══════════════════════════════════════════════════════════╗\n"
        transcript += f"║          TICKET #{ticket['ticket_number']} TRANSCRIPT          \n"
        transcript += f"╚══════════════════════════════════════════════════════════╝\n\n"
        
        transcript += f"Category: {ticket['category'].title()}\n"
        transcript += f"Created: {ticket['created_at']}\n"
        transcript += f"Status: {ticket['status'].title()}\n"
        
        if ticket.get('claimed_by'):
            transcript += f"Claimed By: {ticket['claimed_by']}\n"
        
        if ticket.get('closed_at'):
            transcript += f"Closed: {ticket['closed_at']}\n"
        
        if ticket.get('rating'):
            transcript += f"Rating: {'⭐' * ticket['rating']}\n"
        
        transcript += "=" * 60 + "\n\n"
        
        try:
            messages = []
            async for message in channel.history(limit=None, oldest_first=True):
                messages.append(message)
            
            for message in messages:
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                transcript += f"[{timestamp}] {message.author.name}#{message.author.discriminator}:\n"
                transcript += f"{message.content}\n"
                
                if message.attachments:
                    for attachment in message.attachments:
                        transcript += f"  📎 Attachment: {attachment.filename} ({attachment.url})\n"
                
                if message.embeds:
                    for embed in message.embeds:
                        transcript += f"  📋 Embed: {embed.title if embed.title else 'No title'}\n"
                
                transcript += "\n"
        except Exception as e:
            transcript += f"Error retrieving messages: {e}\n"
        
        transcript += "=" * 60 + "\n"
        transcript += "End of transcript\n"
        
        # Save to local file
        os.makedirs('transcripts', exist_ok=True)
        filename = f"transcripts/ticket-{ticket['ticket_number']}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(transcript)
        except Exception as e:
            print(f"Error saving transcript to file: {e}")
        
        return transcript
    
    async def send_transcript_to_channel(self, ticket_channel, ticket):
        """Send transcript to the configured transcript channel"""
        transcript_channel_id = self.get_transcript_channel(ticket_channel.guild.id)
        
        if not transcript_channel_id:
            print("No transcript channel configured")
            return
        
        transcript_channel = ticket_channel.guild.get_channel(int(transcript_channel_id))
        
        if not transcript_channel:
            print(f"Transcript channel {transcript_channel_id} not found")
            return
        
        # Generate transcript
        transcript_text = await self.generate_transcript_text(ticket_channel, ticket)
        
        # Get user and staff info
        user = ticket_channel.guild.get_member(int(ticket['user_id']))
        user_display = f"{user.mention} ({user})" if user else f"User ID: {ticket['user_id']}"
        
        claimed_by_display = "Unclaimed"
        if ticket.get('claimed_by'):
            staff = ticket_channel.guild.get_channel.guild.get_member(int(ticket['claimed_by']))
            claimed_by_display = f"{staff.mention}" if staff else f"Staff ID: {ticket['claimed_by']}"
        
        closed_by_display = "Unknown"
        if ticket.get('closed_by'):
            closer = ticket_channel.guild.get_member(int(ticket['closed_by']))
            closed_by_display = f"{closer.mention}" if closer else f"User ID: {ticket['closed_by']}"
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 Ticket #{ticket['ticket_number']} Transcript",
            description=f"**Category:** {ticket['category'].title()}\n**User:** {user_display}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if user:
            embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(name="Created", value=f"<t:{int(datetime.fromisoformat(ticket['created_at']).timestamp())}:F>", inline=True)
        
        if ticket.get('closed_at'):
            embed.add_field(name="Closed", value=f"<t:{int(datetime.fromisoformat(ticket['closed_at']).timestamp())}:F>", inline=True)
        
        embed.add_field(name="Status", value=ticket['status'].title(), inline=True)
        embed.add_field(name="Claimed By", value=claimed_by_display, inline=True)
        embed.add_field(name="Closed By", value=closed_by_display, inline=True)
        
        if ticket.get('rating'):
            embed.add_field(name="Rating", value='⭐' * ticket['rating'], inline=True)
        
        embed.set_footer(text=f"Ticket ID: {ticket_channel.id}")
        
        # Send transcript file
        try:
            file = discord.File(
                io.BytesIO(transcript_text.encode()),
                filename=f"ticket-{ticket['ticket_number']}-transcript.txt"
            )
            
            await transcript_channel.send(embed=embed, file=file)
            print(f"Transcript sent for ticket #{ticket['ticket_number']}")
        except discord.Forbidden:
            print(f"Missing permissions to send transcript to channel {transcript_channel_id}")
        except Exception as e:
            print(f"Error sending transcript: {e}")
    
    async def save_rating(self, interaction: discord.Interaction, ticket_id, staff_id, rating):
        """Save ticket rating"""
        guild_key = str(interaction.guild.id)
        
        if guild_key in self.tickets and ticket_id in self.tickets[guild_key]:
            self.tickets[guild_key][ticket_id]['rating'] = rating
            self.save_tickets()
            
            embed = discord.Embed(
                title="✅ Thank You!",
                description=f"Your rating of {'⭐' * rating} has been recorded.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Notify staff member
            staff_member = interaction.guild.get_member(int(staff_id))
            if staff_member:
                try:
                    dm_embed = discord.Embed(
                        title="⭐ New Ticket Rating",
                        description=f"You received a {'⭐' * rating} rating on ticket #{self.tickets[guild_key][ticket_id]['ticket_number']}",
                        color=discord.Color.gold()
                    )
                    await staff_member.send(embed=dm_embed)
                except:
                    pass
    
    @commands.command(name='setuptickets')
    @commands.has_permissions(administrator=True)
    async def setuptickets(self, ctx):
        """Set up the ticket system (creates category, panel, and transcript channel)"""
        guild = ctx.guild
        
        # Create ticket category
        try:
            category = await guild.create_category("Tickets")
            
            # Create transcript channel
            transcript_channel = await guild.create_text_channel(
                name="ticket-transcripts",
                topic="Closed ticket transcripts are logged here"
            )
            
            # Save IDs to config
            config = self.load_config()
            if 'settings' not in config:
                config['settings'] = {}
            config['settings']['ticket_category_id'] = str(category.id)
            config['settings']['transcript_channel_id'] = str(transcript_channel.id)
            self.save_config(config)
            
            # Create ticket panel channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
            }
            
            panel_channel = await category.create_text_channel(
                name="create-ticket",
                overwrites=overwrites
            )
            
            # Send ticket panel
            embed = discord.Embed(
                title="🎫 Support Ticket System",
                description=(
                    "Need help? Create a ticket by clicking one of the buttons below:\n\n"
                    "📩 **Support** - Get help from staff\n"
                    "🚩 **Report** - Report a user or issue\n"
                    "⚖️ **Appeal** - Appeal a ban or punishment\n"
                    "❓ **Other** - Anything else"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Only create tickets for legitimate issues")
            
            await panel_channel.send(embed=embed, view=TicketView())
            
            setup_embed = discord.Embed(
                title="✅ Ticket System Set Up",
                description=(
                    f"Ticket system has been configured!\n\n"
                    f"**Category:** {category.mention}\n"
                    f"**Panel:** {panel_channel.mention}\n"
                    f"**Transcripts:** {transcript_channel.mention}"
                ),
                color=discord.Color.green()
            )
            await ctx.send(embed=setup_embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create categories/channels!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='settranscripts')
    @commands.has_permissions(administrator=True)
    async def settranscripts(self, ctx, channel: discord.TextChannel = None):
        """Set or change the transcript channel"""
        if channel is None:
            channel = ctx.channel
        
        config = self.load_config()
        if 'settings' not in config:
            config['settings'] = {}
        
        config['settings']['transcript_channel_id'] = str(channel.id)
        self.save_config(config)
        
        embed = discord.Embed(
            title="✅ Transcript Channel Set",
            description=f"Ticket transcripts will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='ticketstats')
    @commands.has_permissions(kick_members=True)
    async def ticketstats(self, ctx, member: discord.Member = None):
        """View ticket statistics"""
        if member is None:
            # Server stats
            guild_key = str(ctx.guild.id)
            
            if guild_key not in self.tickets:
                await ctx.send("❌ No ticket data available!")
                return
            
            total_tickets = len(self.tickets[guild_key])
            open_tickets = sum(1 for t in self.tickets[guild_key].values() if t['status'] == 'open')
            closed_tickets = total_tickets - open_tickets
            
            # Count by category
            categories = {}
            for ticket in self.tickets[guild_key].values():
                cat = ticket['category']
                categories[cat] = categories.get(cat, 0) + 1
            
            # Average rating
            ratings = [t['rating'] for t in self.tickets[guild_key].values() if t.get('rating')]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            embed = discord.Embed(
                title="📊 Ticket Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Total Tickets", value=str(total_tickets), inline=True)
            embed.add_field(name="Open", value=f"🟢 {open_tickets}", inline=True)
            embed.add_field(name="Closed", value=f"🔴 {closed_tickets}", inline=True)
            
            cat_text = "\n".join([f"{k.title()}: {v}" for k, v in categories.items()])
            embed.add_field(name="By Category", value=cat_text or "None", inline=False)
            
            if ratings:
                embed.add_field(name="Average Rating", value=f"{'⭐' * int(avg_rating)} ({avg_rating:.1f}/5)", inline=False)
            
            await ctx.send(embed=embed)
        else:
            # User stats
            guild_key = str(ctx.guild.id)
            user_key = str(member.id)
            
            if guild_key not in self.tickets:
                await ctx.send("❌ No ticket data available!")
                return
            
            user_tickets = [t for t in self.tickets[guild_key].values() if t['user_id'] == user_key]
            
            if not user_tickets:
                await ctx.send(f"❌ {member.mention} has no tickets!")
                return
            
            total = len(user_tickets)
            open_count = sum(1 for t in user_tickets if t['status'] == 'open')
            closed_count = total - open_count
            
            embed = discord.Embed(
                title=f"📊 Ticket Stats for {member.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Total Tickets", value=str(total), inline=True)
            embed.add_field(name="Open", value=f"🟢 {open_count}", inline=True)
            embed.add_field(name="Closed", value=f"🔴 {closed_count}", inline=True)
            
            await ctx.send(embed=embed)
    
    @commands.command(name='addticket')
    @commands.has_permissions(kick_members=True)
    async def addticket(self, ctx, member: discord.Member):
        """Add a user to the current ticket"""
        guild_key = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        if guild_key not in self.tickets or channel_id not in self.tickets[guild_key]:
            await ctx.send("❌ This command can only be used in ticket channels!")
            return
        
        try:
            await ctx.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True
            )
            
            embed = discord.Embed(
                description=f"✅ {member.mention} has been added to this ticket.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to modify channel permissions!")
    
    @commands.command(name='removeticket')
    @commands.has_permissions(kick_members=True)
    async def removeticket(self, ctx, member: discord.Member):
        """Remove a user from the current ticket"""
        guild_key = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        if guild_key not in self.tickets or channel_id not in self.tickets[guild_key]:
            await ctx.send("❌ This command can only be used in ticket channels!")
            return
        
        ticket = self.tickets[guild_key][channel_id]
        
        # Can't remove ticket owner
        if str(member.id) == ticket['user_id']:
            await ctx.send("❌ You cannot remove the ticket owner!")
            return
        
        try:
            await ctx.channel.set_permissions(member, overwrite=None)
            
            embed = discord.Embed(
                description=f"✅ {member.mention} has been removed from this ticket.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to modify channel permissions!")
    
    @setuptickets.error
    @settranscripts.error
    @addticket.error
    @removeticket.error
    async def ticket_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")

# Import asyncio
import asyncio

async def setup(bot):
    await bot.add_cog(Tickets(bot))
    print('Enhanced ticket system with transcripts loaded successfully!')
