import discord
from discord.ext import commands
from discord import app_commands
import json
import time
from datetime import datetime, timedelta
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Shifts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shift_file = 'shifts.json'
        self.shifts = self.load_shifts()
        self.embed_color = 0x19385f
        self.footer_text = "Melbourne Roleplay"
        self.staff_role_id = 1384466481831608381  # Staff role ID (from previous context, role F)
        self.admin_role_id = 1385160436046893168  # Admin role ID (from previous context, role AF)

    def load_shifts(self):
        """Load shift data from shifts.json"""
        if os.path.exists(self.shift_file):
            with open(self.shift_file, 'r') as f:
                return json.load(f)
        return {"active": {}, "history": []}

    def save_shifts(self):
        """Save shift data to shifts.json"""
        with open(self.shift_file, 'w') as f:
            json.dump(self.shifts, f, indent=4)
        logger.info("Saved shifts to shifts.json")

    def create_embed(self, title, description="", ephemeral=True):
        """Create a standardized embed"""
        embed = discord.Embed(title=title, description=description, color=self.embed_color)
        embed.set_footer(text=self.footer_text)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed, ephemeral

    def get_total_duty_time(self, user_id):
        """Calculate total duty time for a user from history"""
        total_duration = sum(shift["duration"] for shift in self.shifts["history"] if shift["user_id"] == user_id)
        return str(timedelta(seconds=int(total_duration)))

    async def has_staff_role(self, interaction: discord.Interaction):
        """Check if user has Staff or Admin role"""
        staff_role = discord.utils.get(interaction.guild.roles, id=self.staff_role_id) # type: ignore
        admin_role = discord.utils.get(interaction.guild.roles, id=self.admin_role_id) # type: ignore
        if not (staff_role in interaction.user.roles or admin_role in interaction.user.roles): # type: ignore
            embed, ephemeral = self.create_embed("Error", "You need the Staff or Admin role to use this command.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.info(f"Unauthorized access attempt by {interaction.user.id} for staff command")
            return False
        return True

    async def has_admin_role(self, interaction: discord.Interaction):
        """Check if user has Admin role"""
        admin_role = discord.utils.get(interaction.guild.roles, id=self.admin_role_id) # type: ignore
        if not admin_role or admin_role not in interaction.user.roles: # type: ignore
            embed, ephemeral = self.create_embed("Error", "You need the Admin role to use this command.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.info(f"Unauthorized access attempt by {interaction.user.id} for admin command")
            return False
        return True

    duty_group = app_commands.Group(name="duty", description="Shift management commands")

    @duty_group.command(name="manage", description="Manage your shift (start, stop, view time, view history)")
    async def duty_manage(self, interaction: discord.Interaction):
        """Manage user's shift: start, stop, view time, view history"""
        user_id = str(interaction.user.id)
        view = ManageView(self, interaction.user)
        embed, ephemeral = self.create_embed("Shift Management")
        embed.add_field(name="Status", value="On Duty" if user_id in self.shifts["active"] else "Off Duty", inline=True)
        embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
        if user_id in self.shifts["active"]:
            start_time = self.shifts["active"][user_id]
            start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Opened shift management for user {user_id}")

    @duty_group.command(name="active", description="View active shifts")
    async def duty_active(self, interaction: discord.Interaction):
        """Show all active shifts"""
        if not await self.has_staff_role(interaction):
            return

        if not self.shifts["active"]:
            embed, ephemeral = self.create_embed("Active Shifts", "No active shifts.")
        else:
            description = ""
            for user_id, start_time in self.shifts["active"].items():
                user = await self.bot.fetch_user(int(user_id))
                duration = timedelta(seconds=int(time.time() - start_time))
                start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
                description += f"{user.mention}\n- Start: {start_dt}\n- Duration: {str(duration)}\n\n"
            embed, ephemeral = self.create_embed("Active Shifts", description)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Refresh", style=discord.ButtonStyle.primary, custom_id="refresh_active"))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Displayed active shifts for user {interaction.user.id}")

    @duty_group.command(name="leaderboard", description="View shift leaderboard")
    async def duty_leaderboard(self, interaction: discord.Interaction):
        """Show top 10 shift durations (non-ephemeral)"""
        user_durations = {}
        for shift in self.shifts["history"]:
            user_id = shift["user_id"]
            user_durations[user_id] = user_durations.get(user_id, 0) + shift["duration"]

        sorted_users = sorted(user_durations.items(), key=lambda x: x[1], reverse=True)
        description = ""
        for i, (user_id, duration) in enumerate(sorted_users[:10], 1):
            user = await self.bot.fetch_user(int(user_id))
            duration_str = str(timedelta(seconds=int(duration)))
            description += f"{i}. {user.mention} - {duration_str}\n"
        if not description:
            description = "No shifts recorded."
        embed, _ = self.create_embed("Shift Leaderboard", description, ephemeral=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)
        logger.info(f"Displayed leaderboard for user {interaction.user.id}")

    @duty_group.command(name="wipe", description="Wipe all shift data (Admin only)")
    async def duty_wipe(self, interaction: discord.Interaction):
        """Wipe all shift data with confirmation"""
        if not await self.has_admin_role(interaction):
            return

        embed, ephemeral = self.create_embed("Wipe Confirmation", "Are you sure you want to wipe all shift data? This cannot be undone.")
        view = WipeConfirmationView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Wipe confirmation requested by admin {interaction.user.id}")

    @duty_group.command(name="admin", description="Admin panel for managing a user's shifts (Admin only)")
    @app_commands.describe(user="User to manage")
    async def duty_admin(self, interaction: discord.Interaction, user: discord.User):
        """Admin panel with buttons for user-specific shift management"""
        if not await self.has_admin_role(interaction):
            return

        user_id = str(user.id)
        view = AdminView(self, user)
        embed, ephemeral = self.create_embed("Shift Management")
        embed.add_field(name="User", value=user.mention, inline=False)
        embed.add_field(name="Status", value="On Duty" if user_id in self.shifts["active"] else "Off Duty", inline=True)
        embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
        if user_id in self.shifts["active"]:
            start_time = self.shifts["active"][user_id]
            start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Opened admin panel for user {user.id} by admin {interaction.user.id}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions"""
        if not interaction.data or 'custom_id' not in interaction.data:
            return

        custom_id = interaction.data['custom_id']
        if custom_id.startswith("view_history_"):
            user_id = custom_id.split("_")[-1]
            user = await self.bot.fetch_user(int(user_id))
            history = [shift for shift in self.shifts["history"] if shift["user_id"] == user_id]
            if not history:
                embed, ephemeral = self.create_embed("Shift History", f"No shift history for {user.mention}.")
            else:
                description = ""
                for i, shift in enumerate(history[-5:], 1):  # Show last 5 shifts
                    start_dt = datetime.fromtimestamp(shift["start"]).strftime('%Y-%m-%d %H:%M:%S')
                    end_dt = datetime.fromtimestamp(shift["end"]).strftime('%Y-%m-%d %H:%M:%S') if "end" in shift else "Ongoing"
                    duration = str(timedelta(seconds=int(shift["duration"]))) if "duration" in shift else "N/A"
                    description += f"**Shift {i}**\nStart: {start_dt}\nEnd: {end_dt}\nDuration: {duration}\n\n"
                embed, ephemeral = self.create_embed(f"Shift History for {user.name}", description)
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.info(f"Displayed shift history for user {user_id} by {interaction.user.id}")
        elif custom_id == "refresh_active":
            if not await self.has_staff_role(interaction):
                embed, ephemeral = self.create_embed("Error", "You need the Staff or Admin role to use this button.")
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                return
            if not self.shifts["active"]:
                embed, ephemeral = self.create_embed("Active Shifts", "No active shifts.")
            else:
                description = ""
                for user_id, start_time in self.shifts["active"].items():
                    user = await self.bot.fetch_user(int(user_id))
                    duration = timedelta(seconds=int(time.time() - start_time))
                    start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
                    description += f"{user.mention}\n- Start: {start_dt}\n- Duration: {str(duration)}\n\n"
                embed, ephemeral = self.create_embed("Active Shifts", description)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Refresh", style=discord.ButtonStyle.primary, custom_id="refresh_active"))
            await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
            logger.info(f"Refreshed active shifts for user {interaction.user.id}")
        elif custom_id.startswith("manage_"):
            action, user_id = custom_id.split("_")[1:]
            user = await self.bot.fetch_user(int(user_id))
            if interaction.user.id != int(user_id):
                embed, ephemeral = self.create_embed("Error", "You can only manage your own shift.")
                await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                return
            view = ManageView(self, user)
            if action == "start":
                if user_id in self.shifts["active"]:
                    embed, ephemeral = self.create_embed("Error", "You are already on duty.")
                else:
                    self.shifts["active"][user_id] = time.time()
                    self.save_shifts()
                    embed, ephemeral = self.create_embed("Shift Management")
                    embed.add_field(name="Status", value="On Duty", inline=True)
                    embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
                    start_dt = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                    embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Started shift for user {user_id}")
            elif action == "stop":
                if user_id not in self.shifts["active"]:
                    embed, ephemeral = self.create_embed("Error", "You are not on duty.")
                else:
                    start_time = self.shifts["active"][user_id]
                    end_time = time.time()
                    duration = end_time - start_time
                    self.shifts["history"].append({
                        "user_id": user_id,
                        "start": start_time,
                        "end": end_time,
                        "duration": duration
                    })
                    del self.shifts["active"][user_id]
                    self.save_shifts()
                    embed, ephemeral = self.create_embed("Shift Management")
                    embed.add_field(name="Status", value="Off Duty", inline=True)
                    embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Ended shift for user {user_id}")
            elif action == "time":
                embed, ephemeral = self.create_embed("Shift Management")
                embed.add_field(name="Status", value="On Duty" if user_id in self.shifts["active"] else "Off Duty", inline=True)
                embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
                if user_id in self.shifts["active"]:
                    start_time = self.shifts["active"][user_id]
                    start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
                    embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Displayed total duty time for user {user_id}")
            elif action == "history":
                history = [shift for shift in self.shifts["history"] if shift["user_id"] == user_id]
                if not history:
                    embed, ephemeral = self.create_embed("Shift History", "No shift history available.")
                else:
                    description = ""
                    for i, shift in enumerate(history[-5:], 1):  # Show last 5 shifts
                        start_dt = datetime.fromtimestamp(shift["start"]).strftime('%Y-%m-%d %H:%M:%S')
                        end_dt = datetime.fromtimestamp(shift["end"]).strftime('%Y-%m-%d %H:%M:%S') if "end" in shift else "Ongoing"
                        duration = str(timedelta(seconds=int(shift["duration"]))) if "duration" in shift else "N/A"
                        description += f"**Shift {i}**\nStart: {start_dt}\nEnd: {end_dt}\nDuration: {duration}\n\n"
                    embed, ephemeral = self.create_embed(f"Shift History for {user.name}", description)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Displayed shift history for user {user_id}")
        elif custom_id.startswith("admin_"):
            action, user_id = custom_id.split("_")[1:3]
            user = await self.bot.fetch_user(int(user_id))
            if not await self.has_admin_role(interaction):
                return
            view = AdminView(self, user)
            if action == "start":
                if user_id in self.shifts["active"]:
                    embed, ephemeral = self.create_embed("Error", f"{user.mention} is already on duty.")
                else:
                    self.shifts["active"][user_id] = time.time()
                    self.save_shifts()
                    embed, ephemeral = self.create_embed("Shift Management")
                    embed.add_field(name="User", value=user.mention, inline=False)
                    embed.add_field(name="Status", value="On Duty", inline=True)
                    embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
                    start_dt = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
                    embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Started shift for user {user_id} by admin {interaction.user.id}")
            elif action == "stop":
                if user_id not in self.shifts["active"]:
                    embed, ephemeral = self.create_embed("Error", f"{user.mention} is not on duty.")
                else:
                    start_time = self.shifts["active"][user_id]
                    end_time = time.time()
                    duration = end_time - start_time
                    self.shifts["history"].append({
                        "user_id": user_id,
                        "start": start_time,
                        "end": end_time,
                        "duration": duration
                    })
                    del self.shifts["active"][user_id]
                    self.save_shifts()
                    embed, ephemeral = self.create_embed("Shift Management")
                    embed.add_field(name="User", value=user.mention, inline=False)
                    embed.add_field(name="Status", value="Off Duty", inline=True)
                    embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Ended shift for user {user_id} by admin {interaction.user.id}")
            elif action == "time":
                embed, ephemeral = self.create_embed("Shift Management")
                embed.add_field(name="User", value=user.mention, inline=False)
                embed.add_field(name="Status", value="On Duty" if user_id in self.shifts["active"] else "Off Duty", inline=True)
                embed.add_field(name="Total Duty Time", value=self.get_total_duty_time(user_id) or "0:00:00", inline=True)
                if user_id in self.shifts["active"]:
                    start_time = self.shifts["active"][user_id]
                    start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
                    embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Displayed total duty time for user {user_id} by admin {interaction.user.id}")
            elif action == "history":
                history = [shift for shift in self.shifts["history"] if shift["user_id"] == user_id]
                if not history:
                    embed, ephemeral = self.create_embed("Shift History", f"No shift history for {user.mention}.")
                else:
                    description = ""
                    for i, shift in enumerate(history[-5:], 1):  # Show last 5 shifts
                        start_dt = datetime.fromtimestamp(shift["start"]).strftime('%Y-%m-%d %H:%M:%S')
                        end_dt = datetime.fromtimestamp(shift["end"]).strftime('%Y-%m-%d %H:%M:%S') if "end" in shift else "Ongoing"
                        duration = str(timedelta(seconds=int(shift["duration"]))) if "duration" in shift else "N/A"
                        description += f"**Shift {i}**\nStart: {start_dt}\nEnd: {end_dt}\nDuration: {duration}\n\n"
                    embed, ephemeral = self.create_embed(f"Shift History for {user.name}", description)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                logger.info(f"Displayed shift history for user {user_id} by admin {interaction.user.id}")

class WipeConfirmationView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=30)
        self.cog = cog

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        self.cog.shifts = {"active": {}, "history": []}
        self.cog.save_shifts()
        embed, ephemeral = self.cog.create_embed("Success", "All shift data has been wiped.")
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        logger.info(f"Shift data wiped by admin {interaction.user.id}")
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, ephemeral = self.cog.create_embed("Cancelled", "Shift data wipe cancelled.")
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        logger.info(f"Wipe cancelled by admin {interaction.user.id}")
        self.stop()

class ManageView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user

    @discord.ui.button(label="Start Shift", style=discord.ButtonStyle.green, custom_id="manage_start")
    async def start_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            embed, ephemeral = self.cog.create_embed("Error", "You can only manage your own shift.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return
        user_id = str(self.user.id)
        view = ManageView(self.cog, self.user)
        if user_id in self.cog.shifts["active"]:
            embed, ephemeral = self.cog.create_embed("Error", "You are already on duty.")
        else:
            self.cog.shifts["active"][user_id] = time.time()
            self.cog.save_shifts()
            embed, ephemeral = self.cog.create_embed("Shift Management")
            embed.add_field(name="Status", value="On Duty", inline=True)
            embed.add_field(name="Total Duty Time", value=self.cog.get_total_duty_time(user_id) or "0:00:00", inline=True)
            start_dt = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Started shift for user {user_id}")

    @discord.ui.button(label="Stop Shift", style=discord.ButtonStyle.red, custom_id="manage_stop")
    async def stop_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            embed, ephemeral = self.cog.create_embed("Error", "You can only manage your own shift.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return
        user_id = str(self.user.id)
        view = ManageView(self.cog, self.user)
        if user_id not in self.cog.shifts["active"]:
            embed, ephemeral = self.cog.create_embed("Error", "You are not on duty.")
        else:
            start_time = self.cog.shifts["active"][user_id]
            end_time = time.time()
            duration = end_time - start_time
            self.cog.shifts["history"].append({
                "user_id": user_id,
                "start": start_time,
                "end": end_time,
                "duration": duration
            })
            del self.cog.shifts["active"][user_id]
            self.cog.save_shifts()
            embed, ephemeral = self.cog.create_embed("Shift Management")
            embed.add_field(name="Status", value="Off Duty", inline=True)
            embed.add_field(name="Total Duty Time", value=self.cog.get_total_duty_time(user_id) or "0:00:00", inline=True)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Ended shift for user {user_id}")

    @discord.ui.button(label="View Duty Time", style=discord.ButtonStyle.secondary, custom_id="manage_time")
    async def view_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            embed, ephemeral = self.cog.create_embed("Error", "You can only manage your own shift.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return
        user_id = str(self.user.id)
        view = ManageView(self.cog, self.user)
        embed, ephemeral = self.cog.create_embed("Shift Management")
        embed.add_field(name="Status", value="On Duty" if user_id in self.cog.shifts["active"] else "Off Duty", inline=True)
        embed.add_field(name="Total Duty Time", value=self.cog.get_total_duty_time(user_id) or "0:00:00", inline=True)
        if user_id in self.cog.shifts["active"]:
            start_time = self.cog.shifts["active"][user_id]
            start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Displayed total duty time for user {user_id}")

    @discord.ui.button(label="View History", style=discord.ButtonStyle.primary, custom_id="manage_history")
    async def view_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            embed, ephemeral = self.cog.create_embed("Error", "You can only manage your own shift.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return
        user_id = str(self.user.id)
        view = ManageView(self.cog, self.user)
        history = [shift for shift in self.shifts["history"] if shift["user_id"] == user_id] # type: ignore
        if not history:
            embed, ephemeral = self.cog.create_embed("Shift History", "No shift history available.")
        else:
            description = ""
            for i, shift in enumerate(history[-5:], 1):  # Show last 5 shifts
                start_dt = datetime.fromtimestamp(shift["start"]).strftime('%Y-%m-%d %H:%M:%S')
                end_dt = datetime.fromtimestamp(shift["end"]).strftime('%Y-%m-%d %H:%M:%S') if "end" in shift else "Ongoing"
                duration = str(timedelta(seconds=int(shift["duration"]))) if "duration" in shift else "N/A"
                description += f"**Shift {i}**\nStart: {start_dt}\nEnd: {end_dt}\nDuration: {duration}\n\n"
            embed, ephemeral = self.cog.create_embed(f"Shift History for {self.user.name}", description)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Displayed shift history for user {user_id}")

class AdminView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user

    @discord.ui.button(label="Start Shift", style=discord.ButtonStyle.green, custom_id="admin_start")
    async def start_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        user_id = str(self.user.id)
        view = AdminView(self.cog, self.user)
        if user_id in self.cog.shifts["active"]:
            embed, ephemeral = self.cog.create_embed("Error", f"{self.user.mention} is already on duty.")
        else:
            self.cog.shifts["active"][user_id] = time.time()
            self.cog.save_shifts()
            embed, ephemeral = self.cog.create_embed("Shift Management")
            embed.add_field(name="User", value=self.user.mention, inline=False)
            embed.add_field(name="Status", value="On Duty", inline=True)
            embed.add_field(name="Total Duty Time", value=self.cog.get_total_duty_time(user_id) or "0:00:00", inline=True)
            start_dt = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Started shift for user {user_id} by admin {interaction.user.id}")

    @discord.ui.button(label="Stop Shift", style=discord.ButtonStyle.red, custom_id="admin_stop")
    async def stop_shift(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        user_id = str(self.user.id)
        view = AdminView(self.cog, self.user)
        if user_id not in self.cog.shifts["active"]:
            embed, ephemeral = self.cog.create_embed("Error", f"{self.user.mention} is not on duty.")
        else:
            start_time = self.cog.shifts["active"][user_id]
            end_time = time.time()
            duration = end_time - start_time
            self.cog.shifts["history"].append({
                "user_id": user_id,
                "start": start_time,
                "end": end_time,
                "duration": duration
            })
            del self.cog.shifts["active"][user_id]
            self.cog.save_shifts()
            embed, ephemeral = self.cog.create_embed("Shift Management")
            embed.add_field(name="User", value=self.user.mention, inline=False)
            embed.add_field(name="Status", value="Off Duty", inline=True)
            embed.add_field(name="Total Duty Time", value=self.cog.get_total_duty_time(user_id) or "0:00:00", inline=True)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Ended shift for user {user_id} by admin {interaction.user.id}")

    @discord.ui.button(label="View Duty Time", style=discord.ButtonStyle.secondary, custom_id="admin_time")
    async def view_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        user_id = str(self.user.id)
        view = AdminView(self.cog, self.user)
        embed, ephemeral = self.cog.create_embed("Shift Management")
        embed.add_field(name="User", value=self.user.mention, inline=False)
        embed.add_field(name="Status", value="On Duty" if user_id in self.cog.shifts["active"] else "Off Duty", inline=True)
        embed.add_field(name="Total Duty Time", value=self.cog.get_total_duty_time(user_id) or "0:00:00", inline=True)
        if user_id in self.cog.shifts["active"]:
            start_time = self.cog.shifts["active"][user_id]
            start_dt = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            embed.add_field(name="Current Shift Start", value=start_dt, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Displayed total duty time for user {user_id} by admin {interaction.user.id}")

    @discord.ui.button(label="View History", style=discord.ButtonStyle.primary, custom_id="admin_history")
    async def view_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        user_id = str(self.user.id)
        view = AdminView(self.cog, self.user)
        history = [shift for shift in self.cog.shifts["history"] if shift["user_id"] == user_id]
        if not history:
            embed, ephemeral = self.cog.create_embed("Shift History", f"No shift history for {self.user.mention}.")
        else:
            description = ""
            for i, shift in enumerate(history[-5:], 1):  # Show last 5 shifts
                start_dt = datetime.fromtimestamp(shift["start"]).strftime('%Y-%m-%d %H:%M:%S')
                end_dt = datetime.fromtimestamp(shift["end"]).strftime('%Y-%m-%d %H:%M:%S') if "end" in shift else "Ongoing"
                duration = str(timedelta(seconds=int(shift["duration"]))) if "duration" in shift else "N/A"
                description += f"**Shift {i}**\nStart: {start_dt}\nEnd: {end_dt}\nDuration: {duration}\n\n"
            embed, ephemeral = self.cog.create_embed(f"Shift History for {self.user.name}", description)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
        logger.info(f"Displayed shift history for user {user_id} by admin {interaction.user.id}")

    @discord.ui.button(label="Add Time", style=discord.ButtonStyle.secondary, custom_id="admin_add_time")
    async def add_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        await interaction.response.send_modal(AddTimeModal(self.cog, self.user))

    @discord.ui.button(label="Remove Time", style=discord.ButtonStyle.secondary, custom_id="admin_remove_time")
    async def remove_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.cog.has_admin_role(interaction):
            return
        await interaction.response.send_modal(RemoveTimeModal(self.cog, self.user))

class AddTimeModal(discord.ui.Modal, title="Add Shift Time"):
    def __init__(self, cog, user):
        super().__init__()
        self.cog = cog
        self.user = user
        self.minutes = discord.ui.TextInput(label="Minutes to Add", placeholder="Enter minutes (e.g., 30)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = int(self.minutes.value)
            if minutes <= 0:
                raise ValueError("Minutes must be positive")
            user_id = str(self.user.id)
            duration = minutes * 60
            self.cog.shifts["history"].append({
                "user_id": user_id,
                "start": time.time() - duration,
                "end": time.time(),
                "duration": duration
            })
            self.cog.save_shifts()
            embed, ephemeral = self.cog.create_embed("Success", f"Added {minutes} minutes to {self.user.mention}'s shift history.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.info(f"Added {minutes} minutes to user {user_id} by admin {interaction.user.id}")
        except ValueError as e:
            embed, ephemeral = self.cog.create_embed("Error", f"Invalid input: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.error(f"Failed to add time for user {user_id}: {str(e)}")

class RemoveTimeModal(discord.ui.Modal, title="Remove Shift Time"):
    def __init__(self, cog, user):
        super().__init__()
        self.cog = cog
        self.user = user
        self.minutes = discord.ui.TextInput(label="Minutes to Remove", placeholder="Enter minutes (e.g., 30)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = int(self.minutes.value)
            if minutes <= 0:
                raise ValueError("Minutes must be positive")
            user_id = str(self.user.id)
            duration = minutes * 60
            for i, shift in enumerate(reversed(self.cog.shifts["history"])):
                if shift["user_id"] == user_id and shift["duration"] >= duration:
                    self.cog.shifts["history"][-(i+1)]["duration"] -= duration
                    self.cog.shifts["history"][-(i+1)]["end"] = self.cog.shifts["history"][-(i+1)]["start"] + self.cog.shifts["history"][-(i+1)]["duration"]
                    if self.cog.shifts["history"][-(i+1)]["duration"] <= 0:
                        del self.cog.shifts["history"][-(i+1)]
                    self.cog.save_shifts()
                    embed, ephemeral = self.cog.create_embed("Success", f"Removed {minutes} minutes from {self.user.mention}'s last shift.")
                    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                    logger.info(f"Removed {minutes} minutes from user {user_id} by admin {interaction.user.id}")
                    return
            embed, ephemeral = self.cog.create_embed("Error", f"No suitable shift found for {self.user.mention} to remove {minutes} minutes.")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.info(f"No shift found to remove time for user {user_id}")
        except ValueError as e:
            embed, ephemeral = self.cog.create_embed("Error", f"Invalid input: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            logger.error(f"Failed to remove time for user {user_id}: {str(e)}")

async def setup(bot):
    await bot.add_cog(Shifts(bot))