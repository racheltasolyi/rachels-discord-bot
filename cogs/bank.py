import discord
from discord.ext import commands
import json
import os
import random

#os.chdir(r"C:\Users\dasol\OneDrive\Documents\YTDiscordBot\cogs")

class Bank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @commands.command(aliases=["b"])
    async def balance(self, ctx):
        #print("Need to check balance...")
        await self.open_account(ctx.author)
        #print("Done checking balance.")
        user = ctx.author
        #print("Need to get bank data...")
        users = await self.get_bank_data()
        #print("Done getting bank data.")

        wallet_amt = users[str(user.id)]["wallet"]
        bank_amt = users[str(user.id)]["bank"]

        em = discord.Embed(title = f"{ctx.author.name}'s balance",color = discord.Color.red())
        em.add_field(name = "Wallet balance",value = wallet_amt)
        em.add_field(name = "Bank balance",value = bank_amt)
        await ctx.send(embed = em)
    
    @commands.command()
    async def beg(self, ctx):
        await self.open_account(ctx.author)

        users = await self.get_bank_data()

        user = ctx.author

        earnings = random.randrange(101)

        users[str(user.id)]["wallet"] += earnings

        await ctx.send(f"Someone gave you {earnings} coins!! You now have {users[str(user.id)]["wallet"]} coins.")

        await self.update_bank_data(users)
    
    async def open_account(self, user):
        #print("Do we need to open an account?")
        users = await self.get_bank_data()
        
        if str(user.id) in users:
            #print("No, account already exists.")
            return False
        else:
            #print(f"Yes, creating account for {user.id}...")
            users[str(user.id)] = {}
            users[str(user.id)]["wallet"] = 0
            users[str(user.id)]["bank"] = 0
            #print(f"{user.id}'s account was created.")

        self.update_bank_data(users)
        return True
    
    async def get_bank_data(self):
        #print("Getting bank data...")
        with open("./cogs/mainbank.json","r") as f:
            #print("Reading JSON...")
            users = json.load(f)

        #print("JSON read!")
        return users

    async def update_bank_data(self, users):
        with open("./cogs/mainbank.json","w") as f:
            #print("Updating JSON...")
            json.dump(users,f)

        #print("JSON updated!")
        return True

async def setup(bot):
    await bot.add_cog(Bank(bot))