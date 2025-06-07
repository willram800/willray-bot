import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import has_permissions
from datetime import datetime
import asyncio
from collections import deque
import yt_dlp
import io

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

GUILD_ID = 1380006567654457505  # Replace with your actual guild ID
WELCOME_CHANNEL_ID = 1380007232972001400  # Replace with your welcome channel ID
LOG_CHANNEL_ID = 1380024339562233886  # Replace with your ticket log channel ID
AUTO_ROLE_NAME = "🎶 Fan"
STAFF_ROLE_NAMES = ["Manager", " Mod Team", "WILLRAY"]

# --- Welcome Event ---
@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        await member.add_roles(role)
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(f"👋 Welcome {member.mention} to the server!")

# --- Basic Slash Commands ---
@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@tree.command(name="about", description="Learn about this bot")
async def about(interaction: discord.Interaction):
    await interaction.response.send_message("🎤 I'm the official bot for the WILLRAY community!")

@tree.command(name="rules", description="Show server rules")
async def rules(interaction: discord.Interaction):
    await interaction.response.send_message("📜 Be respectful, no spam, follow Discord TOS.")

# --- Moderation Commands ---
@bot.command()
@has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}")

@bot.command()
@has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention}")

@bot.command()
@has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {amount} messages", delete_after=5)

# --- Ticket System with Transcript Logging ---
open_tickets = {}

@bot.command()
async def ticket(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
    }
    channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites)
    open_tickets[channel.id] = []
    await channel.send(f"🎟️ Hello {ctx.author.mention}, how can we help you?")

@bot.event
async def on_message(message):
    if message.channel.id in open_tickets and not message.author.bot:
        open_tickets[message.channel.id].append(f"[{datetime.now().strftime('%H:%M:%S')}] {message.author}: {message.content}")
    await bot.process_commands(message)

@bot.command()
async def close(ctx):
    if ctx.channel.id not in open_tickets:
        return await ctx.send("❌ This is not a ticket channel.")
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    transcript = "\n".join(open_tickets[ctx.channel.id])
    if log_channel:
        await log_channel.send(f"🗂️ Ticket closed: {ctx.channel.name} by {ctx.author.mention}",
                               file=discord.File(fp=io.StringIO(transcript), filename="transcript.txt"))
    await ctx.send("🗑️ Closing ticket in 5 seconds...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

# --- Staff List Command ---
@bot.command()
async def staff(ctx):
    staff_members = [member.mention for member in ctx.guild.members if any(role.name in STAFF_ROLE_NAMES for role in member.roles)]
    if staff_members:
        await ctx.send("👮 Staff:\n" + "\n".join(staff_members))
    else:
        await ctx.send("No staff found.")

# --- Music System Setup ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send(f"🎶 Joined {ctx.author.voice.channel}!")

@bot.command()
async def play(ctx, *, url):
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
    await ctx.send(f"🎵 Now playing: {player.title}")

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()
    await ctx.send("👋 Left the voice channel")

# --- On Ready ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced {len(synced)} slash commands: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# --- Run Bot ---
bot.run("YOUR_BOT_TOKEN")
