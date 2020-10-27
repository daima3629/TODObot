import discord
from discord.ext import commands
import json
import traceback

initial_extensions = [
    "cogs.todo",
    "cogs.admin",
    "jishaku"
]
with open("config.json", "r") as f:
    config = json.load(f)

class TODObot(commands.Bot):
    def __init__(self, command_prefix, **kwargs):
        super().__init__(command_prefix, **kwargs)
        for cog in initial_extensions:
            try:
                self.load_extension(cog)
            except:
                traceback.print_exc()
        with open("data.json", "r") as f:
            self.data = json.load(f)

    async def on_ready(self):
        await self.change_presence(activity=discord.Game("type todo!help"))
        print("-------------------")
        print(f"TODObot Online => {self.user.id}")

    def save_data(self):
        with open("data.json", "w") as f:
            json.dump(self.data, f, indent=4)

    async def reload(self, ctx):
        with open("data.json", "r") as f:
            self.data = json.load(f)
        for cog in initial_extensions:
            try:
                self.reload_extension(cog)
            except Exception as err:
                err_str = ''.join(traceback.TracebackException.from_exception(err).format())
                await ctx.send(f"```py\n{err_str}\n```")

if __name__ == "__main__":
    intents = discord.Intents.all()
    intents.typing = False
    bot = TODObot(command_prefix="todo!", help_command=None, intents=intents)
    bot.run(config["TOKEN"])
