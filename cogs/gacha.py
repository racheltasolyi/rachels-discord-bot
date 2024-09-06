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

        roll = random.randrange(3)
        cards = await self.get_card_data()
        roll_name = cards[str(roll)]["name"]
        roll_group = cards[str(roll)]["group"]
        roll_image = cards[str(roll)]["image"]
        roll_logo = cards[str(roll)]["logo"]
        roll_claimed = cards[str(roll)]["claimed"]
        #print(roll_name)

        uploaded_roll_image = discord.File(f"./cogs/gacha_images/{roll_image}", filename=roll_image)
        uploaded_roll_logo = discord.File(f"./cogs/gacha_images/{roll_logo}", filename=roll_logo)

        card = discord.Embed(title=roll_name, description=roll_group, color=discord.Color.green())
        card.set_thumbnail(url=f"attachment://{roll_logo}")
        card.set_image(url=f"attachment://{roll_image}")
        card.set_footer(text=f"Rolled by {ctx.author.name}", icon_url=ctx.author.avatar)

        if roll_claimed:
            roll_owner_id = cards[str(roll)]["owner"]
            roll_owner = await ctx.bot.fetch_user(roll_owner_id)
            #print(roll_owner_id)
            #print(roll_owner)
            card.add_field(
                name=f"{roll_name}'s heart already belongs to **{roll_owner}**!",
                value=f"{roll_name} can no longer be claimed.",
                inline=False
            )
        else:
            card.add_field(
                name=f"{roll_name} has not been caught yet 🥺",
                value="React with any emoji to claim!",
                inline=False
            )
        
        await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card)
    
    '''
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        channel = reaction.message.channel
        await client.send_message(channel, "{} has added {} to the message: {}")
    '''
    async def get_card_data(self):
        #print("Getting card data...")
        with open("./cogs/gacha.json","r") as f:
            #print("Reading JSON...")
            cards = json.load(f)

        #print("JSON read!")
        return cards

async def setup(bot):
    await bot.add_cog(Gacha(bot))