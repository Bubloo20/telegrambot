from typing import Final
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, DictPersistence
)
import os
import aiohttp
from datetime import datetime

print("OS INSTALLED")

today = datetime.now().date()
INVEST_AMOUNT = 1
SHARE_VALUE = 2
CALC_PERCENT = 3
SESSION_NOTES = 4
GET_DOT_POINTS = 5
TUTOR_NAME = 6

API_url = "https://openrouter.ai/api/v1/chat/completions"
API_key = os.getenv("API_KEY")
TOKEN = os.getenv("TOKEN")
API_model: Final = "deepseek/deepseek-r1-0528-qwen3-8b:free"
BOT_USERUSERNAME: Final = '@asx_jaris_bot'

# ─── COMMAND HANDLERS ─────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('How can I help you Lord M?')

# ─── INVESTMENT CALC ──────────────────────────────────────────────────────────────

async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("How much money is being invested?")
    return INVEST_AMOUNT

async def share_val(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["invest_num"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return INVEST_AMOUNT
    await update.message.reply_text("What is share value?")
    return SHARE_VALUE

async def calc_percent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["share_num"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return SHARE_VALUE

    invest_num = context.user_data["invest_num"]
    share_num = context.user_data["share_num"]
    percent_needed = 4 / invest_num
    adj_share_val = (1 + percent_needed) * share_num
    await update.message.reply_text(f"Share value needed to break-even: {adj_share_val:.3f}")
    return ConversationHandler.END

# ─── SESSION NOTES FLOW ────────────────────────────────────────────────────────────

async def session_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter dot points of session notes")
    return SESSION_NOTES

async def get_datapoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["dot_points"] = update.message.text
    await update.message.reply_text("Enter student name")
    return GET_DOT_POINTS

async def get_tutor_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["student_name"] = update.message.text
    context.user_data["sessionbool"] = True  # ✅ Set TRUE at the end of note capture
    await get_info(update, context)
    return ConversationHandler.END

# ─── INFO FETCHER ──────────────────────────────────────────────────────────────────

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_bool = context.user_data.get("sessionbool", False)
    print(f"[DEBUG] sessionbool = {session_bool}")

    headers = {
        "Authorization": f"Bearer {API_key}",
        "Content-Type": "application/json"
    }

    if session_bool:
        data = {
            "model": API_model,
            "messages": [{
                "role": "user",
                "content": (
                    f"summarize these session notes and keep concise, in which I as a tutor have taught: "
                    f"{context.user_data.get('dot_points', '')}, "
                    f"student name is {context.user_data.get('student_name', '')}, and write within 100 words, using first person language"
                )
            }]
        }
        context.user_data["sessionbool"] = False  # ✅ Reset after use
    else:
        data = {
            "model": API_model,
            "messages": [{
                "role": "user",
                "content": (
                    f"Get latest overnight news on gold futures and gold shares outlook, uranium prices outlook, crude oil prices and their impact on shares. "
                    f"Include any positive ASX news or developments that could boost company shares. State if ASX is trending up or down. "
                    f"Mention any global conflicts or agreements affecting ASX. Keep it concise, within 100 words. Use date: {today}"
                )
            }]
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_url, headers=headers, json=data) as resp:
                response_json = await resp.json()
                print("✅ FULL API RESPONSE:", response_json)

                choices = response_json.get("choices")
                if not choices:
                    error_msg = response_json.get("error", {}).get("message", "No error message")
                    await update.message.reply_text(f"❌ AI failed.\nDetails: {error_msg}")
                    return

                reply_text = choices[0]["message"].get("content", "No content from AI")
                await update.message.reply_text(reply_text)

    except Exception as e:
        print("Deepseek AI error:", e)
        await update.message.reply_text(f"Something went wrong - error: {e}")

# ─── CATCH-ALL ─────────────────────────────────────────────────────────────────────

async def handle_response(text: str, update: Update) -> str:
    processed = text.lower()
    if processed in ["hi", "hello"]:
        return "hello"
    if "info" in processed or "calc" in processed:
        return "use command"
    return "??"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = await handle_response(update.message.text, update)
    await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update "{update}" caused error "{context.error}"')

# ─── MAIN ──────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Booting...")
    persistence = DictPersistence()
    app = Application.builder().token(TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start_command))

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("calc", calc_start),
            CommandHandler("session_notes", session_notes),
            CommandHandler("sessionnotes", session_notes)
        ],
        states={
            INVEST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, share_val)],
            SHARE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_percent)],
            SESSION_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_datapoints)],
            GET_DOT_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tutor_name)],
        },
        fallbacks=[CommandHandler("cancel", error)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("getinfo", get_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error)

    print("analyzing")
    app.run_polling(poll_interval=1)


