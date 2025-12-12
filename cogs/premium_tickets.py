import discord
from discord.ext import commands
from datetime import datetime
import json
import os
import io
import asyncio

class PremiumTicketView(discord.ui.View):
    """Persistent view for premium ticket panel buttons"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="⭐ Premium Support", style=discord.ButtonStyle.primary, custom_id="premium_ticket_support", emoji="⭐")
    async def premium_support_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.create_premium_ticket(interaction, "premium_support")
    
    @discord.ui.button(label="🎫 VIP Request", style=discord.ButtonStyle.primary, custom_id="premium_ticket_vip", emoji="🎫")
    async def vip_request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.create_premium_ticket(interaction, "vip_request")
    
    @discord.ui.button(label="🔧 Technical Issue", style=discord.ButtonStyle.danger, custom_id="premium_ticket_tech", emoji="🔧")
    async def tech_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.create_premium_ticket(interaction, "technical")
    
    @discord.ui.button(label="💎 Premium Inquiry", style=discord.ButtonStyle.success, custom_id="premium_ticket_inquiry", emoji="💎")
    async def inquiry_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.create_premium_ticket(interaction, "inquiry")

class PremiumTicketControlView(discord.ui.View):
    """View for premium ticket control buttons"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="✋ Claim", style=discord.ButtonStyle.success, custom_id="premium_ticket_claim", emoji="✋")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.claim_premium_ticket(interaction)
    
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, custom_id="premium_ticket_pause", emoji="⏸️")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.pause_premium_ticket(interaction)
    
    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.danger, custom_id="premium_ticket_close", emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.close_premium_ticket(interaction)
    
    @discord.ui.button(label="📋 Transcript", style=discord.ButtonStyle.primary, custom_id="premium_ticket_transcript", emoji="📋")
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.save_premium_transcript(interaction)

class PremiumRatingView(discord.ui.View):
    """View for premium ticket rating with detailed feedback"""
    def __init__(self, ticket_id, staff_id):
        super().__init__(timeout=300)
        self.ticket_id = ticket_id
        self.staff_id = staff_id
        self.rating = None
    
    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, custom_id="premium_rating_1")
    async def rating_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 1)
    
    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary, custom_id="premium_rating_2")
    async def rating_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 2)
    
    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="premium_rating_3")
    async def rating_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 3)
    
    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.primary, custom_id="premium_rating_4")
    async def rating_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 4)
    
    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.success, custom_id="premium_rating_5")
    async def rating_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_rating(interaction, 5)
    
    async def process_rating(self, interaction: discord.Interaction, rating: int):
        self.rating = rating
        cog = interaction.client.get_cog('PremiumTickets')
        if cog:
            await cog.save_premium_rating(interaction, self.ticket_id, self.staff_id, rating)
        self.stop()

