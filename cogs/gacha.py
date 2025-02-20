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
            cursor.execute("""INSERT INTO Players (player_id, player_username)
                              Values (:roller_id, :roller_username)""",
                            {'roller_id': roller_id, 'roller_username': ctx.author.name})

        ### FETCH THE ROLLED IDOL AND THEIR GROUP ###
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll = cursor.fetchone()
        if roll is None:
            await ctx.send("ERROR: The rolled idol does not exist.")
            connection.close()
            return
        cursor.execute("""SELECT group_id FROM GroupMembers
                          WHERE idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll_group_id = cursor.fetchone()[0]
        #print(roll_group_id)
        if roll_group_id is None:
            await ctx.send("ERROR: The rolled idol's Group ID does not exist.")
            connection.close()
            return
        cursor.execute("""SELECT * FROM Groups
                          WHERE group_id = :roll_group_id""",
                        {'roll_group_id': roll_group_id})
        roll_group = cursor.fetchone()
        #print(roll_group)
        if roll_group is None:
            await ctx.send("ERROR: The rolled idol's Group does not exist.")
            connection.close()
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
                view = GachaButtonMenu(roll_number, roller_id)
                view.message = await ctx.send(files=[uploaded_roll_image], embed=card, view=view)
            else:
                view = GachaButtonMenu(roll_number, roller_id)
                view.message = await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card, view=view)
        
        ### UPDATE TIMESTAMP OF PLAYER'S LAST ROLL ###
        cursor.execute("""UPDATE Players
                          SET last_roll_timestamp = DATETIME('now', 'localtime')
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})

        connection.commit()
        connection.close()
    
    ### !RELEASE COMMAND: RELEASE SPECIFIED IDOL ###
    @commands.command(aliases=["r"])
    async def release(self, ctx, arg = None):

        ### IF NO ARGS, DISPLAY CORRECT SYNTAX ###
        if arg is None:
            await ctx.send("ERROR: Insufficient parameters. Please use the following syntax:\n`!release \"<Idol ID>\"`\nExample: `!release 14`")
            return

        ### FAIL IF ARG IS NOT INT ###
        try:
            idol_id = int(arg)
        except (ValueError, TypeError):
            await ctx.send("ERROR: Invalid ID. Please enter a number using the following syntax:\n`!release \"<Idol ID>\"`\nExample: `!release 14`")
            return

        ### FETCH IDOL ###
        else:
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            cursor.execute("""SELECT * FROM Idols
                            WHERE idol_id = :arg""",
                            {'arg': idol_id})
            idol = cursor.fetchone()

            ### ERROR MESSAGE IF IDOL DOES NOT EXIST ###
            if idol is None:
                await ctx.send(f"ERROR: No idols with the ID of {idol_id} can be found. Use !profile to check the IDs of your idols.")
                connection.close()
                return

            ### GET IDOL'S INFO ###
            idol_name = idol[1]
            idol_image = idol[2]
            owner_id = idol[3]
            
            ### IF PLAYER IS OWNER, SEND CONFIRMATION CARD ###
            if ctx.author.id == owner_id:

                uploaded_idol_image = discord.File(f"./cogs/gacha_images/idols/{idol_image}", filename=idol_image)

                ### FETCH IDOL'S GROUP INFO ###
                cursor.execute("""SELECT Groups.group_name, Groups.group_logo
                                FROM GroupMembers
                                INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                                WHERE GroupMembers.idol_id = :idol_id""",
                                {'idol_id': idol_id})
                group_name, group_logo = cursor.fetchone()
                if group_logo:
                    uploaded_group_logo = discord.File(f"./cogs/gacha_images/logos/{group_logo}", filename=group_logo)

                ### BUILD CARD ###
                card = discord.Embed(title=idol_name, description=group_name, color=discord.Color.green())
                if group_logo:
                    card.set_thumbnail(url=f"attachment://{group_logo}")
                card.set_footer(text=f"Owner: {ctx.author.name}", icon_url=ctx.author.avatar)
                card.set_image(url=f"attachment://{idol_image}")
                card.add_field(name=f"Are you sure you want to release {idol_name}?", value="This action cannot be reversed.", inline=False)

                ### SEND CARD WITH RELEASE BUTTON ###
                view = ReleaseButtonMenu(idol_id)
                if group_logo:
                    view.message = await ctx.send(files=[uploaded_idol_image, uploaded_group_logo], embed=card, view=view)
                else:
                    view.message = await ctx.send(files=[uploaded_idol_image], embed=card, view=view)

            else:
                ### ERROR MESSAGE IF USER DOES NOT OWN IDOL ###
                await ctx.send(f"ERROR: {idol_name} is not in your party.")
                connection.close()
                return

            connection.commit()
            connection.close()
    
    ### !PROFILE COMMAND: DISPLAY PLAYER'S PROFILE CARD ###
    @commands.command(aliases=["pf"])
    async def profile(self, ctx):

        player_id = ctx.author.id

        ### FETCH PLAYER FROM DB ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        #print("connection made")

        cursor.execute("""SELECT * FROM Players
                          WHERE player_id = :player_id""",
                        {'player_id': player_id})
        player = cursor.fetchone()
        
        ### IF PLAYER IS NEW, THROW ERROR (LATER: ADD NEW PLAYER TO DATABASE) ###
        if player is None:
            # should create new helper function to create new player?
            await ctx.send("ERROR: Player not found. Use `!gacha` to start the game and catch your first idol!")
            connection.close()
            return

        ### FETCH ALL OF PLAYER'S IDOLS ###
        cursor.execute("""SELECT * FROM Idols
                          WHERE player_id = :player_id""",
                        {'player_id': player_id})
        idol_list = cursor.fetchall()
        #print(idol_list)

        ### FETCH PLAYER'S ACTIVE TITLE & LOGO ###
        cursor.execute("""SELECT COALESCE(TitleList.title_name, 'Trainee') AS title_name, Groups.group_logo
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        LEFT JOIN Groups ON CompletedTitles.title_id = Groups.title_id
                        WHERE CompletedTitles.player_id = :player_id 
                        AND CompletedTitles.active_title = 1""",
                        {'player_id': player_id})
        active_title_query = cursor.fetchone()
        if active_title_query is None:
            active_title_name = "Trainee"
            active_logo = None
        else:
            active_title_name = active_title_query[0]
            active_logo = active_title_query[1]

        ### FETCH ALL OF PLAYER'S TITLES ###
        cursor.execute("""SELECT TitleList.title_name
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        WHERE CompletedTitles.player_id = :player_id 
                        AND CompletedTitles.active_title = 0""",
                        {'player_id': player_id})
        title_list_query = cursor.fetchall()
        title_list = ""
        for title in title_list_query:
            title_list += f"* {title[0]}\n"

        ### FETCH PLAYER'S CHOSEN IDOL IMAGE ###
        if (len(idol_list) > 0):
            active_idol = idol_list[0]
            active_idol_image = active_idol[2]
            #print(active_idol_image)

        ### BUILD PLAYER PROFILE CARD ###
        if (len(idol_list) > 0):
            uploaded_active_idol_image = discord.File(f"./cogs/gacha_images/idols/{active_idol_image}", filename=active_idol_image)
        if active_logo is not None:
            uploaded_active_logo = discord.File(f"./cogs/gacha_images/logos/{active_logo}", filename=active_logo)
        
        card = discord.Embed(title=f"{ctx.author.name}'s Idol Catcher Profile", description=f"### {active_title_name}", color=discord.Color.green())
        if active_logo is not None:
            card.set_thumbnail(url=f"attachment://{active_logo}")
        else:
            card.set_thumbnail(url=ctx.author.avatar)
        if (len(idol_list) > 0):
            card.set_image(url=f"attachment://{active_idol_image}")

        if title_list_query:
            card.add_field(
                name=f"\n{ctx.author.name}'s Titles:",
                value=title_list,
                inline=False
            )

        party_list = ""
        for idol in idol_list:
            if idol[0] < 10:
                #spaces = " " #n-space
                #spaces = "⠀" #braille blank
                spaces = " " #figure space (numerical digits) U+2007
            elif idol[0] >= 10 and idol[0] <100:
                spaces = ""
            party_list += "`" + spaces + f"{idol[0]}` {idol[1]}\n"
        if (len(idol_list) == 0):
            party_list = "Party is empty -- Use `!gacha` to catch an idol!"
        card.add_field(
            name=f"\n{ctx.author.name}'s Party:",
            value=party_list,
            inline=False
        )

        #print("Embed created!")

        ### DISPLAY PLAYER PROFILE CARD ###
        if (len(idol_list) == 0) and active_logo is None:
            await ctx.send(embed=card)
        elif active_logo is None:
            await ctx.send(files=[uploaded_active_idol_image], embed=card)
        else:
            await ctx.send(files=[uploaded_active_idol_image, uploaded_active_logo], embed=card)

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

            await ctx.send("Gacha has been reset.")
            connection.commit()
            connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")
    
    ### !ADDTITLE ADMIN COMMAND: ADD NEW TITLE ###
    @commands.command(aliases=["newtitle", "addt", "newt"])
    async def addtitle(self, ctx, *args):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

        if (ctx.author.id == adminid):
            
            ### IF NO ARGS OR MORE THAN 2 ARGS, DISPLAY CORRECT SYNTAX ###
            if len(args) == 0:
                await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!addtitle \"[Name of Title]\" [(optional)Title ID]`\nExample: `!addtitle \"Stay (Stray Kids Stan)\"`")
            elif len(args) > 2:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addtitle \"[Name of Title]\" [(optional)Title ID]`\nExample: `!addtitle \"Stay (Stray Kids Stan)\"`")
            
            ### IF AT LEAST 1 ARG, ADD TITLE TO DATABASE ###
            else:
                new_title_name = args[0]
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()
                cursor.execute("""INSERT INTO TitleList (title_name)
                                Values (:new_title_name)""",
                                {'new_title_name': new_title_name})
                
                ### IF 2 ARGS, UPDATE TITLE ID TO SPECIFIED NUMBER ###
                if len(args) == 2:
                    new_title_id = args[1]
                    cursor.execute("""UPDATE TitleList SET title_id = :new_title_id
                              WHERE title_name = :new_title_name""",
                              {'new_title_id': new_title_id,'new_title_name': new_title_name})
                
                ### CONFIRMATION MESSAGE ###
                cursor.execute("""SELECT * FROM TitleList
                          WHERE title_name = :new_title_name""",
                          {'new_title_name': new_title_name})
                new_title = cursor.fetchone()

                await ctx.send(f"{new_title} has successfully been added to Titles.")
            
                connection.commit()
                connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")
    
    ### !ADDGROUP ADMIN COMMAND: ADD NEW GROUP ###
    @commands.command(aliases=["newgroup", "addg", "newg"])
    async def addgroup(self, ctx, *args):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

        if (ctx.author.id == adminid):
            
            ### IF LESS THAN 2 ARGS OR MORE THAN 4 ARGS, DISPLAY CORRECT SYNTAX ###
            if len(args) < 2:
                await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Title ID] [(optional)Group ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
            elif len(args) > 4:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Title ID] [(optional)Group ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
            
            ### IF AT LEAST 2 ARGS, ADD GROUP TO DATABASE ###
            else:
                new_group_name = args[0]
                new_group_logo = args[1]
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()
                cursor.execute("""INSERT INTO Groups (group_name, group_logo)
                                Values (:new_group_name, :new_group_logo)""",
                                {'new_group_name': new_group_name, 'new_group_logo': new_group_logo})
                
                ### IF AT LEAST 3 ARGS, UPDATE GROUP'S TITLE ID ###
                if len(args) > 2:
                    group_title_id = args[2]
                    cursor.execute("""UPDATE Groups SET title_id = :group_title_id
                              WHERE group_name = :new_group_name""",
                              {'group_title_id': group_title_id,'new_group_name': new_group_name})
                
                    ### IF 4 ARGS, UPDATE GROUP'S ID ###
                    if len(args) == 4:
                        new_group_id = args[3]
                        cursor.execute("""UPDATE Groups SET group_id = :new_group_id
                                WHERE group_name = :new_group_name""",
                                {'new_group_id': new_group_id,'new_group_name': new_group_name})
                
                ### CONFIRMATION MESSAGE ###
                cursor.execute("""SELECT * FROM Groups
                                WHERE group_name = :new_group_name""",
                                {'new_group_name': new_group_name})
                new_group = cursor.fetchone()
                #await ctx.send(f"{new_group} has successfully been added to Groups.")

                new_group_name = new_group[1]
                new_group_logo = new_group[2]
                new_group_id = new_group[0]
                new_group_title_id = new_group[3]
                #print(f"new_group_name: {new_group_name}")
                #print(f"new_group_logo: {new_group_logo}")
                #print(f"new_group_id: {new_group_id}")
                #print(f"new_group_title_id: {new_group_title_id}")
                if new_group_title_id:
                    cursor.execute("""SELECT title_name FROM TitleList
                                    WHERE title_id = :new_group_title_id""",
                                    {'new_group_title_id': new_group_title_id})
                    new_group_title = cursor.fetchone()[0]
                else:
                    new_group_title = None
                #print(f"new_group_title: {new_group_title}")

                ### BUILD NEW GROUP CONFIRMATION CARD ###
                if new_group_logo and not os.path.exists(f"./cogs/gacha_images/logos/{new_group_logo}"):
                    print(f"ERROR: Group logo file not found: ./cogs/gacha_images/logos/{new_group_logo}")
                    connection.close()
                    return
                uploaded_new_group_logo = discord.File(f"./cogs/gacha_images/logos/{new_group_logo}", filename=new_group_logo)
                
                #print("creating embed")
                card = discord.Embed(title=new_group_name, description="has been added to Groups.", color=discord.Color.green())
                #await ctx.send(embed=card)
                card.set_footer(text=f"New group added by {ctx.author.name}", icon_url=ctx.author.avatar)
                card.set_thumbnail(url=f"attachment://{new_group_logo}")
                card.add_field(name=f"Group ID: {new_group_id}", value=f"Title: {new_group_title}", inline=False)
                await ctx.send(files=[uploaded_new_group_logo], embed=card)
            
                connection.commit()
                connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")
    
    ### !ADDIDOL ADMIN COMMAND: ADD NEW IDOL ###
    @commands.command(aliases=["newidol", "addi", "newi"])
    async def addidol(self, ctx, *args):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

        if (ctx.author.id == adminid):
            
            ### IF LESS THAN 2 ARGS OR MORE THAN 4 ARGS, DISPLAY CORRECT SYNTAX ###
            if len(args) < 2:
                await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID] [(optional)Idol ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
            elif len(args) > 4:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID] [(optional)Idol ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
            
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
                    connection.close()
                    return
                
                new_idol_group_name = new_idol_group[1]
                new_idol_group_logo = new_idol_group[2]

                if not os.path.exists(f"./cogs/gacha_images/idols/{new_idol_image}"):
                    print(f"ERROR: Idol image file not found: ./cogs/gacha_images/idols/{new_idol_image}")
                    connection.close()
                    return
                if new_idol_group_logo and not os.path.exists(f"./cogs/gacha_images/logos/{new_idol_group_logo}"):
                    print(f"ERROR: Group logo file not found: ./cogs/gacha_images/logos/{new_idol_group_logo}")
                    connection.close()
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
                except Exception as e:
                    print(f"Error while sending new idol card: {e}")

            
                connection.commit()
                connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")

    ### !RESETROLLS ADMIN COMMAND: RESET SPECIFIED PLAYER'S ROLLS ###
    @commands.command(aliases=["rr"])
    async def resetrolls(self, ctx, user: discord.User = None):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())
            #print("adminid =", repr(adminid), type(adminid))
            #print("ctx.author.id =", repr(ctx.author.id), type(ctx.author.id))
            #print(ctx.author.id == adminid)

        if (ctx.author.id == adminid):

            ### IF NO ARGS, DISPLAY CORRECT SYNTAX ###
            if user is None:
                await ctx.send(f"ERROR: Insufficient parameters. Please use the following syntax:\n`!resetrolls <@User or User ID>`\nExample: `!resetrolls {ctx.author.id}`")
                return

            ### FETCH USER'S MAX ROLLS ###
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            
            cursor.execute("""SELECT max_rolls FROM Players
                            WHERE player_id = :user_id""",
                            {'user_id': user.id})
            max_rolls = cursor.fetchone()

            ### FAIL IF PLAYER DOES NOT EXIST ###
            if max_rolls is None:
                await ctx.send(f"ERROR: Player could not be found.")
                connection.close()
                return
            max_rolls = max_rolls[0]

            ### RESET USER'S ROLLS TO MAX ###
            cursor.execute("""UPDATE Players SET rolls_left = :max_rolls
                            WHERE (player_id = :user_id)""",
                            {'max_rolls': max_rolls, 'user_id': user.id})

            ### SEND CONFIRMATION MESSAGE ###
            cursor.execute("""SELECT rolls_left FROM Players
                            WHERE (player_id = :user_id)""",
                            {'user_id': user.id})
            rolls_left = cursor.fetchone()[0]

            await ctx.send(f"<@{user.id}>'s rolls have been reset to {rolls_left}.")

            connection.commit()
            connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")

    ### !SETROLLS ADMIN COMMAND: SET SPECIFIED PLAYER'S ROLLS TO SPECIFIED AMOUNT ###
    @commands.command(aliases=["sr"])
    async def setrolls(self, ctx, user: discord.User = None, set_rolls: int = -1):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())
            #print("adminid =", repr(adminid), type(adminid))
            #print("ctx.author.id =", repr(ctx.author.id), type(ctx.author.id))
            #print(ctx.author.id == adminid)

        if (ctx.author.id == adminid):

            ### IF NO ARGS, DISPLAY CORRECT SYNTAX ###
            if user is None or set_rolls < 0:
                await ctx.send(f"ERROR: Insufficient or incorrect parameters. Please use the following syntax:\n`!setrolls <@User or User ID> <Number of Rolls>`\nExample: `!setrolls {ctx.author.id} 10`")
                return

            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            
            ### FAIL IF PLAYER DOES NOT EXIST ###
            cursor.execute("""SELECT * FROM Players
                            WHERE player_id = :user_id""",
                            {'user_id': user.id})
            player = cursor.fetchone()
            if player is None:
                await ctx.send(f"ERROR: Player could not be found.")
                connection.close()
                return

            ### SET USER'S ROLLS ###
            cursor.execute("""UPDATE Players SET rolls_left = :set_rolls
                            WHERE player_id = :user_id""",
                            {'set_rolls': set_rolls, 'user_id': user.id})

            ### SEND CONFIRMATION MESSAGE ###
            cursor.execute("""SELECT rolls_left FROM Players
                            WHERE player_id = :user_id""",
                            {'user_id': user.id})
            rolls_left = cursor.fetchone()[0]

            await ctx.send(f"<@{user.id}>'s rolls have been set to {rolls_left}.")

            connection.commit()
            connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")
    
    ### !ADDROLL ADMIN COMMAND: ADD ROLLS TO SPECIFIED PLAYER (DEFAULT IS +1 ROLL) ###
    @commands.command(aliases=["ar"])
    async def addroll(self, ctx, user: discord.User = None, add_roll: int = 1):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())
            #print("adminid =", repr(adminid), type(adminid))
            #print("ctx.author.id =", repr(ctx.author.id), type(ctx.author.id))
            #print(ctx.author.id == adminid)

        if (ctx.author.id == adminid):

            ### IF NO ARGS, DISPLAY CORRECT SYNTAX ###
            if user is None or add_roll < 1:
                await ctx.send(f"ERROR: Insufficient or incorrect parameters. Please use the following syntax:\n`!addroll <@User or User ID> (optional)<Number of Rolls>`\nExample: `!addroll {ctx.author.id} 5`")
                return

            ### FETCH USER'S ROLLS LEFT ###
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            
            cursor.execute("""SELECT rolls_left FROM Players
                            WHERE player_id = :user_id""",
                            {'user_id': user.id})
            rolls_left = cursor.fetchone()

            ### FAIL IF PLAYER DOES NOT EXIST ###
            if rolls_left is None:
                await ctx.send(f"ERROR: Player could not be found.")
                connection.close()
                return
            
            rolls_left = rolls_left[0] + add_roll

            ### ADD TO USER'S ROLLS ###
            cursor.execute("""UPDATE Players SET rolls_left = :rolls_left
                            WHERE (player_id = :user_id)""",
                            {'rolls_left': rolls_left, 'user_id': user.id})

            ### SEND CONFIRMATION MESSAGE ###
            cursor.execute("""SELECT rolls_left FROM Players
                            WHERE (player_id = :user_id)""",
                            {'user_id': user.id})
            rolls_left = cursor.fetchone()[0]

            await ctx.send(f"<@{user.id}> now has {rolls_left} rolls left.")

            connection.commit()
            connection.close()
        
        ### FAIL IF USER IS NOT ADMIN ###
        else:
            await ctx.send("You do not have permission for this command.")

