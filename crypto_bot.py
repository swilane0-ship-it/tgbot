import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import aiohttp
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user alerts: {user_id: {symbol: [(target_price, direction)]}}
user_alerts: Dict[int, Dict[str, List[tuple]]] = {}

# Store user watchlists: {user_id: [symbols]}
user_watchlists: Dict[int, List[str]] = {}

# Store user language preferences: {user_id: 'en' or 'ru'}
user_languages: Dict[int, str] = {}

# CoinGecko API base URL (free, no API key required)
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Popular cryptocurrencies mapping
CRYPTO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'USDT': 'tether',
    'BNB': 'binancecoin',
    'SOL': 'solana',
    'XRP': 'ripple',
    'ADA': 'cardano',
    'DOGE': 'dogecoin',
    'TRX': 'tron',
    'DOT': 'polkadot',
    'MATIC': 'matic-network',
    'LTC': 'litecoin',
    'SHIB': 'shiba-inu',
    'AVAX': 'avalanche-2',
    'UNI': 'uniswap',
    'LINK': 'chainlink',
    'ATOM': 'cosmos',
    'XLM': 'stellar',
    'TON': 'the-open-network',
    'APT': 'aptos'
}

# Localization strings
LOCALE = {
    'en': {
        'welcome': '''🤖 **Crypto Price Alert Bot**

Welcome! I can help you track cryptocurrency prices and set price alerts.

**Available Commands:**
/price <SYMBOL> - Get current price (e.g., /price BTC)
/alert <SYMBOL> <PRICE> <above/below> - Set price alert (e.g., /alert BTC 50000 above)
/list - Show your active alerts
/watch <SYMBOL> - Add to watchlist
/watchlist - Show your watchlist with current prices
/remove <SYMBOL> - Remove alert
/lang - Change language / Изменить язык
/help - Show this help message

**Supported Cryptocurrencies:**
BTC, ETH, USDT, BNB, SOL, XRP, ADA, DOGE, TRX, DOT, MATIC, LTC, SHIB, AVAX, UNI, LINK, ATOM, XLM, TON, APT

Let's start tracking! 🚀''',
        'lang_changed': '✅ Language changed to English',
        'price_usage': '❌ Please specify a cryptocurrency symbol.\nExample: /price BTC',
        'price_not_found': '❌ Could not find price for {symbol}.\nPlease use a supported cryptocurrency symbol.',
        'price_info': '''💰 **{symbol} Price**

Current Price: ${price:,.2f}
24h Change: {emoji} {sign}{change:.2f}%
Market Cap: ${market_cap:,.0f}

_Updated: {time}_''',
        'alert_usage': '''❌ Invalid format.
Usage: /alert <SYMBOL> <PRICE> <above/below>
Example: /alert BTC 50000 above''',
        'alert_invalid_price': '❌ Invalid price. Please enter a number.',
        'alert_invalid_direction': '❌ Direction must be \'above\' or \'below\'',
        'alert_unsupported': '❌ {symbol} is not supported.\nUse /help to see supported cryptocurrencies.',
        'alert_set': '✅ Alert set!\nI\'ll notify you when {symbol} goes {direction} ${price:,.2f}',
        'list_empty': '📭 You have no active alerts.\nUse /alert to set one!',
        'list_header': '🔔 **Your Active Alerts:**\n\n',
        'watch_usage': '❌ Please specify a cryptocurrency symbol.\nExample: /watch BTC',
        'watch_unsupported': '❌ {symbol} is not supported.\nUse /help to see supported cryptocurrencies.',
        'watch_exists': 'ℹ️ {symbol} is already in your watchlist.',
        'watch_added': '✅ {symbol} added to your watchlist!',
        'watchlist_empty': '📭 Your watchlist is empty.\nUse /watch <SYMBOL> to add cryptocurrencies!',
        'watchlist_header': '👁️ **Your Watchlist:**\n\n',
        'remove_usage': '❌ Please specify a cryptocurrency symbol.\nExample: /remove BTC',
        'remove_success': '✅ All alerts for {symbol} removed.',
        'remove_not_found': 'ℹ️ No alerts found for {symbol}.',
        'remove_watchlist': '✅ {symbol} removed from watchlist.',
        'alert_triggered': '''🚨 **PRICE ALERT TRIGGERED!**

{symbol} has reached your target!

Target: ${target:,.2f} ({direction})
Current Price: ${current:,.2f}

_Alert time: {time}_''',
        'above': 'above',
        'below': 'below'
    },
    'ru': {
        'welcome': '''🤖 **Бот для отслеживания криптовалют**

Добро пожаловать! Я помогу отслеживать цены на криптовалюты и настраивать оповещения.

**Доступные команды:**
/price <СИМВОЛ> - Узнать текущую цену (например, /price BTC)
/alert <СИМВОЛ> <ЦЕНА> <выше/ниже> - Установить оповещение (например, /alert BTC 50000 выше)
/list - Показать активные оповещения
/watch <СИМВОЛ> - Добавить в список отслеживания
/watchlist - Показать список отслеживаемых монет
/remove <СИМВОЛ> - Удалить оповещение
/lang - Change language / Изменить язык
/help - Показать справку

**Поддерживаемые криптовалюты:**
BTC, ETH, USDT, BNB, SOL, XRP, ADA, DOGE, TRX, DOT, MATIC, LTC, SHIB, AVAX, UNI, LINK, ATOM, XLM, TON, APT

Начнем отслеживание! 🚀''',
        'lang_changed': '✅ Язык изменен на русский',
        'price_usage': '❌ Укажите символ криптовалюты.\nПример: /price BTC',
        'price_not_found': '❌ Не удалось найти цену для {symbol}.\nИспользуйте поддерживаемую криптовалюту.',
        'price_info': '''💰 **Цена {symbol}**

Текущая цена: ${price:,.2f}
Изменение за 24ч: {emoji} {sign}{change:.2f}%
Капитализация: ${market_cap:,.0f}

_Обновлено: {time}_''',
        'alert_usage': '''❌ Неверный формат.
Использование: /alert <СИМВОЛ> <ЦЕНА> <выше/ниже>
Пример: /alert BTC 50000 выше''',
        'alert_invalid_price': '❌ Неверная цена. Введите число.',
        'alert_invalid_direction': '❌ Направление должно быть \'выше\' или \'ниже\' (или \'above\'/\'below\')',
        'alert_unsupported': '❌ {symbol} не поддерживается.\nИспользуйте /help для списка поддерживаемых монет.',
        'alert_set': '✅ Оповещение установлено!\nЯ уведомлю вас, когда {symbol} будет {direction} ${price:,.2f}',
        'list_empty': '📭 У вас нет активных оповещений.\nИспользуйте /alert чтобы создать!',
        'list_header': '🔔 **Ваши активные оповещения:**\n\n',
        'watch_usage': '❌ Укажите символ криптовалюты.\nПример: /watch BTC',
        'watch_unsupported': '❌ {symbol} не поддерживается.\nИспользуйте /help для списка поддерживаемых монет.',
        'watch_exists': 'ℹ️ {symbol} уже в вашем списке отслеживания.',
        'watch_added': '✅ {symbol} добавлен в список отслеживания!',
        'watchlist_empty': '📭 Ваш список отслеживания пуст.\nИспользуйте /watch <СИМВОЛ> для добавления!',
        'watchlist_header': '👁️ **Ваш список отслеживания:**\n\n',
        'remove_usage': '❌ Укажите символ криптовалюты.\nПример: /remove BTC',
        'remove_success': '✅ Все оповещения для {symbol} удалены.',
        'remove_not_found': 'ℹ️ Оповещения для {symbol} не найдены.',
        'remove_watchlist': '✅ {symbol} удален из списка отслеживания.',
        'alert_triggered': '''🚨 **ОПОВЕЩЕНИЕ О ЦЕНЕ!**

{symbol} достиг вашей целевой цены!

Цель: ${target:,.2f} ({direction})
Текущая цена: ${current:,.2f}

_Время оповещения: {time}_''',
        'above': 'выше',
        'below': 'ниже'
    }
}


