import datetime
from config import DEBUG


class Logger:
    """
    Logger class
    """

    def __init__(self, prefix: str):
        """
        Initialization of a class

        Args:
            prefix(str): prefix used in logs
        """
        self.prefix = prefix
        self.init_time = str(datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))

    def write(self, message: str) -> None:
        """
        Logging as "[time] [prefix] message" if debug enabled

        Args:
            message (str): message
        """
        
        if DEBUG:
            with open("logs/log" + self.init_time + ".txt", 'a') as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] [{self.prefix}] {message}\n")
