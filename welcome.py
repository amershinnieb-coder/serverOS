import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from io import BytesIO
from easy_pil import Editor, Font, load_image_async

def get_db_connection():
    conn = sqlite3.connect("serveros.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            dm_message TEXT
        )
    """)
    conn.commit()
    return conn

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="إعداد_الترحيب", description="[خاص بالإداريين] تحديد الروم المخصصة لرسائل الترحيب والمغادرة في السيرفر")
    @app_commands.describe(channel="اختر روم الترحيب العام")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?
        """, (interaction.guild.id, channel.id, channel.id))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"✅ تم ضبط روم الترحيب العام بنجاح إلى: {channel.mention}", ephemeral=True)

    @app_commands.command(name="إعداد_رسالة_الخاص", description="[خاص بالإداريين] تخصيص رسالة ترحيبية ترسل للعضو الجديد في الخاص")
    @app_commands.describe(الرسالة="اكتب محتوى رسالة الترحيب (استخدم {user} لذكر اسم العضو)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_dm(self, interaction: discord.Interaction, الرسالة: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, dm_message) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET dm_message = ?
        """, (interaction.guild.id, الرسالة, الرسالة))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ تم حفظ وتحديث رسالة الترحيب الخاصة (DM) لهذا السيرفر بنجاح!", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, dm_message FROM welcome_settings WHERE guild_id = ?", (guild.id,))
        row = cursor.fetchone()
        conn.close()

        channel_id = row[0] if row else None
        custom_dm = row[1] if row else None

        # 1. تصميم وصناعة بطاقة الترحيب الفخمة وإرسالها في الروم
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    # تصميم البطاقة باستخدام easy-pil
                    background = Editor("welcome_bg.png") if False else Editor((900, 300)) # افتراضي لون داكن أو خلفية
                    # إذا لم تتوفر صورة خلفية، نصنع خلفية دكنة فخمة متناسقة مع الديسكورد
                    background.create_radial_gradient(center=(450, 150), start_radius=10, end_radius=600, color1="#2f3136", color2="#18191c")
                    
                    # تحميل أڤاتار العضو بشكل دائري مرتب
                    avatar_image = await load_image_async(str(member.avatar.url if member.avatar else member.default_avatar.url))
                    avatar = Editor(avatar_image).resize((130, 130)).circle_image()
                    
                    # إضافة الأڤاتار والعناصر على البطاقة
                    background.paste(avatar, (85, 85))
                    background.ellipse((85, 85), 130, 130, outline="#5865F2", stroke_width=5) # إطار ملون حول الأڤاتار
                    
                    # خطوط الكتابة (تأكد من وجود خط مدعوم أو استخدام الخط الافتراضي)
                    try:
                        title_font = Font.poppins(size=35, variant="bold")
                        sub_font = Font.poppins(size=22, variant="regular")
                    except:
                        title_font = Font.load_default(size=35)
                        sub_font = Font.load_default(size=22)

                    background.text((250, 95), f"WELCOME TO {guild.name.upper()}", color="#5865F2", font=sub_font)
                    background.text((250, 130), f"{member.name}", color="#FFFFFF", font=title_font)
                    background.text((250, 180), f"Member #{guild.member_count}", color="#b9bbbe", font=sub_font)

                    file = discord.File(fp=background.image_bytes, filename="welcome.png")

                    embed = discord.Embed(
                        description=f"✨ **أهلاً بك يا {member.mention} في سيرفر {guild.name}!**\n\n> نتمنى لك قضاء وقت ممتع معنا، ولا تنسَ مراجعة القوانين لتجنب المخالفات.",
                        color=0x5865F2
                    )
                    embed.set_image(url="attachment://welcome.png")
                    embed.set_footer(text=f"ID: {member.id} • نورت السيرفر برودك!", icon_url=guild.icon.url if guild.icon else None)

                    await channel.send(embed=embed, file=file)
                except Exception as e:
                    # نظام بديل في حال حدث أي خطأ تقني بالصورة لضمان إرسال الترحيب دائماً
                    embed = discord.Embed(
                        title="✨ انضم إلينا بطل جديد!",
                        description=f"أهلاً بك يا {member.mention} في سيرفر **{guild.name}**.\n\n🎯 نتمنى لك قضاء أوقات ممتعة معنا!",
                        color=0x5865F2
                    )
                    if member.avatar:
                        embed.set_thumbnail(url=member.avatar.url)
                    embed.set_footer(text=f"ID: {member.id}")
                    await channel.send(embed=embed)

        # 2. إرسال رسالة الخاص الفخمة للعضو
        if custom_dm:
            try:
                formatted_dm = custom_dm.replace("{user}", member.mention).replace("{username}", member.name).replace("{server}", guild.name)
                dm_embed = discord.Embed(
                    title=f"🌟 مرحباً بك في عائلة {guild.name}",
                    description=formatted_dm,
                    color=0x5865F2
                )
                if guild.icon:
                    dm_embed.set_thumbnail(url=guild.icon.url)
                dm_embed.set_footer(text=f"نتمنى لك رحلة ممتعة معنا!")
                
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass

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
                    title="🚪 وداعاً...",
                    description=f"غادرنا العضو **{member.name}**، نتمنى له كل التوفيق في طريقه.",
                    color=0xED4245
                )
                embed.set_footer(text=f"ID: {member.id}")
                await channel.send(embed=embed)

    @app_commands.command(name="اختبار_الترحيب", description="[خاص بالإداريين] معاينة وتجربة شكل رسالة الترحيب الحالية")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_test(self, interaction: discord.Interaction):
        await interaction.response.send_message("🧪 جاري توليد ومعاينة بطاقة الترحيب والفحص...", ephemeral=True)
        # محاكاة لحدث الدخول للاختبار الفوري
        await self.on_member_join(interaction.user)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
