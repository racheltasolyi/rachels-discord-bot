import discord
from discord.ext import commands
import random
import json
import sqlite3

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @commands.command(aliases=["g"])
    async def gacha(self, ctx, arg: int = None):
        #images = [image for image in os.listdir("./cogs/welcome_images")]
        #randomized_image = random.choice(images)
        #print("!gacha command called!")
        roller_id = ctx.author.id
        #print(roller_id)

        if (arg != None):
            with open("./admin.txt") as file:
                adminid = int(file.read())

            if (roller_id == adminid):
                roll_number = arg
            else:
                await ctx.send("You do not have permission for this command.")
                return

        else:
            #roll_number = 29
            roll_number = random.randrange(30)
            
        print(roll_number)
        #cards = await self.get_card_data()
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        #print("connection made")

        cursor.execute("""SELECT * FROM Players
                    WHERE player_id = :roller_id""",
                    {'roller_id': roller_id})
        player = cursor.fetchone()
        #print(player)
        if player is None:
            cursor.execute("""INSERT INTO Players (player_id)
                        Values (:roller_id)""",
                        {'roller_id': roller_id})

        cursor.execute("""SELECT * FROM Idols
                    WHERE idol_id = :roll_number""",
                    {'roll_number': roll_number})
        roll = cursor.fetchone()
        if roll is None:
            await ctx.send("The rolled idol does not exist.")

        cursor.execute("""SELECT group_id FROM GroupMembers
                    WHERE idol_id = :roll_number""",
                    {'roll_number': roll_number})
        roll_group_id = cursor.fetchone()
        #print(roll_group_id)
        '''if roll_group_id is None:
            await ctx.send("The rolled idol's Group ID does not exist.")'''

        cursor.execute("""SELECT * FROM Groups
                    WHERE group_id = :roll_group_id""",
                    {'roll_group_id': roll_group_id[0]})
        roll_group = cursor.fetchone()
        #print(roll_group)
        '''if roll_group is None:
            await ctx.send("The rolled idol's Group does not exist.")'''

        #print("Got card data!")
        roll_name = roll[1]
        roll_group_name = roll_group[1]
        roll_image = roll[2]
        roll_logo = roll_group[2]
        if (roll[3] == 0 or roll[3] == None):
            roll_claimed = False
        else:
            roll_claimed = True
        #print(roll_name)

        uploaded_roll_image = discord.File(f"./cogs/gacha_images/idols/{roll_image}", filename=roll_image)
        uploaded_roll_logo = discord.File(f"./cogs/gacha_images/logos/{roll_logo}", filename=roll_logo)
        #print("Images uploaded!")

        card = discord.Embed(title=roll_name, description=roll_group_name, color=discord.Color.green())
        card.set_thumbnail(url=f"attachment://{roll_logo}")
        card.set_image(url=f"attachment://{roll_image}")
        card.set_footer(text=f"Rolled by {ctx.author.name}", icon_url=ctx.author.avatar)
        #print("Embed created!")

        if roll_claimed:
            roll_owner_id = roll[3]
            roll_owner = await ctx.bot.fetch_user(roll_owner_id)
            #print(roll_owner_id)
            #print(roll_owner)
            card.add_field(
                name=f"{roll_name}'s heart already belongs to **{roll_owner}**!",
                value=f"{roll_name} can no longer be caught.",
                inline=False
            )
            await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card)
        else:
            card.add_field(
                name=f"{roll_name} has not been caught yet 🥺",
                value="You have 1 minute to throw a Pokeball!",
                inline=False
            )
            #await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card)
            await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card, view=GachaButtonMenu(roll_number))
        connection.commit()
        connection.close()
    
    @commands.command()
    async def resetgacha(self, ctx):
        '''cards = await self.get_card_data()
        for card in cards:
            cards[str(card)]["claimed"] = False
            cards[str(card)]["owner"] = None
        await self.update_card_data(cards)'''
        with open("./admin.txt") as file:
            adminid = int(file.read())
            #print("adminid =", repr(adminid), type(adminid))
            #print("ctx.author.id =", repr(ctx.author.id), type(ctx.author.id))
            #print(ctx.author.id == adminid)

        if (ctx.author.id == adminid):

            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            cursor.execute("UPDATE Idols SET player_id = 0 WHERE (player_id IS NOT NULL AND player_id != 0)")

            await ctx.send("Gacha has been reset.")
            connection.commit()
            connection.close()
        
        else:
            await ctx.send("You do not have permission for this command.")
            
    '''
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        channel = reaction.message.channel
        await client.send_message(channel, "{} has added {} to the message: {}")
    '''
    
    #not needed? just filter thru gachacards table
    '''
    async def create_new_player(self, player):
        #print("Do we need to open an account?")
        players = await self.get_player_data()
        
        if str(player.id) in players:
            #print("No, account already exists.")
            return False
        else:
            #print(f"Yes, creating account for {user.id}...")
            players[str(player.id)] = {}
            players[str(player.id)]["party"] = {}
            players[str(player.id)]["bank"] = 0
            #print(f"{user.id}'s account was created.")

        await self.update_player_data(players)
        return True
    
    async def get_player_data(self):
        #print("Getting bank data...")
        with open("./cogs/gachaplayers.json","r") as f:
            #print("Reading JSON...")
            players = json.load(f)

        #print("JSON read!")
        return players
    
    async def update_player_data(self, players):
        with open("./cogs/mainbank.json","w") as f:
            #print("Updating JSON...")
            json.dump(players,f)

        #print("JSON updated!")
        return True
    '''
    async def get_card_data(self):
        #print("Getting card data...")
        with open("./cogs/gachacards.json","r") as f:
            #print("Reading JSON...")
            cards = json.load(f)

        #print("JSON read!")
        return cards
    
    async def update_card_data(self, cards):
        with open("./cogs/gachacards.json","w") as f:
            #print("Updating JSON...")
            json.dump(cards,f)

        #print("JSON updated!")
        return True
    
