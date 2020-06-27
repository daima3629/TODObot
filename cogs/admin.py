import discord
from discord.ext import commands
import io
import aiofiles
import textwrap
import traceback
from contextlib import redirect_stdout
from cogs.utils.argparser import ArgParser


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, err):
        if isinstance(err, commands.errors.NotOwner):
            embed = discord.Embed(
                title="403 Forbidden",
                description="あなたにはこのコマンドを実行する権限がありません。"
            )
            return await ctx.send(embed=embed)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        
        # remove `foo`
        return content.strip('` \n')

    async def do_eval(self, ctx, body):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message
        }
        env.update(globals())
        body = self.cleanup_code(body)
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.is_owner()
    @commands.command(name="eval")
    async def _eval(self, ctx, *args):
        parsed = ArgParser(args)
        if parsed.options.get("file") == "true":
            embed = discord.Embed(
                title="eval-from-file",
                description="evalがfileモードで実行されました。\n実行したいコードを.pyファイルで投稿してください。"
            )
            await ctx.send(embed=embed)
            msg = await self.bot.wait_for("message", check=lambda m: m.author==ctx.author and m.channel==ctx.channel)
            if not msg.attachments:
                return await ctx.send("Error: ファイルが指定されませんでした。")
            file = msg.attachments[0]
            if not file.filename.endswith(".py"):
                return await ctx.send("Error: pyファイル以外のファイルが投稿されました。")
            byte = await file.read()
            body = byte.decode()
            await self.do_eval(ctx, body)
            return
        embed = discord.Embed(
            title="eval",
            description="実行したいコードを発言してください。"
        )
        await ctx.send(embed=embed)
        msg = await self.bot.wait_for("message", check=lambda m: m.author==ctx.author and m.channel==ctx.channel)
        return await self.do_eval(ctx, msg.content)




def setup(bot):
    bot.add_cog(AdminCog(bot))