#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config
import telebot
import time
import random
import string
from db import engine, Polls, Voters, Variants
from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker, scoped_session

session = scoped_session(sessionmaker(bind=engine))
bot = telebot.TeleBot(config.token)


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(msg):
    start_text = 'Что бы отправить бро на ретрит, ответь на его сообщение текстом !ретритнись'
    bot.send_message(msg.chat.id, start_text)


@bot.message_handler(commands=['me'])
def handle_me(msg):
    text = msg.text.split("/me")[1]
    print(text)
    me = "{} {}".format(msg.from_user.first_name, text)
    bot.send_message(msg.chat.id, me)
    bot.delete_message(msg.chat.id, msg.id)


@bot.message_handler(content_types=["text"])
def handle_commands(msg):
    # print('dbg1: some event handled')
    if msg.text.lower() == '!ретритнись':
        print('dbg2: new poll')
        bot.send_message(msg.chat.id, 'Уже читаю мантры')
        time.sleep(0.5)  # for humanityzm
        if msg.reply_to_message.from_user.first_name is None:
            user = msg.reply_to_message.from_user.username
        else:
            user = msg.reply_to_message.from_user.first_name
        create_poll(msg.chat.id, user, msg.message_id)


@bot.callback_query_handler(func=lambda call: True)
def check_all_messages(msg):
    print('dbg2: key pressed')
    print(msg)
    handle_btn_press(msg.message.chat.id, msg.data, msg.from_user.id, msg.message.message_id)


def handle_btn_press(chat_id, btn_callback, from_user, msg_id):
    variant = session.query(Variants).\
        filter(Variants.variant_callback == btn_callback).first()
    poll_id = variant.poll_id

    voted = session.query(Voters).\
        filter(and_(Voters.poll_id == poll_id,
                    Voters.user_id == from_user)).first()
    if voted is None:
        vote_in_poll(poll_id, from_user, variant)


def vote_in_poll(poll_id, from_user, variant):
    poll = session.query(Polls).filter(Polls.id == poll_id).first()
    if variant.yes_no == 'yes':
        voted_now = Voters(poll_id=poll_id,
                           variant='yes',
                           user_id=from_user)
        poll.yes_count += 1
        cb_y = variant.variant_callback
        cb_n = session.query(Variants.variant_callback).\
            filter(and_(Variants.poll_id == poll_id,
                        Variants.yes_no == 'no')).first()[0]

    elif variant.yes_no == 'no':
        voted_now = Voters(poll_id=poll_id,
                           variant='no',
                           user_id=from_user)
        poll.no_count += 1
        cb_y = session.query(Variants.variant_callback).\
            filter(and_(Variants.poll_id == poll_id,
                        Variants.yes_no == 'yes')).first()[0]
        cb_n = variant.variant_callback

    session.add(voted_now)
    session.commit()

    send_kbd(chat_id, msg_id, cb_y, cb_n, poll)


def create_poll(chat_id, user, poll_id):
    caption = '{} отправляется на випассану?'.format(user)
    cb_yes, cb_no = create_poll_in_db(chat_id, poll_id)
    send_kbd(chat_id, caption, cb_yes, cb_no)


def send_kbd(chat_id, caption, cb_yes, cb_no, poll=None):
    mrkp = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_yes = telebot.types.InlineKeyboardButton(text='Да', callback_data=cb_yes)
    mrkp.add(btn_yes)
    btn_no = telebot.types.InlineKeyboardButton(text='Нет', callback_data=cb_no)
    mrkp.add(btn_no)
    if isinstance(caption, str):
        bot.send_message(chat_id, caption, reply_markup=mrkp)
    else:
        bot.edit_message_text(chat_id=chat_id,
                              message_id=caption,
                              reply_markup=mrkp,
                              text="{}\nЗа - {}\nПротив - {}".format(poll.text, poll.yes_count, poll.no_count))


def create_poll_in_db(caption, chat_id, polls_id=None):
    try:
        last_id = session.query(Polls.id).order_by(Polls.id.desc()).first()[0]
    except Exception as e:
        print('Ошибка при Создании голосования\n{}'.format(e))
        last_id = 1

    callback_yes = callback_generator()
    callback_no = callback_generator()

    poll_row = Polls(id=int(last_id)+1,
                     text=caption,
                     yes_count=0,
                     no_count=0)
    variant_yes = Variants(poll_id=int(last_id)+1,
                           variant_callback=callback_yes,
                           yes_no='yes')
    variant_no = Variants(poll_id=int(last_id)+1,
                          variant_callback=callback_no,
                          yes_no='no')

    session.add(poll_row)
    session.add(variant_yes)
    session.add(variant_no)
    session.commit()

    return callback_yes, callback_no


def callback_generator(size=8, chars=string.ascii_uppercase + string.digits):
    hash = ''.join(random.choice(chars) for _ in range(size))
    if hash in session.query(Variants).all():
        hash = callback_generator(size=9)
    return hash


if __name__ == '__main__':
    print('{} started.'.format(config.botname))
    bot.polling(none_stop=True)
