import time
from datetime import datetime, timedelta
import config
import telebot
import random
import string
from db import engine, Polls, Voters, Variants
from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker, scoped_session

session = scoped_session(sessionmaker(bind=engine))
bot = telebot.TeleBot(config.token)


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
        poll.yes_count += 1
        cb_y = variant.variant_callback
        cb_n = session.query(Variants.variant_callback).\
            filter(and_(Variants.poll_id == poll_id,
                        Variants.yes_no == 'no')).first()[0]

    elif variant.yes_no == 'no':
        poll.no_count += 1
        cb_y = session.query(Variants.variant_callback).\
            filter(and_(Variants.poll_id == poll_id,
                        Variants.yes_no == 'yes')).first()[0]
        cb_n = variant.variant_callback

    voted_now = Voters(poll_id=poll_id,
                       variant=variant.yes_no,
                       user_id=from_user)
    session.add(voted_now)
    session.commit()

    return cb_y, cb_n, poll


def create_poll(msg, user):
    print("dbg2.5: try create poll")
    caption = '{} отправляется на випассану?'.format(user)
    from_user_id = msg.reply_to_message.from_user.id
    poll_id = str(msg.chat.id) + str(msg.message_id)
    cb_yes, cb_no = create_poll_in_db(msg.chat.id, poll_id, from_user_id)
    send_kbd(msg.chat.id, caption, cb_yes, cb_no, poll_id, from_user_id)


def send_kbd(chat_id, caption, cb_yes, cb_no, pid, restricted_user=0):
    print("dbg3: try to send kbd | poll PID: {}".format(pid))
    poll, yes_count, no_count = check_poll_exist(pid)
    print("dbg3.1: yes {} no {}".format(yes_count, no_count))
    mrkp = telebot.types.InlineKeyboardMarkup(row_width=2)
    # TODO refactor all next to separate function
    max_votes = 3
    if yes_count + no_count >= max_votes:
        mrkp.add()  # remove buttons
        if yes_count > no_count:
            if restricted_user == 0:
                poll = session.query(Polls).\
                        filter(pid == pid).first()
                restricted_user = poll.user_id
            try:
                until_time = datetime.now() + timedelta(hours=1)
                bot.restrict_chat_member(chat_id, restricted_user, can_send_messages=False, until_date=until_time)
                caption = "Голосование закончилось. {} отправляется на ретрит. {}".format(restricted_user, until_time)
            except Exception as e:
                print("dbg3.1.1: can't restrict: {}".format(e))
                caption = "Голосова...ие за...сь... Что-то пошло не так..."
        else:
            caption = "Голосование закончилось. Ретрит отменяется"

    else:
        btn_yes = telebot.types.InlineKeyboardButton(text='Да ({})'.format(yes_count), callback_data=cb_yes)
        btn_no = telebot.types.InlineKeyboardButton(text='Нет ({})'.format(no_count), callback_data=cb_no)
        mrkp.add(btn_yes, btn_no)

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
        poll_id = int(pid.split(str(chat_id))[0])
        # poll_id = pid.split(str(chat_id))
        print("dbg3.3: editting msg: {}".format(poll_id))
        bot.edit_message_text(chat_id=chat_id,
                              message_id=poll_id,
                              reply_markup=mrkp,
                              text=caption)


def check_poll_exist(pid):
    poll = session.query(Polls).filter(Polls.pid == pid).first()
    if poll is None:
        poll = session.query(Polls).filter(Polls.id == pid).first()

    if poll is None:
        print("dbg3.2: no poll, setting buttons to zero")
        yes_count, no_count = 0, 0
    else:
        print("dbg3.2: have poll")
        yes_count, no_count = poll.yes_count, poll.no_count

    return poll, yes_count, no_count


def create_poll_in_db(caption, poll_id, ruser):
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
                     no_count=0,
                     user_id=ruser)
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
