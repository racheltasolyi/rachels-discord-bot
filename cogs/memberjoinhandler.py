import discord
from discord.ext import commands
import os
import easy_pil
import random

class MemberJoinHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        welcome_channel = member.guild.system_channel
        images = [image for image in os.listdir("./cogs/welcome_images")]
        randomized_image = random.choice(images)

        bg = easy_pil.Editor(f"./cogs/welcome_images/{randomized_image}").resize((1463, 2048))
        avatar_image = await easy_pil.load_image_async(str(member.avatar.url))
        avatar = easy_pil.Editor(avatar_image).resize((250,250)).circle_image()

        font_big = easy_pil.Font.poppins(size=80, variant="bold")
        font_small = easy_pil.Font.poppins(size=60, variant="bold")

        bg.paste(avatar, (605, 1100)) #(835,340) (600,1500) (620,1350) (610,1000)
        bg.ellipse((605, 1100), 250, 250, outline="white", stroke_width=10) #(835,340)

        bg.text((731, 1380), f"Welcome to {member.guild.name}!", color="white", font=font_big, align="center")
        #960, 620
        bg.text((731, 1500), f"{member.name} is member #{member.guild.member_count}!", color="white", font=font_small, align="center")
        #960, 740

        img_file = discord.File(fp=bg.image_bytes, filename=randomized_image)

        await welcome_channel.send(f"Hello there, {member.mention}! Be sure to read our rules and follow them carefully, thank you for joining our server!")
        await welcome_channel.send(file=img_file)

async def setup(bot):
    await bot.add_cog(MemberJoinHandler(bot))