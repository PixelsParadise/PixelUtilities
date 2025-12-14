import discord
from discord.ext import commands
from datetime import datetime
import json
import os

class ReportView(discord.ui.View):
    """View for report action buttons"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="✅ Resolve", style=discord.ButtonStyle.green, custom_id="report_resolve")
    async def resolve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Reports')
        if cog:
            await cog.resolve_report_button(interaction)
    
    @discord.ui.button(label="👁️ Claim", style=discord.ButtonStyle.blurple, custom_id="report_claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Reports')
        if cog:
            await cog.claim_report_button(interaction)
    
    @discord.ui.button(label="❌ Dismiss", style=discord.ButtonStyle.red, custom_id="report_dismiss")
    async def dismiss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog('Reports')
        if cog:
            await cog.dismiss_report_button(interaction)

class Reports(commands.Cog):
    """User reporting system for rule violations and issues"""
    
    def __init__(self, bot):
        self.bot = bot
        self.reports_file = 'reports.json'
        self.config_file = 'config.json'
        self.reports = self.load_reports()
        
        # Add persistent view
        self.bot.add_view(ReportView())
    
    def load_reports(self):
        """Load reports from file"""
        if os.path.exists(self.reports_file):
            try:
                with open(self.reports_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_reports(self):
        """Save reports to file"""
        try:
            with open(self.reports_file, 'w') as f:
                json.dump(self.reports, f, indent=2)
        except Exception as e:
            print(f"Error saving reports: {e}")
    
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
    
    def get_reports_channel(self, guild_id):
        """Get the reports channel ID from config"""
        config = self.load_config()
        return config.get('settings', {}).get('reports_channel_id')
    
    def is_staff(self, member):
        """Check if member has a staff role"""
        config = self.load_config()
        staff_roles = config.get('staff_roles', {})
        staff_role_ids = [1440731472423026829, 1446199431316766753, 1440731529226616952, 1440731502223560754, 1440731564995641565, 1440731599640723537]
        for roles in staff_roles.values():
            staff_role_ids.extend(roles)
        return any(str(role.id) in staff_role_ids for role in member.roles)
    
    def create_report(self, guild_id, reporter_id, reported_id, reason, evidence=None):
        """Create a new report"""
        guild_key = str(guild_id)
        
        if guild_key not in self.reports:
            self.reports[guild_key] = {}
        
        # Get next report ID
        existing_ids = [int(rid) for rid in self.reports[guild_key].keys() if rid.isdigit()]
        report_id = max(existing_ids, default=0) + 1
        
        report_data = {
            'report_id': report_id,
            'reporter_id': str(reporter_id),
            'reported_id': str(reported_id),
            'reason': reason,
            'evidence': evidence,
            'status': 'pending',
            'claimed_by': None,
            'resolved_by': None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'message_id': None,
            'notes': []
        }
        
        self.reports[guild_key][str(report_id)] = report_data
        self.save_reports()
        return report_data
    
    def get_report(self, guild_id, report_id):
        """Get a specific report"""
        guild_key = str(guild_id)
        report_key = str(report_id)
        
        if guild_key in self.reports and report_key in self.reports[guild_key]:
            return self.reports[guild_key][report_key]
        return None
    
    def update_report(self, guild_id, report_id, updates):
        """Update a report"""
        guild_key = str(guild_id)
        report_key = str(report_id)
        
        if guild_key in self.reports and report_key in self.reports[guild_key]:
            self.reports[guild_key][report_key].update(updates)
            self.reports[guild_key][report_key]['updated_at'] = datetime.utcnow().isoformat()
            self.save_reports()
            return True
        return False
    
    def get_user_reports(self, guild_id, user_id, as_reporter=True):
        """Get all reports by or about a user"""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key not in self.reports:
            return []
        
        reports = []
        for report in self.reports[guild_key].values():
            if as_reporter and report['reporter_id'] == user_key:
                reports.append(report)
            elif not as_reporter and report['reported_id'] == user_key:
                reports.append(report)
        
        return reports
    
    async def send_report_embed(self, channel, report, guild):
        """Send or update report embed"""
        # Get users
        reporter = guild.get_member(int(report['reporter_id']))
        reported = guild.get_member(int(report['reported_id']))
        
        reporter_text = f"{reporter.mention} (`{reporter.id}`)" if reporter else f"User ID: {report['reporter_id']}"
        reported_text = f"{reported.mention} (`{reported.id}`)" if reported else f"User ID: {report['reported_id']}"
        
        # Status colors
        status_colors = {
            'pending': discord.Color.orange(),
            'claimed': discord.Color.blue(),
            'resolved': discord.Color.green(),
            'dismissed': discord.Color.red()
        }
        
        status_emojis = {
            'pending': '🟡',
            'claimed': '🔵',
            'resolved': '✅',
            'dismissed': '❌'
        }
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 Report #{report['report_id']}",
            description=f"{status_emojis[report['status']]} Status: **{report['status'].title()}**",
            color=status_colors[report['status']],
            timestamp=datetime.fromisoformat(report['created_at'])
        )
        
        if reported:
            embed.set_thumbnail(url=reported.display_avatar.url)
        
        embed.add_field(
            name="👤 Reported User",
            value=reported_text,
            inline=True
        )
        
        embed.add_field(
            name="🚨 Reporter",
            value=reporter_text,
            inline=True
        )
        
        embed.add_field(
            name="📅 Created",
            value=f"<t:{int(datetime.fromisoformat(report['created_at']).timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="📝 Reason",
            value=report['reason'],
            inline=False
        )
        
        # Evidence
        if report.get('evidence'):
            embed.add_field(
                name="📎 Evidence",
                value=report['evidence'],
                inline=False
            )
        
        # Claimed by
        if report.get('claimed_by'):
            claimer = guild.get_member(int(report['claimed_by']))
            if claimer:
                embed.add_field(
                    name="👁️ Claimed By",
                    value=f"{claimer.mention}",
                    inline=True
                )
        
        # Resolved by
        if report.get('resolved_by'):
            resolver = guild.get_member(int(report['resolved_by']))
            if resolver:
                embed.add_field(
                    name="✅ Resolved By",
                    value=f"{resolver.mention}",
                    inline=True
                )
        
        # Notes
        if report.get('notes'):
            notes_text = "\n".join([f"• {note}" for note in report['notes'][-3:]])  # Last 3 notes
            embed.add_field(
                name=f"📌 Notes ({len(report['notes'])})",
                value=notes_text,
                inline=False
            )
        
        embed.set_footer(text=f"Report ID: {report['report_id']}")
        
        # Send or edit message
        if report.get('message_id'):
            try:
                message = await channel.fetch_message(int(report['message_id']))
                await message.edit(embed=embed, view=ReportView() if report['status'] == 'pending' or report['status'] == 'claimed' else None)
                return message
            except:
                pass
        
        # Send new message
        view = ReportView() if report['status'] == 'pending' or report['status'] == 'claimed' else None
        message = await channel.send(embed=embed, view=view)
        self.update_report(guild.id, report['report_id'], {'message_id': str(message.id)})
        return message
    
    @commands.command(name='report')
    @commands.cooldown(1, 300, commands.BucketType.user)  # 1 report per 5 minutes
    async def report(self, ctx, member: discord.Member, *, reason: str):
        """Report a user for rule violations
        
        Usage: >report @user reason for report
        """
        # Can't report yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot report yourself!")
            return
        
        # Can't report bots
        if member.bot:
            await ctx.send("❌ You cannot report bots!")
            return
        
        # Check if reports channel is set up
        reports_channel_id = self.get_reports_channel(ctx.guild.id)
        if not reports_channel_id:
            await ctx.send("❌ Reports system is not set up! Ask an administrator to run `>setupreports`")
            return
        
        reports_channel = ctx.guild.get_channel(int(reports_channel_id))
        if not reports_channel:
            await ctx.send("❌ Reports channel not found! Ask an administrator to run `>setupreports` again")
            return
        
        # Create report
        report_data = self.create_report(
            ctx.guild.id,
            ctx.author.id,
            member.id,
            reason
        )
        
        # Send report to reports channel
        await self.send_report_embed(reports_channel, report_data, ctx.guild)
        
        # Confirm to user
        embed = discord.Embed(
            title="✅ Report Submitted",
            description=f"Your report against {member.mention} has been submitted to the moderation team.",
            color=discord.Color.green()
        )
        embed.add_field(name="Report ID", value=f"#{report_data['report_id']}", inline=True)
        embed.add_field(name="Status", value="Pending Review", inline=True)
        embed.set_footer(text="Staff will review your report shortly. False reports may result in punishment.")
        
        await ctx.send(embed=embed)
        
        # Try to delete the command message for privacy
        try:
            await ctx.message.delete()
        except:
            pass
    
    @commands.command(name='reportwith')
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def reportwith(self, ctx, member: discord.Member, evidence: str, *, reason: str):
        """Report a user with evidence links
        
        Usage: >reportwith @user https://evidence.link reason for report
        """
        # Can't report yourself
        if member == ctx.author:
            await ctx.send("❌ You cannot report yourself!")
            return
        
        # Can't report bots
        if member.bot:
            await ctx.send("❌ You cannot report bots!")
            return
        
        # Check if reports channel is set up
        reports_channel_id = self.get_reports_channel(ctx.guild.id)
        if not reports_channel_id:
            await ctx.send("❌ Reports system is not set up! Ask an administrator to run `>setupreports`")
            return
        
        reports_channel = ctx.guild.get_channel(int(reports_channel_id))
        if not reports_channel:
            await ctx.send("❌ Reports channel not found!")
            return
        
        # Create report with evidence
        report_data = self.create_report(
            ctx.guild.id,
            ctx.author.id,
            member.id,
            reason,
            evidence
        )
        
        # Send report to reports channel
        await self.send_report_embed(reports_channel, report_data, ctx.guild)
        
        # Confirm to user
        embed = discord.Embed(
            title="✅ Report Submitted",
            description=f"Your report against {member.mention} (with evidence) has been submitted.",
            color=discord.Color.green()
        )
        embed.add_field(name="Report ID", value=f"#{report_data['report_id']}", inline=True)
        embed.add_field(name="Status", value="Pending Review", inline=True)
        
        await ctx.send(embed=embed)
        
        # Try to delete the command message
        try:
            await ctx.message.delete()
        except:
            pass
    
    @commands.command(name='myreports')
    async def myreports(self, ctx):
        """View your submitted reports"""
        reports = self.get_user_reports(ctx.guild.id, ctx.author.id, as_reporter=True)
        
        if not reports:
            await ctx.send("✅ You haven't submitted any reports!")
            return
        
        # Count by status
        pending = sum(1 for r in reports if r['status'] == 'pending')
        claimed = sum(1 for r in reports if r['status'] == 'claimed')
        resolved = sum(1 for r in reports if r['status'] == 'resolved')
        dismissed = sum(1 for r in reports if r['status'] == 'dismissed')
        
        embed = discord.Embed(
            title="📋 Your Reports",
            description=f"You have submitted **{len(reports)}** report(s)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📊 Status Summary",
            value=(
                f"🟡 Pending: **{pending}**\n"
                f"🔵 Claimed: **{claimed}**\n"
                f"✅ Resolved: **{resolved}**\n"
                f"❌ Dismissed: **{dismissed}**"
            ),
            inline=False
        )
        
        # Show last 5 reports
        recent_reports = sorted(reports, key=lambda x: x['created_at'], reverse=True)[:5]
        
        for report in recent_reports:
            reported = ctx.guild.get_member(int(report['reported_id']))
            reported_text = reported.mention if reported else f"User {report['reported_id']}"
            
            status_emoji = {'pending': '🟡', 'claimed': '🔵', 'resolved': '✅', 'dismissed': '❌'}
            
            embed.add_field(
                name=f"{status_emoji[report['status']]} Report #{report['report_id']}",
                value=(
                    f"**Against:** {reported_text}\n"
                    f"**Status:** {report['status'].title()}\n"
                    f"**Reason:** {report['reason'][:50]}..."
                ),
                inline=False
            )
        
        if len(reports) > 5:
            embed.set_footer(text=f"Showing 5 of {len(reports)} reports")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='viewreport')
    @commands.has_permissions(kick_members=True)
    async def viewreport(self, ctx, report_id: int):
        """View details of a specific report (staff only)"""
        report = self.get_report(ctx.guild.id, report_id)
        
        if not report:
            await ctx.send(f"❌ Report #{report_id} not found!")
            return
        
        await self.send_report_embed(ctx.channel, report, ctx.guild)
    
    @commands.command(name='claimreport')
    @commands.has_permissions(kick_members=True)
    async def claimreport(self, ctx, report_id: int):
        """Claim a report to handle it (staff only)"""
        report = self.get_report(ctx.guild.id, report_id)
        
        if not report:
            await ctx.send(f"❌ Report #{report_id} not found!")
            return
        
        if report['status'] != 'pending':
            await ctx.send(f"❌ Report #{report_id} is already {report['status']}!")
            return
        
        # Update report
        self.update_report(ctx.guild.id, report_id, {
            'status': 'claimed',
            'claimed_by': str(ctx.author.id)
        })
        
        # Update embed in reports channel
        reports_channel_id = self.get_reports_channel(ctx.guild.id)
        if reports_channel_id:
            reports_channel = ctx.guild.get_channel(int(reports_channel_id))
            if reports_channel:
                await self.send_report_embed(reports_channel, self.get_report(ctx.guild.id, report_id), ctx.guild)
        
        await ctx.send(f"✅ You have claimed report #{report_id}")
    
    @commands.command(name='resolvereport')
    @commands.has_permissions(kick_members=True)
    async def resolvereport(self, ctx, report_id: int, *, note: str = "No note provided"):
        """Resolve a report (staff only)"""
        report = self.get_report(ctx.guild.id, report_id)
        
        if not report:
            await ctx.send(f"❌ Report #{report_id} not found!")
            return
        
        if report['status'] == 'resolved':
            await ctx.send(f"❌ Report #{report_id} is already resolved!")
            return
        
        # Add note and update
        notes = report.get('notes', [])
        notes.append(f"[RESOLVED by {ctx.author.name}] {note}")
        
        self.update_report(ctx.guild.id, report_id, {
            'status': 'resolved',
            'resolved_by': str(ctx.author.id),
            'notes': notes
        })
        
        # Update embed
        reports_channel_id = self.get_reports_channel(ctx.guild.id)
        if reports_channel_id:
            reports_channel = ctx.guild.get_channel(int(reports_channel_id))
            if reports_channel:
                await self.send_report_embed(reports_channel, self.get_report(ctx.guild.id, report_id), ctx.guild)
        
        # Notify reporter
        reporter = ctx.guild.get_member(int(report['reporter_id']))
        if reporter:
            try:
                dm_embed = discord.Embed(
                    title="✅ Report Resolved",
                    description=f"Your report #{report_id} has been resolved by the moderation team.",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="Note", value=note, inline=False)
                dm_embed.set_footer(text="Thank you for helping keep the server safe!")
                await reporter.send(embed=dm_embed)
            except:
                pass
        
        await ctx.send(f"✅ Report #{report_id} has been resolved!")
    
    @commands.command(name='dismissreport')
    @commands.has_permissions(kick_members=True)
    async def dismissreport(self, ctx, report_id: int, *, reason: str = "No reason provided"):
        """Dismiss a report as invalid (staff only)"""
        report = self.get_report(ctx.guild.id, report_id)
        
        if not report:
            await ctx.send(f"❌ Report #{report_id} not found!")
            return
        
        if report['status'] == 'dismissed':
            await ctx.send(f"❌ Report #{report_id} is already dismissed!")
            return
        
        # Add note and update
        notes = report.get('notes', [])
        notes.append(f"[DISMISSED by {ctx.author.name}] {reason}")
        
        self.update_report(ctx.guild.id, report_id, {
            'status': 'dismissed',
            'resolved_by': str(ctx.author.id),
            'notes': notes
        })
        
        # Update embed
        reports_channel_id = self.get_reports_channel(ctx.guild.id)
        if reports_channel_id:
            reports_channel = ctx.guild.get_channel(int(reports_channel_id))
            if reports_channel:
                await self.send_report_embed(reports_channel, self.get_report(ctx.guild.id, report_id), ctx.guild)
        
        await ctx.send(f"❌ Report #{report_id} has been dismissed!")
    
    @commands.command(name='addnote')
    @commands.has_permissions(kick_members=True)
    async def addnote(self, ctx, report_id: int, *, note: str):
        """Add a note to a report (staff only)"""
        report = self.get_report(ctx.guild.id, report_id)
        
        if not report:
            await ctx.send(f"❌ Report #{report_id} not found!")
            return
        
        # Add note
        notes = report.get('notes', [])
        notes.append(f"[{ctx.author.name}] {note}")
        
        self.update_report(ctx.guild.id, report_id, {'notes': notes})
        
        # Update embed
        reports_channel_id = self.get_reports_channel(ctx.guild.id)
        if reports_channel_id:
            reports_channel = ctx.guild.get_channel(int(reports_channel_id))
            if reports_channel:
                await self.send_report_embed(reports_channel, self.get_report(ctx.guild.id, report_id), ctx.guild)
        
        await ctx.send(f"✅ Note added to report #{report_id}")
    
    @commands.command(name='reportstats')
    @commands.has_permissions(kick_members=True)
    async def reportstats(self, ctx, member: discord.Member = None):
        """View report statistics for a user or server (staff only)"""
        if member:
            # User stats
            reports_about = self.get_user_reports(ctx.guild.id, member.id, as_reporter=False)
            reports_by = self.get_user_reports(ctx.guild.id, member.id, as_reporter=True)
            
            embed = discord.Embed(
                title=f"📊 Report Statistics - {member.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            embed.add_field(
                name="📋 Reports About This User",
                value=f"**{len(reports_about)}** report(s)",
                inline=True
            )
            embed.add_field(
                name="🚨 Reports By This User",
                value=f"**{len(reports_by)}** report(s)",
                inline=True
            )
            
            if reports_about:
                pending = sum(1 for r in reports_about if r['status'] == 'pending')
                resolved = sum(1 for r in reports_about if r['status'] == 'resolved')
                dismissed = sum(1 for r in reports_about if r['status'] == 'dismissed')
                
                embed.add_field(
                    name="Status Breakdown (Reports About)",
                    value=f"Pending: {pending} | Resolved: {resolved} | Dismissed: {dismissed}",
                    inline=False
                )
        else:
            # Server stats
            guild_key = str(ctx.guild.id)
            
            if guild_key not in self.reports:
                await ctx.send("✅ No reports have been submitted yet!")
                return
            
            all_reports = list(self.reports[guild_key].values())
            
            pending = sum(1 for r in all_reports if r['status'] == 'pending')
            claimed = sum(1 for r in all_reports if r['status'] == 'claimed')
            resolved = sum(1 for r in all_reports if r['status'] == 'resolved')
            dismissed = sum(1 for r in all_reports if r['status'] == 'dismissed')
            
            embed = discord.Embed(
                title=f"📊 Server Report Statistics",
                description=f"**{len(all_reports)}** total reports",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Status Breakdown",
                value=(
                    f"🟡 Pending: **{pending}**\n"
                    f"🔵 Claimed: **{claimed}**\n"
                    f"✅ Resolved: **{resolved}**\n"
                    f"❌ Dismissed: **{dismissed}**"
                ),
                inline=False
            )
            
            # Most reported users
            reported_counts = {}
            for report in all_reports:
                reported_id = report['reported_id']
                reported_counts[reported_id] = reported_counts.get(reported_id, 0) + 1
            
            if reported_counts:
                top_reported = sorted(reported_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                top_text = []
                for user_id, count in top_reported:
                    user = ctx.guild.get_member(int(user_id))
                    user_text = user.mention if user else f"ID: {user_id}"
                    top_text.append(f"{user_text}: **{count}** reports")
                
                embed.add_field(
                    name="Most Reported Users",
                    value="\n".join(top_text),
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='setupreports')
    @commands.has_permissions(administrator=True)
    async def setupreports(self, ctx, channel: discord.TextChannel = None):
        """Set up the reports system (creates or sets reports channel)"""
        if channel is None:
            # Create reports channel
            try:
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                # Add staff roles
                config = self.load_config()
                staff_roles = config.get('staff_roles', {})
                for role_list in staff_roles.values():
                    for role_id in role_list:
                        role = ctx.guild.get_role(int(role_id))
                        if role:
                            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                channel = await ctx.guild.create_text_channel(
                    name="reports",
                    topic="User reports are logged here for staff review",
                    overwrites=overwrites
                )
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to create channels!")
                return
        
        # Save to config
        config = self.load_config()
        if 'settings' not in config:
            config['settings'] = {}
        config['settings']['reports_channel_id'] = str(channel.id)
        self.save_config(config)
        
        embed = discord.Embed(
            title="✅ Reports System Set Up",
            description=f"Reports will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="User Commands",
            value=(
                "`>report @user reason` - Submit a report\n"
                "`>reportwith @user evidence reason` - Submit with evidence\n"
                "`>myreports` - View your reports"
            ),
            inline=False
        )
        embed.add_field(
            name="Staff Commands",
            value=(
                "`>viewreport <id>` - View report details\n"
                "`>claimreport <id>` - Claim a report\n"
                "`>resolvereport <id> <note>` - Resolve a report\n"
                "`>dismissreport <id> <reason>` - Dismiss a report\n"
                "`>addnote <id> <note>` - Add note to report\n"
                "`>reportstats [user]` - View statistics"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Button handlers
    async def resolve_report_button(self, interaction: discord.Interaction):
        """Handle resolve button click"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can resolve reports!", ephemeral=True)
            return
        
        # Get report ID from embed
        embed = interaction.message.embeds[0]
        report_id = int(embed.footer.text.split("Report ID: ")[1])
        
        report = self.get_report(interaction.guild.id, report_id)
        if not report:
            await interaction.response.send_message("❌ Report not found!", ephemeral=True)
            return
        
        # Update report
        notes = report.get('notes', [])
        notes.append(f"[RESOLVED by {interaction.user.name}] Resolved via button")
        
        self.update_report(interaction.guild.id, report_id, {
            'status': 'resolved',
            'resolved_by': str(interaction.user.id),
            'notes': notes
        })
        
        # Update embed
        await self.send_report_embed(interaction.channel, self.get_report(interaction.guild.id, report_id), interaction.guild)
        
        await interaction.response.send_message(f"✅ Report #{report_id} resolved!", ephemeral=True)
        
        # Notify reporter
        reporter = interaction.guild.get_member(int(report['reporter_id']))
        if reporter:
            try:
                dm_embed = discord.Embed(
                    title="✅ Report Resolved",
                    description=f"Your report #{report_id} has been resolved.",
                    color=discord.Color.green()
                )
                await reporter.send(embed=dm_embed)
            except:
                pass
    
    async def claim_report_button(self, interaction: discord.Interaction):
        """Handle claim button click"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can claim reports!", ephemeral=True)
            return
        
        # Get report ID from embed
        embed = interaction.message.embeds[0]
        report_id = int(embed.footer.text.split("Report ID: ")[1])
        
        report = self.get_report(interaction.guild.id, report_id)
        if not report:
            await interaction.response.send_message("❌ Report not found!", ephemeral=True)
            return
        
        if report['status'] != 'pending':
            await interaction.response.send_message(f"❌ Report is already {report['status']}!", ephemeral=True)
            return
        
        # Update report
        self.update_report(interaction.guild.id, report_id, {
            'status': 'claimed',
            'claimed_by': str(interaction.user.id)
        })
        
        # Update embed
        await self.send_report_embed(interaction.channel, self.get_report(interaction.guild.id, report_id), interaction.guild)
        
        await interaction.response.send_message(f"✅ You claimed report #{report_id}!", ephemeral=True)
    
    async def dismiss_report_button(self, interaction: discord.Interaction):
        """Handle dismiss button click"""
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can dismiss reports!", ephemeral=True)
            return
        
        # Get report ID from embed
        embed = interaction.message.embeds[0]
        report_id = int(embed.footer.text.split("Report ID: ")[1])
        
        report = self.get_report(interaction.guild.id, report_id)
        if not report:
            await interaction.response.send_message("❌ Report not found!", ephemeral=True)
            return
        
        # Update report
        notes = report.get('notes', [])
        notes.append(f"[DISMISSED by {interaction.user.name}] Dismissed via button")
        
        self.update_report(interaction.guild.id, report_id, {
            'status': 'dismissed',
            'resolved_by': str(interaction.user.id),
            'notes': notes
        })
        
        # Update embed
        await self.send_report_embed(interaction.channel, self.get_report(interaction.guild.id, report_id), interaction.guild)
        
        await interaction.response.send_message(f"❌ Report #{report_id} dismissed!", ephemeral=True)
    
    # Error handlers
    @report.error
    @reportwith.error
    async def report_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument! Use `{ctx.prefix}help {ctx.command.name}` for usage.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱️ You can only submit one report every 5 minutes. Try again in {int(error.retry_after)} seconds.")

async def setup(bot):
    await bot.add_cog(Reports(bot))
    print('Reports system loaded successfully!')