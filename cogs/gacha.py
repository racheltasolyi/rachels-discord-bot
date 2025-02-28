import os
import discord
from discord.ext import commands, menus
from discord.ext.menus import button, First, Last
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

        ### SPECIFY HIGHEST IDOL ID ###
        len_idols = 42

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
            roll_number = random.randrange(len_idols + 1) # excludes last number
            
        print(roll_number)

        ### ERROR MESSAGE IF INVALID IDOL ID ###
        if (roll_number < 0 or roll_number > len_idols):
            await ctx.send(f"ERROR: Invalid Idol ID: {roll_number}")
            return

        ### FETCH PLAYER ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        #print("connection made")

        cursor.execute("""SELECT * FROM Players
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})
        player = cursor.fetchone()
        #print(player)
        
        ### IF PLAYER IS NEW, ADD NEW PLAYER TO DATABASE ###
        if player is None:
            self.createplayer(ctx, cursor)
            cursor.execute("""SELECT * FROM Players
                            WHERE player_id = :roller_id""",
                            {'roller_id': roller_id})
            player = cursor.fetchone()
            #print(player)

        ### FETCH THE ROLLED IDOL AND THEIR GROUP ###
        cursor.execute("""SELECT Idols.idol_name, Idols.idol_image, GroupMembers.group_id, Groups.group_name, Groups.group_logo
                        FROM GroupMembers
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        INNER JOIN Idols ON GroupMembers.idol_id = Idols.idol_id
                        WHERE GroupMembers.idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll = cursor.fetchone()
        #print(roll)
        if roll is None:
            await ctx.send("ERROR: The rolled idol does not exist.")
            connection.close()
            return
        
        ### GET IDOL'S INFORMATION ###
        roll_name, roll_image, roll_group_id, roll_group_name, roll_logo = roll

        ### ERROR IF GROUP INFORMATION CAN NOT BE FOUND ###
        if roll_group_id is None:
            await ctx.send("ERROR: The rolled idol's Group does not exist.")
            connection.close()
            return

        ### DETERMINE IF ROLL IS OWNED OR WILD ###
        cursor.execute("""SELECT PartyPositions.player_id
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        WHERE PartyPositions.idol_id = :roll_number""",
                        {'roll_number': roll_number})
        owner_id = cursor.fetchone()
        #print(owner_id)
        if owner_id is None:
            roll_claimed = False
        else:
            owner_id = owner_id[0]
            roll_claimed = True

        ### BUILD IDOL CARD ###
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
            roll_owner = await ctx.bot.fetch_user(owner_id)
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
            await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!release \"<Idol ID>\"`\nExample: `!release 14`")
            return

        ### FETCH IDOL ###
        else:
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()
            cursor.execute("""SELECT Idols.idol_name, Idols.idol_image, PartyPositions.player_id
                            FROM PartyPositions
                            LEFT JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                            WHERE Idols.idol_id = :idol_id""",
                            {'idol_id': idol_id})
            idol = cursor.fetchone()
            #print(idol)

            ### ERROR MESSAGE IF IDOL DOES NOT EXIST ###
            if idol is None:
                await ctx.send(f"ERROR: The idol could not be found in your party. Use !profile to check the IDs of your idols.")
                connection.close()
                return

            ### GET IDOL'S INFO ###
            idol_name, idol_image, owner_id = idol
            
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
                view = ReleaseButtonMenu(idol_id, owner_id)
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
        
        ### IF PLAYER IS NEW, ADD NEW PLAYER TO DATABASE ###
        if player is None:
            self.createplayer(ctx, cursor)
            cursor.execute("""SELECT * FROM Players
                            WHERE player_id = :roller_id""",
                            {'roller_id': player_id})
            player = cursor.fetchone()

        ### FETCH ALL OF PLAYER'S IDOLS ###
        cursor.execute("""SELECT PartyPositions.idol_id, Idols.idol_name, Idols.idol_image
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        WHERE player_id = :player_id""",
                        {'player_id': player_id})
        idol_list = cursor.fetchall()
        print(idol_list)

        ### FETCH PLAYER'S ACTIVE TITLE & LOGO ###
        cursor.execute("""SELECT TitleList.title_name, Groups.group_logo
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        LEFT JOIN Groups ON CompletedTitles.title_id = Groups.title_id
                        WHERE (CompletedTitles.player_id = :player_id AND CompletedTitles.active_title = 1)""",
                        {'player_id': player_id})
        active_title = cursor.fetchone()
        if active_title is None:
            active_title_name = "Trainee"
            active_logo = None
        else:
            active_title_name, active_logo = active_title
        print(active_title_name)
        print(active_logo)

        ### FETCH ALL OF PLAYER'S TITLES ###
        cursor.execute("""SELECT TitleList.title_name
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        WHERE CompletedTitles.player_id = :player_id 
                        AND CompletedTitles.active_title = 0""",
                        {'player_id': player_id})
        titles = cursor.fetchall()
        formatted_titles = ""
        for title in titles:
            formatted_titles += f"* {title[0]}\n"
        #print(titles)

        ### BUILD PLAYER PROFILE CARD ###
        card = discord.Embed(
            title=f"{ctx.author.name}'s Idol Catcher Profile",
            description=f"### {active_title_name}",
            color=discord.Color.green())

        if active_logo is not None:
            uploaded_active_logo = discord.File(f"./cogs/gacha_images/logos/{active_logo}", filename=active_logo)
            card.set_thumbnail(url=f"attachment://{active_logo}")
        else:
            card.set_thumbnail(url=ctx.author.avatar)
        
        ### FETCH & SET PLAYER'S ACTIVE IDOL IMAGE ###
        if (len(idol_list) > 0):
            active_idol_image = idol_list[0][2]
            uploaded_active_idol_image = discord.File(f"./cogs/gacha_images/idols/{active_idol_image}", filename=active_idol_image)
            card.set_image(url=f"attachment://{active_idol_image}")

        ### ADD TITLES IF ANY ###
        if len(titles) > 0:
            card.add_field(
                name=f"Titles:",
                value=formatted_titles,
                inline=False)

        ### DISPLAY IDOLS IF ANY ###
        party_list = ""
        for i in range(10):
            if i >= len(idol_list):
                break
            if idol_list[i][0] < 10:
                #spaces = " " #n-space
                #spaces = "⠀" #braille blank
                spaces = " " #figure space (numerical digits) U+2007
            elif idol_list[i][0] >= 10 and idol_list[i][0] <100:
                spaces = ""
            party_list += "`" + spaces + f"{idol_list[i][0]}` {idol_list[i][1]}\n"
        if (len(idol_list) == 0):
            party_list = "Party is empty -- Use `!gacha` to catch an idol!"
        card.add_field(
            name=f"Top 10 Party Members:",
            value=party_list,
            inline=False
        )

        #print("Embed created!")

        ### DISPLAY PLAYER PROFILE CARD ###
        if (len(idol_list) == 0) and active_logo is None: # no idols and no logo
            await ctx.send(embed=card)
        elif (len(idol_list) == 0) and active_logo: # has logo but no idols
            await ctx.send(files=[uploaded_active_logo], embed=card)
        elif active_logo is None: # has idols but no logo
            await ctx.send(files=[uploaded_active_idol_image], embed=card)
        else: # has both idols and logo
            await ctx.send(files=[uploaded_active_idol_image, uploaded_active_logo], embed=card)

        connection.commit()
        connection.close()
    
    ### !RELEASE COMMAND: RELEASE SPECIFIED IDOL ###
    @commands.command(aliases=["picktitle", "title"])
    async def activetitle(self, ctx):
        
        ### FETCH PLAYER'S TITLES ###
        player_id = ctx.author.id
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT CompletedTitles.title_id, TitleList.title_name, CompletedTitles.active_title
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        WHERE player_id = :player_id""",
                        {'player_id': player_id})
        titles = cursor.fetchall()
        #print(titles)

        ### ERROR MESSAGE IF NO TITLES FOUND ###
        if titles is None:
            await ctx.send(f"ERROR: No titles found for player <@{player_id}>.")
            connection.close()
            return
        
        ### SEND SELECT MENU ###
        view = ActiveTitleSelectMenu(player_id, titles)
        view.message = await ctx.send("Choose one to set as your Active Title:", view=view)

        connection.commit()
        connection.close()
    
    ### !IDOLS COMMAND: DISPLAY PLAYER'S IDOLS IN A PAGINATED MENU ###
    @commands.command(aliases=["party"])
    async def idols(self, ctx):
        
        ### FETCH PLAYER'S IDOLS ###
        player_id = ctx.author.id
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT Idols.idol_id, Idols.idol_name, Groups.group_name
                        FROM GroupMembers
                        INNER JOIN Idols ON GroupMembers.idol_id = Idols.idol_id
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        INNER JOIN PartyPositions ON PartyPositions.idol_id = GroupMembers.idol_id
                        WHERE PartyPositions.player_id = :player_id""",
                        {'player_id': player_id})
        idols = cursor.fetchall()
        #print(idols)

        ### ERROR MESSAGE IF PLAYER NOT FOUND ###
        '''if titles is None:
            await ctx.send(f"ERROR: Player <@{player_id}> not found. Use `!gacha` to start the game!")
            connection.close()
            return'''
        
        ### SEND IDOLS LIST ###
        #view = ActiveTitleSelectMenu(player_id, titles)
        #view.message = await ctx.send("Choose one to set as your Active Title:", view=view)
        #data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        formatter = IdolsListPagesFormatter(idols, per_page=10)
        menu = IdolsListPages(formatter)
        await menu.start(ctx)

        #connection.commit()
        #connection.close()
    
    ### !MOVE COMMAND: REORGANIZE PARTY ORDER ###
    @commands.command(aliases=["mi", "movei", "midol"])
    async def moveidol(self, ctx, *args):
        print("!moveidol called")

        ### IF NO ARGS OR MORE THAN 3 ARGS, DISPLAY CORRECT SYNTAX ###
        if len(args) < 2:
            await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!move <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!move 0 down 3` or `!move 0 14`")
            return
        elif len(args) > 4:
            await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!move <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!move 0 down 3` or `!move 0 14`")
            return

        ### FAIL IF ARG[0] IS NOT INT ###
        try:
            idol_id = int(args[0])
        except (ValueError, TypeError):
            await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!move <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!move 0 down 3` or `!move 0 14`")
            return
        
        ### FETCH IDOL POSITION ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT PartyPositions.party_position, Idols.idol_name
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        WHERE PartyPositions.idol_id = :idol_id""",
                        {'idol_id': idol_id})
        idol = cursor.fetchone()
        print(idol)

        ### ERROR MESSAGE IF IDOL DOES NOT EXIST ###
        if idol is None:
            await ctx.send(f"ERROR: The idol with ID {idol_id} could not be found in your party. Use !profile to check the IDs of your idols.")
            connection.close()
            return
        
        idol_position, idol_name = idol
        print(idol_position)
        #print(args[1])

        ### MOVE IDOL POSITION DOWN ###
        if args[1] == "down" or args[1] == "d":
            if len(args) == 3:
                #print(args[2])
                ### FAIL IF ARG[2] IS NOT INT ###
                try:
                    positions = int(args[2])
                except (ValueError, TypeError):
                    await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!move <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!move 0 down 3` or `!move 0 14`")
                    return
            else:
                positions = 1
            
            print("move " + str(idol_id) + " down by " + str(positions))
            ### MOVE IDOL THE CORRECT NUMBER OF POSITIONS DOWN ###
            final_position = idol_position + positions

            ### SHIFT ALL IDOLS IN BETWEEN THE OLD AND NEW POSITIONS UP BY 1 ###
            cursor.execute("""SELECT party_position, idol_id FROM PartyPositions
                            WHERE (party_position > :idol_position AND party_position <= :final_position)""",
                            {'idol_position': idol_position, 'final_position': final_position})
            idols_to_move = cursor.fetchall()

            for party_position, moving_idol_id in idols_to_move:
                new_position = party_position - 1
                cursor.execute("""UPDATE PartyPositions
                                SET idol_id = :moving_idol_id
                                WHERE party_position = :new_position""",
                                {'moving_idol_id': moving_idol_id, 'new_position': new_position})
            
            ### PUT IDOL IN FINAL POSITION ###
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :idol_id
                            WHERE party_position = :final_position""",
                            {'idol_id': idol_id, 'final_position': final_position})

            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{idol_name} has been moved down by {positions}.")

        ### MOVE IDOL POSITION UP ###
        elif args[1] == "up" or args[1] == "u":
            if len(args) == 3:
                #print(args[2])
                ### FAIL IF ARG[2] IS NOT INT ###
                try:
                    positions = int(args[2])
                except (ValueError, TypeError):
                    await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!move <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!move 0 down 3` or `!move 0 14`")
                    return
            else:
                positions = 1

            print("move " + str(idol_id) + " up by " + str(positions))
            ### MOVE IDOL THE CORRECT NUMBER OF POSITIONS UP ###
            final_position = idol_position - positions

            ### SHIFT ALL IDOLS IN BETWEEN THE OLD AND NEW POSITIONS DOWN BY 1 ###
            cursor.execute("""SELECT party_position, idol_id FROM PartyPositions
                            WHERE (party_position > :idol_position AND party_position <= :final_position)
                            ORDER BY party_position DESC""",
                            {'idol_position': idol_position, 'final_position': final_position})
            idols_to_move = cursor.fetchall()

            for party_position, moving_idol_id in idols_to_move:
                new_position = party_position + 1
                cursor.execute("""UPDATE PartyPositions
                                SET idol_id = :moving_idol_id
                                WHERE party_position = :new_position""",
                                {'moving_idol_id': moving_idol_id, 'new_position': new_position})
            
            ### PUT IDOL IN FINAL POSITION ###
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :idol_id
                            WHERE party_position = :final_position""",
                            {'idol_id': idol_id, 'final_position': final_position})
            
            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{idol_name} has been moved up by {positions}.")

        ### SWAP IDOL POSITIONS ###
        else:
            ### FAIL IF ARG[1] IS NOT INT ###
            try:
                swap_id = int(args[1])
            except (ValueError, TypeError):
                await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!move <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!move 0 down 3` or `!move 0 14`")
                return
            
            print("swap " + str(idol_id) + " and " + str(swap_id))
            ### CHECK IF 2ND IDOL IS IN PLAYER'S PARTY AND FETCH POSITION ###
            cursor.execute("""SELECT PartyPositions.party_position, Idols.idol_name
                            FROM PartyPositions
                            INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                            WHERE PartyPositions.idol_id = :swap_id""",
                            {'swap_id': swap_id})
            swap_idol = cursor.fetchone()
            print(swap_idol)

            ### ERROR MESSAGE IF IDOL DOES NOT EXIST ###
            if swap_idol is None:
                await ctx.send(f"ERROR: The idol with ID {swap_id} could not be found in your party. Use !profile to check the IDs of your idols.")
                connection.close()
                return
            
            swap_position, swap_name = swap_idol
            
            ### SWAP POSITIONS ###
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :swap_id
                            WHERE party_position = :idol_position""",
                            {'swap_id': swap_id, 'idol_position': idol_position})
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :idol_id
                            WHERE party_position = :swap_position""",
                            {'idol_id': idol_id, 'swap_position': swap_position})
            
            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{idol_name} and {swap_name} have been swapped.")

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
            cursor.execute("""UPDATE PartyPositions SET idol_id = NULL
                              WHERE idol_id IS NOT NULL""")

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
                return
            elif len(args) > 2:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addtitle \"[Name of Title]\" [(optional)Title ID]`\nExample: `!addtitle \"Stay (Stray Kids Stan)\"`")
                return
            
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
                return
            elif len(args) > 4:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Title ID] [(optional)Group ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
                return

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
                return
            elif len(args) > 4:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID] [(optional)Idol ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
                return

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
    
    ### PRIVATE FUNCTION: ADD NEW PLAYER TO DATABASE ###
    def createplayer(self, ctx, cursor):

        player_id = ctx.author.id
        
        ### ADD NEW PLAYER TO PLAYERS ###
        cursor.execute("""INSERT INTO Players (player_id, player_username)
                            Values (:player_id, :player_username)""",
                        {'player_id': player_id, 'player_username': ctx.author.name})
        
        ### ADD PARTY SIZE OF 10 TO PLAYER ###
        for position in range(1, 11):
            cursor.execute("""INSERT INTO PartyPositions (player_id, party_position)
                                Values (:player_id, :position)""",
                            {'player_id': player_id, 'position': position})
        
        cursor.connection.commit()


### BUTTON MENU TO CATCH IDOLS ###
class GachaButtonMenu(discord.ui.View):
    roll_number = None

    ### BUTTON TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, roll_number, roller_id):
        super().__init__(timeout=10)
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
            ### GET PLAYER'S NEXT AVAILABLE POSITION ###
            cursor.execute("""SELECT party_position FROM PartyPositions
                            WHERE (player_id = :roller_id AND idol_id IS NULL)""",
                            {'roller_id': self.roller_id})
            party_position = cursor.fetchone()[0]
            print(party_position)

            ### ADD IDOL ID TO CORRECT PARTY POSITION ##
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :roll_number
                            WHERE (player_id = :roller_id AND party_position = :party_position)""",
                            {'roll_number': self.roll_number,
                             'roller_id': self.roller_id,
                             'party_position': party_position})
            content=f"{roll_name} was caught by {interaction.user.mention}!"
            for button in self.children:
                button.disabled = True
                button.label = f"{roll_name} has been caught!"
            await self.message.edit(view=self)
            #print(roll)

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"Nice try {interaction.user.mention}, {roll_name} can only be caught by <@{self.roller_id}> this time!"
        
        connection.commit()
        connection.close()

        await interaction.response.send_message(content=content)


### BUTTON MENU FOR !RELEASE CONFIRMATION ###
class ReleaseButtonMenu(discord.ui.View):
    idol_id = None
    owner_id = None
    idol_name = None

    ### MENU TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, idol_id, owner_id):
        super().__init__(timeout=60)
        self.idol_id = idol_id
        self.owner_id = owner_id

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT * FROM Idols
                          WHERE idol_id = :idol_id""",
                        {'idol_id': self.idol_id})
        idol = cursor.fetchone()
        self.idol_name = idol[1]
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

        ### RELEASE IDOL IF CORRECT USER, THEN DISABLE MENU ###
        if (user_id == self.owner_id):
            connection = sqlite3.connect("./cogs/idol_gacha.db")
            cursor = connection.cursor()

            ### GET PARTY POSITION BEFORE RELEASING ###
            cursor.execute("""SELECT party_position
                            FROM PartyPositions
                            WHERE idol_id = :idol_id""",
                            {'idol_id': self.idol_id})
            empty_position = cursor.fetchone()[0]
            print(empty_position)

            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = NULL
                            WHERE idol_id = :idol_id""",
                            {'idol_id': self.idol_id})
            content=f"{self.idol_name} has been released from <@{self.owner_id}>'s party."

            ### MOVE REMAINING IDOLS' PARTY POSITIONS UP BY 1 ###
            cursor.execute("""SELECT party_position, idol_id FROM PartyPositions
                            WHERE party_position > :empty_position""",
                            {'empty_position': empty_position})
            idols_to_move = cursor.fetchall()

            for party_position, moving_idol_id in idols_to_move:
                new_position = party_position - 1
                cursor.execute("""UPDATE PartyPositions
                                SET idol_id = :moving_idol_id
                                WHERE party_position = :new_position""",
                                {'moving_idol_id': moving_idol_id, 'new_position': new_position})
            
            ### FREE UP LAST PARTY POSITION ###
            final_position = idols_to_move[-1][0]
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = NULL
                            WHERE party_position = :final_position""",
                            {'final_position': final_position})

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"{self.idol_name} was released"
            await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER (IDOL NOT YET RELEASED) ###
        else:
            content=f"ERROR: Only <@{self.owner_id}> has permission to use this menu!"

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
        

