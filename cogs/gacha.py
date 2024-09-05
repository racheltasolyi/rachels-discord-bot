import discord
from discord.ext import commands
import os
import random
import json

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

        pick = random.randrange(3)
        cards = await self.get_card_data()
        name = cards[str(pick)]["name"]
        group = cards[str(pick)]["group"]
        image = cards[str(pick)]["image"]
        group_image = cards[str(pick)]["group_image"]
        #print(name)

        welcome1 = discord.File(f"./cogs/welcome_images/{image}", filename=image)
        skzlogo = discord.File(f"./cogs/welcome_images/{group_image}", filename=group_image)

        card = discord.Embed(title=name, description=group, color=discord.Color.green())
        card.set_author(name=f"Rolled by {ctx.author.name}", icon_url=ctx.author.avatar)
        card.set_thumbnail(url=f"attachment://{group_image}")
        #card.add_field(name="Name of field", value="Value of field", inline=False)
        card.set_image(url=f"attachment://{image}")
        #card.set_image(f"./cogs/welcome_images/{randomized_image}")
        card.set_footer(text=f"{name} has not been caught yet!")
        await ctx.send(files=[welcome1, skzlogo], embed=card)
    
    async def get_card_data(self):
        #print("Getting card data...")
        with open("./cogs/gacha.json","r") as f:
            #print("Reading JSON...")
            cards = json.load(f)

        #print("JSON read!")
        return cards

async def setup(bot):
    await bot.add_cog(Gacha(bot))