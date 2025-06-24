from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
import aiohttp
from datetime import datetime

today = datetime.now().date()
INVEST_AMOUNT = 1
SHARE_VALUE = 2
CALC_PERCENT = 3
SESSION_NOTES = 4
GET_DOT_POINTS = 5
TUTOR_NAME = 6

percent_needed: int
invest_num: float
share_num: float
adj_share_val: float
dot_points: str

API_url = "https://openrouter.ai/api/v1/chat/completions"

API_key = os.getenv("API_KEY")
TOKEN = os.getenv("TOKEN")
API_model: Final = "deepseek/deepseek-r1-0528-qwen3-8b:free"
BOT_USERUSERNAME: Final = '@asx_jaris_bot'


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('How can I help you Lord M?')


async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("How much money is being invested?")
    return INVEST_AMOUNT


async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    headers = {
        "Authorization": f"Bearer {API_key}",
        "Content-Type": "application/json"
    }
    userinput = update.message.text

    # Safely get 'sessionbool' with default False
    session_bool = context.user_data.get("sessionbool", False)
    print(f"data boolean is {session_bool}")

    if session_bool:
        data = {
            "model": f"{API_model}",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"summarize these session notes and keep concise, in which i as a tutor has taught: {context.user_data.get('dot_points', '')}, "
                        f"student name is {context.user_data.get('student_name', '')}, and write within 100 words, using first person language"
                    )
                }
            ]
        }
    else:
        data = {
            "model": f"{API_model}",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Get latest overnight news on gold futures and gold shares outlook, uranium prices outlook, crude oil prices and their impact on shares. "
                        f"Include any positive ASX news or developments that could boost company shares. State if ASX is trending up or down. "
                        f"Mention any global conflicts or agreements affecting ASX. Keep it concise, within 100 words. Include date of info, use date: {today}"
                    )
                }
            ]
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_url, headers=headers, json=data) as resp:
                response_json = await resp.json()
                print("✅ FULL API RESPONSE:")
                print(response_json)

                choices = response_json.get("choices")
                if not choices or len(choices) == 0:
                    error_msg = response_json.get("error", {}).get("message", "No error message")
                    await update.message.reply_text(
                        f"❌ The AI did not respond properly.\nDetails: {error_msg}"
                    )
                    return

                reply_text = choices[0]["message"].get("content", "No content from AI")
                await update.message.reply_text(reply_text)

    except Exception as e:
        print("Deepseek AI error:", e)
        await update.message.reply_text(f"Something went wrong - error: {e}")


async def session_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sessionbool"] = True
    await update.message.reply_text("Enter dot points of session notes")
    return SESSION_NOTES


async def get_datapoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    context.user_data["dot_points"] = update.message.text
    print(f"dot points interpreted: {context.user_data['dot_points']}")
    await update.message.reply_text("Enter student name")
    return GET_DOT_POINTS


async def get_tutor_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_name"] = update.message.text
    print(f"student name: {context.user_data['student_name']}")
    await get_info(update, context)
    return ConversationHandler.END


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
    print("amount invested: ", invest_num)
    print("share value: ", share_num)
    percent_needed = 4 / invest_num
    adj_share_val = (1 + percent_needed) * share_num
    print("adj share value: ", adj_share_val)
    await update.message.reply_text(f"Share value needed to break-even: {adj_share_val:.3f}")
    return ConversationHandler.END


async def handle_response(text: str, update: Update) -> str:
    processed: str = text.lower()
    if processed in ["hi", "hello"]:
        return "hello"
    if "info" in processed:
        return "use command"
    if "calc" in processed:
        return "use command"
    print("msg not understood")
    return "??"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request: str = update.message.text
    print("user entered: ", request)
    handled: str = await handle_response(request, update)
    print("bot: ", handled)
    await update.message.reply_text(handled)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update "{update}" caused error "{context.error}"')


if __name__ == '__main__':
    print("Booting...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("calc", calc_start),
            CommandHandler("sessionnotes", session_notes)
        ],
        states={
            INVEST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, share_val)],
            SHARE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_percent)],
            SESSION_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_datapoints)],
            GET_DOT_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tutor_name)],
            TUTOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_info)],
        },
        fallbacks=[CommandHandler("cancel", error)],
    )

    app.add_handler(CommandHandler("getinfo", get_info))
    app.add_handler(CommandHandler("session_notes", get_info))  # This handler may be redundant

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.add_error_handler(error)
    print("analyzing")
    app.run_polling(poll_interval=1)


