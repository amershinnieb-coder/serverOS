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

    # 1. أمر تجربة الترحيب الفوري
    @app_commands.command(name="تجربة_الترحيب", description="[إدارة السيرفر] معاينة شكل رسالة الترحيب الحالية وتجربتها بنفسك")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        await interaction.response.send_message("🧪 جاري إرسال معاينة الترحيب...", ephemeral=True)
        await self.send_welcome_message(interaction.user)

    # 2. أمر إعداد الروم وتشغيل الترحيب الجاهز
    @app_commands.command(name="إعداد_الترحيب", description="[إدارة السيرفر] حدد روم الترحيب وسيقوم البوت بتفعيل التصميم الجاهز الفخم فوراً")
    @app_commands.describe(الروم="اختر روم الترحيب العام")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_welcome(self, interaction: discord.Interaction, الروم: discord.TextChannel):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # النص الجاهز الفخم الافتراضي (مع منشن حقيقي ومضمون للعضو)
        default_text = "✨ أهلاً بك يا {user} في سيرفر **{server}**!\n\n🎯 نتمنى لك قضاء أوقات ممتعة معنا، ولا تنسَ مراجعة القوانين لتجنب المخالفات."
        # بانر متحرك فخم افتراضي (يمكنك تغييره لاحقاً)
        default_banner = "https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif"

        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, channel_id, welcome_text, image_url) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?
        """, (interaction.guild.id, الروم.id, default_text, default_banner, الروم.id))
        
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ **تم تفعيل الترحيب الجاهز بنجاح في الروم:** {الروم.mention}\n"
            f"- جرب الآن أمر `/تجربة_الترحيب` لرؤية الشكل الفخم فوراً!",
            ephemeral=True
        )

    # 3. أمر اختياري لو تبي تغير النص أو صورة البانر المتحركة لاحقاً ببساطة
    @app_commands.command(name="تعديل_نص_الترحيب", description="[إدارة السيرفر] تغيير النص أو صورة البانر المتحركة (GIF)")
    @app_commands.describe(النص="اكتب نصاً جديداً (اختياري)", رابط_الـgif="رابط صورة GIF جديدة تظهر تحت (اختياري)")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_welcome(self, interaction: discord.Interaction, النص: str = None, رابط_الـgif: str = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT welcome_text, image_url FROM welcome_settings WHERE guild_id = ?", (interaction.guild.id,))
        row = cursor.fetchone()

        new_text = النص if النص else (row[0] if row else "أهلاً بك يا {user}")
        new_img = رابط_الـgif if رابط_الـgif else (row[1] if row else None)

        cursor.execute("""
            UPDATE welcome_settings SET welcome_text = ?, image_url = ? WHERE guild_id = ?
        """, (new_text, new_img, interaction.guild.id))
        conn.commit()
        conn.close()

        await interaction.response.send_message("✅ تم تحديث إعدادات الترحيب بنجاح!", ephemeral=True)

    async def send_welcome_message(self, member: discord.Member):
        guild = member.guild
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, welcome_text, image_url FROM welcome_settings WHERE guild_id = ?", (guild.id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return

        channel_id, welcome_text, image_url = row

        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                # تنسيق النص ومنشن اليوزر بشكل مضمون 100%
                raw_text = welcome_text or "أهلاً بك يا {user} في سيرفر **{server}**!"
                formatted_text = (
                    raw_text
                    .replace("{user}", member.mention)
                    .replace("{username}", member.name)
                    .replace("{server}", guild.name)
                    .replace("{count}", str(guild.member_count))
                )

                # تصميم الـ Embed الجاهز والفخم
                embed = discord.Embed(
                    title="🎉 عضو جديد انضم إلينا!",
                    description=formatted_text,
                    color=0x5865F2 # لون ديسكورد المميز الفخم
                )
                
                # صورة أڤاتار العضو (فوق على اليمين)
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                
                # ترتيب العضو في السيرفر
                embed.add_field(name="👥 ترتيب العضو", value=f"#{guild.member_count}", inline=True)
                
                # البانر المتحرك أو الصورة (تحت)
                if image_url:
                    embed.set_image(url=image_url)

                embed.set_footer(text=f"ID: {member.id} • نورت السيرفر برودك!", icon_url=guild.icon.url if guild.icon else None)
                await channel.send(embed=embed)

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

        channel_id = row[0] if row else None
        if channel_id:
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
