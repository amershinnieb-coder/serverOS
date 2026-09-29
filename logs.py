import datetime
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

# نظام كاش بسيط لحفظ محتوى الرسائل والمرفقات (الصور) لمدة مؤقتة قبل حذفها
MESSAGE_CACHE = {}


def get_log_channel(guild_id: int):
    conn = sqlite3.connect("serveros.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS log_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER)"
    )
    cursor.execute(
        "SELECT channel_id FROM log_settings WHERE guild_id = ?", (guild_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


class Logs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="إعداد_اللوق",
        description="تحديد الروم الخاصة بسجل الأحداث والنشاطات في السيرفر",
    )
    @app_commands.describe(channel="اختر روم السجلات")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_setup(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        conn = sqlite3.connect("serveros.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS log_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER)"
        )
        cursor.execute(
            "REPLACE INTO log_settings (guild_id, channel_id) VALUES (?, ?)",
            (interaction.guild.id, channel.id),
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="📋 إعداد سجل الأحداث الشامل",
            description=f"✅ تم ربط روم السجلات بـ: {channel.mention}\nسيتم رصد كافة العمليات بدقة متناهية.",
            color=discord.Color.from_rgb(46, 204, 113),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="تعطيل_اللوق", description="إيقاف وتعطيل نظام سجل الأحداث"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_disable(self, interaction: discord.Interaction):
        conn = sqlite3.connect("serveros.db")
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM log_settings WHERE guild_id = ?",
            (interaction.guild.id,),
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            "🛑 تم تعطيل نظام سجل الأحداث بنجاح.", ephemeral=True
        )

    # --- تخزين الرسائل في الكاش لرصد محتواها وصورها عند الحذف ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        attachments = [att.url for att in message.attachments]
        MESSAGE_CACHE[message.id] = {
            "content": message.content,
            "attachments": attachments,
            "author": message.author,
        }
        # تنظيف الكاش القديم إذا تجاوز 1000 رسالة لحماية الذاكرة
        if len(MESSAGE_CACHE) > 1000:
            # إزالة أقدم العناصر
            for key in list(MESSAGE_CACHE.keys()[:200]):
                del MESSAGE_CACHE[key]

    # 1. رصد حذف الرسائل (مع دعم الصور والمرفقات وهوية الحاذف)
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        channel_id = get_log_channel(message.guild.id)
        if not channel_id:
            return
        channel = message.guild.get_channel(channel_id)
        if not channel:
            return

        # جلب البيانات من الكاش أو الرسالة مباشرة
        cached = MESSAGE_CACHE.get(message.id, {})
        content = cached.get("content") or message.content or "*[لا يوجد نص]*"
        attachments = cached.get("attachments", []) or [
            att.url for att in message.attachments
        ]
        author = cached.get("author") or message.author

        # محاولة معرفة من قام بالحذف بدقة من سجل التدقيق
        deleter = "غير معروف (ربما حذفت من قبل صاحبها)"
        try:
            async for entry in message.guild.audit_logs(
                limit=10, action=discord.AuditLogAction.message_delete
            ):
                if (
                    entry.target.id == author.id
                    and (datetime.datetime.utcnow() - entry.created_at).total_seconds()
                    < 15
                ):
                    deleter = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except Exception:
            pass

        if len(content) > 1000:
            content = content[:997] + "..."

        embed = discord.Embed(
            title="🗑️ رصد حذف رسالة",
            color=discord.Color.from_rgb(231, 76, 60),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="👤 صاحب الرسالة",
            value=f"{author.mention} (`{author}`)",
            inline=False,
        )
        embed.add_field(name="🛠️ من قام بالحذف", value=deleter, inline=False)
        embed.add_field(
            name="📍 القناة", value=message.channel.mention, inline=False
        )
        embed.add_field(
            name="📝 المحتوى",
            value=f"```ansi\n\u001b[31m{content}\u001b[0m\n```",
            inline=False,
        )

        if attachments:
            embed.add_field(
                name="🖼️ المرفقات / الصور المحذوفة",
                value="\n".join(
                    [f"[صورة / ملف مرفق]({url})" for url in attachments]
                ),
                inline=False,
            )
            # إذا كانت الصورة الأولى، نعرضها كصورة بارزة في الإيمبد
            embed.set_image(url=attachments[0])

        embed.set_footer(text=f"User ID: {author.id}")
        await channel.send(embed=embed)

    # 2. تعديل الرسائل
    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ):
        if (
            before.author.bot
            or not before.guild
            or before.content == after.content
        ):
            return
        channel_id = get_log_channel(before.guild.id)
        if not channel_id:
            return
        channel = before.guild.get_channel(channel_id)
        if not channel:
            return

        old_c = before.content or "*[فارغ]*"
        new_c = after.content or "*[فارغ]*"
        if len(old_c) > 900:
            old_c = old_c[:897] + "..."
        if len(new_c) > 900:
            new_c = new_c[:897] + "..."

        embed = discord.Embed(
            title="✏️ تعديل رسالة",
            color=discord.Color.from_rgb(241, 196, 15),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="👤 صاحب الرسالة",
            value=f"{before.author.mention} (`{before.author}`)",
            inline=False,
        )
        embed.add_field(
            name="📍 القناة", value=before.channel.mention, inline=False
        )
        embed.add_field(
            name="📜 قبل التعديل",
            value=f"```ansi\n\u001b[33m{old_c}\u001b[0m\n```",
            inline=False,
        )
        embed.add_field(
            name="✨ بعد التعديل",
            value=f"```ansi\n\u001b[32m{new_c}\u001b[0m\n```",
            inline=False,
        )
        embed.set_footer(text=f"User ID: {before.author.id}")
        await channel.send(embed=embed)

    # 3. دخول ومغادرة الأعضاء
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel_id = get_log_channel(member.guild.id)
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        created_ts = int(member.created_at.timestamp())
        embed = discord.Embed(
            title="📥 انضمام عضو جديد",
            color=discord.Color.from_rgb(46, 204, 113),
            timestamp=datetime.datetime.utcnow(),
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(
            name="👤 العضو",
            value=f"{member.mention} (`{member}`)",
            inline=False,
        )
        embed.add_field(
            name="📅 إنشاء الحساب",
            value=f"<t:{created_ts}:F> (<t:{created_ts}:R>)",
            inline=False,
        )
        embed.set_footer(text=f"إجمالي الأعضاء: {member.guild.member_count}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel_id = get_log_channel(member.guild.id)
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title="📤 مغادرة عضو",
            color=discord.Color.from_rgb(231, 76, 60),
            timestamp=datetime.datetime.utcnow(),
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(
            name="👤 العضو",
            value=f"{member.mention} (`{member}`)",
            inline=False,
        )
        embed.set_footer(text=f"إجمالي الأعضاء: {member.guild.member_count}")
        await channel.send(embed=embed)

    # 4. رصد التايم أوت (الإسكات) مع اسم المشرف والسبب بدقة
    @commands.Cog.listener()
    async def on_member_update(
        self, before: discord.Member, after: discord.Member
    ):
        channel_id = get_log_channel(after.guild.id)
        if not channel_id:
            return
        channel = after.guild.get_channel(channel_id)
        if not channel:
            return

        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until:
                moderator = "مشرف غير معروف"
                reason = "لا يوجد سبب مدون"
                try:
                    async for entry in after.guild.audit_logs(
                        limit=5, action=discord.AuditLogAction.member_update
                    ):
                        if (
                            entry.target.id == after.id
                            and entry.changes.before.timed_out_until
                            != entry.changes.after.timed_out_until
                        ):
                            moderator = f"{entry.user.mention} (`{entry.user}`)"
                            reason = entry.reason or "لا يوجد سبب"
                            break
                except Exception:
                    pass

                timeout_ts = int(after.timed_out_until.timestamp())
                embed = discord.Embed(
                    title="⏳ تطبيق عقوبة إسكات (Timeout)",
                    color=discord.Color.from_rgb(230, 126, 34),
                    timestamp=datetime.datetime.utcnow(),
                )
                embed.add_field(
                    name="👤 العضو المعاقب",
                    value=f"{after.mention} (`{after}`)",
                    inline=False,
                )
                embed.add_field(
                    name="🛠️ بواسطة المشرف", value=moderator, inline=False
                )
                embed.add_field(name="📌 السبب", value=reason, inline=False)
                embed.add_field(
                    name="⏰ ينتهي في",
                    value=f"<t:{timeout_ts}:F> (<t:{timeout_ts}:R>)",
                    inline=False,
                )
                await channel.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🔊 رفع عقوبة الإسكات",
                    color=discord.Color.from_rgb(52, 152, 219),
                    timestamp=datetime.datetime.utcnow(),
                )
                embed.add_field(
                    name="👤 العضو",
                    value=f"{after.mention} (`{after}`)",
                    inline=False,
                )
                await channel.send(embed=embed)

    # 5. رصد الحظر (Ban) وإلغاء الحظر
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        channel_id = get_log_channel(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        moderator = "مشرف غير معروف"
        reason = "لا يوجد سبب مدون"
        try:
            async for entry in guild.audit_logs(
                limit=5, action=discord.AuditLogAction.ban
            ):
                if entry.target.id == user.id:
                    moderator = f"{entry.user.mention} (`{entry.user}`)"
                    reason = entry.reason or "لا يوجد سبب"
                    break
        except Exception:
            pass

        embed = discord.Embed(
            title="🔨 رصد عقوبة حظر (Ban)",
            color=discord.Color.from_rgb(155, 89, 182),
            timestamp=datetime.datetime.utcnow(),
        )
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        embed.add_field(
            name="👤 المستخدم المحظور",
            value=f"{user.mention} (`{user}`)",
            inline=False,
        )
        embed.add_field(
            name="🛠️ بواسطة المشرف", value=moderator, inline=False
        )
        embed.add_field(name="📌 السبب", value=reason, inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        channel_id = get_log_channel(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title="🔓 إلغاء حظر (Unban)",
            color=discord.Color.from_rgb(26, 188, 156),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="👤 المستخدم",
            value=f"{user.mention} (`{user}`)",
            inline=False,
        )
        await channel.send(embed=embed)

    # 6. رصد إنشاء وحذف وتعديل الرومات (Channels)
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        channel_id = get_log_channel(channel.guild.id)
        if not channel_id:
            return
        log_ch = channel.guild.get_channel(channel_id)
        if not log_ch:
            return

        creator = "مشرف غير معروف"
        try:
            async for entry in channel.guild.audit_logs(
                limit=5, action=discord.AuditLogAction.channel_create
            ):
                if entry.target.id == channel.id:
                    creator = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except Exception:
            pass

        embed = discord.Embed(
            title="📁 إنشاء روم جديدة",
            color=discord.Color.from_rgb(46, 204, 113),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="🏷️ اسم الروم", value=f"{channel.mention} (`{channel.name}`)"
        )
        embed.add_field(name="🛠️ بواسطة", value=creator)
        await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        channel_id = get_log_channel(channel.guild.id)
        if not channel_id:
            return
        log_ch = channel.guild.get_channel(channel_id)
        if not log_ch:
            return

        deleter = "مشرف غير معروف"
        try:
            async for entry in channel.guild.audit_logs(
                limit=5, action=discord.AuditLogAction.channel_delete
            ):
                if entry.target.id == channel.id:
                    deleter = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except Exception:
            pass

        embed = discord.Embed(
            title="🗑️ حذف روم",
            color=discord.Color.from_rgb(231, 76, 60),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="🏷️ اسم الروم", value=f"`{channel.name}`")
        embed.add_field(name="🛠️ بواسطة", value=deleter)
        await log_ch.send(embed=embed)

    # 7. رصد إنشاء وحذف الرتب (Roles)
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        channel_id = get_log_channel(role.guild.id)
        if not channel_id:
            return
        log_ch = role.guild.get_channel(channel_id)
        if not log_ch:
            return

        creator = "مشرف غير معروف"
        try:
            async for entry in role.guild.audit_logs(
                limit=5, action=discord.AuditLogAction.role_create
            ):
                if entry.target.id == role.id:
                    creator = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except Exception:
            pass

        embed = discord.Embed(
            title="✨ إنشاء رتبة جديدة",
            color=discord.Color.from_rgb(52, 152, 219),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="🛡️ اسم الرتبة", value=f"{role.mention} (`{role.name}`)"
        )
        embed.add_field(name="🛠️ بواسطة", value=creator)
        await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        channel_id = get_log_channel(role.guild.id)
        if not channel_id:
            return
        log_ch = role.guild.get_channel(channel_id)
        if not log_ch:
            return

        deleter = "مشرف غير معروف"
        try:
            async for entry in role.guild.audit_logs(
                limit=5, action=discord.AuditLogAction.role_delete
            ):
                if entry.target.id == role.id:
                    deleter = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except Exception:
            pass

        embed = discord.Embed(
            title="❌ حذف رتبة",
            color=discord.Color.from_rgb(231, 76, 60),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="🛡️ اسم الرتبة المحذوفة", value=f"`{role.name}`")
        embed.add_field(name="🛠️ بواسطة", value=deleter)
        await log_ch.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logs(bot))
