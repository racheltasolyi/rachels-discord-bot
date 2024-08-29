import discord
from discord.ext import commands

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
        card = discord.Embed(title="Title of embed", description="Description of embed", color=discord.Color.green())
        card.set_author(name="Author text", icon_url=ctx.author.avatar)
        card.set_thumbnail(url=ctx.author.avatar)
        card.add_field(name="Name of field", value="Value of field", inline=False)
        card.set_image(url=ctx.guild.icon)
        card.set_footer(text="Footer text", icon_url=ctx.author.avatar)
        await ctx.send(embed=card)

async def setup(bot):
    await bot.add_cog(Gacha(bot))