### BUTTON MENU TO CATCH IDOLS ###
class GachaButtonMenu(discord.ui.View):
    roll_number = None

    ### BUTTON TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, roll_number, roller_id):
        super().__init__(timeout=5)
        self.roll_number = roll_number
        self.roller_id = roller_id

    ### BUTTON DISABLES UPON TIMEOUT ###
    async def on_timeout(self) -> None:
        for button in self.children:
            if not button.disabled:
                button.disabled = True
                button.label = "The wild idol fled!"
        await self.message.edit(view=self)
    
    ### IDOL IS CAUGHT UPON BUTTON PRESS ###
    @discord.ui.button(label="Throw Pokeball", style=discord.ButtonStyle.blurple)
    async def throwpokeball(self, interaction: discord.Interaction, button: discord.ui.Button):
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

        ### SUCCESSFULLY CATCH IDOL IF CORRECT PLAYER, THEN DISABLE BUTTON ###
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
                for button in self.children:
                    button.disabled = True
                    button.label = f"{roll_name} has been caught!"
                await self.message.edit(view=self)
                #print(roll)
            else:
                content=f"You already caught {roll_name}!"

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"Nice try {interaction.user.mention}, {roll_name} can only be caught by <@{roller}> this time!"
        
        connection.commit()
        connection.close()

        await interaction.response.send_message(content=content)


