import datetime
from config import DEBUG


class Logger:
    def __init__(self, prefix):
        self.prefix = prefix
        self.init_time = str(datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))

    def write(self, message):
        if DEBUG:
            with open("logs/log" + self.init_time + ".txt", 'a') as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [{self.prefix}] {message}\n")