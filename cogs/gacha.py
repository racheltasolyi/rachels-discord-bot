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

    ### !GACHA COMMAND: ROLL A RANDOM IDOL ###
    @commands.command(aliases=["g"])
    async def gacha(self, ctx, arg: int = None):

        #print("!gacha command called!")
        roller_id = ctx.author.id
        #print(f"roller_id = {roller_id}")

        ### ADMIN COMMAND: ROLL SPECIFIED IDOL ###
        if (arg != None):
            with open("./admin.txt") as file:
                adminid = int(file.read())

            if (roller_id == adminid):
                roll_number = arg
            else:
                await ctx.send("You do not have permission for this command.")
                return

        ### DETERMINE ROLL NUMBER ###
        else:
            #roll_number = 29
            roll_number = random.randrange(30)
            
        print(roll_number)

        ### FETCH PLAYER ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        #print("connection made")

        cursor.execute("""SELECT * FROM Players
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})
        player = cursor.fetchone()
        
        ### IF PLAYER IS NEW, ADD NEW PLAYER TO DATABASE ###
        if player is None:
            cursor.execute("""INSERT INTO Players (player_id)
                              Values (:roller_id)""",
                            {'roller_id': roller_id})

        ### FETCH THE ROLLED IDOL AND THEIR GROUP ###
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll = cursor.fetchone()
        if roll is None:
            await ctx.send("The rolled idol does not exist.")
            return
        cursor.execute("""SELECT group_id FROM GroupMembers
                          WHERE idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll_group_id = cursor.fetchone()
        #print(roll_group_id)
        if roll_group_id is None:
            await ctx.send("The rolled idol's Group ID does not exist.")
            return
        cursor.execute("""SELECT * FROM Groups
                          WHERE group_id = :roll_group_id""",
                        {'roll_group_id': roll_group_id[0]})
        roll_group = cursor.fetchone()
        #print(roll_group)
        if roll_group is None:
            await ctx.send("The rolled idol's Group does not exist.")
            return
        #print("Got card data!")

        ### BUILD IDOL CARD ###
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
        if roll_logo is not None:
            uploaded_roll_logo = discord.File(f"./cogs/gacha_images/logos/{roll_logo}", filename=roll_logo)
        #print("Images uploaded!")

        card = discord.Embed(title=roll_name, description=roll_group_name, color=discord.Color.green())
        if roll_logo is not None:
            card.set_thumbnail(url=f"attachment://{roll_logo}")
        card.set_image(url=f"attachment://{roll_image}")
        card.set_footer(text=f"Rolled by {ctx.author.name}", icon_url=ctx.author.avatar)
        #print("Embed created!")

        ### DISPLAY IDOL CARD WITH CATCH BUTTON, DEPENDING ON WHETHER IT IS CLAIMED OR NOT ###
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
            if roll_logo is None:
                await ctx.send(files=[uploaded_roll_image], embed=card)
            else:
                await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card)
        else:
            card.add_field(
                name=f"{roll_name} has not been caught yet 🥺",
                value="You have 1 minute to throw a Pokeball!",
                inline=False
            )
            #await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card)
            if roll_logo is None:
                await ctx.send(files=[uploaded_roll_image], embed=card, view=GachaButtonMenu(roll_number))
            else:
                await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card, view=GachaButtonMenu(roll_number))
        
        ### UPDATE TIMESTAMP OF PLAYER'S LAST ROLL ###
        cursor.execute("""UPDATE Players
                          SET last_roll_timestamp = DATETIME('now', 'localtime')
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})

        connection.commit()
        connection.close()
    
    ### ADMIN COMMAND: RESET GACHA GAME ###
    @commands.command()
    async def resetgacha(self, ctx):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())
            #print("adminid =", repr(adminid), type(adminid))
            #print("ctx.author.id =", repr(ctx.author.id), type(ctx.author.id))
            #print(ctx.author.id == adminid)

        if (ctx.author.id == adminid):

            ### RELEASE ALL IDOLS BACK INTO THE WILD ###
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            cursor.execute("""UPDATE Idols SET player_id = 0
                              WHERE (player_id IS NOT NULL AND player_id != 0)""")

            await ctx.send("Gacha has been reset.")
            connection.commit()
            connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")

### BUTTON TO CATCH IDOLS ###
class GachaButtonMenu(discord.ui.View):
    roll_number = None

    ### BUTTON TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, roll_number):
        super().__init__(timeout=60)
        self.roll_number = roll_number
    
    @discord.ui.button(label="Throw Pokeball", style=discord.ButtonStyle.blurple)
    async def throwpokeball(self, interaction: discord.Interaction, Button: discord.ui.Button):
        userid = interaction.user.id
        roller = self.roller_id

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        #print("connection made")

        ### FETCH IDOL NAME ###
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': self.roll_number})
        roll = cursor.fetchone()
        roll_name = roll[1]
        #print(roll)

        ### SUCCESSFULLY CATCH IDOL IF CORRECT PLAYER, FAIL UPON REPEATED ATTEMPTS ###
        if (userid == self.roller_id):
            if (roll[3] == 0 or roll[3] == None):
                roll_claimed = False
            else:
                roll_claimed = True
            
            if not roll_claimed:
                cursor.execute("""UPDATE Idols
                                SET player_id = :userid
                                WHERE idol_id = :roll_number""",
                                {'userid': userid, 'roll_number': self.roll_number})
                content=f"{roll_name} was caught by {interaction.user.mention}!"
                #print(roll)
            else:
                content=f"You already caught {roll_name}!"

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"Nice try {interaction.user.mention}, {roll_name} can only be caught by <@{roller}> this time!"
        
        connection.commit()
        connection.close()

        await interaction.response.send_message(content=content)
        

async def setup(bot):
    await bot.add_cog(Gacha(bot))