import discord
from discord.ext import commands, tasks
import os
import asyncio
from itertools import cycle
import logging

#logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

bot_statuses = cycle(["Alpha Test", "!tutorial"])

@tasks.loop(seconds=3)
async def change_bot_status():
    await bot.change_presence(activity=discord.Game(next(bot_statuses)))

@bot.event
async def on_ready():
    # await bot.tree.sync() # [Paradoxical] Part 21: Buttons
    print("Bot ready!")
    change_bot_status.start()
    # try:
    #     synced_commands = await bot.tree.sync()
    #     print(f"Synced {len(synced_commands)} commands.")
    # except Exception as e:
    #     print("An error with syncing application commands has occurred: ", e)

@bot.command(aliases=["s", "synccmd"])
async def sync(ctx):
    await bot.tree.sync()
    try:
        synced_commands = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced_commands)} commands.")
    except Exception as e:
        await ctx.send("An error with syncing application commands has occurred: ", e)

@bot.tree.command(name="hello", description="Says hello back to the user.")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.user.mention}, hello there!")

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

# [Paradoxical] Part 21: Buttons (button menu as slash command)

# class TestMenuButton(discord.ui.View):
#     def __init__(self):
#         super().__init__(timeout=None)
    
#     @discord.ui.button(label="Test", style=discord.ButtonStyle.blurple)
#     async def test(self, interaction: discord.Interaction, Button: discord.ui.Button):
#         await interaction.response.send_message(content="Test successful!")
#     @discord.ui.button(label="Click Me...", style=discord.ButtonStyle.green)
#     async def test2(self, interaction: discord.Interaction, Button: discord.ui.Button):
#         await interaction.response.send_message(content="I've been clicked!")
#     @discord.ui.button(label="Exit", style=discord.ButtonStyle.red)
#     async def test3(self, interaction: discord.Interaction, Button: discord.ui.Button):
#         await interaction.response.send_message(content="Exiting Menu...")
    
# @bot.tree.command(name="buttonmenu")
# async def buttonmenu(interaction: discord.Interaction):
#     await interaction.response.send_message(content="Here's my button menu!", view=TestMenuButton())

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