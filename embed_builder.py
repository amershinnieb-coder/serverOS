import discord
from discord import app_commands
from discord.ext import commands

class CustomMultiButtonsView(discord.ui.View):
    def __init__(self, buttons_data):
        super().__init__(timeout=None) # أزرار دائمة لا تنتهي

        for label, action, emoji in buttons_data:
            # التحقق إذا كان الإجراء عبارة عن رابط حقيقي
            if action.startswith("http://") or action.startswith("https://"):
                button = discord.ui.Button(
                    label=label[:80],
                    style=discord.ButtonStyle.link,
                    url=action,
                    emoji=emoji if emoji else "🔗"
                )
            else:
                # زر عادي يفتح إيمبد سري خاص بالعضو (Ephemeral Embed)
                button = discord.ui.Button(
                    label=label[:80],
                    style=discord.ButtonStyle.primary,
                    emoji=emoji if emoji else "📌"
                )
                button.callback = self.create_callback(label, action)
            
            self.add_item(button)

    def create_callback(self, button_label, hidden_text):
        async def button_callback(interaction: discord.Interaction):
            # بناء إيمبد سري فخم يظهر للعضو وحده عند الضغط
            secret_embed = discord.Embed(
                title=f"📌 تفاصيل: {button_label}",
                description=hidden_text,
                color=0x5865F2
            )
            secret_embed.set_footer(
                text=f"مطلوب بواسطة: {interaction.user.name}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.response.send_message(
                embed=secret_embed, ephemeral=True
            )
        return button_callback


class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="إنشاء_إيمبد_بأزرار",
        description="[إدارة السيرفر] إرسال إيمبد فخم مع حتى 25 زر مخصص (روابط أو إيمبدات سرية)"
    )
    @app_commands.describe(
        العنوان="عنوان الإيمبد الرئيسي",
        الوصف="محتوى ووصف الإيمبد الأساسي في الروم",
        الأزرار="اكتب كل زر بسطر هكذا: (اسم الزر : النص السري للإيمبد أو الرابط : الايموجي)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_embed(
        self,
        interaction: discord.Interaction,
        العنوان: str,
        الوصف: str,
        الأزرار: str
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # تحليل الأزرار المدخلة
        buttons_data = []
        lines = الأزرار.split("\n")
        for line in lines:
            if ":" in line:
                parts = line.split(":")
                label = parts[0].strip()
                action = parts[1].strip() # إما نص الإيمبد السري أو رابط
                emoji = parts[2].strip() if len(parts) > 2 else None # الايموجي اختياري
                
                if label and action:
                    buttons_data.append((label, action, emoji))

        if not buttons_data:
            await interaction.followup.send(
                "❌ خطأ: يرجى كتابة الأزرار بالطريقة الصحيحة:\n`اسم الزر : النص السري للإيمبد أو الرابط : الايموجي`",
                ephemeral=True
            )
            return

        # السماح حتى 25 زر كحد أقصى مسموح به في ديسكورد
        if len(buttons_data) > 25:
            await interaction.followup.send(
                "❌ عذراً، الحد الأقصى المسموح به من ديسكورد هو 25 زر في الرسالة الواحدة!",
                ephemeral=True
            )
            return

        # بناء الإيمبد الأساسي للروم
        embed = discord.Embed(
            title=العنوان,
            description=الوصف,
            color=0x5865F2
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(
            text=f"تم النشر بواسطة: {interaction.user.name}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        # إرسال الإيمبد والأزرار الفخمة للروم
        view = CustomMultiButtonsView(buttons_data)
        await interaction.channel.send(embed=embed, view=view)
        
        await interaction.followup.send(
            f"✅ تم نشر الإيمبد الفخم ومعه ({len(buttons_data)}) زر بنجاح!",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