def get_user_lang(user_id: int) -> str:
    """Get user's language preference, default to English"""
    return user_languages.get(user_id, 'en')


def t(user_id: int, key: str, **kwargs) -> str:
    """Translate text based on user's language preference"""
    lang = get_user_lang(user_id)
    text = LOCALE[lang].get(key, LOCALE['en'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


async def get_crypto_price(symbol: str) -> Optional[Dict]:
    """Get current cryptocurrency price from CoinGecko API"""
    symbol = symbol.upper()
    
    if symbol not in CRYPTO_IDS:
        return None
    
    crypto_id = CRYPTO_IDS[symbol]
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{COINGECKO_API}/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if crypto_id in data:
                        return {
                            'symbol': symbol,
                            'price': data[crypto_id]['usd'],
                            'change_24h': data[crypto_id].get('usd_24h_change', 0),
                            'market_cap': data[crypto_id].get('usd_market_cap', 0)
                        }
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
    
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    if user_id not in user_alerts:
        user_alerts[user_id] = {}
    if user_id not in user_watchlists:
        user_watchlists[user_id] = []
    if user_id not in user_languages:
        user_languages[user_id] = 'en'
    
    await update.message.reply_text(t(user_id, 'welcome'), parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await start(update, context)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get current price of a cryptocurrency"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(t(user_id, 'price_usage'))
        return
    
    symbol = context.args[0].upper()
    
    price_data = await get_crypto_price(symbol)
    
    if price_data:
        change_emoji = "📈" if price_data['change_24h'] >= 0 else "📉"
        change_sign = "+" if price_data['change_24h'] >= 0 else ""
        
        message = t(user_id, 'price_info',
                   symbol=price_data['symbol'],
                   price=price_data['price'],
                   emoji=change_emoji,
                   sign=change_sign,
                   change=price_data['change_24h'],
                   market_cap=price_data['market_cap'],
                   time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(t(user_id, 'price_not_found', symbol=symbol))


async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a price alert"""
    user_id = update.effective_user.id
    
    if len(context.args) < 3:
        await update.message.reply_text(t(user_id, 'alert_usage'))
        return
    
    symbol = context.args[0].upper()
    try:
        target_price = float(context.args[1])
    except ValueError:
        await update.message.reply_text(t(user_id, 'alert_invalid_price'))
        return
    
    direction = context.args[2].lower()
    # Support both English and Russian direction words
    if direction in ['выше', 'higher']:
        direction = 'above'
    elif direction in ['ниже', 'lower']:
        direction = 'below'
    
    if direction not in ['above', 'below']:
        await update.message.reply_text(t(user_id, 'alert_invalid_direction'))
        return
    
    if symbol not in CRYPTO_IDS:
        await update.message.reply_text(t(user_id, 'alert_unsupported', symbol=symbol))
        return
    
    if user_id not in user_alerts:
        user_alerts[user_id] = {}
    
    if symbol not in user_alerts[user_id]:
        user_alerts[user_id][symbol] = []
    
    user_alerts[user_id][symbol].append((target_price, direction))
    
    # Translate direction for display
    direction_text = t(user_id, direction)
    await update.message.reply_text(
        t(user_id, 'alert_set', symbol=symbol, direction=direction_text, price=target_price)
    )


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all active alerts for the user"""
    user_id = update.effective_user.id
    
    if user_id not in user_alerts or not user_alerts[user_id]:
        await update.message.reply_text(t(user_id, 'list_empty'))
        return
    
    message = t(user_id, 'list_header')
    
    for symbol, alerts in user_alerts[user_id].items():
        message += f"**{symbol}:**\n"
        for price, direction in alerts:
            arrow = "⬆️" if direction == "above" else "⬇️"
            direction_text = t(user_id, direction)
            message += f"  {arrow} ${price:,.2f} ({direction_text})\n"
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a cryptocurrency to watchlist"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(t(user_id, 'watch_usage'))
        return
    
    symbol = context.args[0].upper()
    
    if symbol not in CRYPTO_IDS:
        await update.message.reply_text(t(user_id, 'watch_unsupported', symbol=symbol))
        return
    
    if user_id not in user_watchlists:
        user_watchlists[user_id] = []
    
    if symbol in user_watchlists[user_id]:
        await update.message.reply_text(t(user_id, 'watch_exists', symbol=symbol))
        return
    
    user_watchlists[user_id].append(symbol)
    await update.message.reply_text(t(user_id, 'watch_added', symbol=symbol))


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's watchlist with current prices"""
    user_id = update.effective_user.id
    
    if user_id not in user_watchlists or not user_watchlists[user_id]:
        await update.message.reply_text(t(user_id, 'watchlist_empty'))
        return
    
    message = t(user_id, 'watchlist_header')
    
    for symbol in user_watchlists[user_id]:
        price_data = await get_crypto_price(symbol)
        if price_data:
            change_emoji = "📈" if price_data['change_24h'] >= 0 else "📉"
            change_sign = "+" if price_data['change_24h'] >= 0 else ""
            message += (
                f"**{symbol}:** ${price_data['price']:,.2f} "
                f"{change_emoji} {change_sign}{price_data['change_24h']:.2f}%\n"
            )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove all alerts for a cryptocurrency"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(t(user_id, 'remove_usage'))
        return
    
    symbol = context.args[0].upper()
    
    if user_id in user_alerts and symbol in user_alerts[user_id]:
        del user_alerts[user_id][symbol]
        await update.message.reply_text(t(user_id, 'remove_success', symbol=symbol))
    else:
        await update.message.reply_text(t(user_id, 'remove_not_found', symbol=symbol))
    
    # Also remove from watchlist
    if user_id in user_watchlists and symbol in user_watchlists[user_id]:
        user_watchlists[user_id].remove(symbol)
        await update.message.reply_text(t(user_id, 'remove_watchlist', symbol=symbol))


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change language preference"""
    user_id = update.effective_user.id
    
    # Create inline keyboard with language options
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'),
            InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_lang = get_user_lang(user_id)
    if current_lang == 'en':
        text = "Choose your language:\nВыберите язык:"
    else:
        text = "Выберите язык:\nChoose your language:"
    
    await update.message.reply_text(text, reply_markup=reply_markup)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection from inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'lang_en':
        user_languages[user_id] = 'en'
        await query.edit_message_text(text=t(user_id, 'lang_changed'))
    elif query.data == 'lang_ru':
        user_languages[user_id] = 'ru'
        await query.edit_message_text(text=t(user_id, 'lang_changed'))


async def check_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Background task to check all alerts"""
    for user_id, alerts in list(user_alerts.items()):
        for symbol, alert_list in list(alerts.items()):
            price_data = await get_crypto_price(symbol)
            
            if not price_data:
                continue
            
            current_price = price_data['price']
            alerts_to_remove = []
            
            for idx, (target_price, direction) in enumerate(alert_list):
                triggered = False
                
                if direction == 'above' and current_price >= target_price:
                    triggered = True
                elif direction == 'below' and current_price <= target_price:
                    triggered = True
                
                if triggered:
                    direction_text = t(user_id, direction)
                    message = t(user_id, 'alert_triggered',
                               symbol=symbol,
                               target=target_price,
                               direction=direction_text,
                               current=current_price,
                               time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        alerts_to_remove.append(idx)
                    except Exception as e:
                        logger.error(f"Error sending alert to user {user_id}: {e}")
            
            # Remove triggered alerts
            for idx in sorted(alerts_to_remove, reverse=True):
                alert_list.pop(idx)
            
            # Clean up empty alert lists
            if not alert_list:
                del alerts[symbol]


def load_token() -> str:
    """Load bot token from rr.env file or environment variable"""
    # First, try to load from rr.env file
    env_file = Path(__file__).parent / 'rr.env'
    
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == 'TELEGRAM_BOT_TOKEN':
                            token = value.strip().strip('"').strip("'")
                            if token and token != 'your_actual_token_here':
                                print(f"✅ Token loaded from rr.env file")
                                return token
        except Exception as e:
            logger.warning(f"Could not read rr.env file: {e}")
    
    # Fallback to environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        print("✅ Token loaded from environment variable")
        return token
    
    return None


def main() -> None:
    """Start the bot."""
    # Get token from rr.env file or environment variable
    token = load_token()
    
    if not token:
        logger.error("Please set TELEGRAM_BOT_TOKEN!")
        print("\n❌ Error: TELEGRAM_BOT_TOKEN not found!")
        print("\nPlease add your token to rr.env file:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        print("\nOr set it as environment variable:")
        print("SET TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("alert", alert_command))
    application.add_handler(CommandHandler("list", list_alerts))
    application.add_handler(CommandHandler("watch", watch_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("lang", lang_command))
    
    # Register callback query handler for language selection
    application.add_handler(CallbackQueryHandler(language_callback, pattern='^lang_'))
    
    # Set up background task to check alerts every 60 seconds
    job_queue = application.job_queue
    job_queue.run_repeating(check_alerts, interval=60, first=10)
    
    logger.info("Bot started successfully!")
    print("\n✅ Crypto Alert Bot is running!")
    print("Press Ctrl+C to stop.\n")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
