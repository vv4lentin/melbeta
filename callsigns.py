import discord
from discord.ext import commands
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiscordCMDS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Role ID to prefix mapping (cleaned, with O → F, CO → CF, and updated A role ID)
        self.role_prefixes = {
            1402933851436879932: "TM",
            1384460078928625755: "JM",
            1384459593366769776: "M",
            1384459510571335681: "SM",
            1384459413401899028: "HM",
            1420729658114052177: "HoM",
            1384438610303914015: "JA",
            1384437924652781690: "A",
            1384438407421497548: "SA",
            1384438224021094482: "HA",
            1420729110031765618: "HoA",
            1384437544825131171: "TSS",
            1384437559068987505: "JSS",
            1384437426503684127: "SS",
            1420635304607485972: "SSS",
            1384437286841876530: "HSS",
            1383402914340671558: "TMT",
            1420415728137277440: "TJMT",
            1383402824783626281: "JMT",
            1383402737340776468: "MGT",
            1383402634462892032: "SMT",
            1383402460777021500: "CM",
            1383401961621159957: "TAD",
            1383401856620957696: "AD",
            1383401686827143201: "DD",
            1383401586285346938: "D",
            1383401266998153216: "AF",
            1383386801682649088: "CF",
            1383401122063978496: "F"
        }
        # Role groups in specified order
        self.role_groups = [
            ("FounderShip", ["AF", "CF", "F"]),
            ("DirectorShip", ["TAD", "AD", "DD", "D"]),
            ("Management Team", ["TMT", "TJMT", "JMT", "MGT", "SMT", "CM"]),
            ("Staff Supervision Team", ["TSS", "JSS", "SS", "SSS", "HSS"]),
            ("Administration Team", ["JA", "A", "SA", "HA", "HoA"]),
            ("Moderation Team", ["TM", "JM", "M", "SM", "HM", "HoM"])
        ]

    # Helper function to generate callsign based on role
    def generate_callsign(self, role_id, index):
        # Get prefix from role ID, default to "X" if not found
        prefix = self.role_prefixes.get(role_id, "X")
        return f"{prefix}-{index}"

    async def check_permissions(self, channel, ctx):
        """Check if bot has permissions to send embeds in the channel"""
        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.embed_links:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description="**Error**\nMissing 'Embed Links' permission in this channel.",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent missing embed links permission embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send missing embed links permission embed: {str(e)}")
                await ctx.send("Error: Missing 'Embed Links' permission in this channel.")
            return False
        return True

    @commands.command(name="update_callsigns")
    async def update_callsigns(self, ctx):
        # Check if user has the required role
        required_role_id = 1385160436046893168
        if not any(role.id == required_role_id for role in ctx.author.roles):
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description="**Error**\nYou are not allowed to update callsigns.",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent unauthorized access embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send unauthorized embed: {str(e)}")
                await ctx.send("Error: You are not allowed to update callsigns.")
            return

        guild = ctx.guild
        if not guild:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description="**Error**\nThis command must be used in a server.",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent guild not found embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send guild not found embed: {str(e)}")
                await ctx.send("Error: This command must be used in a server.")
            return

        # Get the target channel
        target_channel = guild.get_channel(1421432657891557426)
        if not target_channel:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description="**Error**\nTarget channel not found.",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent target channel not found embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send target channel not found embed: {str(e)}")
                await ctx.send("Error: Target channel not found.")
            return

        # Check permissions for target channel
        if not await self.check_permissions(target_channel, ctx):
            return
        # Check permissions for command channel
        if not await self.check_permissions(ctx.channel, ctx):
            return

        # Purge the target channel (up to 100 messages)
        try:
            await target_channel.purge(limit=100)
            logger.info(f"Successfully purged target channel {target_channel.id}")
        except discord.Forbidden:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description="**Error**\nI lack permission to purge messages in the target channel.",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent purge permission error embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send purge permission error embed: {str(e)}")
                await ctx.send("Error: I lack permission to purge messages in the target channel.")
            return
        except Exception as e:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description=f"**Error**\nAn error occurred during purge: {str(e)}",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent purge general error embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send purge general error embed: {str(e)}")
                await ctx.send(f"Error: An error occurred during purge: {str(e)}")
            return

        # Dictionary to store callsigns by member
        callsigns = {}
        role_counts = {}  # Track number of members per role for indexing

        # Iterate through all members in the guild
        try:
            for member in guild.members:
                # Get roles that match the role_prefixes keys
                eligible_roles = [role for role in member.roles if role.id in self.role_prefixes]
                if not eligible_roles:
                    continue  # Skip members with no mapped roles

                # Sort roles by position (highest role first)
                highest_role = max(eligible_roles, key=lambda r: r.position)

                # Initialize or increment role count
                role_id = highest_role.id
                role_counts[role_id] = role_counts.get(role_id, 0) + 1

                # Generate callsign
                callsign = self.generate_callsign(highest_role.id, role_counts[role_id])
                callsigns[member] = callsign
            logger.info("Successfully generated callsigns")
        except Exception as e:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description=f"**Error**\nAn error occurred while generating callsigns: {str(e)}",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent callsign generation error embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send callsign generation error embed: {str(e)}")
                await ctx.send(f"Error: An error occurred while generating callsigns: {str(e)}")
            return

        # Ping the role
        try:
            ping_role = guild.get_role(1384465784042029198)
            ping_message = f"<@&{1384465784042029198}> The callsigns has been updated! Your callsign might have changed." if ping_role else "On-Duty Role not found"
            message = await target_channel.send(ping_message)
            logger.info(f"Sent ping message with ID {message.id} to channel {target_channel.id}")
        except Exception as e:
            embed = discord.Embed(
                title="Melbourne Roleplay",
                description=f"**Error**\nAn error occurred while sending ping message: {str(e)}",
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            try:
                await ctx.send(embed=embed)
                logger.info(f"Sent ping message error embed to channel {ctx.channel.id}")
            except Exception as e:
                logger.error(f"Failed to send ping message error embed: {str(e)}")
                await ctx.send(f"Error: An error occurred while sending ping message: {str(e)}")
            return

        # Create an embed for each role group in specified order
        for group_name, prefixes in self.role_groups:
            # Filter members whose callsigns match the group's prefixes
            group_members = {
                member: cs for member, cs in callsigns.items()
                if any(cs.startswith(prefix + '-') for prefix in prefixes)
            }

            # Skip empty groups
            if not group_members:
                continue

            # Create embed for this group
            embed = discord.Embed(
                title=group_name,
                description="\n".join(
                    f"{member.mention} - {callsign}"
                    for member, callsign in sorted(group_members.items(), key=lambda x: x[1])  # Sort by callsign
                ),
                color=discord.Colour(0x19385f)
            )
            embed.set_footer(text="Melbourne Roleplay")
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)

            # Send embed to target channel
            try:
                message = await target_channel.send(embed=embed)
                logger.info(f"Sent embed for group {group_name} with message ID {message.id} to channel {target_channel.id}")
            except Exception as e:
                embed = discord.Embed(
                    title="Melbourne Roleplay",
                    description=f"**Error**\nAn error occurred while sending embed for {group_name}: {str(e)}",
                    color=discord.Colour(0x19385f)
                )
                embed.set_footer(text="Melbourne Roleplay")
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
                try:
                    await ctx.send(embed=embed)
                    logger.info(f"Sent error embed for group {group_name} to channel {ctx.channel.id}")
                except Exception as e:
                    logger.error(f"Failed to send error embed for group {group_name}: {str(e)}")
                    await ctx.send(f"Error: An error occurred while sending embed for {group_name}: {str(e)}")

    # Error handling for the command
    @update_callsigns.error
    async def update_callsigns_error(self, ctx, error):
        embed = discord.Embed(
            title="Melbourne Roleplay",
            description=f"**Error**\nAn error occurred: {str(error)}",
            color=discord.Colour(0x19385f)
        )
        embed.set_footer(text="Melbourne Roleplay")
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        try:
            await ctx.send(embed=embed)
            logger.info(f"Sent command error embed to channel {ctx.channel.id}")
        except Exception as e:
            logger.error(f"Failed to send command error embed: {str(e)}")
            await ctx.send(f"Error: An error occurred: {str(error)}")

async def setup(bot):
    await bot.add_cog(DiscordCMDS(bot))