class PremiumTickets(commands.Cog):
    """Premium ticket system with priority support for premium role holders"""
    
    def __init__(self, bot):
        self.bot = bot
        self.premium_tickets_file = 'premium_tickets.json'
        self.config_file = 'config.json'
        self.premium_tickets = self.load_premium_tickets()
        
        # Priority levels for different premium tiers
        self.premium_priorities = {
            'tier3': {'priority': 1, 'name': '💎 Diamond', 'color': discord.Color.from_rgb(185, 242, 255)},
            'tier2': {'priority': 2, 'name': '⭐ Gold', 'color': discord.Color.gold()},
            'tier1': {'priority': 3, 'name': '🥈 Silver', 'color': discord.Color.from_rgb(192, 192, 192)},
        }
        
        # Add persistent views
        self.bot.add_view(PremiumTicketView())
        self.bot.add_view(PremiumTicketControlView())
    
    def load_premium_tickets(self):
        """Load premium ticket data from file"""
        if os.path.exists(self.premium_tickets_file):
            try:
                with open(self.premium_tickets_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_premium_tickets(self):
        """Save premium ticket data to file"""
        try:
            with open(self.premium_tickets_file, 'w') as f:
                json.dump(self.premium_tickets, f, indent=2)
        except Exception as e:
            print(f"Error saving premium tickets: {e}")
    
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
    
    def get_premium_category(self, guild_id):
        """Get the premium ticket category ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('premium_ticket_category_id')
    
    def get_premium_transcript_channel(self, guild_id):
        """Get the premium transcript channel ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('premium_transcript_channel_id')
    
    def get_premium_roles(self, guild):
        """Get premium role IDs from config"""
        config = self.load_config()
        return config.get('premium_roles', {})
    
    def get_premium_tier(self, member):
        """Check if member has premium role and return tier"""
        config = self.load_config()
        premium_roles = config.get('premium_roles', {})
        
        for tier, role_ids in premium_roles.items():
            for role_id in role_ids:
                if any(str(role.id) == role_id for role in member.roles):
                    return tier
        return None
    
    def is_staff(self, member):
        """Check if member has a staff role"""
        config = self.load_config()
        staff_roles = config.get('staff_roles', {})
        staff_role_ids = []
        for roles in staff_roles.values():
            staff_role_ids.extend(roles)
        return any(str(role.id) in staff_role_ids for role in member.roles)
    
    async def create_premium_ticket(self, interaction: discord.Interaction, category: str):
        """Create a new premium ticket"""
        guild = interaction.guild
        user = interaction.user
        
        # Check if user has premium role
        premium_tier = self.get_premium_tier(user)
        if not premium_tier:
            await interaction.response.send_message(
                "❌ You need a premium role to create premium tickets!\n\n"
                "Premium tickets offer:\n"
                "• Priority response times\n"
                "• Dedicated staff support\n"
                "• Enhanced features\n"
                "• VIP treatment\n\n"
                "Contact an administrator to learn about premium membership.",
                ephemeral=True
            )
            return
        
        # Check if user already has an open premium ticket
        guild_key = str(guild.id)
        user_key = str(user.id)
        
        if guild_key in self.premium_tickets:
            for ticket_id, ticket_data in self.premium_tickets[guild_key].items():
                if ticket_data.get('user_id') == user_key and ticket_data.get('status') == 'open':
                    await interaction.response.send_message(
                        f"❌ You already have an open premium ticket: <#{ticket_data['channel_id']}>",
                        ephemeral=True
                    )
                    return
        
        # Get premium ticket category
        category_id = self.get_premium_category(guild.id)
        ticket_category = None
        
        if category_id:
            ticket_category = guild.get_channel(int(category_id))
        
        if not ticket_category:
            await interaction.response.send_message(
                "❌ Premium ticket system is not set up! An administrator needs to run `>setuppremiumtickets`",
                ephemeral=True
            )
            return
        
        # Create ticket counter
        if guild_key not in self.premium_tickets:
            self.premium_tickets[guild_key] = {}
        
        # Get highest ticket number
        existing_numbers = [t.get('ticket_number', 0) for t in self.premium_tickets[guild_key].values()]
        ticket_number = max(existing_numbers, default=0) + 1
        
        # Category emojis and names
        category_info = {
            "premium_support": {"emoji": "⭐", "name": "Premium Support"},
            "vip_request": {"emoji": "🎫", "name": "VIP Request"},
            "technical": {"emoji": "🔧", "name": "Technical Issue"},
            "inquiry": {"emoji": "💎", "name": "Premium Inquiry"}
        }
        
        cat_info = category_info.get(category, {"emoji": "⭐", "name": "Premium"})
        
        # Get tier info
        tier_info = self.premium_priorities.get(premium_tier, {'priority': 99, 'name': '🌟 Premium', 'color': discord.Color.gold()})
        
        # Create ticket channel
        channel_name = f"premium-{ticket_number:04d}"
        
        # Set permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True, 
                attach_files=True, 
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add staff roles to overwrites
        config = self.load_config()
        staff_role_ids = []
        for roles in config.get('staff_roles', {}).values():
            staff_role_ids.extend(roles)
        
        for role_id in staff_role_ids:
            role = guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True,
                    manage_messages=True
                )
        
        try:
            ticket_channel = await ticket_category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Premium Ticket #{ticket_number} | {cat_info['name']} | {tier_info['name']} | User: {user.name}"
            )
            
            # Store ticket data
            ticket_id = str(ticket_channel.id)
            self.premium_tickets[guild_key][ticket_id] = {
                'ticket_number': ticket_number,
                'user_id': user_key,
                'category': category,
                'premium_tier': premium_tier,
                'priority': tier_info['priority'],
                'status': 'open',
                'claimed_by': None,
                'resolved_by': None,
                'paused': False,
                'channel_id': ticket_channel.id,
                'created_at': datetime.utcnow().isoformat(),
                'closed_at': None,
                'response_time': None,
                'resolution_time': None,
                'rating': None,
                'feedback': None,
                'notes': []
            }
            self.save_premium_tickets()
            
            # Create welcome embed
            embed = discord.Embed(
                title=f"{cat_info['emoji']} {cat_info['name']} - Premium Ticket #{ticket_number}",
                description=(
                    f"**Premium Member:** {user.mention}\n"
                    f"**Tier:** {tier_info['name']}\n"
                    f"**Priority Level:** P{tier_info['priority']}\n\n"
                    f"Thank you for being a premium member! A dedicated staff member will assist you shortly.\n\n"
                    f"**Premium Benefits Active:**\n"
                    f"✅ Priority response queue\n"
                    f"✅ Extended support hours\n"
                    f"✅ Direct staff communication\n"
                    f"✅ Enhanced ticket features"
                ),
                color=tier_info['color'],
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Category", value=cat_info['name'], inline=True)
            embed.add_field(name="Status", value="🟢 Open", inline=True)
            embed.add_field(name="Queue Position", value=f"Priority: P{tier_info['priority']}", inline=True)
            embed.set_footer(text=f"Premium Ticket ID: {ticket_id}")
            
            # Send welcome message with control buttons
            await ticket_channel.send(
                content=f"⭐ {user.mention}",
                embed=embed,
                view=PremiumTicketControlView()
            )
            
            # Send staff notification
            staff_embed = discord.Embed(
                title="🔔 New Premium Ticket Alert",
                description=f"A {tier_info['name']} member has created a premium ticket!",
                color=tier_info['color']
            )
            staff_embed.add_field(name="Ticket", value=f"#{ticket_number}", inline=True)
            staff_embed.add_field(name="Priority", value=f"P{tier_info['priority']}", inline=True)
            staff_embed.add_field(name="Category", value=cat_info['name'], inline=True)
            
            # Mention staff roles
            staff_mentions = []
            for role_id in staff_role_ids[:3]:  # Mention up to 3 staff roles
                role = guild.get_role(int(role_id))
                if role:
                    staff_mentions.append(role.mention)
            
            if staff_mentions:
                await ticket_channel.send(
                    content=f"{'  '.join(staff_mentions)}",
                    embed=staff_embed
                )
            
            await interaction.response.send_message(
                f"✅ Premium ticket created! {ticket_channel.mention}\n"
                f"**Your Premium Benefits:**\n"
                f"• Priority: P{tier_info['priority']}\n"
                f"• Faster response times\n"
                f"• Dedicated support",
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
    
    async def claim_premium_ticket(self, interaction: discord.Interaction):
        """Claim a premium ticket"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Only staff members can claim premium tickets!",
                ephemeral=True
            )
            return
        
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.premium_tickets or channel_id not in self.premium_tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid premium ticket channel!",
                ephemeral=True
            )
            return
        
        ticket = self.premium_tickets[guild_key][channel_id]
        
        if ticket['claimed_by']:
            claimer = interaction.guild.get_member(int(ticket['claimed_by']))
            await interaction.response.send_message(
                f"❌ This premium ticket is already claimed by {claimer.mention if claimer else 'a staff member'}!",
                ephemeral=True
            )
            return
        
        # Claim the ticket and record response time
        ticket['claimed_by'] = str(interaction.user.id)
        created_time = datetime.fromisoformat(ticket['created_at'])
        response_time = (datetime.utcnow() - created_time).total_seconds()
        ticket['response_time'] = response_time
        self.save_premium_tickets()
        
        # Format response time
        minutes = int(response_time // 60)
        seconds = int(response_time % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        tier_info = self.premium_priorities.get(ticket['premium_tier'], {'color': discord.Color.gold()})
        
        embed = discord.Embed(
            title="✋ Premium Ticket Claimed",
            description=f"{interaction.user.mention} is now handling this premium ticket.",
            color=tier_info['color'],
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Response Time", value=time_str, inline=True)
        embed.add_field(name="Priority", value=f"P{ticket['priority']}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    async def pause_premium_ticket(self, interaction: discord.Interaction):
        """Pause a premium ticket (waiting for user response)"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Only staff members can pause tickets!",
                ephemeral=True
            )
            return
        
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.premium_tickets or channel_id not in self.premium_tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid premium ticket channel!",
                ephemeral=True
            )
            return
        
        ticket = self.premium_tickets[guild_key][channel_id]
        
        # Toggle pause state
        ticket['paused'] = not ticket['paused']
        self.save_premium_tickets()
        
        if ticket['paused']:
            embed = discord.Embed(
                title="⏸️ Ticket Paused",
                description="This ticket is now paused. Waiting for member response.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await interaction.channel.edit(name=f"paused-{ticket['ticket_number']:04d}")
        else:
            embed = discord.Embed(
                title="▶️ Ticket Resumed",
                description="This ticket has been resumed and is now active.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await interaction.channel.edit(name=f"premium-{ticket['ticket_number']:04d}")
        
        await interaction.response.send_message(embed=embed)
    
    async def close_premium_ticket(self, interaction: discord.Interaction):
        """Close a premium ticket"""
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.premium_tickets or channel_id not in self.premium_tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid premium ticket channel!",
                ephemeral=True
            )
            return
        
        ticket = self.premium_tickets[guild_key][channel_id]
        
        # Check if user is ticket owner or staff
        is_owner = str(interaction.user.id) == ticket['user_id']
        is_staff_member = self.is_staff(interaction.user)
        
        if not (is_owner or is_staff_member):
            await interaction.response.send_message(
                "❌ Only the ticket owner or staff can close premium tickets!",
                ephemeral=True
            )
            return
        
        # Update ticket status
        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.utcnow().isoformat()
        ticket['closed_by'] = str(interaction.user.id)
        
        # Calculate resolution time
        created_time = datetime.fromisoformat(ticket['created_at'])
        resolution_time = (datetime.utcnow() - created_time).total_seconds()
        ticket['resolution_time'] = resolution_time
        
        self.save_premium_tickets()
        
        # Send closing message
        tier_info = self.premium_priorities.get(ticket['premium_tier'], {'color': discord.Color.gold()})
        
        embed = discord.Embed(
            title="🔒 Premium Ticket Closing",
            description=f"This premium ticket is being closed by {interaction.user.mention}.\n\nGenerating transcript and the channel will be deleted in 15 seconds.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        # Add resolution stats
        minutes = int(resolution_time // 60)
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if hours > 0:
            time_str = f"{hours}h {remaining_minutes}m"
        elif minutes > 0:
            time_str = f"{minutes}m"
        else:
            time_str = f"{int(resolution_time)}s"
        
        embed.add_field(name="Total Resolution Time", value=time_str, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
        # Ask for rating if staff helped
        if ticket['claimed_by'] and str(interaction.user.id) == ticket['user_id']:
            rating_embed = discord.Embed(
                title="⭐ Rate Your Premium Support Experience",
                description="As a premium member, your feedback is invaluable!\n\nPlease rate the support you received:",
                color=discord.Color.gold()
            )
            
            try:
                user = interaction.guild.get_member(int(ticket['user_id']))
                if user:
                    await interaction.channel.send(
                        content=user.mention,
                        embed=rating_embed,
                        view=PremiumRatingView(channel_id, ticket['claimed_by'])
                    )
            except:
                pass
        
        # Generate and send transcript
        await self.send_premium_transcript_to_channel(interaction.channel, ticket)
        
        # Wait and delete channel
        await asyncio.sleep(15)
        try:
            await interaction.channel.delete()
        except:
            pass
    
    async def save_premium_transcript(self, interaction: discord.Interaction):
        """Save premium ticket transcript"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Only staff members can save transcripts!",
                ephemeral=True
            )
            return
        
        guild_key = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_key not in self.premium_tickets or channel_id not in self.premium_tickets[guild_key]:
            await interaction.response.send_message(
                "❌ This is not a valid premium ticket channel!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        ticket = self.premium_tickets[guild_key][channel_id]
        transcript = await self.generate_premium_transcript_text(interaction.channel, ticket)
        
        # Send transcript as file
        file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"premium-ticket-{ticket['ticket_number']}-transcript.txt"
        )
        
        await interaction.followup.send(
            "✅ Premium transcript saved!",
            file=file,
            ephemeral=True
        )
    
    async def generate_premium_transcript_text(self, channel, ticket):
        """Generate a text transcript of the premium ticket"""
        tier_info = self.premium_priorities.get(ticket['premium_tier'], {'name': 'Premium'})
        
        transcript = f"╔═══════════════════════════════════════════════════════════╗\n"
        transcript += f"║     PREMIUM TICKET #{ticket['ticket_number']} TRANSCRIPT - {tier_info['name'].upper()}     \n"
        transcript += f"╚═══════════════════════════════════════════════════════════╝\n\n"
        
        transcript += f"Premium Tier: {tier_info['name']}\n"
        transcript += f"Priority: P{ticket['priority']}\n"
        transcript += f"Category: {ticket['category'].replace('_', ' ').title()}\n"
        transcript += f"Created: {ticket['created_at']}\n"
        transcript += f"Status: {ticket['status'].title()}\n"
        
        if ticket.get('claimed_by'):
            transcript += f"Claimed By: {ticket['claimed_by']}\n"
            if ticket.get('response_time'):
                minutes = int(ticket['response_time'] // 60)
                seconds = int(ticket['response_time'] % 60)
                transcript += f"Response Time: {minutes}m {seconds}s\n"
        
        if ticket.get('closed_at'):
            transcript += f"Closed: {ticket['closed_at']}\n"
            if ticket.get('resolution_time'):
                minutes = int(ticket['resolution_time'] // 60)
                hours = minutes // 60
                remaining_minutes = minutes % 60
                transcript += f"Resolution Time: {hours}h {remaining_minutes}m\n"
        
        if ticket.get('rating'):
            transcript += f"Rating: {'⭐' * ticket['rating']} ({ticket['rating']}/5)\n"
        
        if ticket.get('feedback'):
            transcript += f"Feedback: {ticket['feedback']}\n"
        
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
        transcript += "End of premium transcript\n"
        transcript += "\nThank you for being a premium member!\n"
        
        # Save to local file
        os.makedirs('premium_transcripts', exist_ok=True)
        filename = f"premium_transcripts/premium-ticket-{ticket['ticket_number']}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(transcript)
        except Exception as e:
            print(f"Error saving premium transcript to file: {e}")
        
        return transcript
    
    async def send_premium_transcript_to_channel(self, ticket_channel, ticket):
        """Send premium transcript to the configured transcript channel"""
        transcript_channel_id = self.get_premium_transcript_channel(ticket_channel.guild.id)
        
        if not transcript_channel_id:
            print("No premium transcript channel configured")
            return
        
        transcript_channel = ticket_channel.guild.get_channel(int(transcript_channel_id))
        
        if not transcript_channel:
            print(f"Premium transcript channel {transcript_channel_id} not found")
            return
        
        # Generate transcript
        transcript_text = await self.generate_premium_transcript_text(ticket_channel, ticket)
        
        # Get user and staff info
        user = ticket_channel.guild.get_member(int(ticket['user_id']))
        user_display = f"{user.mention} ({user})" if user else f"User ID: {ticket['user_id']}"
        
        tier_info = self.premium_priorities.get(ticket['premium_tier'], {'name': '🌟 Premium', 'color': discord.Color.gold()})
        
        claimed_by_display = "Unclaimed"
        if ticket.get('claimed_by'):
            staff = ticket_channel.guild.get_member(int(ticket['claimed_by']))
            claimed_by_display = f"{staff.mention}" if staff else f"Staff ID: {ticket['claimed_by']}"
        
        # Create embed
        embed = discord.Embed(
            title=f"⭐ Premium Ticket #{ticket['ticket_number']} Transcript",
            description=f"**Tier:** {tier_info['name']}\n**Priority:** P{ticket['priority']}\n**User:** {user_display}",
            color=tier_info['color'],
            timestamp=datetime.utcnow()
        )
        
        if user:
            embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="Category",
            value=ticket['category'].replace('_', ' ').title(),
            inline=True
        )
        embed.add_field(
            name="Status",
            value=ticket['status'].title(),
            inline=True
        )
        embed.add_field(
            name="Priority",
            value=f"P{ticket['priority']}",
            inline=True
        )
        
        embed.add_field(
            name="Created",
            value=f"<t:{int(datetime.fromisoformat(ticket['created_at']).timestamp())}:F>",
            inline=True
        )
        
        if ticket.get('closed_at'):
            embed.add_field(
                name="Closed",
                value=f"<t:{int(datetime.fromisoformat(ticket['closed_at']).timestamp())}:F>",
                inline=True
            )
        
        embed.add_field(
            name="Claimed By",
            value=claimed_by_display,
            inline=True
        )
        
        # Add response time
        if ticket.get('response_time'):
            minutes = int(ticket['response_time'] // 60)
            seconds = int(ticket['response_time'] % 60)
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            embed.add_field(name="Response Time", value=time_str, inline=True)
        
        # Add resolution time
        if ticket.get('resolution_time'):
            minutes = int(ticket['resolution_time'] // 60)
            hours = minutes // 60
            remaining_minutes = minutes % 60
            time_str = f"{hours}h {remaining_minutes}m" if hours > 0 else f"{minutes}m"
            embed.add_field(name="Resolution Time", value=time_str, inline=True)
        
        if ticket.get('rating'):
            embed.add_field(
                name="Rating",
                value='⭐' * ticket['rating'] + f" ({ticket['rating']}/5)",
                inline=True
            )
        
        if ticket.get('feedback'):
            embed.add_field(
                name="Feedback",
                value=ticket['feedback'][:1024],
                inline=False
            )
        
        embed.set_footer(text=f"Premium Ticket ID: {ticket_channel.id}")
        
        # Send transcript file
        try:
            file = discord.File(
                io.BytesIO(transcript_text.encode()),
                filename=f"premium-ticket-{ticket['ticket_number']}-transcript.txt"
            )
            
            await transcript_channel.send(embed=embed, file=file)
            print(f"Premium transcript sent for ticket #{ticket['ticket_number']}")
        except discord.Forbidden:
            print(f"Missing permissions to send premium transcript to channel {transcript_channel_id}")
        except Exception as e:
            print(f"Error sending premium transcript: {e}")
    
    async def save_premium_rating(self, interaction: discord.Interaction, ticket_id, staff_id, rating):
        """Save premium ticket rating"""
        guild_key = str(interaction.guild.id)
        
        if guild_key in self.premium_tickets and ticket_id in self.premium_tickets[guild_key]:
            self.premium_tickets[guild_key][ticket_id]['rating'] = rating
            self.save_premium_tickets()
            
            embed = discord.Embed(
                title="✅ Thank You Premium Member!",
                description=f"Your rating of {'⭐' * rating} has been recorded.\n\nYour feedback helps us improve our premium support service!",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Notify staff member
            staff_member = interaction.guild.get_member(int(staff_id))
            if staff_member:
                try:
                    tier_info = self.premium_priorities.get(
                        self.premium_tickets[guild_key][ticket_id]['premium_tier'],
                        {'name': 'Premium'}
                    )
                    dm_embed = discord.Embed(
                        title="⭐ New Premium Ticket Rating",
                        description=f"You received a {'⭐' * rating} rating from a {tier_info['name']} member on premium ticket #{self.premium_tickets[guild_key][ticket_id]['ticket_number']}",
                        color=discord.Color.gold()
                    )
                    await staff_member.send(embed=dm_embed)
                except:
                    pass
    
    @commands.command(name='setuppremiumtickets')
    @commands.has_permissions(administrator=True)
    async def setuppremiumtickets(self, ctx):
        """Set up the premium ticket system"""
        guild = ctx.guild
        
        # Create premium ticket category
        try:
            category = await guild.create_category("⭐ Premium Support")
            
            # Create premium transcript channel
            transcript_channel = await guild.create_text_channel(
                name="premium-transcripts",
                topic="Premium ticket transcripts are logged here"
            )
            
            # Save IDs to config
            config = self.load_config()
            if 'settings' not in config:
                config['settings'] = {}
            config['settings']['premium_ticket_category_id'] = str(category.id)
            config['settings']['premium_transcript_channel_id'] = str(transcript_channel.id)
            self.save_config(config)
            
            # Create premium ticket panel channel
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
                name="create-premium-ticket",
                overwrites=overwrites
            )
            
            # Send premium ticket panel
            embed = discord.Embed(
                title="⭐ Premium Support Ticket System",
                description=(
                    "**Welcome Premium Members!**\n\n"
                    "As a valued premium member, you have access to our exclusive priority support system with:\n\n"
                    "✨ **Benefits:**\n"
                    "• Priority response times\n"
                    "• Dedicated staff support\n"
                    "• Extended support hours\n"
                    "• Enhanced ticket features\n"
                    "• VIP treatment\n\n"
                    "**Select your ticket type below:**\n"
                    "⭐ **Premium Support** - General premium assistance\n"
                    "🎫 **VIP Request** - Special requests and inquiries\n"
                    "🔧 **Technical Issue** - Technical problems and bugs\n"
                    "💎 **Premium Inquiry** - Questions about premium features"
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text="Premium membership required • Priority support guaranteed")
            
            await panel_channel.send(embed=embed, view=PremiumTicketView())
            
            setup_embed = discord.Embed(
                title="✅ Premium Ticket System Set Up",
                description=(
                    f"Premium ticket system has been configured!\n\n"
                    f"**Category:** {category.mention}\n"
                    f"**Panel:** {panel_channel.mention}\n"
                    f"**Transcripts:** {transcript_channel.mention}\n\n"
                    f"⚠️ **Important:** Configure premium roles using:\n"
                    f"`>setpremiumrole <tier> <role>`\n\n"
                    f"**Available tiers:**\n"
                    f"• `tier1` - 🥈 Premium (P3 Priority)\n"
                    f"• `tier2` - ⭐ Premium+ (P2 Priority)\n"
                    f"• `tier3` - 💎 Super Premium (P1 Priority - Highest)"
                ),
                color=discord.Color.green()
            )
            await ctx.send(embed=setup_embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create categories/channels!")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='setpremiumrole')
    @commands.has_permissions(administrator=True)
    async def setpremiumrole(self, ctx, tier: str, role: discord.Role):
        """Set a premium role for a specific tier
        
        Usage: >setpremiumrole tier1 @Silver
               >setpremiumrole tier2 @Gold
               >setpremiumrole tier3 @Diamond
        """
        tier = tier.lower()
        valid_tiers = ['tier1', 'tier2', 'tier3']
        
        if tier not in valid_tiers:
            await ctx.send(f"❌ Invalid tier! Valid tiers: {', '.join(valid_tiers)}")
            return
        
        config = self.load_config()
        if 'premium_roles' not in config:
            config['premium_roles'] = {}
        
        if tier not in config['premium_roles']:
            config['premium_roles'][tier] = []
        
        if str(role.id) not in config['premium_roles'][tier]:
            config['premium_roles'][tier].append(str(role.id))
        
        self.save_config(config)
        
        tier_info = self.premium_priorities.get(tier, {'name': 'Premium', 'priority': 99})
        
        embed = discord.Embed(
            title="✅ Premium Role Configured",
            description=f"Role {role.mention} has been set as a **{tier_info['name']}** premium tier!",
            color=discord.Color.green()
        )
        embed.add_field(name="Tier", value=tier_info['name'], inline=True)
        embed.add_field(name="Priority", value=f"P{tier_info['priority']}", inline=True)
        embed.add_field(
            name="Benefits",
            value=(
                "✅ Access to premium tickets\n"
                "✅ Priority support queue\n"
                "✅ Dedicated staff assistance\n"
                "✅ Extended support hours"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='premiumstats')
    @commands.has_permissions(kick_members=True)
    async def premiumstats(self, ctx):
        """View premium ticket statistics"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.premium_tickets:
            await ctx.send("❌ No premium ticket data available!")
            return
        
        total_tickets = len(self.premium_tickets[guild_key])
        open_tickets = sum(1 for t in self.premium_tickets[guild_key].values() if t['status'] == 'open')
        closed_tickets = total_tickets - open_tickets
        
        # Count by tier
        tier_counts = {}
        for ticket in self.premium_tickets[guild_key].values():
            tier = ticket.get('premium_tier', 'unknown')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Calculate average ratings
        ratings = [t['rating'] for t in self.premium_tickets[guild_key].values() if t.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Calculate average response time
        response_times = [t['response_time'] for t in self.premium_tickets[guild_key].values() if t.get('response_time')]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate average resolution time
        resolution_times = [t['resolution_time'] for t in self.premium_tickets[guild_key].values() if t.get('resolution_time')]
        avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        embed = discord.Embed(
            title="⭐ Premium Ticket Statistics",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Total Premium Tickets", value=str(total_tickets), inline=True)
        embed.add_field(name="Open", value=f"🟢 {open_tickets}", inline=True)
        embed.add_field(name="Closed", value=f"🔴 {closed_tickets}", inline=True)
        
        # Tier breakdown
        tier_text = []
        for tier, count in tier_counts.items():
            tier_info = self.premium_priorities.get(tier, {'name': tier})
            tier_text.append(f"{tier_info['name']}: {count}")
        
        embed.add_field(
            name="By Premium Tier",
            value="\n".join(tier_text) if tier_text else "None",
            inline=False
        )
        
        if ratings:
            embed.add_field(
                name="Average Rating",
                value=f"{'⭐' * int(avg_rating)} ({avg_rating:.2f}/5)\nTotal Ratings: {len(ratings)}",
                inline=False
            )
        
        if avg_response > 0:
            minutes = int(avg_response // 60)
            seconds = int(avg_response % 60)
            embed.add_field(
                name="Avg Response Time",
                value=f"{minutes}m {seconds}s",
                inline=True
            )
        
        if avg_resolution > 0:
            minutes = int(avg_resolution // 60)
            hours = minutes // 60
            remaining_minutes = minutes % 60
            embed.add_field(
                name="Avg Resolution Time",
                value=f"{hours}h {remaining_minutes}m",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='addpremiumuser')
    @commands.has_permissions(kick_members=True)
    async def addpremiumuser(self, ctx, member: discord.Member):
        """Add a user to the current premium ticket"""
        guild_key = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)
        
        if guild_key not in self.premium_tickets or channel_id not in self.premium_tickets[guild_key]:
            await ctx.send("❌ This command can only be used in premium ticket channels!")
            return
        
        try:
            await ctx.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True,
                attach_files=True
            )
            
            embed = discord.Embed(
                description=f"✅ {member.mention} has been added to this premium ticket.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to modify channel permissions!")
    
    @commands.command(name='premiumhelp')
    async def premiumhelp(self, ctx):
        """Show premium ticket system help"""
        embed = discord.Embed(
            title="⭐ Premium Ticket System Help",
            description="Welcome to the premium support system!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🎫 For Premium Members",
            value=(
                "`Create Ticket` - Use the premium ticket panel\n"
                "Your ticket gets priority based on your tier:\n"
                "• 💎 Super Premium: P1 (Highest Priority)\n"
                "• ⭐ Premium+: P2 Priority\n"
                "• 🥈 Premium: P3 Priority"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🛠️ For Staff",
            value=(
                "`>premiumstats` - View premium ticket statistics\n"
                "`>addpremiumuser @user` - Add user to ticket\n"
                "`>setuppremiumtickets` - Set up the system (Admin)\n"
                "`>setpremiumrole <tier> @role` - Configure premium roles (Admin)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="✨ Premium Benefits",
            value=(
                "• Priority response queue\n"
                "• Dedicated staff support\n"
                "• Extended support hours\n"
                "• Enhanced ticket features\n"
                "• Detailed transcripts\n"
                "• Performance tracking"
            ),
            inline=False
        )
        
        embed.set_footer(text="Premium support is available 24/7 for all tiers")
        
        await ctx.send(embed=embed)
    
    @setuppremiumtickets.error
    @setpremiumrole.error
    @addpremiumuser.error
    async def premium_ticket_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")

async def setup(bot):
    await bot.add_cog(PremiumTickets(bot))
    print('Premium ticket system loaded successfully!')