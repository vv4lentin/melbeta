import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
ERLC_API_KEY = os.getenv('ERLC_API_KEY')  # Set in .env file
BASE_URL = 'https://api.policeroleplay.community/v1'
MODERATIONS_FILE = 'moderations.json'
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', '0'))  # Set in .env file for moderation logs
RESTRICTED_ROLE_ID = 1384466481831608381  # Role ID for command access

# Custom check for role restriction
def has_restricted_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, id=RESTRICTED_ROLE_ID) # type: ignore
        if role is None:
            raise app_commands.MissingRole(RESTRICTED_ROLE_ID)
        return True
    return app_commands.check(predicate)

class RevokeModal(discord.ui.Modal, title='Revoke Moderation'):
    mod_id = discord.ui.TextInput(
        label='Moderation ID',
        placeholder='ID',
        required=True,
        max_length=10
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mod_id = int(self.mod_id.value)
            moderations = self.cog.load_moderations()
            
            revoked = False
            for mod in moderations:
                if mod['id'] == mod_id and not mod.get('revoked', False):
                    mod['revoked'] = True
                    mod['revoke_time'] = datetime.utcnow().isoformat()
                    mod['revoked_by'] = str(interaction.user)
                    revoked = True
                    break
            
            if revoked:
                self.cog.save_moderations(moderations)
                # Log to Discord channel
                if LOG_CHANNEL_ID:
                    channel = interaction.guild.get_channel(LOG_CHANNEL_ID) # type: ignore
                    if channel:
                        embed = discord.Embed(
                            title='Moderation Revoked',
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                        embed.add_field(name='Moderation ID', value=str(mod_id), inline=True)
                        embed.add_field(name='Revoked By', value=interaction.user.mention, inline=True)
                        embed.set_footer(text='Melbourne Roleplay')
                        await channel.send(embed=embed) # type: ignore
                await interaction.response.send_message('Moderation revoked successfully!', ephemeral=True)
            else:
                await interaction.response.send_message('Moderation not found or already revoked.', ephemeral=True)
        except ValueError:
            await interaction.response.send_message('Invalid ID format.', ephemeral=True)
        except Exception as e:
            logger.error(f"Error in RevokeModal: {str(e)}")
            await interaction.response.send_message(f'Error: {str(e)}', ephemeral=True)

class CompleteBoloModal(discord.ui.Modal, title='Complete BOLO'):
    mod_id = discord.ui.TextInput(
        label='BOLO ID',
        placeholder='ID',
        required=True,
        max_length=10
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mod_id = int(self.mod_id.value)
            moderations = self.cog.load_moderations()
            
            completed = False
            for mod in moderations:
                if mod['id'] == mod_id and mod['type'] == 'bolo' and not mod.get('revoked', False):
                    mod['revoked'] = True
                    mod['status'] = 'completed'
                    mod['revoke_time'] = datetime.utcnow().isoformat()
                    mod['completed_by'] = str(interaction.user)
                    completed = True
                    break
            
            if completed:
                self.cog.save_moderations(moderations)
                # Log to Discord channel
                if LOG_CHANNEL_ID:
                    channel = interaction.guild.get_channel(LOG_CHANNEL_ID) # type: ignore
                    if channel:
                        embed = discord.Embed(
                            title='BOLO Completed',
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                        embed.add_field(name='BOLO ID', value=str(mod_id), inline=True)
                        embed.add_field(name='Completed By', value=interaction.user.mention, inline=True)
                        embed.set_footer(text='Melbourne Roleplay')
                        await channel.send(embed=embed) # type: ignore
                await interaction.response.send_message('BOLO completed successfully!', ephemeral=True)
            else:
                await interaction.response.send_message('BOLO not found or already handled.', ephemeral=True)
        except ValueError:
            await interaction.response.send_message('Invalid ID.', ephemeral=True)
        except Exception as e:
            logger.error(f"Error in CompleteBoloModal: {str(e)}")
            await interaction.response.send_message(f'Error: {str(e)}', ephemeral=True)

class ModerationView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label='Revoke Moderation', style=discord.ButtonStyle.danger)
    async def revoke(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RevokeModal(self.cog))

class BoloView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label='Revoke BOLO', style=discord.ButtonStyle.danger)
    async def revoke_bolo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RevokeModal(self.cog))

    @discord.ui.button(label='Complete BOLO', style=discord.ButtonStyle.success)
    async def complete_bolo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CompleteBoloModal(self.cog))

