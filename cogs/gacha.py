import os
import discord
from discord.ext import commands, menus
from discord.ext.menus import button, First, Last
import random
import sqlite3
from datetime import datetime

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    ### !GACHA COMMAND: ROLL A RANDOM IDOL ###
    @commands.command(aliases=["g"])
    async def gacha(self, ctx, arg: int = None):

        roller_id = ctx.author.id

        ### SPECIFY HIGHEST IDOL ID ###
        len_idols = 244 # about 4% chance to roll a specific idol with each 10 pull

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
            roll_number = random.randrange(len_idols + 1) # randrange() excludes last number
            
        print(f"!gacha roll_number: {roll_number}")

        ### ERROR MESSAGE IF INVALID IDOL ID ###
        if (roll_number < 0 or roll_number > len_idols):
            await ctx.send(f"ERROR: Invalid Idol ID: {roll_number}")
            return

        ### FETCH PLAYER ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()

        cursor.execute("""SELECT rolls_left, max_rolls, last_roll_timestamp FROM Players
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})
        player = cursor.fetchone()
        
        ### IF PLAYER IS NEW, ADD NEW PLAYER TO DATABASE ###
        if player is None:
            self.createplayer(ctx, roller_id, cursor)
            cursor.execute("""SELECT rolls_left, max_rolls, last_roll_timestamp FROM Players
                            WHERE player_id = :roller_id""",
                            {'roller_id': roller_id})
            player = cursor.fetchone()
        
        rolls_left, max_rolls, last_roll_timestamp = player
        
        ### UPDATE AND GET NEW TIMESTAMP OF PLAYER'S LAST ROLL ###
        cursor.execute("""UPDATE Players
                          SET last_roll_timestamp = DATETIME('now', 'localtime')
                          WHERE player_id = :roller_id""",
                        {'roller_id': roller_id})
        cursor.execute("""SELECT last_roll_timestamp FROM Players
                            WHERE player_id = :roller_id""",
                            {'roller_id': roller_id})
        current_roll_timestamp = cursor.fetchone()[0]
        print(f"!gacha current timestamp for roll {roll_number}: {current_roll_timestamp}")

        ### IF LAST ROLL WAS BEFORE THE HOURLY RESET, RESET PLAYER'S ROLLS_LEFT TO MAX ###
        last_dt = datetime.strptime(last_roll_timestamp, "%Y-%m-%d %H:%M:%S")
        current_dt = datetime.strptime(current_roll_timestamp, "%Y-%m-%d %H:%M:%S")
        if (last_dt.date() == current_dt.date() and last_dt.hour == current_dt.hour):
            reset = False
        else:
            reset = True
        
        if reset:
            print(f"!gacha: Resetting rolls for {ctx.author.name}")
            cursor.execute("""UPDATE Players
                          SET rolls_left = :max_rolls
                          WHERE player_id = :roller_id""",
                        {'max_rolls': max_rolls, 'roller_id': roller_id})
            rolls_left = max_rolls
        
        ### IF NO ROLLS LEFT, SEND HOW MANY MINUTES UNTIL NEXT RESET ###
        if rolls_left <= 0:
            minutes_left = 60 - datetime.now().minute
            await ctx.send(f"No rolls left! Time until next reset: {minutes_left} minutes")
            connection.close()
            return
        
        ### IF PLAYER HAS ROLLS, DECREMENT 1 ROLL ###
        else:
            rolls_left -= 1
            cursor.execute("""UPDATE Players
                          SET rolls_left = :rolls_left
                          WHERE player_id = :roller_id""",
                        {'rolls_left': rolls_left, 'roller_id': roller_id})

        ### FETCH THE ROLLED IDOL AND THEIR GROUP ###
        cursor.execute("""SELECT Idols.idol_name, Idols.idol_image, GroupMembers.group_id, Groups.group_name, Groups.group_logo
                        FROM GroupMembers
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        INNER JOIN Idols ON GroupMembers.idol_id = Idols.idol_id
                        WHERE GroupMembers.idol_id = :roll_number""",
                        {'roll_number': roll_number})
        roll = cursor.fetchone()
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
        if owner_id is None:
            roll_claimed = False
        else:
            owner_id = owner_id[0]
            roll_claimed = True

        ### BUILD IDOL CARD ###
        uploaded_roll_image = discord.File(f"./cogs/gacha_images/idols/{roll_image}", filename=roll_image)
        if roll_logo is not None:
            uploaded_roll_logo = discord.File(f"./cogs/gacha_images/logos/{roll_logo}", filename=roll_logo)

        card = discord.Embed(title=f"{roll_name}", description=roll_group_name, color=discord.Color.green())
        if roll_logo is not None:
            card.set_thumbnail(url=f"attachment://{roll_logo}")
        card.set_image(url=f"attachment://{roll_image}")
        card.set_footer(text=f"Rolled by {ctx.author.name} 🎲 Rolls remaining: {rolls_left}", icon_url=ctx.author.avatar)

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
                card = discord.Embed(title=idol_name, description=group_name, color=discord.Color.red())
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
    async def profile(self, ctx, member: discord.Member = None):
        
        if member is None:
            player_id = ctx.author.id
            player_name = ctx.author.name
            avatar = ctx.author.avatar
        else:
            player_id = member.id
            player_name = member.name
            avatar = member.avatar
        print(f"!profile called for: {player_name}")

        ### FETCH PLAYER FROM DB ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()

        cursor.execute("""SELECT * FROM Players
                          WHERE player_id = :player_id""",
                        {'player_id': player_id})
        player = cursor.fetchone()
        
        ### IF PLAYER IS NEW, ADD NEW PLAYER TO DATABASE ###
        if player is None:
            self.createplayer(ctx, player_id, cursor)
            cursor.execute("""SELECT * FROM Players
                            WHERE player_id = :roller_id""",
                            {'roller_id': player_id})
            player = cursor.fetchone()

        ### FETCH ALL OF PLAYER'S IDOLS ###
        cursor.execute("""SELECT PartyPositions.idol_id, Idols.idol_name, Idols.idol_image, Groups.group_name
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        INNER JOIN GroupMembers ON Idols.idol_id = GroupMembers.idol_id
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        WHERE player_id = :player_id
                        LIMIT 5""",
                        {'player_id': player_id})
        idol_list = cursor.fetchall()
        print(f"!profile idol_list for {player_name}: {idol_list}")

        ### FETCH PLAYER'S ACTIVE TITLE & LOGO ###
        cursor.execute("""SELECT TitleList.title_name, Groups.group_logo
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        LEFT JOIN Groups ON CompletedTitles.title_id = Groups.title_id
                        WHERE (CompletedTitles.player_id = :player_id AND CompletedTitles.position = 1)""",
                        {'player_id': player_id})
        active_title = cursor.fetchone()
        if active_title is None:
            active_title_name = "Trainee"
            active_logo = None
        else:
            active_title_name, active_logo = active_title

        ### FETCH ALL OF PLAYER'S TITLES WITH IDS ###
        cursor.execute("""SELECT CompletedTitles.title_id, TitleList.title_name
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        WHERE (CompletedTitles.player_id = :player_id AND CompletedTitles.position > 1)""",
                        {'player_id': player_id})
        titles = cursor.fetchall()

        ### BUILD PLAYER PROFILE CARD ###
        card = discord.Embed(
            title=f"{player_name}'s Idol Catcher Profile",
            description=f"### {active_title_name}",
            color=discord.Color.purple())

        if active_logo is not None:
            uploaded_active_logo = discord.File(f"./cogs/gacha_images/logos/{active_logo}", filename=active_logo)
            card.set_thumbnail(url=f"attachment://{active_logo}")
        else:
            card.set_thumbnail(url=avatar)
        
        ### FETCH & SET PLAYER'S ACTIVE IDOL IMAGE ###
        if (len(idol_list) > 0):
            active_idol_image = idol_list[0][2]
            uploaded_active_idol_image = discord.File(f"./cogs/gacha_images/idols/{active_idol_image}", filename=active_idol_image)
            card.set_image(url=f"attachment://{active_idol_image}")

        ### FORMAT AND DISPLAY TITLES IF ANY ###
        if len(titles) > 0:
            formatted_titles = ""
            max_digits = len(str(max(titles)[0]))
            for title in titles:
                spaces = ""
                num_digits = len(str(title[0]))
                for i in range(max_digits - num_digits):
                    spaces += " " #figure space (numerical digits) U+2007
                formatted_titles += "`" + spaces + f"{title[0]}` {title[1]}\n"
            card.add_field(
                name=f"Titles:",
                value=formatted_titles,
                inline=False)

        ### FORMAT AND DISPLAY IDOLS IF ANY ###
        if (len(idol_list) > 0):
            party_list = ""
            max_digits = len(str(max(idol_list)[0])) # max_digits=3, num_digits=1, spaces=2
            for idol in idol_list:
                spaces = ""
                num_digits = len(str(idol[0]))
                for i in range(max_digits - num_digits):
                    spaces += " " #figure space (numerical digits) U+2007
                party_list += "`" + spaces + f"{idol[0]}` `{idol[3]}` {idol[1]}\n"
        else:
            party_list = "Party is empty -- Use `!gacha` to catch an idol!"
        card.add_field(
            name=f"Top Party Members:",
            value=party_list,
            inline=False
        )

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
    
    ### !VIEW COMMAND: VIEW A CAPTURED IDOL ###
    @commands.command(aliases=["v"])
    async def view(self, ctx, arg: int = None):

        ### GET IDOL ID ###
        idol_id = arg
        print(f"!view called for: {idol_id}")

        ### FETCH THE ROLLED IDOL, THEIR GROUP, AND OWNER ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT Idols.idol_name, Idols.idol_image, Groups.group_name, Groups.group_logo, PartyPositions.player_id
                        FROM PartyPositions
                        INNER JOIN GroupMembers ON PartyPositions.idol_id = GroupMembers.idol_id
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        INNER JOIN Idols ON GroupMembers.idol_id = Idols.idol_id
                        WHERE PartyPositions.idol_id = :idol_id""",
                        {'idol_id': idol_id})
        idol = cursor.fetchone()
        
        if idol is None:
            await ctx.send("That idol has not been captured or does not exist.")
            connection.close()
            return
        
        ### GET IDOL'S INFORMATION ###
        idol_name, idol_image, group_name, group_logo, owner_id = idol

        ### BUILD IDOL CARD ###
        uploaded_idol_image = discord.File(f"./cogs/gacha_images/idols/{idol_image}", filename=idol_image)
        if group_logo is not None:
            uploaded_group_logo = discord.File(f"./cogs/gacha_images/logos/{group_logo}", filename=group_logo)

        card = discord.Embed(title=f"{idol_name} `{group_name}`", description=f"ID: {idol_id}", color=discord.Color.purple())
        if group_logo is not None:
            card.set_thumbnail(url=f"attachment://{group_logo}")
        card.set_image(url=f"attachment://{idol_image}")
        card.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar)

        ### DISPLAY IDOL CARD ###
        owner_name = await ctx.bot.fetch_user(owner_id)
        card.add_field(
            name=f"Owner: {owner_name}",
            value="",
            inline=False
        )
        if group_logo is None:
            await ctx.send(files=[uploaded_idol_image], embed=card)
        else:
            await ctx.send(files=[uploaded_idol_image, uploaded_group_logo], embed=card)
        
        connection.commit()
        connection.close()

    ### !TRADE COMMAND: TRADE YOUR IDOL WITH ANOTHER PLAYER'S IDOL ###
    @commands.command(aliases=["t"])
    async def trade(self, ctx, *args):

        ### IF NOT ENOUGH OR TOO MANY ARGS, DISPLAY CORRECT SYNTAX ###
        if len(args) < 3:
            await ctx.send("ERROR: Insufficient parameters. Please use the following syntax:\n`!trade <@User> <Your Idol ID> <User's Idol ID>`\nExample: `!trade @souldaida 0 14`")
            return
        if len(args) > 3:
            await ctx.send("ERROR: Too many parameters. Please use the following syntax:\n`!trade <@User> <Your Idol ID> <User's Idol ID>`\nExample: `!trade @souldaida 0 14`")
            return
        
        ### FAIL IF USER IS NOT MENTIONED CORRECTLY ###
        try:
            trade_user = await commands.MemberConverter().convert(ctx, args[0])
        except commands.CommandError:
            await ctx.send(f"ERROR: Invalid mention: {args[0]}")
            return

        user_id = ctx.author.id
        trade_user_id = trade_user.id

        ### FAIL IF USER TRADES WITH SELF ###
        if user_id == trade_user_id:
            await ctx.send("ERROR: You cannot trade with yourself.")
            return

        ### FAIL IF 2ND OR 3RD ARGS ARE NOT INTS ###
        try:
            user_idol_id = int(args[1])
        except (ValueError, TypeError):
            await ctx.send("ERROR: Your Idol ID was invalid. Please enter a number using the following syntax:\n`!trade <@User> <Your Idol ID> <User's Idol ID>`\nExample: `!trade @souldaida 0 14`")
            return

        try:
            trade_idol_id = int(args[2])
        except (ValueError, TypeError):
            await ctx.send("ERROR: User's Idol ID was invalid. Please enter a number using the following syntax:\n`!trade <@User> <Your Idol ID> <User's Idol ID>`\nExample: `!trade @souldaida 0 14`")
            return
        
        user_name = ctx.author.name
        trade_user_name = await ctx.bot.fetch_user(trade_user_id)

        ### FETCH IDOL ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT Idols.idol_name, Groups.group_name
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        INNER JOIN GroupMembers ON PartyPositions.idol_id = GroupMembers.idol_id
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        WHERE (PartyPositions.player_id = :user_id AND Idols.idol_id = :idol_id)""",
                        {'user_id': user_id, 'idol_id': user_idol_id})
        user_idol = cursor.fetchone()

        ### ERROR MESSAGE IF IDOL NOT IN PLAYER'S PARTY ###
        if user_idol is None:
            await ctx.send(f"ERROR: The idol could not be found in your party. Use `!profile` or `!idols` to check the IDs of your idols.")
            connection.close()
            return

        ### FETCH TRADE IDOL ###
        cursor.execute("""SELECT Idols.idol_name, Groups.group_name
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        INNER JOIN GroupMembers ON PartyPositions.idol_id = GroupMembers.idol_id
                        INNER JOIN Groups ON GroupMembers.group_id = Groups.group_id
                        WHERE (PartyPositions.player_id = :user_id AND Idols.idol_id = :idol_id)""",
                        {'user_id': trade_user_id, 'idol_id': trade_idol_id})
        trade_idol = cursor.fetchone()

        ### ERROR MESSAGE IF TRADE IDOL NOT IN TRADE PLAYER'S PARTY ###
        if trade_idol is None:
            await ctx.send(f"ERROR: The requested idol could not be found in <@{trade_user_id}>'s party.")
            connection.close()
            return
        
        ### GET IDOL'S INFO ###
        user_idol_name, user_group_name = user_idol
        trade_idol_name, trade_group_name = trade_idol

        ### BUILD CARD ###
        card = discord.Embed(title=f"Trade requested by {user_name}", description="", color=discord.Color.gold())
        card.add_field(
            name=f"{user_name}",
            value=f"`{user_idol_id}` `{user_group_name}` {user_idol_name}",
            inline=False
        )
        card.add_field(
            name=f"{trade_user_name}",
            value=f"`{trade_idol_id}` `{trade_group_name}` {trade_idol_name}",
            inline=False
        )
        card.add_field(
            name="Do you accept this trade?",
            value="Press your buttons to confirm in the next 60 seconds.",
            inline=False
        )

        ### SEND CONFIRMATION BUTTONS ###
        view = TradeButtonMenu(user_id, user_name, user_idol_id, user_idol_name, trade_user_id, trade_user_name, trade_idol_id, trade_idol_name)
        view.message = await ctx.send(embed=card, view=view)

        connection.commit()
        connection.close()

    ### !ACTIVETITLE COMMAND: CHANGE ACTIVE TITLE ###
    @commands.command(aliases=["picktitle", "title", "at"])
    async def activetitle(self, ctx):
        
        ### FETCH PLAYER'S TITLES ###
        player_id = ctx.author.id
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT CompletedTitles.title_id, TitleList.title_name, CompletedTitles.position
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        WHERE player_id = :player_id
                        ORDER BY CompletedTitles.position""",
                        {'player_id': player_id})
        titles = cursor.fetchall()

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
    @commands.command(aliases=["i", "party"])
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

        ### ERROR MESSAGE IF NO IDOLS ###
        if len(idols) == 0:
            await ctx.send(f"Your party is empty. Use `!gacha` to catch some idols!")
            connection.close()
            return
        
        ### SEND IDOLS LIST ###
        #view = ActiveTitleSelectMenu(player_id, titles)
        #view.message = await ctx.send("Choose one to set as your Active Title:", view=view)
        #data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        formatter = IdolsListPagesFormatter(idols, per_page=10)
        menu = IdolsListPages(formatter)
        await menu.start(ctx)

        connection.commit()
        connection.close()
    
    ### !MOVEIDOL COMMAND: REORGANIZE PARTY ORDER ###
    @commands.command(aliases=["mi", "movei", "midol"])
    async def moveidol(self, ctx, *args):

        ### IF NO ARGS OR MORE THAN 3 ARGS, DISPLAY CORRECT SYNTAX ###
        if len(args) < 2:
            await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!moveidol <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`")
            return
        elif len(args) > 4:
            await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!moveidol <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`")
            return

        ### FAIL IF ARG[0] IS NOT INT ###
        try:
            idol_id = int(args[0])
        except (ValueError, TypeError):
            await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!moveidol <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`")
            return
        
        ### GET PLAYER ID ###
        player_id = ctx.author.id
        
        ### FETCH IDOL POSITION ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT PartyPositions.party_position, Idols.idol_name
                        FROM PartyPositions
                        INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                        WHERE (PartyPositions.idol_id = :idol_id AND PartyPositions.player_id = :player_id)""",
                        {'idol_id': idol_id, 'player_id': player_id})
        idol = cursor.fetchone()
        print(f"!moveidol called on idol {idol_id}")

        ### ERROR MESSAGE IF IDOL NOT IN PLAYER'S PARTY ###
        if idol is None:
            await ctx.send(f"ERROR: The idol with ID {idol_id} could not be found in your party. Use `!profile` or `!idols` to check the IDs of your idols.")
            connection.close()
            return
        
        idol_position, idol_name = idol

        ### MOVE IDOL POSITION DOWN ###
        if args[1] == "down" or args[1] == "d":
            if len(args) == 3:
                ### FAIL IF ARG[2] IS NOT INT ###
                try:
                    positions = int(args[2])
                except (ValueError, TypeError):
                    await ctx.send("ERROR: Invalid number of positions. Please enter a number using the following syntax:\n`!moveidol <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`")
                    connection.close()
                    return
            else:
                positions = 1
            
            ### MOVE IDOL THE CORRECT NUMBER OF POSITIONS DOWN ###
            final_position = idol_position + positions # ID=21, idol_position=1, positions=10(8), final_position=11(9), max_positions=9
            cursor.execute("""SELECT COUNT(*)
                            FROM PartyPositions
                            WHERE (player_id = :player_id AND idol_id IS NOT NULL)""",
                            {'player_id': player_id})
            max_positions = cursor.fetchone()[0]

            if (final_position > max_positions):
                positions = max_positions - idol_position
                final_position = max_positions

            ### SHIFT ALL IDOLS IN BETWEEN THE OLD AND NEW POSITIONS UP BY 1 ###
            cursor.execute("""SELECT party_position, idol_id
                            FROM PartyPositions
                            WHERE (player_id = :player_id AND party_position > :idol_position AND party_position <= :final_position)""",
                            {'player_id': player_id, 'idol_position': idol_position, 'final_position': final_position})
            idols_to_move = cursor.fetchall()

            for party_position, moving_idol_id in idols_to_move:
                new_position = party_position - 1
                cursor.execute("""UPDATE PartyPositions
                                SET idol_id = :moving_idol_id
                                WHERE (player_id = :player_id AND party_position = :new_position)""",
                                {'player_id': player_id, 'moving_idol_id': moving_idol_id, 'new_position': new_position})
            
            ### PUT IDOL IN FINAL POSITION ###
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :idol_id
                            WHERE (player_id = :player_id AND party_position = :final_position)""",
                            {'player_id': player_id, 'idol_id': idol_id, 'final_position': final_position})

            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{idol_name} has been moved down by {positions}.")

        ### MOVE IDOL POSITION UP ###
        elif args[1] == "up" or args[1] == "u":
            if len(args) == 3:
                ### FAIL IF ARG[2] IS NOT INT ###
                try:
                    positions = int(args[2])
                except (ValueError, TypeError):
                    await ctx.send("ERROR: Invalid number of positions. Please enter a number using the following syntax:\n`!moveidol <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`")
                    connection.close()
                    return
            else:
                positions = 1

            ### MOVE IDOL THE CORRECT NUMBER OF POSITIONS UP ###
            final_position = idol_position - positions # ID=40, idol_position=5, positions=10, final_position=-5
            if (final_position < 1):
                positions = idol_position - 1
                final_position = 1

            ### SHIFT ALL IDOLS IN BETWEEN THE OLD AND NEW POSITIONS DOWN BY 1 ###
            cursor.execute("""SELECT party_position, idol_id
                            FROM PartyPositions
                            WHERE (player_id = :player_id AND party_position < :idol_position AND party_position >= :final_position)
                            ORDER BY party_position DESC""",
                            {'player_id': player_id, 'idol_position': idol_position, 'final_position': final_position})
            idols_to_move = cursor.fetchall()

            for party_position, moving_idol_id in idols_to_move:
                new_position = party_position + 1
                cursor.execute("""UPDATE PartyPositions
                                SET idol_id = :moving_idol_id
                                WHERE (player_id = :player_id AND party_position = :new_position)""",
                                {'player_id': player_id, 'moving_idol_id': moving_idol_id, 'new_position': new_position})
            
            ### PUT IDOL IN FINAL POSITION ###
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :idol_id
                            WHERE (player_id = :player_id AND party_position = :final_position)""",
                            {'player_id': player_id, 'idol_id': idol_id, 'final_position': final_position})
            
            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{idol_name} has been moved up by {positions}.")

        ### SWAP IDOL POSITIONS ###
        else:
            ### FAIL IF ARG[1] IS NOT INT ###
            try:
                swap_id = int(args[1])
            except (ValueError, TypeError):
                await ctx.send("ERROR: Invalid Idol ID. Please enter a number using the following syntax:\n`!moveidol <Idol ID> <up/down/ID of Idol to swap with> <(optional) #>`\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`")
                connection.close()
                return
            
            ### CHECK IF 2ND IDOL IS IN PLAYER'S PARTY AND FETCH POSITION ###
            cursor.execute("""SELECT PartyPositions.party_position, Idols.idol_name
                            FROM PartyPositions
                            INNER JOIN Idols ON PartyPositions.idol_id = Idols.idol_id
                            WHERE (PartyPositions.player_id = :player_id AND PartyPositions.idol_id = :swap_id)""",
                            {'player_id': player_id, 'swap_id': swap_id})
            swap_idol = cursor.fetchone()

            ### ERROR MESSAGE IF IDOL NOT IN PLAYER'S PARTY ###
            if swap_idol is None:
                await ctx.send(f"ERROR: The idol with ID {swap_id} could not be found in your party. Use `!profile` or `!idols` to check the IDs of your idols.")
                connection.close()
                return
            
            swap_position, swap_name = swap_idol
            
            ### SWAP POSITIONS ###
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :swap_id
                            WHERE (player_id = :player_id AND party_position = :idol_position)""",
                            {'player_id': player_id, 'swap_id': swap_id, 'idol_position': idol_position})
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :idol_id
                            WHERE (player_id = :player_id AND party_position = :swap_position)""",
                            {'player_id': player_id, 'idol_id': idol_id, 'swap_position': swap_position})
            
            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{idol_name} and {swap_name} have been swapped.")

        connection.commit()
        connection.close()
    
    ### !MOVETITLE COMMAND: REORGANIZE TITLE LIST ORDER ###
    @commands.command(aliases=["mt", "movet", "mtitle"])
    async def movetitle(self, ctx, *args):

        ### IF NO ARGS OR MORE THAN 3 ARGS, DISPLAY CORRECT SYNTAX ###
        if len(args) < 2:
            await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!movetitle <Title ID> <up/down/ID of Title to swap with> <(optional) #>`\nExample: `!movetitle 0 down 2` or `!movetitle 0 1`")
            return
        elif len(args) > 4:
            await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!movetitle <Title ID> <up/down/ID of Title to swap with> <(optional) #>`\nExample: `!movetitle 0 down 2` or `!movetitle 0 1`")
            return

        ### FAIL IF ARG[0] IS NOT INT ###
        try:
            title_id = int(args[0])
        except (ValueError, TypeError):
            await ctx.send("ERROR: Invalid Title ID. Please enter a number using the following syntax:\n`!movetitle <Title ID> <up/down/ID of Title to swap with> <(optional) #>`\nExample: `!movetitle 0 down 2` or `!movetitle 0 1`")
            return
        
        ### GET PLAYER ID ###
        player_id = ctx.author.id
        
        ### FETCH TITLE POSITION ###
        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT CompletedTitles.position, TitleList.title_name
                        FROM CompletedTitles
                        INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                        WHERE (CompletedTitles.title_id = :title_id AND CompletedTitles.player_id = :player_id)""",
                        {'title_id': title_id, 'player_id': player_id})
        title = cursor.fetchone()
        print(f"!movetitle called on {title}")

        ### ERROR MESSAGE IF PLAYER DOES NOT HAVE TITLE ###
        if title is None:
            await ctx.send(f"ERROR: You have not completed the title with ID {title_id}. Use `!profile` to check the IDs of your titles.")
            connection.close()
            return
        
        title_position, title_name = title

        ### ERROR IF ACTIVE TITLE ###
        if title_position == 1:
            await ctx.send(f"ERROR: You cannot move your active title. Use `!activetitle` to change it to a different title first.")
            connection.close()
            return

        ### MOVE TITLE POSITION DOWN ###
        if args[1] == "down" or args[1] == "d":
            if len(args) == 3:
                ### FAIL IF ARG[2] IS NOT INT ###
                try:
                    positions = int(args[2])
                except (ValueError, TypeError):
                    await ctx.send("ERROR: Invalid number of positions. Please enter a number using the following syntax:\n`!movetitle <Title ID> <up/down/ID of Title to swap with> <(optional) #>`\nExample: `!movetitle 0 down 2` or `!movetitle 0 1`")
                    connection.close()
                    return
            else:
                positions = 1
            
            ### MOVE TITLE THE CORRECT NUMBER OF POSITIONS DOWN ###
            final_position = title_position + positions # ID=21, idol_position=1, positions=10(8), final_position=11(9), max_positions=9
            cursor.execute("""SELECT position
                            FROM CompletedTitles
                            WHERE player_id = :player_id
                            ORDER BY position DESC
                            LIMIT 1""",
                            {'player_id': player_id})
            max_positions = cursor.fetchone()[0]

            if (final_position > max_positions):
                positions = max_positions - title_position
                final_position = max_positions

            ### SHIFT ALL TITLES IN BETWEEN THE OLD AND NEW POSITIONS UP BY 1 ###
            cursor.execute("""SELECT position, title_id
                            FROM CompletedTitles
                            WHERE (player_id = :player_id AND position > :title_position AND position <= :final_position)""",
                            {'player_id': player_id, 'title_position': title_position, 'final_position': final_position})
            titles_to_move = cursor.fetchall()

            for position, moving_title_id in titles_to_move:
                new_position = position - 1
                cursor.execute("""UPDATE CompletedTitles
                                SET title_id = :moving_title_id
                                WHERE (player_id = :player_id AND position = :new_position)""",
                                {'player_id': player_id, 'moving_title_id': moving_title_id, 'new_position': new_position})
            
            ### PUT TITLE IN FINAL POSITION ###
            cursor.execute("""UPDATE CompletedTitles
                            SET title_id = :title_id
                            WHERE (player_id = :player_id AND position = :final_position)""",
                            {'player_id': player_id, 'title_id': title_id, 'final_position': final_position})

            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{title_name} has been moved down by {positions}.")

        ### MOVE TITLE POSITION UP ###
        elif args[1] == "up" or args[1] == "u":
            if len(args) == 3:
                ### FAIL IF ARG[2] IS NOT INT ###
                try:
                    positions = int(args[2])
                except (ValueError, TypeError):
                    await ctx.send("ERROR: Invalid number of positions. Please enter a number using the following syntax:\n`!movetitle <Title ID> <up/down/ID of Title to swap with> <(optional) #>`\nExample: `!movetitle 0 down 2` or `!movetitle 0 1`")
                    connection.close()
                    return
            else:
                positions = 1

            ### MOVE TITLE THE CORRECT NUMBER OF POSITIONS UP (MIN POSITION IS 2) ###
            final_position = title_position - positions # ID=0, title_position=2, positions=10, final_position=-8
            if (final_position < 2):
                positions = title_position - 2
                final_position = 2

            ### SHIFT ALL TITLES IN BETWEEN THE OLD AND NEW POSITIONS DOWN BY 1 ###
            cursor.execute("""SELECT position, title_id
                            FROM CompletedTitles
                            WHERE (player_id = :player_id AND position < :title_position AND position >= :final_position)
                            ORDER BY position DESC""",
                            {'player_id': player_id, 'title_position': title_position, 'final_position': final_position})
            titles_to_move = cursor.fetchall()

            for position, moving_title_id in titles_to_move:
                new_position = position + 1
                cursor.execute("""UPDATE CompletedTitles
                                SET title_id = :moving_title_id
                                WHERE (player_id = :player_id AND position = :new_position)""",
                                {'player_id': player_id, 'moving_title_id': moving_title_id, 'new_position': new_position})
            
            ### PUT TITLE IN FINAL POSITION ###
            cursor.execute("""UPDATE CompletedTitles
                            SET title_id = :title_id
                            WHERE (player_id = :player_id AND position = :final_position)""",
                            {'player_id': player_id, 'title_id': title_id, 'final_position': final_position})
            
            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{title_name} has been moved up by {positions}.")

        ### SWAP TITLE POSITIONS ###
        else:
            ### FAIL IF ARG[1] IS NOT INT ###
            try:
                swap_id = int(args[1])
            except (ValueError, TypeError):
                await ctx.send("ERROR: Invalid Title ID. Please enter a number using the following syntax:\n`!movetitle <Title ID> <up/down/ID of Title to swap with> <(optional) #>`\nExample: `!movetitle 0 down 2` or `!movetitle 0 1`")
                connection.close()
                return
            
            ### CHECK IF PLAYER HAS 2ND TITLE AND FETCH POSITION ###
            cursor.execute("""SELECT CompletedTitles.position, TitleList.title_name
                            FROM CompletedTitles
                            INNER JOIN TitleList ON CompletedTitles.title_id = TitleList.title_id
                            WHERE (CompletedTitles.player_id = :player_id AND CompletedTitles.title_id = :swap_id)""",
                            {'player_id': player_id, 'swap_id': swap_id})
            swap_title = cursor.fetchone()

            ### ERROR MESSAGE IF PLAYER DOES NOT HAVE TITLE ###
            if swap_title is None:
                await ctx.send(f"ERROR: You have not completed the title with ID {swap_id}. Use `!profile` to check the IDs of your titles.")
                connection.close()
                return
            
            swap_position, swap_name = swap_title
            
            ### SWAP POSITIONS ###
            cursor.execute("""UPDATE CompletedTitles
                            SET title_id = :swap_id
                            WHERE (player_id = :player_id AND position = :title_position)""",
                            {'player_id': player_id, 'swap_id': swap_id, 'title_position': title_position})
            cursor.execute("""UPDATE CompletedTitles
                            SET title_id = :title_id
                            WHERE (player_id = :player_id AND position = :swap_position)""",
                            {'player_id': player_id, 'title_id': title_id, 'swap_position': swap_position})
            
            ### CONFIRMATION MESSAGE ###
            await ctx.send(f"{title_name} and {swap_name} have been swapped.")

        connection.commit()
        connection.close()

    ### !TUTORIAL COMMAND: BRIEF OVERVIEW OF IDOL CATCHER ###
    @commands.command(aliases=["tut"])
    async def tutorial(self, ctx):

        ### INITIALIZE CARD ###
        card = discord.Embed(
            title="Idol Catcher Tutorial",
            description="Alpha Test: 3/8/2025 - 3/16/2025\nWelcome to the Idol Catcher alpha, where you can roll and collect your favorite idols. Please note that your progress will not be saved after the alpha. Use `!gacha` to start playing.",
            color=discord.Color.blue())
        
        card.set_footer(text="Use !idolhelp for additional help and commands.")

        card.add_field(
                name="Rolling",
                value="* Use `!gacha` or `!g` to roll.\n* You get 10 rolls per hour. Rolls reset on the hour.\n* You can only catch idols that you roll.\n* If another player owns an idol, you cannot catch it, even if you roll it.\n* You can change an idol's picture once you catch it. Ping Admin SoulDaiDa for this.",
                inline=False)
        
        card.add_field(
                name="Your Party",
                value="* Use `!profile` to see your player profile with your top 5 idols, or use `!idols` to see your full party.\n* Use `!moveidol` to rearrange your party.",
                inline=False)
        
        card.add_field(
                name="Trading",
                value="* Use `!trade <@User> <Idol ID> <Idol ID>` to trade idols with another player.\n* Use `!profile` or `!idols` to see your idols' IDs.",
                inline=False)
        
        card.add_field(
                name="Release",
                value="* Use `!release <Idol ID>` to release an idol from your party.",
                inline=False)
        
        await ctx.send(embed=card)
    
    ### !IDOLHELP COMMAND: EXPLANATION OF ALL COMMANDS ###
    @commands.command(aliases=["h", "ih"])
    async def idolhelp(self, ctx, arg: str = None):

        ### !IDOLHELP GACHA ###
        if arg in {"gacha", "g", "!gacha", "!g"}:
            card = discord.Embed(
            title="!gacha command",
            description="Aliases: `!g`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="None",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Roll a random idol. If the idol is wild, the player may catch it.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* Players have unlimited pokeballs.\n* Idols can only be caught by the player who rolled it.\n* Non-wild (owned) idols can be rolled.\n* If an owned idol is rolled, it cannot be caught.\n* Players get 10 rolls per hour. Rolls reset on the hour.\n* Ping Admin SoulDaiDa to change your idol's picture.\n* Pokeball button times out after 60 seconds of inaction.",
                    inline=False)

        ### !IDOLHELP RELEASE ###
        elif arg in {"release", "r", "!release", "!r"}:
            card = discord.Embed(
            title="!release command",
            description="Aliases: `!r`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="1. Idol ID (can be found with `!profile` or `!idols`)\nExample: `!release 0`",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Release the specified idol.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* The player is prompted for confirmation before release.\n* Once confirmed, this cannot be reversed.\n* Confirmation times out after 60 seconds of inaction.",
                    inline=False)

        ### !IDOLHELP PROFILE ###
        elif arg in {"profile", "pf", "!profile", "!pf"}:
            card = discord.Embed(
            title="!profile command",
            description="Aliases: `!pf`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value=f"1. (optional) @User\nExample: `!profile @{ctx.author.name}`",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Display player's profile.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* If no parameter is given, your profile is displayed.\n* The profile displays the user's top 5 party members and their top idol's picture.",
                    inline=False)
        
        ### !IDOLHELP VIEW ###
        elif arg in {"view", "v", "!view", "!v"}:
            card = discord.Embed(
            title="!view command",
            description="Aliases: `!v`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="1. Idol ID (can be found with `!profile` or `!idols`)\nExample: `!view 0`",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="View a captured idol card.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* Wild idols cannot be viewed.\n* You can view idols that are in other players' parties.",
                    inline=False)
            
        ### !IDOLHELP TRADE ###
        elif arg in {"trade", "t", "!trade", "!t"}:
            card = discord.Embed(
            title="!trade command",
            description="Aliases: `!t`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="1. @User you want to trade with\n2. Idol ID from your party (can be found with `!profile` or `!idols`)\n3. Idol ID from User's party\nExample: `!trade @souldaida 0 14`",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Trade your idol with another player's idol.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* Both players must confirm the trade with their respective buttons.\n* Either player may cancel the trade.\n* Trade auto-times out after 60 seconds of inaction.",
                    inline=False)
            
        ### !IDOLHELP IDOLS ###
        elif arg in {"idols", "i", "party", "!idols", "!i", "!party"}:
            card = discord.Embed(
            title="!idols command",
            description="Aliases: `!i` `!party`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="None",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Display player's full party as a paginated list.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* Each page displays 10 idols.\n* Navigation buttons time out after 60 seconds of inaction.",
                    inline=False)
            
        ### !IDOLHELP MOVEIDOL ###
        elif arg in {"moveidol", "mi", "movei", "midol", "!moveidol", "!mi", "!movei", "!midol"}:
            card = discord.Embed(
            title="!moveidol command",
            description="Aliases: `!mi` `!movei` `!midol`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="1. Idol1 ID (can be found with `!profile` or `!idols`)\n2. Idol2 ID OR `up` OR `down`\n3. (optional) Number of positions to be moved up or down\nExample: `!moveidol 0 down 3` or `!moveidol 0 14`",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Adjusts Idol1's position in user's party list.",
                    inline=False)
            card.add_field(
                    name="Notes",
                    value="* Use `Idol2 ID` to switch the positions of Idol1 and Idol2.\n* Use `up` or `down` to move Idol1 up or down the party list once.\n* Use `up [number]` or `down [number]` to move Idol1 up or down that many times.",
                    inline=False)
            
        ### !IDOLHELP TUTORIAL ###
        elif arg in {"tutorial", "tut", "!tutorial", "!tut"}:
            card = discord.Embed(
            title="!tutorial command",
            description="Aliases: `!tut`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="None",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Exactly what you expect.",
                    inline=False)
        
        ### !IDOLHELP IDOLHELP ###
        elif arg in {"idolhelp", "h", "ih", "!idolhelp", "!h", "!ih"}:
            card = discord.Embed(
            title="!idolhelp command",
            description="Aliases: `!h` `!ih`",
            color=discord.Color.blue())
            card.add_field(
                    name="Parameters",
                    value="None",
                    inline=False)
            card.add_field(
                    name="Function",
                    value="Really?",
                    inline=False)

        ### DEFAULT !IDOLHELP ###
        else:
            card = discord.Embed(
                title="Idol Catcher Commands",
                description="Use `!idolhelp <command>` for more details about a command.",
                color=discord.Color.blue())
            card.add_field(
                    name="Key: !command <parameter> [optional parameter]",
                    value="",
                    inline=False)
            card.add_field(
                    name="!gacha",
                    value="Aliases: `!g`\nRoll a random idol.",
                    inline=False)
            card.add_field(
                    name="!release <Idol ID>",
                    value="Aliases: `!r`\nRelease the specified idol from your party.",
                    inline=False)
            card.add_field(
                    name="!profile [user]",
                    value="Aliases: `!pf`\nSee your profile or another user's profile.",
                    inline=False)
            card.add_field(
                    name="!view <Idol ID>",
                    value="Aliases: `!v`\nView an idol card if someone owns it.",
                    inline=False)
            card.add_field(
                    name="!trade <@User> <Your Idol ID> <User's Idol ID>",
                    value="Aliases: `!t`\nTrade your idol with another user's idol.",
                    inline=False)
            card.add_field(
                    name="!idols",
                    value="Aliases: `!i` `!party`\nSee your full list of idols.",
                    inline=False)
            card.add_field(
                    name="!moveidol <Idol1 ID> <Idol2 ID/up/down> [number]",
                    value="Aliases: `!mi` `!movei` `!midol`\nMove Idol1 around in your party list.",
                    inline=False)
            card.add_field(
                    name="!tutorial",
                    value="Aliases: `!tut`\nDisplays the tutorial for Idol Catcher.",
                    inline=False)
            card.add_field(
                    name="!idolhelp",
                    value="Aliases: `!h` `!ih`",
                    inline=False)
        
        await ctx.send(embed=card)

    ### !RESETGACHA ADMIN COMMAND: RESET GACHA GAME ###
    @commands.command(aliases=["rg"])
    async def resetgacha(self, ctx):

        ### CHECK IF USER IS ADMIN ###
        with open("./admin.txt") as file:
            adminid = int(file.read())

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
                await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!addtitle \"[Name of Title]\"`\nExample: `!addtitle \"Stay (Stray Kids Stan)\"`")
                return
            elif len(args) > 2:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addtitle \"[Name of Title]\"`\nExample: `!addtitle \"Stay (Stray Kids Stan)\"`")
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
                await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Title ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
                return
            elif len(args) > 4:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addgroup \"[Name of Group]\" [Group Logo Filename] [(optional)Title ID]`\nExample: `!addgroup \"Stray Kids\" skz_logo.jpg 1`")
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
                if new_group_title_id:
                    cursor.execute("""SELECT title_name FROM TitleList
                                    WHERE title_id = :new_group_title_id""",
                                    {'new_group_title_id': new_group_title_id})
                    new_group_title = cursor.fetchone()[0]
                else:
                    new_group_title = None

                ### BUILD NEW GROUP CONFIRMATION CARD ###
                if new_group_logo and not os.path.exists(f"./cogs/gacha_images/logos/{new_group_logo}"):
                    print(f"ERROR: Group logo file not found: ./cogs/gacha_images/logos/{new_group_logo}")
                    connection.close()
                    return
                uploaded_new_group_logo = discord.File(f"./cogs/gacha_images/logos/{new_group_logo}", filename=new_group_logo)
                
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
                await ctx.send("Insufficient parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
                return
            elif len(args) > 4:
                await ctx.send("Too many parameters.\nPlease use the following syntax:\n`!addidol \"[Name of Idol]\" [Idol Image Filename] [(leave blank for Soloists)Group ID]`\nExample: `!addidol \"Lee Know\" skzleeknow.jpg 1`")
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
                    if new_idol_group_logo:
                        await ctx.send(files=[uploaded_new_idol_image, uploaded_new_idol_group_logo], embed=card)
                    else:
                        await ctx.send(files=[uploaded_new_idol_image], embed=card)
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
    def createplayer(self, ctx, player_id, cursor):
        
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
        super().__init__(timeout=60)
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

        ### FETCH IDOL NAME AND CHECK IF CAUGHT ###
        cursor.execute("""SELECT idol_name FROM Idols
                          WHERE idol_id = :roll_number""",
                        {'roll_number': self.roll_number})
        roll_name = cursor.fetchone()[0]

        cursor.execute("""SELECT player_id FROM PartyPositions
                          WHERE idol_id = :roll_number""",
                        {'roll_number': self.roll_number})
        owner_id = cursor.fetchone()

        ### SUCCESSFULLY CATCH IDOL IF CORRECT PLAYER AND IDOL IS WILD, THEN DISABLE BUTTON ###
        if (userid == self.roller_id):
            if owner_id is None:
                ### GET PLAYER'S NEXT AVAILABLE POSITION ###
                cursor.execute("""SELECT party_position FROM PartyPositions
                                WHERE (player_id = :roller_id AND idol_id IS NULL)""",
                                {'roller_id': self.roller_id})
                party_position = cursor.fetchone()

                ### IF PARTY IS FULL, SEND ERROR ###
                if party_position is None:
                    content=f"{interaction.user.mention}, your party is full! Use `!release` to make space for {roll_name}."

                ### IF PARTY IS NOT FULL, ADD IDOL ID TO CORRECT PARTY POSITION ##
                else:
                    party_position = party_position[0]
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

            ### IF IDOL IS ALREADY CAUGHT, SEND ERROR AND DISABLE BUTTON ###
            else:
                owner_id = owner_id[0]
                content=f"Oops, {roll_name} has already been caught by <@{owner_id}>!"
                for button in self.children:
                    button.disabled = True
                    button.label = f"{roll_name} has been caught!"
                await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"Nice try {interaction.user.mention}, {roll_name} can only be caught by <@{self.roller_id}> this time!"
        
        connection.commit()
        connection.close()

        await interaction.response.send_message(content=content)


### BUTTON MENU FOR !RELEASE CONFIRMATION ###
class ReleaseButtonMenu(discord.ui.View):

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

            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = NULL
                            WHERE idol_id = :idol_id""",
                            {'idol_id': self.idol_id})
            content=f"{self.idol_name} has been released from <@{self.owner_id}>'s party."

            ### MOVE REMAINING IDOLS' PARTY POSITIONS UP BY 1 ###
            cursor.execute("""SELECT party_position, idol_id FROM PartyPositions
                            WHERE (player_id = :owner_id AND party_position > :empty_position)""",
                            {'owner_id': self.owner_id, 'empty_position': empty_position})
            idols_to_move = cursor.fetchall()

            for party_position, moving_idol_id in idols_to_move:
                new_position = party_position - 1
                cursor.execute("""UPDATE PartyPositions
                                SET idol_id = :moving_idol_id
                                WHERE (player_id = :owner_id AND party_position = :new_position)""",
                                {'moving_idol_id': moving_idol_id, 'owner_id': self.owner_id, 'new_position': new_position})
            
            ### FREE UP LAST PARTY POSITION ###
            final_position = idols_to_move[-1][0]
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = NULL
                            WHERE (player_id = :owner_id AND party_position = :final_position)""",
                            {'owner_id': self.owner_id, 'final_position': final_position})

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"{self.idol_name} was released"
            await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER (IDOL NOT YET RELEASED) ###
        else:
            content=f"Nice try, <@{user_id}>, only <@{self.owner_id}> has permission to use this menu!"

        connection.commit()
        connection.close()
        await interaction.response.send_message(content=content)

    ### CANCEL BUTTON: MENU IS DEACTIVATED ###
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def releasecancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()
        cursor.execute("""SELECT player_id
                        FROM PartyPositions
                        WHERE idol_id = :idol_id""",
                        {'idol_id': self.idol_id})
        owner = cursor.fetchone()
        connection.close()

        ### DISABLE MENU IF IDOL HAS ALREADY BEEN RELEASED ###
        if (owner is None or owner[0] != self.owner_id):
            content=f"ERROR: {self.idol_name} has already been released."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"{self.idol_name} was released"
            await self.message.edit(view=self)

        ### CANCEL COMMAND IF CORRECT USER, THEN DISABLE MENU ###
        elif (user_id == self.owner_id):
            content=f"<@{self.owner_id}> canceled the command."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
                if button.label == "Release":
                    button.label = f"Command was canceled"
            await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"ERROR: Only <@{self.owner_id}> has permission to use this menu!"

        await interaction.response.send_message(content=content)


### BUTTON MENU FOR !TRADE CONFIRMATION ###
class TradeButtonMenu(discord.ui.View):

    ### MENU TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, user_id1, user_name1, idol_id1, idol_name1, user_id2, user_name2, idol_id2, idol_name2):
        super().__init__(timeout=60)
        self.user_id1 = user_id1
        self.user_name1 = user_name1
        self.idol_id1 = idol_id1
        self.idol_name1 = idol_name1
        self.user_id2 = user_id2
        self.user_name2 = user_name2
        self.idol_id2 = idol_id2
        self.idol_name2 = idol_name2
        self.confirm1 = False
        self.confirm2 = False

        self.tradeconfirmation1.label = user_name1
        #self.tradeconfirmation1.label = "Test1"
        self.tradeconfirmation2.label = user_name2

    ### BUTTONS DISABLE UPON TIMEOUT ###
    async def on_timeout(self) -> None:
        for button in self.children:
            if not button.disabled:
                button.disabled = True
        await self.message.edit(view=self)
    
    ### CONFIRMATION BUTTON 1 ###
    @discord.ui.button(label="Loading", style=discord.ButtonStyle.blurple)
    async def tradeconfirmation1(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = interaction.user.id

        ### FAIL IF DIFFERENT PLAYER TRIES TO USE BUTTONS ###
        if (user_id != self.user_id1):
            await interaction.response.send_message(content=f"<@{user_id}>, only <@{self.user_id1}> can confirm with this button!")

        ### CHANGE & DISABLE BUTTON IF CORRECT USER ###
        else:
            ### CHANGE & DISABLE BUTTON ###
            for button in self.children:
                if button.label == f"{self.user_name1}":
                #if button.label == "Test1":
                    button.disabled = True
                    button.label = f"Accepted"
                    button.style = discord.ButtonStyle.green
            await self.message.edit(view=self)

            ### SEND CONFIRMATION MESSAGE
            self.confirm1 = True
            await interaction.response.send_message(content=f"<@{self.user_id1}> has accepted.")

            ### TRADE IF BOTH USERS HAVE CONFIRMED ###
            if self.confirm1 and self.confirm2:
                trade_confirmation = await self.trade()
                await interaction.followup.send(content=trade_confirmation)
    
    ### CONFIRMATION BUTTON 2 ###
    @discord.ui.button(label="Loading", style=discord.ButtonStyle.blurple)
    async def tradeconfirmation2(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = interaction.user.id

        ### FAIL IF DIFFERENT PLAYER TRIES TO USE BUTTONS ###
        if (user_id != self.user_id1):
            await interaction.response.send_message(content=f"<@{user_id}>, only <@{self.user_id2}> can confirm with this button!")

        ### CHANGE & DISABLE BUTTON IF CORRECT USER ###
        else:
            ### CHANGE & DISABLE BUTTON ###
            for button in self.children:
                if button.label == f"{self.user_name2}":
                    button.disabled = True
                    button.label = f"Accepted"
                    button.style = discord.ButtonStyle.green
            await self.message.edit(view=self)

            ### SEND CONFIRMATION MESSAGE
            self.confirm2 = True
            await interaction.response.send_message(content=f"<@{self.user_id2}> has accepted.")

            ### TRADE IF BOTH USERS HAVE CONFIRMED ###
            if self.confirm1 and self.confirm2:
                trade_confirmation = await self.trade()
                await interaction.followup.send(content=trade_confirmation)

    ### CANCEL BUTTON: MENU IS DEACTIVATED ###
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def releasecancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = interaction.user.id

        ### CANCEL COMMAND IF CORRECT USER, THEN DISABLE MENU ###
        if (user_id == self.user_id1 or user_id == self.user_id2):

            content=f"The trade has been canceled."

            ### DISABLE MENU ###
            for button in self.children:
                button.disabled = True
            await self.message.edit(view=self)

        ### FAIL IF DIFFERENT PLAYER ###
        else:
            content=f"<@{user_id}>, only <@{self.user_id1}> and <@{self.user_id2}> have permission to use this menu!"

        await interaction.response.send_message(content=content)
    
    ### TRADE FUNCTION ###
    async def trade(self):

        connection = sqlite3.connect("./cogs/idol_gacha.db")
        cursor = connection.cursor()

        ### GET IDOL1'S PARTY POSITION BEFORE TRADING ###
        cursor.execute("""SELECT party_position
                        FROM PartyPositions
                        WHERE idol_id = :idol_id1""",
                        {'idol_id1': self.idol_id1})
        empty_position = cursor.fetchone()[0]

        ### MOVE USER1'S REMAINING IDOLS' PARTY POSITIONS UP BY 1 ###
        cursor.execute("""SELECT party_position, idol_id FROM PartyPositions
                        WHERE (player_id = :user_id1 AND party_position > :empty_position)""",
                        {'user_id1': self.user_id1, 'empty_position': empty_position})
        idols_to_move = cursor.fetchall()

        for party_position, moving_idol_id in idols_to_move:
            new_position = party_position - 1
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :moving_idol_id
                            WHERE (player_id = :user_id1 AND party_position = :new_position)""",
                            {'moving_idol_id': moving_idol_id, 'user_id1': self.user_id1, 'new_position': new_position})
        
        ### PUT IDOL2 IN USER1'S FINAL PARTY POSITION ###
        final_position = idols_to_move[-1][0]
        cursor.execute("""UPDATE PartyPositions
                        SET idol_id = :idol_id2
                        WHERE (player_id = :user_id1 AND party_position = :final_position)""",
                        {'idol_id2': self.idol_id2, 'user_id1': self.user_id1, 'final_position': final_position})
        
        ### GET IDOL2'S PARTY POSITION BEFORE TRADING ###
        cursor.execute("""SELECT party_position
                        FROM PartyPositions
                        WHERE idol_id = :idol_id2""",
                        {'idol_id2': self.idol_id2})
        empty_position = cursor.fetchone()[0]

        ### MOVE USER2'S REMAINING IDOLS' PARTY POSITIONS UP BY 1 ###
        cursor.execute("""SELECT party_position, idol_id FROM PartyPositions
                        WHERE (player_id = :user_id2 AND party_position > :empty_position)""",
                        {'user_id2': self.user_id2, 'empty_position': empty_position})
        idols_to_move = cursor.fetchall()

        for party_position, moving_idol_id in idols_to_move:
            new_position = party_position - 1
            cursor.execute("""UPDATE PartyPositions
                            SET idol_id = :moving_idol_id
                            WHERE (player_id = :user_id2 AND party_position = :new_position)""",
                            {'moving_idol_id': moving_idol_id, 'user_id2': self.user_id2, 'new_position': new_position})
        
        ### PUT IDOL1 IN USER2'S FINAL PARTY POSITION ###
        final_position = idols_to_move[-1][0]
        cursor.execute("""UPDATE PartyPositions
                        SET idol_id = :idol_id1
                        WHERE (player_id = :user_id2 AND party_position = :final_position)""",
                        {'idol_id1': self.idol_id1, 'user_id2': self.user_id2, 'final_position': final_position})
        
        connection.commit()
        connection.close()

        ### DISABLE REMAINING BUTTON ###
        for button in self.children:
            button.disabled = True
        await self.message.edit(view=self)

        ### RETURN CONFIRMATION ###
        confirmation = f"{self.idol_name1} and {self.idol_name2} have successfully been traded!"
        return confirmation
        

