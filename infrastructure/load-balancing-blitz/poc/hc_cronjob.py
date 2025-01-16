import logging
import time

from .system_health import get_system_health


LOGFILE = "/tmp/flask_app_cronjob.log"

logging.basicConfig(
    filename=LOGFILE,
    format="%(asctime)s - %(message)s",
    # filemode="w",
    level=logging.INFO,
)


def send_hc_message_to_pubsub():
    # 1. Check if server is running
    # 2. Check if the config is enabled for Cron Job
    # 3. Collect the load Statistics
    # 4. Post the load stats it PubSub
    raise NotImplementedError("TODO(sampathm)")


def main():
    system_health = get_system_health()
    logging.info(f"system health: {str(system_health)}")
    try:
        logging.debug("Sending system_health to Pub/Sub ")
        send_hc_message_to_pubsub()
    except Exception as e:
        print(e)
        logging.error("Exception occurred", exc_info=True)


if __name__ == "__main__":
    logging.debug("#" * 50)
    logging.debug("Running HC Report")
    try:
        while True:
            main()
            time.sleep(5)
    except Exception as e:
        print(e)
        logging.error("Exception occurred", exc_info=True)
    logging.debug("Running HC Report,.. completed!")
