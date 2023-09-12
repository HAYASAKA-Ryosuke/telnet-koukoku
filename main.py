import curses
import locale
import telnetlib
import re

HOST = "koukoku.shadan.open.ad.jp"
PORT = 23
ENCODING = 'shift_jis'


class PublicNoticeTelnetClient:
    def __init__(self, host, port):
        self.__connection = telnetlib.Telnet(host, port)
        self.__connection.write('notalk\n'.encode(ENCODING))
        
    def write(self, message):
        self.__connection.write(message.encode(ENCODING))
        
    def read(self):
        return self.__connection.read_eager()
    
    def close(self):
        self.__connection.close()


class ChatTelnetClient:
    def __init__(self, host, port):
        self.__connection = telnetlib.Telnet(host, port)
        self.__connection.write('nobody\n'.encode(ENCODING))
        
    def write(self, message):
        self.__connection.write(message.encode(ENCODING))
        
    def read(self):
        return self.__connection.read_eager()
    
    def close(self):
        self.__connection.close()


class PublicNoticeWindow:
    def __init__(self, height, width, start_y, start_x):
        self.__window = curses.newwin(height, width, start_y, start_x)
        self.height = height
    
    def show_messages(self, messages):
        self.__window.clear()
        self.__window.refresh()
        if len(messages) > self.height:
            for y, s in enumerate(messages[len(messages) - self.height:]):
                self.__window.addstr(y, 1, s)
        else:
            for y, s in enumerate(messages):
                self.__window.addstr(y, 1, s)
        self.__window.refresh()


class ChatViewWindow:
    def __init__(self, height, width, starty, startx):
        self.position = 0
        self.__window = curses.newwin(height, width, starty, startx)

    def increment_position(self, messages_length):
        h, _ = self.__window.getmaxyx()
        if self.position < messages_length - (h - 2) - 1:
            self.position += 1

    def decrement_position(self):
        if self.position > 0:
            self.position -= 1
    
    def show_messages(self, messages, title=" Chat Message "):
        self.__window.clear()
        self.__window.border()
        self.__window.addstr(0, 2, title)
        self.__window.refresh()
        h, _ = self.__window.getmaxyx()
        if len(messages) > h - 2:
            for y, s in enumerate(messages[len(messages) - (h - 2) - self.position:len(messages) - self.position]):
                self.__window.addstr(y + 1, 1, s)
        else:
            self.position = 0
            for y, s in enumerate(messages):
                self.__window.addstr(y + 1, 1, s)
        self.__window.refresh()
        

class InputWindow:
    def __init__(self, height, width, starty, startx):
        self.__window = curses.newwin(height, width, starty, startx)
        self.__window.keypad(True)
        self.height = height
        self.__init_ui()
    
    def __init_ui(self):
        self.__window.clear()
        self.__window.border()
        self.__window.addstr(0, 2, " Input Message ")
        self.__window.addstr(1, 1, "Input: ")
        self.__window.nodelay(1)
        
    def update_message(self, message):
        self.__init_ui()
        self.__window.addstr(1, 1, f"Input: {message}")
        self.__window.refresh()
        
    def get_wch(self):
        return self.__window.get_wch()
    

class Application:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.chat_messages = []
        self.receive_message = ''
        self.message = ''
        self.public_notice_telnet_client = PublicNoticeTelnetClient(HOST, PORT)
        self.chat_telnet_client = ChatTelnetClient(HOST, PORT)
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self.init_ui()
        
    def init_ui(self, chat_view_win_height=10):
        locale.setlocale(locale.LC_ALL, '')
        curses.nl()
        curses.raw()
        curses.curs_set(0)
        self.stdscr.clear()
        self.stdscr.refresh()
        
        h, w = self.stdscr.getmaxyx()

        input_win_height = 3  # 入力欄(入力[1行]+枠[2行])

        # 入力欄(3行)+チャットメッセージ表示欄(chat_view_win_height+枠[2行])+公告の下部マージン(1行)を除いた残りすべてを公告表示欄とする
        public_notice_win_height = h - (chat_view_win_height + input_win_height + 2) - 1
        self.public_notice_win = PublicNoticeWindow(public_notice_win_height, w, 0, 0)

        self.chat_view_win = ChatViewWindow(chat_view_win_height + 2, w, h - (chat_view_win_height + input_win_height + 2), 0)
        self.input_win = InputWindow(input_win_height, w, h-input_win_height, 0)
    
    def send_message_to_server(self):
        self.chat_telnet_client.write(f'{self.message}\n')

    def show_chat_messages(self, chat_chunk):
        if chat_chunk:
            try:
                self.chat_messages.append(self.ansi_escape.sub('', chat_chunk.decode(ENCODING).replace('\r', '').replace('\n', '')))
            except UnicodeDecodeError:
                pass
            self.chat_view_win.show_messages(re.compile(r'>>\s*(.*?)\s*<<').findall(''.join(self.chat_messages)))

    def show_public_notice(self, public_notice_chunk):
        if public_notice_chunk:
            try:
                decoded_chunk = public_notice_chunk.decode(ENCODING)
                self.receive_message += decoded_chunk
                self.receive_message = self.ansi_escape.sub('', self.receive_message)
                self.public_notice_win.show_messages(self.receive_message.split('\r\n'))
            except UnicodeDecodeError:
                pass

    def is_input_delete_key(self, c):
        return c == curses.KEY_BACKSPACE or c == '\x08' or c == '\x7f'

    def input_control(self) -> bool:
        ENTER = '\n'
        EXIT = 'exit'

        try:
            c = self.input_win.get_wch()
            if c == ENTER:
                if self.message == EXIT:
                    return True
                else:
                    self.sending_message()
            elif c == curses.KEY_UP:
                self.chat_view_win.increment_position(len(self.chat_messages))
                self.chat_view_win.show_messages(re.compile(r'>>\s*(.*?)\s*<<').findall(''.join(self.chat_messages)))
            elif c == curses.KEY_DOWN:
                self.chat_view_win.decrement_position()
                self.chat_view_win.show_messages(re.compile(r'>>\s*(.*?)\s*<<').findall(''.join(self.chat_messages)))
            elif self.is_input_delete_key(c):
                self.message = self.message[:-1]
                self.input_win.update_message(self.message)
            elif c != curses.ERR:
                self.message += str(c)
                self.input_win.update_message(self.message)
        except curses.error:
            pass
        return False 
    
    def sending_message(self):
        self.send_message_to_server()
        self.message = ""
        self.input_win.update_message(self.message)
        
    def exit(self):
        self.public_notice_telnet_client.close()
        self.chat_telnet_client.close()

    def run(self):
        while True:
            chat_chunk = self.chat_telnet_client.read()
            self.show_chat_messages(chat_chunk)

            public_notice_chunk = self.public_notice_telnet_client.read()
            self.show_public_notice(public_notice_chunk)

            is_exit = self.input_control()
            if is_exit:
                self.exit()
                break

def main(stdscr):
    app = Application(stdscr)
    app.run()


curses.wrapper(main)
