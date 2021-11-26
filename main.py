#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
from common import handle_btn_press, create_poll
import config
import telebot
bot = telebot.TeleBot(config.token)


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(msg):
    print("dbg1: start or help handled")
    start_text = 'Что бы отправить бро на ретрит,\n' \
                 'ответь на его сообщение текстом "!ретритнись"\n' \
                 'Сообщить о своём действии можно так:\n' \
                 '"/me медитирует"'
    bot.send_message(msg.chat.id, start_text)


@bot.message_handler(commands=["mute"])
def handle_mute(msg):
    from_user = msg.reply_to_message.from_user.id
    print("dbg: try to mute: {}".format(from_user))
    # TODO d set max mute time un unixtime
    if int(msg.from_user.id) == 611317205:
        bot.restrict_chat_member(msg.chat.id, from_user, can_send_messages=False)
        bot.send_message(msg.chat.id, "{} отправился медитировать в тишине.".format(from_user))


@bot.message_handler(commands=["unmute"])
def handle_unmute(msg):
    from_user = msg.reply_to_message.from_user.id
    print("dbg: try to unmute: {}".format(from_user))
    # TODO d set max mute time un unixtime
    if int(msg.from_user.id) == 611317205:
        bot.restrict_chat_member(msg.chat.id, from_user, can_send_messages=True, can_send_polls=True, can_send_media_messages=True, can_send_other_messages=True)
        bot.send_message(msg.chat.id, "{} возвращается из медитативной тишины.".format(from_user))


@bot.message_handler(commands=['me'])
def handle_me(msg):
    text = msg.text.split("/me")[1].lstrip()
    print(text)
    me = "{} {}".format(msg.from_user.first_name, text)
    bot.send_message(msg.chat.id, me)
    bot.delete_message(msg.chat.id, msg.id)


@bot.message_handler(content_types=["text"])
def handle_commands(msg):
    # print('dbg1: some event handled {}'.format(msg.chat.id))
    # TODO проверить, что это реплай, если нет, ответить, что нужен реплай
    # TODO искать подстроку, а не полное соотвветсвие
    mtext = msg.text.lower()
    if '!ретритнись' in mtext or '!ретрит' in mtext or '!р ' in mtext:
        print('dbg2: need poll')
        bot.send_message(msg.chat.id, 'Уже читаю мантры')
        time.sleep(0.5)  # for humanityzm
        if msg.reply_to_message.from_user.first_name is None:
            from_user = msg.reply_to_message.from_user.username
        else:
            from_user = msg.reply_to_message.from_user.first_name
        create_poll(msg, from_user)
        # next_step need some long time or not work correctly
        # bot.register_next_step_handler(msg, create_poll, from_user)


@bot.callback_query_handler(func=lambda call: True)
def check_all_messages(msg):
    print('dbg1: key pressed')
    print(msg)
    handle_btn_press(msg.message.chat.id, msg.data, msg.from_user.id, msg.message.text)


if __name__ == '__main__':
    print('{} started.'.format(config.botname))
    while True:
        try:
            bot.polling(none_stop=True)
        except requests.exceptions.ReadTimeout as e:
            print("Err in Polling: {}".format(e))
        except Exception as e:
            print("ERROR in Polling: {}".format(e))
