import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

def get_db_connection():
    conn = sqlite3.connect("serveros.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            welcome_text TEXT,
            image_url TEXT
        )
    """)
    conn.commit()
    return conn

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. أمر تجربة الترحيب الفوري (مع حل مشكلة التعليق)
    @app_commands.command(name="تجربة_الترحيب", description="[إدارة السيرفر] معاينة شكل رسالة الترحيب الحالية وتجربتها بنفسك")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        # إعلام ديسكورد فوراً بأن البوت قاعد يشتغل عشان ما يعلق الأمر
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            await self.send_welcome_message(interaction.user, test_channel=interaction.channel)
            await interaction.followup.send("✅ تم إرسال معاينة الترحيب في هذه الروم بنجاح!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ أثناء إرسال المعاينة: {e}", ephemeral=True)

    # 2. أمر إعداد الروم وتشغيل الترحيب الجاهز
    @app_commands.command(name="إعداد_الترحيب", description="[إدارة السيرفر] حدد روم الترحيب وسيقوم البوت بتفعيل التصميم الجاهز الفخم فوراً")
    @app_commands.describe(الروم="اختر روم الترحيب العام")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_welcome(self, interaction: discord.Interaction, الروم: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        default_text = "✨ أهلاً بك يا {user} في سيرفر **{server}**!\n\n🎯 نتمنى لك قضاء أوقات ممتعة معنا، ولا تنسَ مراجعة القوانين لتجنب المخالفات."
        default_banner = "https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif"

        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, channel_id, welcome_text, image_url) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?, welcome_text = COALESCE(welcome_text, ?), image_url = COALESCE(image_url, ?)
        """, (interaction.guild.id, الروم.id, default_text, default_banner, الروم.id, default_text, default_banner))
        
        conn.commit()
        conn.close()

        await interaction.followup.send(
            f"✅ **تم تفعيل الترحيب الجاهز بنجاح في الروم:** {الروم.mention}\n"
            f"- جرب الآن أمر `/تجربة_الترحيب` لرؤية الشكل الفخم فوراً!",
            ephemeral=True
        )

    # 3. أمر تعديل النص أو البانر المتحرك
    @app_commands.command(name="تعديل_نص_الترحيب", description="[إدارة السيرفر] تغيير النص أو صورة البانر المتحركة (GIF)")
    @app_commands.describe(النص="اكتب نصاً جديداً (اختياري)", رابط_الـgif="رابط صورة GIF جديدة تظهر تحت (اختياري)")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_welcome(self, interaction: discord.Interaction, النص: str = None, رابط_الـgif: str = None):
        await interaction.response.defer(ephemeral=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT welcome_text, image_url FROM welcome_settings WHERE guild_id = ?", (interaction.guild.id,))
        row = cursor.fetchone()

        default_text = "✨ أهلاً بك يا {user} في سيرفر **{server}**!\n\n🎯 نتمنى لك قضاء أوقات ممتعة معنا، ولا تنسَ مراجعة القوانين لتجنب المخالفات."
        
        current_text = row[0] if (row and row[0]) else default_text
        current_img = row[1] if (row and row[1]) else None

        new_text = النص if النص is not None else current_text
        new_img = رابط_الـgif if رابط_الـgif is not None else current_img

        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, welcome_text, image_url) 
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET welcome_text = ?, image_url = ?
        """, (interaction.guild.id, new_text, new_img, new_text, new_img))
        
        conn.commit()
        conn.close()

        await interaction.followup.send("✅ تم تحديث إعدادات الترحيب بنجاح!", ephemeral=True)

    async def send_welcome_message(self, member: discord.Member, test_channel=None):
        guild = member.guild
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, welcome_text, image_url FROM welcome_settings WHERE guild_id = ?", (guild.id,))
        row = cursor.fetchone()
        conn.close()

        if not row and not test_channel:
            return

        channel_id, welcome_text, image_url = row if row else (None, None, None)

        # إذا كان أمر تجربة، نرسل في نفس روم التجربة، وإذا دخول حقيقي نرسل في روم الترحيب المحدد
        target_channel = test_channel if test_channel else (guild.get_channel(channel_id) if channel_id else None)

        if target_channel:
            raw_text = welcome_text if welcome_text else "✨ أهلاً بك يا {user} في سيرفر **{server}**!"
            formatted_text = (
                raw_text
                .replace("{user}", member.mention)
                .replace("{username}", member.name)
                .replace("{server}", guild.name)
                .replace("{count}", str(guild.member_count))
            )

            embed = discord.Embed(
                title="🎉 عضو جديد انضم إلينا!",
                description=formatted_text,
                color=0x5865F2
            )
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            
            embed.add_field(name="👥 ترتيب العضو", value=f"#{guild.member_count}", inline=True)
            
            if image_url and image_url.strip():
                embed.set_image(url=image_url)

            icon_url = guild.icon.url if guild.icon else None
            embed.set_footer(text=f"ID: {member.id} • نورت السيرفر برودك!", icon_url=icon_url)
            await target_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send_welcome_message(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM welcome_settings WHERE guild_id = ?", (member.guild.id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            channel_id = row[0]
            channel = member.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="🚪 غادرنا عضو",
                    description=f"نودع العضو **{member.name}**، نتمنى له التوفيق.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
