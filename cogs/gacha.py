import os
import discord
from discord.ext import commands
import random
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
                await ctx.send("ERROR: You do not have permission for this command.")
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
            await ctx.send("ERROR: The rolled idol does not exist.")
            return
        cursor.execute("""SELECT group_id FROM GroupMembers
                          WHERE idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll_group_id = cursor.fetchone()
        #print(roll_group_id)
        if roll_group_id is None:
            await ctx.send("ERROR: The rolled idol's Group ID does not exist.")
            return
        cursor.execute("""SELECT * FROM Groups
                          WHERE group_id = :roll_group_id""",
                        {'roll_group_id': roll_group_id[0]})
        roll_group = cursor.fetchone()
        #print(roll_group)
        if roll_group is None:
            await ctx.send("ERROR: The rolled idol's Group does not exist.")
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
                await ctx.send(files=[uploaded_roll_image], embed=card, view=GachaButtonMenu(roll_number, roller_id))
            else:
                await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card, view=GachaButtonMenu(roll_number, roller_id))
        
        ### UPDATE TIMESTAMP OF PLAYER'S LAST ROLL ###
        cursor.execute("""UPDATE Players
                          SET last_roll_timestamp = DATETIME('now', 'localtime')
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})

        connection.commit()
        connection.close()
    
    ### !RELEASE COMMAND: RELEASE SPECIFIED IDOL ###
    @commands.command(aliases=["r"])
    async def release(self, ctx, *, arg: str = None):

        ### IF NO ARGS, DISPLAY CORRECT SYNTAX ###
        if arg is None:
            await ctx.send("ERROR: Insufficient parameters.\nPlease use the following syntax:\n`!release \"[Name of Idol]\"`\nExample: `!release \"Lee Know\"`")

        ### CHECK IF THE IDOL IS OWNED BY USER ###
        else:
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            cursor.execute("""SELECT * FROM Idols
                            WHERE (idol_name = :arg AND player_id = :user_id)""",
                            {'arg': arg, 'user_id': ctx.author.id})
            idol = cursor.fetchall()

            ### ERROR HANDLING ###
            if len(idol) == 0 or len(idol) > 1:

                ### ERROR MESSAGE IF MORE THAN 1 IDOL ARE FOUND IN PARTY ###
                if len(idol) > 1:
                    await ctx.send(f"ERROR: Multiple idols named {arg} were found in your party. Please contact admin SoulDaiDa for assistance.")

                else:
                    cursor.execute("""SELECT * FROM Idols
                                    WHERE idol_name = :arg""",
                                    {'arg': arg})
                    idol = cursor.fetchall()
                    
                    ### ERROR MESSAGE IF IDOL DOES NOT EXIST ###
                    if len(idol) == 0:
                        await ctx.send(f"ERROR: No idols named {arg} can be found. Please check spelling and capitalization.")
                
                    ### ERROR MESSAGE IF USER DOES NOT OWN IDOL ###
                    elif idol[0][3] != ctx.author.id:
                        await ctx.send(f"ERROR: {arg} is not in your party.")

            ### RELEASE THE IDOL BACK INTO THE WILD ###
            else:
                release_idol_id = idol[0][0]
                cursor.execute("""UPDATE Idols SET player_id = 0
                                WHERE idol_id == :release_idol_id""",
                                {'release_idol_id': release_idol_id})
                
                await ctx.send(f"{arg} has successfully been released from your party.")

            connection.commit()
            connection.close()
    
    ### !RESETGACHA ADMIN COMMAND: RESET GACHA GAME ###
    @commands.command(aliases=["rg"])
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

            await ctx.send("Gacha has successfully been reset.")
            connection.commit()
            connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("ERROR: You do not have permission for this command.")
    
    ### !ADDACHIEVEMENT ADMIN COMMAND: ADD NEW ACHIEVEMENT ###
    @commands.command(aliases=["newachievement", "adda", "newa"])
    async def addachievement(self, ctx, *args):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

        if (ctx.author.id == adminid):
            
            ### IF NO ARGS OR MORE THAN 2 ARGS, DISPLAY CORRECT SYNTAX ###
            print(len(args))
            print(args[0])
            print(args[1])
            if len(args) == 0:
                await ctx.send("ERROR: Insufficient parameters.\nPlease use the following syntax:\n`!addachievement \"[Name of Achievement]\" [(optional)Achievement ID]`\nExample: `!addachievement \"Stay (Stray Kids Stan)\"`")
            elif len(args) > 2:
                await ctx.send("ERROR: Too many parameters.\nPlease use the following syntax:\n`!addachievement \"[Name of Achievement]\" [(optional)Achievement ID]`\nExample: `!addachievement \"Stay (Stray Kids Stan)\"`")
            
            ### IF AT LEAST 1 ARG, ADD ACHIEVEMENT TO DATABASE ###
            else:
                new_achievement_name = args[0]
                print(new_achievement_name)
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()
                cursor.execute("""INSERT INTO AchievementList (achievement_name)
                                Values (:new_achievement_name)""",
                                {'new_achievement_name': new_achievement_name})
                
                ### IF 2 ARGS, UPDATE ACHIEVEMENT ID TO SPECIFIED NUMBER ###
                if len(args) == 2:
                    new_achievement_id = int(args[1])
                    print(new_achievement_id)
                    cursor.execute("""SELECT * FROM AchievementList
                                    WHERE achievement_id = :new_achievement_id""",
                                    {'new_achievement_id': new_achievement_id})
                    achievement_id_check = cursor.fetchone()
                    print(achievement_id_check)
                    
                    if (achievement_id_check is None or achievement_id_check[1] == new_achievement_name):
                        print(achievement_id_check)
                        cursor.execute("""UPDATE AchievementList SET achievement_id = :new_achievement_id
                                        WHERE achievement_name = :new_achievement_name""",
                                        {'new_achievement_id': new_achievement_id,'new_achievement_name': new_achievement_name})
                    
                    ### FAIL IF AN ACHIEVEMENT ALREADY EXISTS AT THAT ID ###
                    else:
                        await ctx.send(f"ERROR: ID #{new_achievement_id} already belongs to the achievement {achievement_id_check[1]}")
                        connection.rollback()
                        connection.close()
                        return

                
                ### CONFIRMATION MESSAGE ###
                cursor.execute("""SELECT * FROM AchievementList
                                WHERE achievement_name = :new_achievement_name""",
                                {'new_achievement_name': new_achievement_name})
                new_achievement = cursor.fetchone()

                await ctx.send(f"{new_achievement} has successfully been added to Achievements.")
            
                connection.commit()
                connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("ERROR: You do not have permission for this command.")
    
    ### !ADDGROUP ADMIN COMMAND: ADD NEW GROUP ###
    @commands.command(aliases=["newgroup", "addg", "newg"])
    async def addgroup(self, ctx, *args):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

        if (ctx.author.id == adminid):
            
            ### IF LESS THAN 2 ARGS OR MORE THAN 4 ARGS, DISPLAY CORRECT SYNTAX ###
            if len(args) < 2:
                await ctx.send("ERROR: Insufficient parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Achievement ID] [(optional)Group ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
            elif len(args) > 4:
                await ctx.send("ERROR: Too many parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Achievement ID] [(optional)Group ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
            
            ### IF AT LEAST 2 ARGS, ADD GROUP TO DATABASE ###
            else:
                new_group_name = args[0]
                new_group_logo = args[1]
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()
                cursor.execute("""INSERT INTO Groups (group_name, group_logo)
                                Values (:new_group_name, :new_group_logo)""",
                                {'new_group_name': new_group_name, 'new_group_logo': new_group_logo})
                
                ### IF AT LEAST 3 ARGS, UPDATE GROUP'S ACHIEVEMENT ID ###
                if len(args) > 2:
                    group_achievement_id = int(args[2])
                    cursor.execute("""UPDATE Groups SET achievement_id = :group_achievement_id
                              WHERE group_name = :new_group_name""",
                              {'group_achievement_id': group_achievement_id,'new_group_name': new_group_name})
                
                    ### IF 4 ARGS, UPDATE GROUP'S ID ###
                    if len(args) == 4:
                        new_group_id = int(args[3])
                        cursor.execute("""SELECT * FROM Groups
                                        WHERE group_id = :new_group_id""",
                                        {'new_group_id': new_group_id})
                        group_id_check = cursor.fetchone()
                        
                        if (group_id_check is None):
                            cursor.execute("""UPDATE Groups SET group_id = :new_group_id
                                            WHERE group_name = :new_group_name""",
                                            {'new_group_id': new_group_id,'new_group_name': new_group_name})
                        
                        ### FAIL IF A GROUP ALREADY EXISTS AT THAT ID ###
                        else:
                            await ctx.send(f"ERROR: ID #{new_group_id} already belongs to the group {group_id_check[1]}")
                            return
                
                ### CONFIRMATION MESSAGE ###
                cursor.execute("""SELECT * FROM Groups
                                WHERE group_name = :new_group_name""",
                                {'new_group_name': new_group_name})
                new_group = cursor.fetchone()

                new_group_name = new_group[1]
                new_group_logo = new_group[2]
                new_group_id = new_group[0]
                new_group_achievement_id = new_group[3]
                if new_group_achievement_id:
                    cursor.execute("""SELECT achievement_name FROM AchievementList
                                    WHERE achievement_id = :new_group_achievement_id""",
                                    {'new_group_achievement_id': new_group_achievement_id})
                    new_group_achievement = cursor.fetchone()[0]
                else:
                    new_group_achievement = None

                ### BUILD NEW GROUP CONFIRMATION CARD ###
                if new_group_logo and not os.path.exists(f"./cogs/gacha_images/logos/{new_group_logo}"):
                    print(f"ERROR: Group logo file not found: ./cogs/gacha_images/logos/{new_group_logo}")
                    return
                uploaded_new_group_logo = discord.File(f"./cogs/gacha_images/logos/{new_group_logo}", filename=new_group_logo)
                
                #print("creating embed")
                card = discord.Embed(title=new_group_name, description="has successfully been added to Groups.", color=discord.Color.green())
                #await ctx.send(embed=card)
                card.set_footer(text=f"New group added by {ctx.author.name}", icon_url=ctx.author.avatar)
                card.set_thumbnail(url=f"attachment://{new_group_logo}")
                card.add_field(name=f"Group ID: {new_group_id}", value=f"Achievement: {new_group_achievement}", inline=False)
                await ctx.send(files=[uploaded_new_group_logo], embed=card)
            
                connection.commit()
                connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("ERROR: You do not have permission for this command.")
    
    ### !ADDIDOL ADMIN COMMAND: ADD NEW IDOL ###
    @commands.command(aliases=["newidol", "addi", "newi"])
    async def addidol(self, ctx, *args):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

        if (ctx.author.id == adminid):
            
            ### IF LESS THAN 2 ARGS OR MORE THAN 4 ARGS, DISPLAY CORRECT SYNTAX ###
            if len(args) < 2:
                await ctx.send("ERROR: Insufficient parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID] [(optional)Idol ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
            elif len(args) > 4:
                await ctx.send("ERROR: Too many parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID] [(optional)Idol ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
            
            ### IF AT LEAST 2 ARGS, ADD IDOL TO DATABASE ###
            else:
                new_idol_name = args[0]
                new_idol_image = args[1]
                
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()
                cursor.execute("""INSERT INTO Idols (idol_name, idol_image)
                                Values (:new_idol_name, :new_idol_image)""",
                                {'new_idol_name': new_idol_name, 'new_idol_image': new_idol_image})
                
                ### IF 4 ARGS, UPDATE IDOL'S ID ###
                if len(args) == 4:
                    new_idol_id = args[3]
                    cursor.execute("""UPDATE Idols SET idol_id = :new_idol_id
                                    WHERE idol_image = :new_idol_image""",
                                    {'new_idol_id': new_idol_id,'new_idol_image': new_idol_image})
                
                ### ELSE, FETCH NEW IDOL'S ID ###
                else:
                    cursor.execute("""SELECT idol_id FROM Idols
                                    WHERE idol_image = :new_idol_image""",
                                    {'new_idol_image': new_idol_image})
                    new_idol_id = cursor.fetchone()[0]
                
                ### IF AT LEAST 3 ARGS, ENTER IDOL'S GROUP IN GROUPMEMBERS ###
                if len(args) > 2:
                    new_idol_group_id = args[2]
                
                ### IF ONLY 2 ARGS, DEFAULT IDOL'S GROUP TO 0 (SOLOIST) ###
                else:
                    new_idol_group_id = 0

                cursor.execute("""INSERT INTO GroupMembers (idol_id, group_id, active)
                                Values (:new_idol_id, :new_idol_group_id, TRUE)""",
                                {'new_idol_id': new_idol_id,'new_idol_group_id': new_idol_group_id})

                ### BUILD NEW IDOL CARD ###
                cursor.execute("""SELECT * FROM Groups
                                WHERE group_id = :new_idol_group_id""",
                                {'new_idol_group_id': new_idol_group_id})
                new_idol_group = cursor.fetchone()
                if new_idol_group is None:
                    await ctx.send("ERROR: The new idol's Group does not exist.")
                    return
                
                new_idol_group_name = new_idol_group[1]
                new_idol_group_logo = new_idol_group[2]

                if not os.path.exists(f"./cogs/gacha_images/idols/{new_idol_image}"):
                    print(f"ERROR: Idol image file not found: ./cogs/gacha_images/idols/{new_idol_image}")
                    return
                if new_idol_group_logo and not os.path.exists(f"./cogs/gacha_images/logos/{new_idol_group_logo}"):
                    print(f"ERROR: Group logo file not found: ./cogs/gacha_images/logos/{new_idol_group_logo}")
                    return
                uploaded_new_idol_image = discord.File(f"./cogs/gacha_images/idols/{new_idol_image}", filename=new_idol_image)
                if new_idol_group_logo:
                    uploaded_new_idol_group_logo = discord.File(f"./cogs/gacha_images/logos/{new_idol_group_logo}", filename=new_idol_group_logo)

                ### DISPLAY NEW IDOL CARD WITHOUT CATCH BUTTON ###
                card = discord.Embed(title=new_idol_name, description=new_idol_group_name, color=discord.Color.green())
                if new_idol_group_logo:
                    card.set_thumbnail(url=f"attachment://{new_idol_group_logo}")
                card.set_footer(text=f"New idol added by {ctx.author.name}", icon_url=ctx.author.avatar)
                card.set_image(url=f"attachment://{new_idol_image}")
                card.add_field(name=f"{new_idol_name} successfully added!", value="New idol has been added to the database.", inline=False)

                try:
                    await ctx.send(files=[uploaded_new_idol_image, uploaded_new_idol_group_logo], embed=card)
                    print("New idol card sent successfully")
                except Exception as e:
                    print(f"Error while sending new idol card: {e}")

            
                connection.commit()
                connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("ERROR: You do not have permission for this command.")

### BUTTON TO CATCH IDOLS ###
class GachaButtonMenu(discord.ui.View):
    roll_number = None

    ### BUTTON TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, roll_number, roller_id):
        super().__init__(timeout=60)
        self.roll_number = roll_number
        self.roller_id = roller_id
    
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