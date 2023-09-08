import curses
import locale
import telnetlib
import re

HOST = "koukoku.shadan.open.ad.jp"
PORT = 23

tn = telnetlib.Telnet(HOST, PORT)
tn.write('notalk\n'.encode('shift_jis'))
tn_chat = telnetlib.Telnet(HOST, PORT)
tn_chat.write('nobody\n'.encode('shift_jis'))

def show_user_chat(chat_win, chat_messages, chat_win_height):
    chat_win.clear()
    chat_win.border()
    chat_win.addstr(0, 2, " Chat Message ")
    chat_win.refresh()
    for y, s in enumerate(chat_messages):
        chat_win.addstr(y + 1, 1, s)
    chat_win.refresh()


def show_server_message(text_win, receive_message, text_win_height):
    try:
        showing_receive_messages = receive_message.split('\r\n')
        text_win.clear()
        if len(showing_receive_messages) > text_win_height:
            for y, s in enumerate(showing_receive_messages[len(showing_receive_messages) - text_win_height:]):
                text_win.addstr(y, 1, s)
        else:
            for y, s in enumerate(showing_receive_messages):
                text_win.addstr(y, 1, s)
        text_win.refresh()
    except curses.error:
        pass
    except UnicodeDecodeError:
        pass

def clear_input_win(input_win):
    input_win.clear()
    input_win.border()
    input_win.addstr(1, 1, "Input: ")
    input_win.refresh()

def add_message_to_input_win(input_win, c):
    input_win.addstr(c)
    input_win.refresh()


def is_input_delete_key(c):
    return c == curses.KEY_BACKSPACE or c == '\x08' or c == '\x7f'


def delete_message_to_input_win(input_win, message):
    y, x = input_win.getyx()
    if x > 7:
        input_win.move(1, x-1)
        input_win.clrtoeol()
        input_win.border()
        input_win.addstr(1, 1, f"Input: {message}")
    input_win.refresh()


def send_message_to_server(message):
    tn_chat.write((f'{message}\n').encode('shift_jis'))


def main(stdscr):
    receive_message = ''
    message = ''
    chat_messages = []

    locale.setlocale(locale.LC_ALL, '')
    curses.nl()
    curses.raw()

    curses.encoding = 'UTF-8'
    
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()

    h, w = stdscr.getmaxyx()

    # 公告表示欄
    text_win_height = h - 15
    text_win = curses.newwin(text_win_height, w, 0, 0)

    # チャット表示欄
    chat_win_height = 9
    chat_win = curses.newwin(chat_win_height, w, h - 12, 0)

    # 入力欄
    input_win = curses.newwin(3, w, h-3, 0)
    input_win.border()
    input_win.addstr(0, 2, " Input ")
    input_win.addstr(1, 1, "Input: ")
    input_win.nodelay(1)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    while True:
        chat_chunk = tn_chat.read_eager()
        if chat_chunk:
            if len(chat_messages) > 6:
                chat_messages = chat_messages[1:]
            try:
                chat_messages.append(ansi_escape.sub('', chat_chunk.decode('shift_jis').replace('\r', '').replace('\n', '')))
            except UnicodeDecodeError:
                pass
            show_user_chat(chat_win, chat_messages, chat_win_height)
        chunk = tn.read_some()
        if chunk:
            try:
                decoded_chunk = chunk.decode('shift_jis')
                receive_message += decoded_chunk
                receive_message = ansi_escape.sub('', receive_message)
                show_server_message(text_win, receive_message, text_win_height)
            except UnicodeDecodeError:
                pass
        try:
            c = input_win.get_wch()
            if c == '\n':
                if message == 'exit':
                    tn.close()
                    tn_chat.close()
                    break

                send_message_to_server(message)

                message = ""
                clear_input_win(input_win)
            elif is_input_delete_key(c):
                message = message[:-1]
                delete_message_to_input_win(input_win, message)
            elif c != curses.ERR:
                message += str(c)
                add_message_to_input_win(input_win, str(c))
        except curses.error:
            pass

curses.wrapper(main)


