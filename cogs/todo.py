import discord
from discord.ext import commands
import json
import hashlib


class TODOCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def make_request(self, ctx, to_user, todo):
        text = f"{ctx.message.id} - {ctx.author.id} -> {to_user.id}"
        hashed = hashlib.sha256(text.encode()).hexdigest()
        data = {
            "author": ctx.author.id,
            "to": to_user.id,
            "content": todo
        }
        self.bot.data["request"][hashed[:10]] = data
        self.bot.save_data()
        return hashed[:10]

    @commands.command(name="help")
    async def _help(self, ctx):
        msg = """
>>> TODO:
- やること

 のようなフォーマットのメッセージを書くと認識して記憶してくれる、ただそれだけのボットです。
 ハイフンの前のスペースが何個でも認識してくれるようになりました。

 `todo!list` でTODOのリストが見れます。(alias: `todo!l`)
 `todo!delete TODO番号` でTODOを削除できます。(alias: `todo!d`)

 **招待リンク**
 https://discord.com/api/oauth2/authorize?client_id=716294656987758702&permissions=67648&scope=bot
 (GitHubにあげるのめんどいのでソースコードは)ないです。"""
        return await ctx.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.content.startswith("TODO:"):
            return

        s = message.content.split("\n")
        if len(s) < 2:
            return
        todos = s[1:]
        for i, todo in enumerate(todos):
            todos[i] = todo.strip()
            if not todos[i].startswith("- "):
                return

        for i, todo in enumerate(todos):
            todos[i] = todo[2:]
        msg = f"{message.author.mention}TODOが検出されました。\n\n>>> "
        for todo in todos:
            msg += f"{todo}\n"
        msg += "\nTODOに追加しますか？"
        msg = await message.channel.send(msg)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

        def check(reac, user):
            if not user == message.author:
                return False
            if not str(reac.emoji) in ["👍", "👎"]:
                return False
            return True

        reac, _ = await self.bot.wait_for("reaction_add", check=check)
        if str(reac.emoji) == "👍":
            if not self.bot.data.get(str(message.author.id)):
                self.bot.data[str(message.author.id)] = []

            for todo in todos:
                self.bot.data[str(message.author.id)].append(todo)
                self.bot.save_data()
            await message.channel.send(">>> 正常にTODOに追加されました。\n一覧を見るには`todo!list`")
            await msg.delete()
        else:
            return await msg.delete()

    @commands.command(name="list", aliases=["l"])
    async def _list(self, ctx):
        l = self.bot.data.get(str(ctx.author.id))
        todos = ""
        if not l:
            return await ctx.send(f">>> {ctx.author.mention}のTODOリスト\n\nNone")

        for i, todo in enumerate(l):
            todos += f"{i}: {todo}" + "\n"
        todos = todos.rstrip("\n")
        msg = f">>> {ctx.author.mention}のTODOリスト\n\n" + todos
        return await ctx.send(msg)

    @commands.command(aliases=["d"])
    async def delete(self, ctx, num: int):
        l = self.bot.data.get(str(ctx.author.id))
        if not l:
            return await ctx.send("> そのTODOはありません。`todo!list`で確認してください。")
        try:
            deleted_todo = self.bot.data[str(ctx.author.id)][num]
            del self.bot.data[str(ctx.author.id)][num]
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

    @commands.command()
    async def request(self, ctx, member: discord.Member, *, todo):
        text = f"""
>>> `{str(member)}`さんにtodoリクエストを送ります。
内容:
・{todo}

よろしいですか？"""
        msg = await ctx.send(text)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

        def check(reac, user):
            if not user == ctx.author: return
            if not reac.message == msg: return
            if not str(reac.emoji) in ["👍", "👎"]: return
            return True

        reac, _ = await self.bot.wait_for("reaction_add", check=check)
        if str(reac.emoji) == "👎":
            await msg.delete()
            return await ctx.send("> todoリクエストをキャンセルしました。", delete_after=5)

        req_id = self.make_request(ctx, member, todo)
        dm_msg = f"""
>>> {ctx.author.mention}さんからTODOリクエストが届きました。

内容:
・{todo}

リクエストID: `{req_id}`

このリクエストを承認する場合は`todo!request_approve {req_id}`
拒否する場合は`todo!request_deny {req_id}`
とコマンドを実行してください。"""
        try:
            await member.send(dm_msg)
        except:
            await ctx.send(f"{member.mention}\n" + dm_msg)

        result = f"""
>>> リクエストの送信に成功しました。

リクエストID: `{req_id}`"""
        return await ctx.send(result)

    @commands.command()
    async def request_approve(self, ctx, req_id: str):
        req_todo = self.bot.data["request"].get(req_id)
        if not req_id:
            return await ctx.send("> そのIDのリクエストは存在しません。もう一度確認してください。")

        self.bot.data["todo"][str(ctx.author.id)].append(req_todo.content)
        del self.bot.data["request"][req_id]
        self.bot.save_data()
        return await ctx.send(f"> リクエストを承認しました。\n\n追加されたTODO:\n・{req_todo.content}")

    @commands.command()
    async def request_deny(self, ctx, req_id: str):
        req_todo = self.bot.data["request"].get(req_id)
        if not req_id:
            return await ctx.send("> そのIDのリクエストは存在しません。もう一度確認してください。")

        del self.bot.data["request"][req_id]
        self.bot.save_data()
        return await ctx.send(f"> リクエストを拒否しました。")


def setup(bot):
    bot.add_cog(TODOCog(bot))
    print("todocog loaded")
