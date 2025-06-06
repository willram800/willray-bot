import os
from discord.ext import commands
import discord

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(os.getenv("YOUR_BOT_TOKEN"))
