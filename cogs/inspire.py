import discord
from discord.ext import commands
import requests
import json

class Inspire(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @commands.command(aliases=["quote", "inspiration", "i"])
    async def inspire(self, ctx):
        response = requests.get("https://zenquotes.io/api/random/")
        json_data = json.loads(response.text)
        quote = json_data[0]['q'] + " -" + json_data[0]['a']
        await ctx.send(quote)

async def setup(bot):
    await bot.add_cog(Inspire(bot))