### BUTTON MENU FOR !RELEASE CONFIRMATION ###
class ReleaseButtonMenu(discord.ui.View):
    idol_id = None
    idol_name = None
    caller_id = None

    ### MENU TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, idol_id):
        super().__init__(timeout=60)
        self.idol_id = idol_id

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': self.idol_id})
        idol = cursor.fetchone()
        self.idol_name = idol[1]
        self.caller_id = idol[3]
        connection.commit()
        connection.close()

    ### BUTTONS DISABLE UPON TIMEOUT ###
    async def on_timeout(self) -> None:
        for button in self.children:
            if not button.disabled:
                button.disabled = True
                if button.label == "Release":
                    button.label = "Command timed out"
        await self.message.edit(view=self)
    
    ### RELEASE BUTTON: IDOL IS RELEASED ###
    @discord.ui.button(label="Release", style=discord.ButtonStyle.red)
    async def releaseconfirmation(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': self.idol_id})
        owner_id = cursor.fetchone()[3]

        ### RELEASE IDOL IF CORRECT USER, THEN DISABLE MENU ###
        if (user_id == owner_id):
            cursor.execute("""UPDATE Idols SET player_id = 0
                            WHERE idol_id == :idol_id""",
                            {'idol_id': self.idol_id})
            content=f"{self.idol_name} has been released from <@{owner_id}>'s party."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"{self.idol_name} was released"
            await self.message.edit(view=self)
        
        ### FAIL IF IDOL HAS ALREADY BEEN RELEASED ###
        elif (owner_id == 0):
            content=f"ERROR: {self.idol_name} has already been released."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"{self.idol_name} was released"
            await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER (IDOL NOT YET RELEASED) ###
        else:
            content=f"ERROR: Only <@{self.caller_id}> has permission to use this menu!"

        connection.commit()
        connection.close()
        await interaction.response.send_message(content=content)

    ### CANCEL BUTTON: MENU IS DEACTIVATED ###
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def releasecancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': self.idol_id})
        owner_id = cursor.fetchone()[3]
        connection.close()

        ### DISABLE MENU IF IDOL HAS ALREADY BEEN RELEASED ###
        if (owner_id == 0):
            content=f"ERROR: {self.idol_name} has already been released."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"{self.idol_name} was released"
            await self.message.edit(view=self)

        ### CANCEL COMMAND IF CORRECT USER, THEN DISABLE MENU ###
        elif (user_id == self.caller_id):

            content=f"<@{self.caller_id}> canceled the command."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"Command was canceled"
            await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"ERROR: Only <@{self.caller_id}> has permission to use this menu!"

        await interaction.response.send_message(content=content)
        

async def setup(bot):
    await bot.add_cog(Gacha(bot))