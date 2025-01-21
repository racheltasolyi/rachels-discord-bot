import discord
from discord import app_commands
from discord.ext import commands

class ButtonMenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{__name__} is online!")

    @app_commands.command(name="uselessbuttonmenu", description="Displays a useless button menu.")
    async def buttonmenu(self, interaction: discord.Interaction):
        await interaction.response.send_message(content="Here's my button menu!", view=TestMenuButton())

class TestMenuButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Test", style=discord.ButtonStyle.blurple)
    async def test(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="Test successful!")
    @discord.ui.button(label="Click Me...", style=discord.ButtonStyle.green)
    async def test2(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="I've been clicked!")
    @discord.ui.button(label="Exit", style=discord.ButtonStyle.red)
    async def test3(self, interaction: discord.Interaction, Button: discord.ui.Button):
        await interaction.response.send_message(content="Exiting Menu...")
    
async def setup(bot):
    await bot.add_cog(ButtonMenuCog(bot))