import discord
from discord.ext import commands, tasks
import os
import asyncio
from itertools import cycle
import logging

#logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

bot_statuses = cycle(["Status One", "Status Two", "Status Three", "Status Four"])

@tasks.loop(seconds=2)
async def change_bot_status():
    await bot.change_presence(activity=discord.Game(next(bot_statuses)))

@bot.event
async def on_ready():
    print("Bot ready!")
    change_bot_status.start()

@bot.command(aliases=["hi"])
async def hello(ctx):
    await ctx.send(f"Hello there, {ctx.author.mention}!")

@bot.command(aliases=["gm", "morning"])
async def goodmorning(ctx):
    await ctx.send(f"Good morning, {ctx.author.mention}!")

@bot.command()
async def sendembed(ctx):
    embeded_msg = discord.Embed(title="Title of embed", description="Description of embed", color=discord.Color.green())
    embeded_msg.set_author(name="Author text", icon_url=ctx.author.avatar)
    embeded_msg.set_thumbnail(url=ctx.author.avatar)
    embeded_msg.add_field(name="Name of field", value="Value of field", inline=False)
    embeded_msg.set_image(url=ctx.guild.icon)
    embeded_msg.set_footer(text="Footer text", icon_url=ctx.author.avatar)
    await ctx.send(embed=embeded_msg)

# @bot.command()
# async def ping(ctx):
#     ping_embed = discord.Embed(title="Ping",description="Latency in ms", color=discord.Color.blue())
#     ping_embed.add_field(name=f"{bot.user.name}'s Latency: ", value=f"{round(bot.latency * 1000)}ms.", inline=False)
#     ping_embed.set_footer(text=f"Requested by {ctx.author.name}.", icon_url=ctx.author.avatar)
#     await ctx.send(embed=ping_embed)

@bot.event
async def on_reaction_add(ctx, reaction, user):
    channel = reaction.message.channel
    await ctx.send(channel, "{} has added {} to the message: {}".format(user.name, reaction.emoji, reaction.message.content))

with open("token.txt") as file:
    token = file.read()

async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load()
        await bot.start(token)

asyncio.run(main())
#bot.run(token)