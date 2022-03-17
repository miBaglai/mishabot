#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to send timed Telegram messages.

This Bot uses the Updater class to handle the bot and the JobQueue to send
timed messages.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Alarm Bot example, sends a message after a set time.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from multiprocessing import context

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

from examples.conversationbot2 import CHOOSING
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__) 

RECESS , WORK , CHOOSING = range(3)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
# Best practice would be to replace context with an underscore,
# since context is an unused local variable.
# This being an example and not having context present confusing beginners,
# we decided to have it present as context.
def start(update: Update, context: CallbackContext) -> None:
    """Sends explanation on how to use the bot."""
    update.message.reply_text('Hi! Use /set <seconds> to set a timer.\n Use /work to start timer.')


def alarm(context: CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    context.bot.send_message(job.context, text='Beep!')


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def set_timer(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(alarm, due, context=chat_id, name=str(chat_id))

        text = 'Timer successfully set!'
        if job_removed:
            text += ' Old one was removed.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


def unset(update: Update, context: CallbackContext) -> None:        
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Timer successfully cancelled!' if job_removed else 'You have no active timer.'
    update.message.reply_text(text)

# Начало работы. установка первоначального таймера, после чего вопрос о продолжении

def work_start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    #update.message.reply_text('Началось! пошел таймер на 25 мин')
    #context.job_queue.run_once(recess_alarm, 3, context=chat_id, name=str(chat_id))    
    #context.user_data['job_timer'].update({'job_timer': []})
    reply_keyboard = [
    ['10', '15'],
    ['20', '25'],
    ['back']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text('На сколько поставить таймер?', reply_markup=markup)
    return WORK

def work_alarm(context: CallbackContext) -> int:
    """Asks about a pause"""
    #reply_keyboard = [['Делаю перерыв на 5 мин', 'Хватит на пока']]
    reply_keyboard = [['5', 'back']]
    job = context.job
    #jobtimer = context.user_data.get('job_timer', 'Not found')
    context.bot.send_message(job.context[0], text=f'Beep! Ты поработал {job.context[1]} минут.')
    update = job.context[2]
    update.message.reply_text(
        'Надо сделать перерыв на 5 мин. Разумеешь? Размяться.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return RECESS 

def work(update: Update, context: CallbackContext) -> int:
    logger.info("Timer of %s: %s", update.message.from_user.first_name, update.message.text)
    chat_id = update.message.chat_id
    timer_min = update.message.text
    context.user_data['job_timer'] = timer_min
    print('Записалось значение: ',context.user_data['job_timer'])
    update.message.reply_text(f'Началось! пошел таймер на {timer_min} мин', reply_markup=ReplyKeyboardRemove())
    context.job_queue.run_once(work_alarm, int(timer_min),context = [chat_id, timer_min, update], name=str(chat_id))  
    return RECESS

def recess(update: Update, context: CallbackContext) -> int:
    logger.info("Timer of %s: %s", update.message.from_user.first_name, update.message.text)
    chat_id = update.message.chat_id
    recess_timer = update.message.text
    context.user_data['recess_timer'] = recess_timer
    print('Записалось значение: ',context.user_data['recess_timer'])
    update.message.reply_text(f'Началcя перерыв! пошел таймер на {recess_timer} мин', reply_markup=ReplyKeyboardRemove())
    context.job_queue.run_once(recess_alarm, int(recess_timer),context = [chat_id, recess_timer, update], name=str(chat_id))  
    return WORK

def recess_alarm(context: CallbackContext) -> int:
    """Asks about work"""
    reply_keyboard = [
    ['10', '15'],
    ['20', '25'],
    ['back']]
    job = context.job
    context.bot.send_message(job.context[0], text=f'Beep! Ты отдохнул {job.context[1]} минут.')
    update = job.context[2]
    update.message.reply_text(
        'Можно продолжать работать. На сколько таймер?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return WORK     

def main() -> None:
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater("TOKEN")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Create user_data with timers
    #job_timer = {}
    #context.user_data.update(job_timer)

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("set", set_timer))
    dispatcher.add_handler(CommandHandler("unset", unset))
    #dispatcher.add_handler(CommandHandler("work", work_start))

    worktime_handler = ConversationHandler(
        entry_points=[CommandHandler("work", work_start)],
        states={
            WORK: [MessageHandler(Filters.regex('[0-9]+'), work), MessageHandler(Filters.regex('^back$'), work_start)],
            RECESS: [MessageHandler(Filters.regex('[0-9]+'), recess), MessageHandler(Filters.regex('^back$'), work_start)],
            CHOOSING: [],
            #BIG_RECESS: [MessageHandler()],
            #WORK: [MessageHandler()],
        },
        fallbacks=[CommandHandler('stop', ConversationHandler.END)]
    )

    dispatcher.add_handler(worktime_handler)


    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()