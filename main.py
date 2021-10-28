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
    text = msg.text.split("/me")[1].lstrip()
    print(text)
    me = "{} {}".format(msg.from_user.first_name, text)
    bot.send_message(msg.chat.id, me)
    bot.delete_message(msg.chat.id, msg.id)


@bot.message_handler(content_types=["text"])
def handle_commands(msg):
    print('dbg1: some event handled')
    # TODO проверить, что это реплай, если нет, ответить, что нужен реплай
    # TODO искать подстроку, а не полное соотвветсвие
    mtext = msg.text.lower()
    if mtext == '!ретритнись' or mtext == '!ретрит' or mtext == '!р':
        print('dbg2: need poll')
        bot.send_message(msg.chat.id, 'Уже читаю мантры')

        if msg.reply_to_message.from_user.first_name is None:
            from_user = msg.reply_to_message.from_user.username
        else:
            from_user = msg.reply_to_message.from_user.first_name

        # bot.register_next_step_handler(msg, create_poll, from_user)
        # time.sleep(0.5)  # for humanityzm
        create_poll(msg, from_user)


@bot.callback_query_handler(func=lambda call: True)
def check_all_messages(msg):
    print('dbg1: key pressed')
    print(msg)
    handle_btn_press(msg.message.chat.id, msg.data, msg.from_user.id, msg.message.text)


def handle_btn_press(chat_id, btn_callback, from_user, text):
    print("dbg2: try to register keypress: {}".format(btn_callback))
    variant = session.query(Variants).\
        filter(Variants.variant_callback == btn_callback).first()
    poll_id = variant.poll_id
    print("dbg2.1: poll ID: {}".format(poll_id))
    voted = session.query(Voters).\
        filter(and_(Voters.poll_id == poll_id,
                    Voters.user_id == from_user)).first()

    if voted is None:
        print("dbg2.1: User not voted in this poll, try register and update kbd")
        cb_y, cb_n, poll = vote_in_poll(poll_id, from_user, variant)
        send_kbd(chat_id, text, cb_y, cb_n, poll_id)


def vote_in_poll(poll_id, from_user, variant):
    print("dbg3: register vote")
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

    return cb_y, cb_n, poll


def create_poll(msg, user):
    print("dbg2.5: try create poll")
    caption = '{} отправляется на випассану?'.format(user)
    poll_id = str(msg.chat.id) + str(msg.message_id)
    cb_yes, cb_no = create_poll_in_db(msg.chat.id, poll_id)
    send_kbd(msg.chat.id, caption, cb_yes, cb_no, poll_id)


def send_kbd(chat_id, caption, cb_yes, cb_no, pid):
    print("dbg3: try to send kbd | poll PID: {}".format(pid))
    poll = session.query(Polls).filter(Polls.pid == pid).first()
    if poll is None:
        poll = session.query(Polls).filter(Polls.id == pid).first()
    mrkp = telebot.types.InlineKeyboardMarkup(row_width=1)
    if poll is None:
        print("dbg3.1: no poll, setting buttons to zero")
        yes_count, no_count = 0, 0
    else:
        print("dbg3.1: have poll")
        yes_count, no_count = poll.yes_count, poll.no_count

    btn_yes = telebot.types.InlineKeyboardButton(text='Да ({})'.format(yes_count), callback_data=cb_yes)
    mrkp.add(btn_yes)
    btn_no = telebot.types.InlineKeyboardButton(text='Нет ({})'.format(no_count), callback_data=cb_no)
    mrkp.add(btn_no)
    # If new than send, else edit
    if (yes_count == 0 and no_count == 0) and (cb_yes or cb_no):
        new_poll = bot.send_message(chat_id=chat_id,
                                    reply_markup=mrkp,
                                    text=caption)
        poll.pid = new_poll.id
        session.commit()
        print("dbg3.2 new poll: {}".format(new_poll))
    else:
        pid = str(poll.pid)
        print('dbg3.2 pid: {} {}, {}'.format(pid, type(pid), chat_id))
        # poll_id = pid.split(str(chat_id))[1]
        poll_id = pid.split(str(chat_id))
        print("dbg3.3: editting msg: {}".format(poll_id))
        bot.edit_message_text(chat_id=chat_id,
                              message_id=poll_id,
                              reply_markup=mrkp,
                              text=caption)


def create_poll_in_db(caption, poll_id):
    try:
        last_id = session.query(Polls.id).order_by(Polls.id.desc()).first()[0]
    except Exception as e:
        print('Ошибка при Создании голосования\n{}'.format(e))
        last_id = 1

    callback_yes = callback_generator()
    callback_no = callback_generator()

    poll_row = Polls(id=int(last_id)+1,
                     pid=poll_id,
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
