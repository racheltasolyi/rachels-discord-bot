import discord
from discord.ext import commands
import random
import json

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @commands.command(aliases=["g"])
    async def gacha(self, ctx):
        #images = [image for image in os.listdir("./cogs/welcome_images")]
        #randomized_image = random.choice(images)

        roll_number = random.randrange(3)
        cards = await self.get_card_data()
        roll_name = cards[str(roll_number)]["name"]
        roll_group = cards[str(roll_number)]["group"]
        roll_image = cards[str(roll_number)]["image"]
        roll_logo = cards[str(roll_number)]["logo"]
        roll_claimed = cards[str(roll_number)]["claimed"]
        #print(roll_name)

        uploaded_roll_image = discord.File(f"./cogs/gacha_images/{roll_image}", filename=roll_image)
        uploaded_roll_logo = discord.File(f"./cogs/gacha_images/{roll_logo}", filename=roll_logo)

        card = discord.Embed(title=roll_name, description=roll_group, color=discord.Color.green())
        card.set_thumbnail(url=f"attachment://{roll_logo}")
        card.set_image(url=f"attachment://{roll_image}")
        card.set_footer(text=f"Rolled by {ctx.author.name}", icon_url=ctx.author.avatar)

        if roll_claimed:
            roll_owner_id = cards[str(roll_number)]["owner"]
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
                value="Throw a Pokeball to catch!",
                inline=False
            )
            await ctx.send(files=[uploaded_roll_image, uploaded_roll_logo], embed=card, view=GachaButtonMenu(roll_number))
            
    '''
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        channel = reaction.message.channel
        await client.send_message(channel, "{} has added {} to the message: {}")
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
        super().__init__(timeout=None)
        self.roll_number = roll_number
    
    @discord.ui.button(label="Throw Pokeball", style=discord.ButtonStyle.blurple)
    async def test(self, interaction: discord.Interaction, Button: discord.ui.Button):
        userid = interaction.user.id
        #print(userid)
        cards = await Gacha.get_card_data(self)
        #print(cards)
        #print(self.roll_number)
        #print(f"before: {cards[str(self.roll_number)]['claimed']}")
        cards[str(self.roll_number)]["claimed"] = True
        cards[str(self.roll_number)]["owner"] = userid
        #print(f"after: {cards[str(self.roll_number)]['claimed']}")
        #print(cards[str(self.roll_number)]["owner"])
        await Gacha.update_card_data(self, cards)
        await interaction.response.send_message(content=f"{cards[str(self.roll_number)]['name']} was caught by {interaction.user.name}!")

async def setup(bot):
    await bot.add_cog(Gacha(bot))