### SELECT MENU FOR ACTIVE TITLE ###
class ActiveTitleSelectMenu(discord.ui.View):
    caller_id = None
    active_title_id = None
    active_title = None
    active_title_position = 1

    ### MENU TIMES OUT AFTER 60 SECONDS ###
    def __init__(self, caller_id, titles):
        super().__init__(timeout=60)
        self.caller_id = caller_id

        options = []
        for title in titles:
            option = discord.SelectOption(label=title[1], value=title[0])
            if title[2] == 1:
                option.label += " <ACTIVE>"
                self.active_title_id = int(title[0])
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

        if (user_id == self.caller_id):

            ### CHANGE ACTIVE TITLE IF NEW TITLE IS SELECTED, THEN DISABLE MENU ###
            if (new_active_title_id != self.active_title_id):
                
                connection = sqlite3.connect("./cogs/idol_gacha.db")
                cursor = connection.cursor()

                ### GET NEW ACTIVE TITLE POSITION ###
                cursor.execute("""SELECT position
                                FROM CompletedTitles
                                WHERE (player_id = :caller_id AND title_id = :new_active_title_id)
                                ORDER BY position DESC""",
                                {'caller_id': self.caller_id, 'new_active_title_id': new_active_title_id})
                new_active_title_position = cursor.fetchone()[0]

                ### SHIFT DOWN TITLES BETWEEN NEW & OLD ACTIVE TITLES ###
                cursor.execute("""SELECT position, title_id
                                FROM CompletedTitles
                                WHERE (player_id = :caller_id AND position < :new_active_title_position AND position >= 1)
                                ORDER BY position DESC""",
                                {'caller_id': self.caller_id, 'new_active_title_position': new_active_title_position})
                titles_to_move = cursor.fetchall()

                for position, moving_title_id in titles_to_move:
                    new_position = position + 1
                    cursor.execute("""UPDATE CompletedTitles
                                    SET title_id = :moving_title_id
                                    WHERE (player_id = :caller_id AND position = :new_position)""",
                                    {'caller_id': self.caller_id, 'moving_title_id': moving_title_id, 'new_position': new_position})

                ### PLACE NEW ACTIVE TITLE IN POSITION 1 ###
                cursor.execute("""UPDATE CompletedTitles
                                SET title_id = :new_active_title_id
                                WHERE (player_id = :caller_id AND position = 1)""",
                                {'caller_id': self.caller_id, 'new_active_title_id': new_active_title_id})
                
                ### GET NEW ACTIVE TITLE NAME ###
                cursor.execute("""SELECT title_name
                                FROM TitleList
                                WHERE title_id == :new_active_title_id""",
                                {'new_active_title_id': new_active_title_id})
                new_active_title = cursor.fetchone()[0]

                connection.commit()
                connection.close()

                ### CONFIRMATION MESSAGE ###
                content=f"<@{self.caller_id}>'s active title has been updated to {new_active_title}."

                ### DISABLE MENU ###
                for child in self.children:
                    child.disabled = True
                    child.placeholder = new_active_title
                await interaction.response.edit_message(view=self)
            
            ### DO NOTHING IF ACTIVE TITLE IS SELECTED ###
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
        if (await self.interaction_check(interaction)):
            await self.show_page(0)
            await interaction.response.defer()
        else:
            await interaction.response.send_message(content=f"This interaction can only be used by {self.ctx.author}")

    @discord.ui.button(emoji='◀️', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction, button):
        if (await self.interaction_check(interaction)):
            await self.show_checked_page(self.current_page - 1)
            await interaction.response.defer()
        else:
            await interaction.response.send_message(content=f"This interaction can only be used by {self.ctx.author}")

    @discord.ui.button(emoji='▶️', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, button):
        if (await self.interaction_check(interaction)):
            await self.show_checked_page(self.current_page + 1)
            await interaction.response.defer()
        else:
            await interaction.response.send_message(content=f"This interaction can only be used by {self.ctx.author}")

    @discord.ui.button(emoji='⏭️', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction, button):
        if (await self.interaction_check(interaction)):
            await self.show_page(self._source.get_max_pages() - 1)
            await interaction.response.defer()
        else:
            await interaction.response.send_message(content=f"This interaction can only be used by {self.ctx.author}")
    
    @discord.ui.button(emoji='⏹️', style=discord.ButtonStyle.gray)
    async def stop_page(self, interaction, button):
        if (await self.interaction_check(interaction)):
            self.stop()
            for child in self.children:
                if not child.disabled:
                    child.disabled = True
            await self.message.edit(view=self)
            #await self.message.edit(view=None)
            await interaction.response.defer()
        else:
            await interaction.response.send_message(content=f"This interaction can only be used by {self.ctx.author}")


### FORMATS PAGES FOR !IDOLS ###
class IdolsListPagesFormatter(menus.ListPageSource):
    async def format_page(self, menu, entries):
        embed = discord.Embed(
            title=f"{menu.ctx.author}'s Party",
            color=discord.Color.teal()
        )

        party_list = ""
        max_digits = len(str(max(entries)[0]))
        for idol in entries:
            spaces = ""
            num_digits = len(str(idol[0]))
            for i in range(max_digits - num_digits):
                spaces += " " #figure space (numerical digits) U+2007
            party_list += "`" + spaces + f"{idol[0]}` `{idol[2]}` {idol[1]}\n"
        embed.add_field(
            name="",
            value=party_list,
            inline=False
        )

        #embed.set_footer(text=f"{self.get_page}")
        return embed
    

async def setup(bot):
    await bot.add_cog(Gacha(bot))