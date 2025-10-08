import discord
from discord.ext import commands
import os
import time
import asyncio
from discord import Embed, Colour, Activity, ActivityType, Status, ui, Interaction

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# Configuration
RESTRICTED_ROLE_ID = 1383401266998153216
EMBED_COLOR = 0x19385f  # Hex color #19385f
FOOTER_TEXT = "Melbourne Roleplay"
START_TIME = time.time()  # Track bot start time for uptime

# Custom cog names mapping
COG_NAMES = {
    "callsigns": "Discord Commands",
    "shifts": "Shift",
    "erlc_commands": "Roblox Commands",
    "erlc_moderations": "ER:LC Integration",
    "jishaku": "Jishaku",
    "ticket_system": "Tickets",
}

async def has_restricted_role(ctx):
    """Check if user has the restricted role"""
    role = discord.utils.get(ctx.guild.roles, id=RESTRICTED_ROLE_ID)
    if not role:
        await ctx.send(embed=Embed(
            title="Melbourne Roleplay",
            description="**Error**\nRestricted role not found.",
            color=Colour(EMBED_COLOR)
        ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
        return False
    if role not in ctx.author.roles:
        await ctx.send(embed=Embed(
            title="Melbourne Roleplay",
            description="**Error**\nYou don't have permission to use this command.",
            color=Colour(EMBED_COLOR)
        ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
        return False
    return True

# Modal for server ID input
class LeaveServerModal(ui.Modal, title="Leave Server"):
    server_id = ui.TextInput(label="Server ID", placeholder="Enter the server ID to leave")

    async def on_submit(self, interaction: Interaction):
        try:
            guild_id = int(self.server_id.value)
            guild = bot.get_guild(guild_id)
            if guild:
                await guild.leave()
                await interaction.response.send_message(embed=Embed(
                    description=f"Successfully left server {guild.name}!",
                    color=Colour(EMBED_COLOR)
                ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
            else:
                await interaction.response.send_message(embed=Embed(
                    title="Melbourne Roleplay",
                    description="**Error**\nServer not found or bot is not in that server.",
                    color=Colour(EMBED_COLOR)
                ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
        except ValueError:
            await interaction.response.send_message(embed=Embed(
                title="Melbourne Roleplay",
                description="**Error**\nInvalid server ID format.",
                color=Colour(EMBED_COLOR)
            ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore

# View for server buttons
class ServerButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Leave Server", style=discord.ButtonStyle.red)
    async def leave_server(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(LeaveServerModal())

# View for stop command buttons
class StopButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Shutdown Bot", style=discord.ButtonStyle.red)
    async def shutdown_button(self, interaction: Interaction, button: ui.Button):
        # Check if user has the restricted role
        role = discord.utils.get(interaction.guild.roles, id=RESTRICTED_ROLE_ID) # type: ignore
        if not role or role not in interaction.user.roles: # type: ignore
            await interaction.response.send_message(embed=Embed(
                title="Melbourne Roleplay",
                description="**Error**\nYou don't have permission to use this button.",
                color=Colour(EMBED_COLOR)
            ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None), ephemeral=True) # type: ignore
            return

        embed = Embed(
            title="Shutting Down",
            description="Bot is shutting down...",
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=FOOTER_TEXT)
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # pyright: ignore[reportOptionalMemberAccess]
        await interaction.response.send_message(embed=embed)
        await bot.close()

# View for purge confirmation
class PurgeButtons(ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=30)
        self.channel_id = channel_id

    @ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: Interaction, button: ui.Button):
        # Check if user has the restricted role
        role = discord.utils.get(interaction.guild.roles, id=RESTRICTED_ROLE_ID) # pyright: ignore[reportOptionalMemberAccess]
        if not role or role not in interaction.user.roles: # pyright: ignore[reportAttributeAccessIssue]
            await interaction.response.send_message(embed=Embed(
                title="Melbourne Roleplay",
                description="**Error**\nYou don't have permission to use this button.",
                color=Colour(EMBED_COLOR)
            ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None), ephemeral=True) # pyright: ignore[reportOptionalMemberAccess]
            return

        try:
            channel = bot.get_channel(int(self.channel_id))
            if not channel:
                await interaction.response.send_message(embed=Embed(
                    title="Melbourne Roleplay",
                    description="**Error**\nChannel not found or bot cannot access it.",
                    color=Colour(EMBED_COLOR),
                    timestamp=discord.utils.utcnow()
                ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # pyright: ignore[reportOptionalMemberAccess]
                return

            deleted_count = 0
            async for message in channel.history(limit=None): # type: ignore
                if not message.pinned:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)  # 0.5-second cooldown to avoid rate limits

            await interaction.response.send_message(embed=Embed(
                title="Purge Complete",
                description=f"Successfully deleted {deleted_count} non-pinned message(s) in {channel.mention}.", # type: ignore
                color=Colour(EMBED_COLOR),
                timestamp=discord.utils.utcnow()
            ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
        except Exception as e:
            await interaction.response.send_message(embed=Embed(
                title="Melbourne Roleplay",
                description=f"**Error**\nAn error occurred: {str(e)}",
                color=Colour(EMBED_COLOR),
                timestamp=discord.utils.utcnow()
            ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore

    @ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message(embed=Embed(
            title="Purge Cancelled",
            description="Purge operation cancelled.",
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
        self.stop()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}') # type: ignore
    # Load discord_commands cog automatically
    try:
        await bot.load_extension("shifts")
        print("Loaded shifts cog")
    except Exception as e:
        print(f"Failed to load shifts cog: {str(e)}")
    try:
        await bot.load_extension("erlc_moderations")
        print("Loaded ERLC MODS cog")
    except Exception as e:
        print(f"Failed to load ERLC MODS cog: {str(e)}")
    try:
        await bot.load_extension("jishaku")
        print("Loaded JSK cog")
    except Exception as e:
        print(f"Failed to load JSK cog: {str(e)}")
    await bot.tree.sync()

@bot.command()
async def start(ctx):
    if not await has_restricted_role(ctx):
        return

    loaded_cogs = []
    failed_cogs = []
    
    # Load cogs from current directory, excluding discord_commands
    for filename in os.listdir('.'):
        if filename.endswith('.py') and not filename.startswith('__') and filename != 'main.py' and filename != '':
            cog_name = filename[:-3]
            try:
                await bot.load_extension(cog_name)
                loaded_cogs.append(cog_name)
            except Exception as e:
                failed_cogs.append(f"{cog_name}: {str(e)}")

    # Create embed
    if failed_cogs:
        embed = Embed(
            title="Melbourne Roleplay",
            description=f"**Error**\nAn error occurred: {failed_cogs[0].split(':', 1)[1]}",
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
    else:
        embed = Embed(
            title="Bot Started",
            description="The Melbourne Roleplay Bot is now running and loaded with:\n\n**- **" +
                        "\n- ".join([COG_NAMES.get(cog, cog) for cog in loaded_cogs]) if loaded_cogs else "", # type: ignore
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )

    embed.set_footer(text=FOOTER_TEXT)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # type: ignore
    
    # Set activity
    await bot.change_presence(
        status=Status.dnd,
        activity=Activity(type=ActivityType.watching, name="Melbourne Roleplay")
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def stop(ctx):
    if not await has_restricted_role(ctx):
        return

    unloaded_cogs = []
    failed_cogs = []
    
    # Unload all cogs except discord_commands
    for extension in list(bot.extensions):
        if extension != "":
            try:
                await bot.unload_extension(extension)
                unloaded_cogs.append(extension.split('.')[-1])
            except Exception as e:
                failed_cogs.append(f"{extension.split('.')[-1]}: {str(e)}")

    # Create embed
    if failed_cogs:
        embed = Embed(
            title="Melbourne Roleplay",
            description=f"**Error**\nAn error occurred: {failed_cogs[0].split(':', 1)[1]}",
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
    else:
        embed = Embed(
            title="Bot Stopped",
            description="The Melbourne Roleplay Bot has unloaded:\n\n**- **" +
                        "\n- ".join([COG_NAMES.get(cog, cog) for cog in unloaded_cogs]) if unloaded_cogs else "No cogs unloaded", # type: ignore
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
    
    embed.set_footer(text=FOOTER_TEXT)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # type: ignore
    
    # Set activity
    await bot.change_presence(
        status=Status.idle,
        activity=None
    )
    
    await ctx.send(embed=embed, view=StopButtons())

@bot.command()
async def servers(ctx):
    if not await has_restricted_role(ctx):
        return

    # Create embed
    embed = Embed(
        title="Server Management",
        description="Use the buttons below to manage servers",
        color=Colour(EMBED_COLOR),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="Current Servers",
        value="\n".join([f"{guild.name} (ID: {guild.id})" for guild in bot.guilds]) if bot.guilds else "None",
        inline=False
    )
    
    embed.set_footer(text=FOOTER_TEXT)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # type: ignore
    
    # Send embed with buttons
    await ctx.send(embed=embed, view=ServerButtons())

@bot.command()
async def latency(ctx):
    if not await has_restricted_role(ctx):
        return

    # Calculate uptime
    uptime_seconds = time.time() - START_TIME
    uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"

    # Measure API response time
    start_time = time.time()
    await ctx.typing()  # Trigger a small API call
    api_response_time = (time.time() - start_time) * 1000

    # Create embed
    embed = Embed(
        title="Bot Latency",
        color=Colour(EMBED_COLOR),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="Websocket Latency",
        value=f"{round(bot.latency * 1000, 2)} ms",
        inline=False
    )
    embed.add_field(
        name="API Response Time",
        value=f"{round(api_response_time, 2)} ms",
        inline=False
    )
    embed.add_field(
        name="Uptime",
        value=uptime_str,
        inline=False
    )
    
    embed.set_footer(text=FOOTER_TEXT)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # type: ignore
    
    await ctx.send(embed=embed)

@bot.command()
async def nick(ctx, *, nickname: str = None): # type: ignore
    if not await has_restricted_role(ctx):
        return

    try:
        await ctx.guild.me.edit(nick=nickname)
        message = f"Nickname changed to {nickname}" if nickname else "Nickname reset"
        embed = Embed(
            title="Nickname Update",
            description=message,
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
    except Exception as e:
        embed = Embed(
            title="Melbourne Roleplay",
            description=f"**Error**\nAn error occurred: {str(e)}",
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
    
    embed.set_footer(text=FOOTER_TEXT)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # type: ignore
    await ctx.send(embed=embed)

@bot.command()
async def purge(ctx, channel_id: str):
    if not await has_restricted_role(ctx):
        return

    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            await ctx.send(embed=Embed(
                title="Melbourne Roleplay",
                description="**Error**\nChannel not found or bot cannot access it.",
                color=Colour(EMBED_COLOR),
                timestamp=discord.utils.utcnow()
            ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore
            return

        embed = Embed(
            title="Purge Confirmation",
            description=f"Are you sure you want to delete all non-pinned messages in {channel.mention}?", # type: ignore
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=FOOTER_TEXT)
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None) # type: ignore
        
        await ctx.send(embed=embed, view=PurgeButtons(channel_id))
    except ValueError:
        await ctx.send(embed=Embed(
            title="Melbourne Roleplay",
            description="**Error**\nInvalid channel ID format.",
            color=Colour(EMBED_COLOR),
            timestamp=discord.utils.utcnow()
        ).set_footer(text=FOOTER_TEXT).set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)) # type: ignore


bot.run('MTQyMTQzNzIxNjg2MDgwMzIxNQ.GmTv3R.FVee6xZI_s9_whUlvjt31Rah2xIhBD1FBG5zok')  # Replace with your bot token
