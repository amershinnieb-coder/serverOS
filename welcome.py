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
            dm_message TEXT,
            thumbnail_url TEXT,
            image_url TEXT,
            use_embed INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    return conn

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. أمر تجربة الترحيب
    @app_commands.command(name="تجربة_الترحيب", description="[إدارة السيرفر] معاينة وتجربة رسالة الترحيب الحالية وصور الـ GIF والإيمبد بنفسك")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        await interaction.response.send_message("🧪 جاري إرسال معاينة الترحيب الحالية...", ephemeral=True)
        await self.send_welcome_message(interaction.user)

    # 2. الأمر الشامل لإعداد الترحيب باللغة العربية بالكامل
    @app_commands.command(name="إعداد_الترحيب", description="[إدارة السيرفر] التحكم الكامل بنظام الترحيب، الصور، الإيمبد، والرسائل")
    @app_commands.describe(
        الروم="اختر روم الترحيب العام",
        نوع_الإيمبد="هل تريد رسالة الترحيب بصيغة Embed فخم أم نص عادي؟",
        النص="نص الترحيب (استخدم {user} لذكر العضو، {server} لاسم السيرفر، {count} للعدد)",
        صورة_فوق="رابط صورة مصغرة فوق (تدعم GIF) أو اكتب none للحذف",
        صورة_تحت="رابط صورة بانر كبيرة تحت (تدعم GIF) أو اكتب none للحذف",
        رسالة_الخاص="رسالة الخاص التي تصل العضو عند دخوله (اختياري)"
    )
    @app_commands.choices(نوع_الإيمبد=[
        app_commands.Choice(name="نعم (Embed فخم)", value=1),
        app_commands.Choice(name="لا (نص عادي فقط)", value=0)
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_welcome(
        self, 
        interaction: discord.Interaction, 
        الروم: discord.TextChannel,
        نوع_الإيمبد: int = 1,
        النص: str = None,
        صورة_فوق: str = None,
        صورة_تحت: str = None,
        رسالة_الخاص: str = None
    ):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب الإعدادات القديمة للحفاظ عليها في حال لم يقم المالك بتعديلها
        cursor.execute("SELECT welcome_text, dm_message, thumbnail_url, image_url FROM welcome_settings WHERE guild_id = ?", (interaction.guild.id,))
        old_data = cursor.fetchone()

        final_text = النص if النص else (old_data[0] if old_data and old_data[0] else "أهلاً بك يا {user} في سيرفر **{server}**!")
        final_dm = رسالة_الخاص if رسالة_الخاص else (old_data[1] if old_data else None)
        final_thumb = صورة_فوق if صورة_فوق else (old_data[2] if old_data else None)
        final_img = صورة_تحت if صورة_تحت else (old_data[3] if old_data else None)

        if final_thumb and final_thumb.lower() == "none": final_thumb = None
        if final_img and final_img.lower() == "none": final_img = None

        cursor.execute("""
            INSERT INTO welcome_settings (guild_id, channel_id, welcome_text, dm_message, thumbnail_url, image_url, use_embed) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET 
                channel_id = ?, 
                welcome_text = ?, 
                dm_message = ?, 
                thumbnail_url = ?, 
                image_url = ?, 
                use_embed = ?
        """, (
            interaction.guild.id, الروم.id, final_text, final_dm, final_thumb, final_img, نوع_الإيمبد,
            الروم.id, final_text, final_dm, final_thumb, final_img, نوع_الإيمبد
        ))
        
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ **تم تحديث إعدادات الترحيب بنجاح!**\n"
            f"- الروم: {الروم.mention}\n"
            f"- نظام الإيمبد: {'مفعل (Embed)' if نوع_الإيمبد == 1 else 'معطل (نص عادي)'}\n"
            f"- استخدم أمر `/تجربة_الترحيب` في أي وقت لمعاينة الشكل!",
            ephemeral=True
        )

    async def send_welcome_message(self, member: discord.Member):
        guild = member.guild
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, welcome_text, dm_message, thumbnail_url, image_url, use_embed FROM welcome_settings WHERE guild_id = ?", (guild.id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return

        channel_id, welcome_text, dm_message, thumbnail_url, image_url, use_embed = row

        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                raw_text = welcome_text or "أهلاً بك يا {user} في سيرفر **{server}**!"
                formatted_text = (
                    raw_text
                    .replace("{user}", member.mention)
                    .replace("{username}", member.name)
                    .replace("{server}", guild.name)
                    .replace("{count}", str(guild.member_count))
                )

                # إذا كان الإيمبد مفعل
                if use_embed == 1:
                    embed = discord.Embed(
                        title="✨ انضم إلينا بطل جديد!",
                        description=formatted_text,
                        color=0x2b2d31
                    )
                    
                    # الصورة المصغرة (فوق)
                    if thumbnail_url:
                        embed.set_thumbnail(url=thumbnail_url)
                    elif member.avatar:
                        embed.set_thumbnail(url=member.avatar.url)
                    
                    embed.add_field(name="👥 ترتيب العضو", value=f"#{guild.member_count}", inline=True)
                    
                    # الصورة الكبيرة أو المتحركة (تحت في البانر)
                    if image_url:
                        embed.set_image(url=image_url)

                    embed.set_footer(text=f"ID: {member.id}", icon_url=guild.icon.url if guild.icon else None)
                    await channel.send(embed=embed)
                
                # إذا كان نص عادي بدون إيمبد
                else:
                    content_to_send = formatted_text
                    if image_url:
                        content_to_send += f"\n{image_url}"
                    await channel.send(content_to_send)

        # رسالة الخاص (DM)
        if dm_message:
            try:
                formatted_dm = (
                    dm_message
                    .replace("{user}", member.mention)
                    .replace("{username}", member.name)
                    .replace("{server}", guild.name)
                )
                dm_embed = discord.Embed(
                    title=f"🌟 مرحباً بك في {guild.name}",
                    description=formatted_dm,
                    color=0x2b2d31
                )
                if guild.icon:
                    dm_embed.set_thumbnail(url=guild.icon.url)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass

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
