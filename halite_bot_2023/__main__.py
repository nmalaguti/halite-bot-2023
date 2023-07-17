import logging
import sys

logger = logging.getLogger(__name__)

logging.basicConfig(
    filename="bot.log", format="%(asctime)s %(message)s", level=logging.DEBUG
)

try:
    from . import bot
except:
    logger.exception("Unhandled Exception")
    sys.exit(1)