### SELECT MENU FOR ACTIVE TITLE ###
class ActiveTitleSelectMenu(discord.ui.View):
    caller_id = None

    ### MENU TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, caller_id, titles):
        super().__init__(timeout=60)
        self.caller_id = caller_id

        options = []
        for title in titles:
            option = discord.SelectOption(label=title[1], value=title[0])
            if title[2] == 1:
                option.label += " <ACTIVE>"
                self.active_title_id = title[0]
                self.active_title = title[1]
            options.append(option)

        self.select = discord.ui.Select(
            placeholder="Select a Title",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    ### MENU DISABLES UPON TIMEOUT ###
    async def on_timeout(self) -> None:
        for child in self.children:
            if not child.disabled:
                child.disabled = True
                child.placeholder = "Command timed out"
        await self.message.edit(view=self)
    
    ### CALLBACK FUNCTION ###
    async def select_callback(self, interaction):
        user_id = interaction.user.id
        new_active_title_id = int(self.select.values[0])
        #print(new_active_title_id)
        #print(self.active_title_id)

        ### DO NOTHING IF ACTIVE TITLE IS SELECTED ###
        if (user_id == self.caller_id):

            if (new_active_title_id != self.active_title_id):

                ### CHANGE ACTIVE TITLE IF NEW TITLE IS SELECTED, THEN DISABLE MENU ###
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()

                ### DEACTIVATE OLD ACTIVE TITLE ###
                cursor.execute("""UPDATE CompletedTitles SET active_title = 0
                                WHERE title_id == :active_title_id""",
                                {'active_title_id': self.active_title_id})

                ### ACTIVATE NEW ACTIVE TITLE ###
                cursor.execute("""UPDATE CompletedTitles SET active_title = 1
                                WHERE title_id == :new_active_title_id""",
                                {'new_active_title_id': new_active_title_id})
                cursor.execute("""SELECT title_name FROM TitleList
                                WHERE title_id == :new_active_title_id""",
                                {'new_active_title_id': new_active_title_id})
                new_active_title = cursor.fetchone()[0]

                connection.commit()
                connection.close()

                content=f"<@{self.caller_id}>'s active title has been updated to {new_active_title}."

                ### DISABLE MENU ###
                for child in self.children:
                    child.disabled = True
                    child.placeholder = new_active_title
                await interaction.response.edit_message(view=self)
            
            else:
                content=f"ERROR: <@{self.caller_id}>'s active title is already {self.active_title}."

                ### DISABLE MENU ###
                for child in self.children:
                    child.disabled = True
                    child.placeholder = self.active_title
                await interaction.response.edit_message(view=self)

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"ERROR: Only <@{self.caller_id}> has permission to use this menu!"

        await interaction.followup.send(content=content)


### BUTTON MENU FOR !IDOLS ###
class IdolsListPages(discord.ui.View, menus.MenuPages):

    ### MENU TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, source):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None

    ### BUTTONS DISABLE UPON TIMEOUT ###
    async def on_timeout(self) -> None:
        for child in self.children:
            if not child.disabled:
                child.disabled = True
        await self.message.edit(view=self)

    async def start(self, ctx, *, channel=None, wait=False):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.ctx.author

    @discord.ui.button(emoji='⏮️', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction, button):
        await self.show_page(0)
        await interaction.response.defer()

    @discord.ui.button(emoji='◀️', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction, button):
        await self.show_checked_page(self.current_page - 1)
        await interaction.response.defer()

    @discord.ui.button(emoji='▶️', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, button):
        await self.show_checked_page(self.current_page + 1)
        await interaction.response.defer()

    @discord.ui.button(emoji='⏭️', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction, button):
        await self.show_page(self._source.get_max_pages() - 1)
        await interaction.response.defer()
    
    @discord.ui.button(emoji='⏹️', style=discord.ButtonStyle.gray)
    async def stop_page(self, interaction, button):
        self.stop()
        for child in self.children:
            if not child.disabled:
                child.disabled = True
        await self.message.edit(view=self)
        #await self.message.edit(view=None)
        await interaction.response.defer()


### FORMATS PAGES FOR !IDOLS ###
class IdolsListPagesFormatter(menus.ListPageSource):
    async def format_page(self, menu, entries):
        embed = discord.Embed(
            title=f"{menu.ctx.author}'s Party",
            color=discord.Color.green()
        )

        party_list = ""
        for idol in entries:
            if idol[0] < 10:
                spaces = " " #figure space (numerical digits) U+2007
            elif idol[0] >= 10 and idol[0] <100:
                spaces = ""
            party_list += "`" + spaces + f"{idol[0]}` `{idol[2]}` {idol[1]}\n"
        embed.add_field(
            name="",
            value=party_list,
            inline=False
        )

        #embed.set_footer(text=f"{self.get_page}")
        return embed
    

async def setup(bot):
    await bot.add_cog(Gacha(bot))