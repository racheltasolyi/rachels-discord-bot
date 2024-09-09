import discord
from discord.ext import commands

class ButtonMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @commands.command(aliases=["buttons", "button", "menu"])
    async def buttonmenu(self, interaction: discord.Interaction):
        await interaction.response.send_message(content="Here's my button menu!", view=TestMenuButton())

class TestMenuButton(discord.ui.View):
    def __init__(self, timeout=10):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Test", style=discord.ButtonStyle.blurple)
    async def test(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="Test successful!")
        #self.stop()
    @discord.ui.button(label="Click Me...", style=discord.ButtonStyle.green)
    async def test2(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="I've been clicked!")
        #self.stop()
    @discord.ui.button(label="Exit", style=discord.ButtonStyle.red)
    async def test3(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="Exiting Menu...")
        #self.stop()
    
async def setup(bot):
    await bot.add_cog(ButtonMenu(bot))