import discord
from discord.ext import commands
import numpy
import textwrap

REACTIONS = ["👍", "👎"]
REACTION_YES = "👍"
REACTION_NO = "👎"


class TODOCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _make_request(self, ctx, user_send_to, todo):
        req_id = numpy.base_repr(ctx.message.id, 36)
        data = {
            "author": ctx.author.id,
            "to": user_send_to.id,
            "content": todo
        }
        self.bot.data["request"][req_id] = data
        self.bot.save_data()
        return req_id

    @commands.command(name="help")
    async def _help(self, ctx):
        msg = """\
        >>> TODO:
        - やること

        のようなフォーマットのメッセージを書くと認識して記憶してくれる、ただそれだけのボットです。
        ハイフンの前のスペースが何個でも認識してくれるようになりました。

        `todo!list` でTODOのリストが見れます。(alias: `todo!l`)
        `todo!delete TODO番号` でTODOを削除できます。(alias: `todo!d`)

        **招待リンク**
        https://discord.com/api/oauth2/authorize?client_id=716294656987758702&permissions=67648&scope=bot
        **ソースコード**
        https://github.com/daima3629/TODObot
        """
        return await ctx.send(textwrap.dedent(msg))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.content.startswith("TODO:"):
            return

        s = message.content.splitlines()
        if len(s) < 2:
            return
        todos = s[1:]
        for i, todo in enumerate(todos):
            todos[i] = todo.strip()
            if not todos[i].startswith("- "):
                return

        for i, todo in enumerate(todos):
            todos[i] = todo[2:]
        confirm_msg_text = f"{message.author.mention}TODOが検出されました。\n\n>>> "
        for todo in todos:
            confirm_msg_text += f"{todo}\n"
        confirm_msg_text += "\nTODOに追加しますか？"
        confirm_msg = await message.channel.send(confirm_msg_text)
        for reaction in REACTIONS:
            await confirm_msg.add_reaction(reaction)

        def check(reaction, user):
            if not user == message.author:
                return False
            if not str(reaction.emoji) in REACTIONS:
                return False
            return True

        reaction, _ = await self.bot.wait_for("reaction_add", check=check)
        if str(reaction.emoji) == REACTION_YES:
            if not self.bot.data["todo"].get(str(message.author.id)):
                self.bot.data["todo"][str(message.author.id)] = []

            for todo in todos:
                self.bot.data["todo"][str(message.author.id)].append(todo)
                self.bot.save_data()
            await message.channel.send(">>> 正常にTODOに追加されました。\n一覧を見るには`todo!list`")
            await msg.delete()
        else:
            return await msg.delete()

    @commands.command(name="list", aliases=["l"])
    async def _list(self, ctx):
        todo_list = self.bot.data["todo"].get(str(ctx.author.id))
        todos = ""
        if not todo_list:
            return await ctx.send(f">>> {ctx.author.mention}のTODOリスト\n\nNone")

        for i, todo in enumerate(todo_list):
            todos += f"{i}: {todo}" + "\n"
        todos = todos.rstrip("\n")
        msg = f">>> {ctx.author.mention}のTODOリスト\n\n" + todos
        return await ctx.send(msg)

    @commands.command(aliases=["d"])
    async def delete(self, ctx, num: int):
        todo_list = self.bot.data["todo"].get(str(ctx.author.id))
        if not todo_list:
            return await ctx.send("> そのTODOはありません。`todo!list`で確認してください。")
        try:
            deleted_todo = self.bot.data["todo"][str(ctx.author.id)][num]
            del self.bot.data["todo"][str(ctx.author.id)][num]
        except IndexError:
            return await ctx.send("> そのTODOはありません。`todo!list`で確認してください。")
        self.bot.save_data()
        return await ctx.send(f"> TODO`{deleted_todo}`の削除に成功しました。")

    @delete.error
    async def error_delete(self, ctx, err):
        if isinstance(err, commands.errors.BadArgument):
            return await ctx.send("> 引数は整数で指定してください。")
        if isinstance(err, commands.errors.MissingRequiredArgument):
            return await ctx.send(">>> TODOの番号を引数で指定してください。\n番号は`todo!list`で確認できます。")

    @commands.group(aliases=["req"])
    async def request(self, ctx):
        if not ctx.invoked_subcommand:
            return await ctx.send("> サブコマンドを指定してください。")

    @request.command(aliases=["c"])
    async def create(self, ctx, member: discord.Member, *, todo):
        if not todo:
            return await ctx.send("> 引数に送りたいTODOを指定してください。")
        text = f"""\
        >>> `{member}`さんにtodoリクエストを送ります。
        内容:
        ・{todo}

        よろしいですか？
        """
        msg = await ctx.send(textwrap.dedent(text))
        for reaction in REACTIONS:
            await msg.add_reaction(reaction)

        def check(reaction, user):
            if not user == ctx.author: return
            if not reaction.message == msg: return
            if not str(reaction.emoji) in REACTIONS: return
            return True

        reaction, _ = await self.bot.wait_for("reaction_add", check=check)
        if str(reaction.emoji) == REACTION_NO:
            await msg.delete()
            return await ctx.send("> todoリクエストをキャンセルしました。", delete_after=5)

        req_id = self._make_request(ctx, member, todo)
        dm_msg = f"""\
        >>> {ctx.author.mention}さんからTODOリクエストが届きました。

        内容:
        ・{todo}

        リクエストID: `{req_id}`

        このリクエストを承認する場合は`todo!request approve {req_id}`
        拒否する場合は`todo!request deny {req_id}`
        とコマンドを実行してください。
        """
        try:
            await member.send(textwrap.dedent(dm_msg))
        except discord.Forbidden:
            await ctx.send(f"{member.mention}\n" + textwrap.dedent(dm_msg))

        result = f"""
        >>> リクエストの送信に成功しました。

        リクエストID: `{req_id}`
        """
        return await ctx.send(textwrap.dedent(result))

    @request.command(aliases=["a"])
    async def approve(self, ctx, req_id: str):
        req_todo = self.bot.data["request"].get(req_id)
        if not req_todo:
            return await ctx.send("> そのIDのリクエストは存在しません。もう一度確認してください。")

        self.bot.data["todo"][str(ctx.author.id)].append(req_todo.content)
        del self.bot.data["request"][req_id]
        self.bot.save_data()
        return await ctx.send(f"> リクエストを承認しました。\n\n追加されたTODO:\n・{req_todo.content}")

    @request.command(aliases=["d"])
    async def deny(self, ctx, req_id: str):
        if not req_id:
            return await ctx.send("> そのIDのリクエストは存在しません。もう一度確認してください。")

        del self.bot.data["request"][req_id]
        self.bot.save_data()
        return await ctx.send("> リクエストを拒否しました。")


def setup(bot):
    bot.add_cog(TODOCog(bot))
    print("TODOCog loaded")