class InfoView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label='Refresh', style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            # Call the erlc_info command logic directly
            await self.cog.erlc_info.callback(self.cog, interaction)
        except Exception as e:
            logger.error(f"Error in refresh button: {str(e)}")
            await interaction.followup.send(f'Error refreshing info: {str(e)}', ephemeral=True)

class ERLCIntegration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moderations = self.load_moderations()

    def load_moderations(self):
        try:
            if os.path.exists(MODERATIONS_FILE):
                with open(MODERATIONS_FILE, 'r') as f:
                    data = json.load(f)
                    # Ensure data is a list
                    if not isinstance(data, list):
                        logger.warning(f"Moderations file is not a list, resetting to empty list")
                        return []
                    return data
            return []
        except json.JSONDecodeError:
            logger.error(f"Corrupted moderations.json, resetting to empty list")
            return []
        except Exception as e:
            logger.error(f"Error loading moderations: {str(e)}")
            return []

    def save_moderations(self, moderations):
        try:
            with open(MODERATIONS_FILE, 'w') as f:
                json.dump(moderations, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving moderations: {str(e)}")

    async def get_roblox_user_info(self, user_id):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://users.roblox.com/v1/users/{user_id}') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        username = data.get('name', 'Unknown')
                        # Fetch avatar thumbnail
                        async with session.get(f'https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png') as avatar_resp:
                            if avatar_resp.status == 200:
                                avatar_data = await avatar_resp.json()
                                avatar_url = avatar_data.get('data', [{}])[0].get('imageUrl', None)
                            else:
                                avatar_url = None
                        return username, avatar_url
                    return 'Unknown', None
        except Exception as e:
            logger.error(f"Error fetching Roblox user info for ID {user_id}: {str(e)}")
            return 'Unknown', None

    @app_commands.command(name='erlc_info')
    @has_restricted_role()
    async def erlc_info(self, interaction: discord.Interaction):
        if not ERLC_API_KEY:
            await interaction.response.send_message('API key not configured. Please contact @vavax989', ephemeral=True)
            return

        headers = {'Server-Key': ERLC_API_KEY}

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch server info
                async with session.get(f'{BASE_URL}/server', headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message('Failed to fetch server info. Check API key or server status.', ephemeral=True)
                        return
                    server_data = await resp.json()

                # Fetch players
                async with session.get(f'{BASE_URL}/server/players', headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message('Failed to fetch player data.', ephemeral=True)
                        return
                    players_data = await resp.json()

                # Fetch queue
                async with session.get(f'{BASE_URL}/server/queue', headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message('Failed to fetch queue data.', ephemeral=True)
                        return
                    queue_data = await resp.json()

                # Fetch staff configuration
                async with session.get(f'{BASE_URL}/server/staff', headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message('Failed to fetch staff data.', ephemeral=True)
                        return
                    staff_data = await resp.json()

            players_count = server_data.get('CurrentPlayers', 0)
            max_players = server_data.get('MaxPlayers', 0)
            queue_count = len(queue_data)
            staff_online = sum(1 for p in players_data if p.get('Permission') in ['Server Moderator', 'Server Administrator', 'Server Owner'])

            server_name = server_data.get('Name', 'Unknown')
            join_code = server_data.get('JoinKey', 'N/A')

            # Fetch owner and co-owner info
            owner_id = server_data.get('OwnerId', 0)
            owner_name, owner_avatar = await self.get_roblox_user_info(owner_id)

            co_owner_ids = staff_data.get('CoOwners', [])
            co_owners = []
            for co_id in co_owner_ids:
                name, _ = await self.get_roblox_user_info(co_id)
                if name != 'Unknown':
                    co_owners.append(name)

            embed = discord.Embed(
                title=f'{server_name}',
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_thumbnail(url=owner_avatar if owner_avatar else '')  # Fallback image
            embed.add_field(name='Server Code', value=join_code, inline=True)
            embed.add_field(name='Players', value=f'{players_count}/{max_players}', inline=True)
            embed.add_field(name='Staff Online', value=str(staff_online), inline=True)
            embed.add_field(name='Queue', value=str(queue_count), inline=True)
            embed.add_field(name='Owner', value=owner_name, inline=False)
            co_owner_str = ', '.join(co_owners[:5]) + ('...' if len(co_owners) > 5 else '') or 'None'
            embed.add_field(name='Co-Owners', value=co_owner_str, inline=False)
            embed.set_footer(text='Melbourne Roleplay')

            view = InfoView(self)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in erlc_info: {str(e)}")
            await interaction.response.send_message(f'Error fetching server info: {str(e)}', ephemeral=True)

    @app_commands.command(name='moderate')
    @app_commands.describe(username='Roblox username', type='Moderation type', reason='Reason for moderation')
    @app_commands.choices(type=[
        app_commands.Choice(name='Warn', value='warn'),
        app_commands.Choice(name='Kick', value='kick'),
        app_commands.Choice(name='Ban', value='ban'),
        app_commands.Choice(name='BOLO', value='bolo')
    ])
    @has_restricted_role()
    async def moderate(self, interaction: discord.Interaction, username: str, type: str, reason: str):
        try:
            moderations = self.load_moderations()
            mod_id = len(moderations) + 1
            mod_entry = {
                'id': mod_id,
                'username': username,
                'type': type,
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat(),
                'moderator': str(interaction.user),
                'revoked': False,
                'revoke_time': None,
                'status': None
            }
            moderations.append(mod_entry)
            self.save_moderations(moderations)

            avatar_url = None
            # Fetch Roblox avatar for the moderated user
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://users.roblox.com/v1/users/search?keyword={username}&limit=10') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        user_id = next((user['id'] for user in data.get('data', []) if user['name'].lower() == username.lower()), None)
                        if user_id:
                            async with session.get(f'https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png') as avatar_resp:
                                if avatar_resp.status == 200:
                                    avatar_data = await avatar_resp.json()
                                    avatar_url = avatar_data.get('data', [{}])[0].get('imageUrl', None)

            # Log to Discord channel
            if LOG_CHANNEL_ID:
                channel = interaction.guild.get_channel(LOG_CHANNEL_ID) # type: ignore
                if channel:
                    embed = discord.Embed(
                        title=f'{type.upper()} Issued',
                        color=discord.Color.red() if type in ['ban', 'bolo'] else discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                    embed.set_thumbnail(url=avatar_url if avatar_url else 'https://i.imgur.com/4M34hi2.png')
                    embed.add_field(name='User', value=username, inline=True)
                    embed.add_field(name='Type', value=type.upper(), inline=True)
                    embed.add_field(name='Reason', value=reason[:1000], inline=False)
                    embed.add_field(name='ID', value=str(mod_id), inline=True)
                    embed.add_field(name='Moderator', value=interaction.user.mention, inline=True)
                    embed.set_footer(text='Melbourne Roleplay')
                    await channel.send(embed=embed) # type: ignore

            # Response embed
            embed = discord.Embed(
                title=f'{type.upper()} Issued',
                color=discord.Color.red() if type in ['ban', 'bolo'] else discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_thumbnail(url=avatar_url if avatar_url else 'https://i.imgur.com/4M34hi2.png')
            embed.add_field(name='User', value=username, inline=True)
            embed.add_field(name='Type', value=type.upper(), inline=True)
            embed.add_field(name='Reason', value=reason[:1000], inline=False)
            embed.add_field(name='ID', value=str(mod_id), inline=True)
            embed.add_field(name='Moderator', value=interaction.user.mention, inline=True)
            embed.set_footer(text='ERLC Moderation')

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in moderate: {str(e)}")
            await interaction.response.send_message(f'Error issuing moderation: {str(e)}', ephemeral=True)

    @app_commands.command(name='search')
    @app_commands.describe(username='Roblox username to search')
    @has_restricted_role()
    async def search(self, interaction: discord.Interaction, username: str):
        try:
            moderations = self.load_moderations()
            matching = [mod for mod in moderations if username.lower() in mod['username'].lower() and not mod.get('revoked', False)]
            
            if not matching:
                await interaction.response.send_message(f'No active moderations found for "{username}".', ephemeral=True)
                return

            avatar_url = None
            # Fetch Roblox avatar for the searched user
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://users.roblox.com/v1/users/search?keyword={username}&limit=10') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        user_id = next((user['id'] for user in data.get('data', []) if user['name'].lower() == username.lower()), None)
                        if user_id:
                            async with session.get(f'https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=48x48&format=Png') as avatar_resp:
                                if avatar_resp.status == 200:
                                    avatar_data = await avatar_resp.json()
                                    avatar_url = avatar_data.get('data', [{}])[0].get('imageUrl', None)

            embed = discord.Embed(
                title=f'Active Moderations for {username}',
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_thumbnail(url=avatar_url if avatar_url else '')
            for mod in matching[:10]:  # Limit to 10
                status = f"**Type:** {mod['type'].upper()}\n**Reason:** {mod['reason'][:100]}{'...' if len(mod['reason']) > 100 else ''}\n**ID:** {mod['id']}\n**Issued:** {mod['timestamp'][:16]}\n**Moderator:** {mod['moderator']}"
                embed.add_field(name=f"Moderation #{mod['id']}", value=status, inline=False)

            if len(matching) > 10:
                embed.set_footer(text=f'And {len(matching) - 10} more... | Melbourne Roleplay')
            else:
                embed.set_footer(text='Melbourne Roleplay')

            view = ModerationView(self)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            await interaction.response.send_message(f'Error searching moderations: {str(e)}', ephemeral=True)

    @app_commands.command(name='bolos')
    @has_restricted_role()
    async def bolos(self, interaction: discord.Interaction):
        try:
            moderations = self.load_moderations()
            active_bolos = [mod for mod in moderations if mod['type'] == 'bolo' and not mod.get('revoked', False)]
            
            if not active_bolos:
                await interaction.response.send_message('No active BOLOs found.', ephemeral=True)
                return

            embed = discord.Embed(
                title='Active BOLOs',
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            for bolo in active_bolos[:10]:  # Limit to 10
                info = f"**User:** {bolo['username']}\n**Reason:** {bolo['reason'][:100]}{'...' if len(bolo['reason']) > 100 else ''}\n**ID:** {bolo['id']}\n**Issued:** {bolo['timestamp'][:16]}\n**Moderator:** {bolo['moderator']}"
                embed.add_field(name=f"BOLO #{bolo['id']}", value=info, inline=False)

            if len(active_bolos) > 10:
                embed.set_footer(text=f'And {len(active_bolos) - 10} more... | ERLC BOLO List')
            else:
                embed.set_footer(text='Melbourne Roleplay')

            view = BoloView(self)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in bolos: {str(e)}")
            await interaction.response.send_message(f'Error listing BOLOs: {str(e)}', ephemeral=True)

async def setup(bot):
    await bot.add_cog(ERLCIntegration(bot))