class GachaButtonMenu(discord.ui.View):
    roll_number = None

    def __init__(self, roll_number):
        super().__init__(timeout=60)
        self.roll_number = roll_number
    
    @discord.ui.button(label="Throw Pokeball", style=discord.ButtonStyle.blurple)
    async def test(self, interaction: discord.Interaction, Button: discord.ui.Button):
        userid = interaction.user.id
        #print(userid)
        #cards = await Gacha.get_card_data(self)
        #print(cards)
        #print(self.roll_number)
        #print(f"before: {cards[str(self.roll_number)]['claimed']}")
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        #print("connection made")

        cursor.execute("""SELECT * FROM Idols
                       WHERE idol_id = :roll_number""",
                       {'roll_number': self.roll_number})
        roll = cursor.fetchone()
        roll_name = roll[1]
        #print(roll)

        if (roll[3] == 0 or roll[3] == None):
            roll_claimed = False
        else:
            roll_claimed = True
        
        if not roll_claimed:
            cursor.execute("UPDATE Idols SET player_id = :userid WHERE idol_id = :roll_number",
                       {'userid': userid, 'roll_number': self.roll_number})
            content=f"{roll_name} was caught by {interaction.user.mention}!"
            #print(roll)
        else:
            content=f"Too bad, {roll_name} has already been caught!"
        
        connection.commit()
        connection.close()

        '''
        if cards[str(self.roll_number)]["claimed"] is False:
            cards[str(self.roll_number)]["claimed"] = True
            cards[str(self.roll_number)]["owner"] = userid
            await Gacha.update_card_data(self, cards)
            content=f"{cards[str(self.roll_number)]['name']} was caught by {interaction.user.mention}!"
        else:
            content=f"Too bad, {cards[str(self.roll_number)]['name']} has already been caught!"
        '''
        #print(f"after: {cards[str(self.roll_number)]['claimed']}")
        #print(cards[str(self.roll_number)]["owner"])

        await interaction.response.send_message(content=content)
        

async def setup(bot):
    await bot.add_cog(Gacha(bot))