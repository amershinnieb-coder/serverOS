import discord
from discord import app_commands
from discord.ext import commands


class CustomMultiButtonsView(discord.ui.View):

    def __init__(self, buttons_data):
        super().__init__(timeout=None)

        for label, hidden_text in buttons_data:
            if label and hidden_text:
                button = discord.ui.Button(
                    label=label[:80],
                    style=discord.ButtonStyle.primary,
                    emoji="📌",
                )
                button.callback = self.create_callback(hidden_text)
                self.add_item(button)

    def create_callback(self, hidden_text):
        async def button_callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                content=hidden_text, ephemeral=True
            )

        return button_callback


class EmbedBuilder(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="إنشاء_إيمبد_بأزرار",
        description=(
            "[إدارة السيرفر] إرسال إيمبد مع أزرار مخصصة (اكتب كل زر في"
            " سطر بداخل خانة الأزرار)"
        ),
    )
    @app_commands.describe(
        العنوان="عنوان الإيمبد الرئيسي",
        الوصف="محتوى ووصف الإيمبد",
        الأزرار=(
            "اكتب الأزرار هكذا: (اسم الزر : النص السري) وكل زر في سطر مستقل"
        ),
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_embed(
        self,
        interaction: discord.Interaction,
        العنوان: str,
        الوصف: str,
        الأزرار: str,
    ):
        guild = interaction.guild

        # تحليل الأزرار المدخلة
        buttons_data = []
        lines = الأزرار.split("\n")
        for line in lines:
            if ":" in line:
                parts = line.split(":", 1)
                label = parts[0].strip()
                text = parts[1].strip()
                if label and text:
                    buttons_data.append((label, text))

        if not buttons_data:
            await interaction.response.send_message(
                "❌ خطأ: يرجى كتابة الأزرار بالطريقة الصحيحة (اسم الزر : النص"
                " السري)",
                ephemeral=True,
            )
            return

        if len(buttons_data) > 5:
            await interaction.response.send_message(
                "❌ عذراً، الحد الأقصى هو 5 أزرار في هذه الرسالة لتجنب الأخطاء!",
                ephemeral=True,
            )
            return

        # بناء الإيمبد
        embed = discord.Embed(
            title=العنوان,
            description=الوصف,
            color=discord.Color.from_rgb(88, 101, 242),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(
            text=f"تم الإرسال بواسطة: {interaction.user.name}",
            icon_url=(
                interaction.user.avatar.url
                if interaction.user.avatar
                else None
            ),
        )

        # إرسال الرسالة والأزرار
        view = CustomMultiButtonsView(buttons_data)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ تم نشر الإيمبد ومعه ({len(buttons_data)}) أزرار بنجاح!",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
