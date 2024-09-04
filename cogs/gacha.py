import discord
from discord.ext import commands
import os
import random

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    """@commands.command()
    async def ping(self, ctx):
        ping_embed = discord.Embed(title="Ping",description="Latency in ms", color=discord.Color.blue())
        ping_embed.add_field(name=f"{self.bot.user.name}'s Latency: ", value=f"{round(self.bot.latency * 1000)}ms.", inline=False)
        ping_embed.set_footer(text=f"Requested by {ctx.author.name}.", icon_url=ctx.author.avatar)
        await ctx.send(embed=ping_embed)"""

    @commands.command(aliases=["g"])
    async def gacha(self, ctx):
        #images = [image for image in os.listdir("./cogs/welcome_images")]
        #randomized_image = random.choice(images)

        welcome1 = discord.File("./cogs/welcome_images/welcome1.jpg", filename="welcome1.jpg")
        skzlogo = discord.File("./cogs/welcome_images/skzlogo.jpg", filename="skzlogo.jpg")

        card = discord.Embed(title="Lee Know", description="Stray Kids", color=discord.Color.green())
        card.set_author(name=f"Rolled by {ctx.author.name}", icon_url=ctx.author.avatar)
        card.set_thumbnail(url="attachment://skzlogo.jpg")
        #card.add_field(name="Name of field", value="Value of field", inline=False)
        card.set_image(url="attachment://welcome1.jpg")
        #card.set_image(f"./cogs/welcome_images/{randomized_image}")
        card.set_footer(text="Lee Know has not been caught yet!")
        await ctx.send(files=[welcome1, skzlogo], embed=card)

async def setup(bot):
    await bot.add_cog(Gacha(bot))