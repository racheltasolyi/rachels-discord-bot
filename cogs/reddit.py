import discord
from discord.ext import commands
from random import choice
import asyncpraw as praw

class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = praw.Reddit(client_id="VEf7ZU_hPNDG1HeStFWcrg", client_secret="iWo95WMxm8ciD9guFJlxhYpmTk5qcA", user_agent="script:randommeme:v1.0 (by u/SoulDai23)")
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is ready!")
    
    @commands.command(aliases=["memes", "m"])
    async def meme(self, ctx: commands.Context):

        subreddit = await self.reddit.subreddit("memes")
        posts_list = []

        async for post in subreddit.hot(limit=30):
            if not post.over_18 and post.author is not None and any(post.url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
                author_name = post.author.name
                posts_list.append((post.url, author_name))
            if post.author is None:
                posts_list.append((post.url, "N/A"))
        
        if posts_list:

            random_post = choice(posts_list)

            meme_embed = discord.Embed(title="Random Meme", description="Fetches random meme from r/memes", color=discord.Color.random())
            meme_embed.set_author(name=f"Meme requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            meme_embed.set_image(url=random_post[0])
            meme_embed.set_footer(text=f"Post created by {random_post[1]}.", icon_url=None)
            await ctx.send(embed=meme_embed)
        
        else:
            await ctx.send("Unable to fetch meme, try again later.")
    
    @commands.command(aliases=["cats", "catpic", "catt", "c"])
    async def cat(self, ctx: commands.Context):

        subreddit = await self.reddit.subreddit("cats")
        posts_list = []

        async for post in subreddit.hot(limit=30):
            if not post.over_18 and post.author is not None and any(post.url.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
                author_name = post.author.name
                posts_list.append((post.url, author_name))
            if post.author is None:
                posts_list.append((post.url, "N/A"))
        
        if posts_list:

            random_post = choice(posts_list)

            meme_embed = discord.Embed(title="Cat Pic", description="Fetches a random cat from r/cat", color=discord.Color.random())
            meme_embed.set_author(name=f"Cat requested by {ctx.author.name}", icon_url=ctx.author.avatar)
            meme_embed.set_image(url=random_post[0])
            meme_embed.set_footer(text=f"Post created by {random_post[1]}.", icon_url=None)
            await ctx.send(embed=meme_embed)
        
        else:
            await ctx.send("Unable to fetch cat, try again later.")
    
    def cog_unload(self):
        self.bot.loop.create_task(self.reddit.close())
    
async def setup(bot):
    await bot.add_cog(Reddit(bot))