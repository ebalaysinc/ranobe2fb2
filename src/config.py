import argparse

parser = argparse.ArgumentParser(description="")
parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
)

DEBUG = parser.parse_args().debug

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
