import logging

from django.contrib.auth.signals import user_login_failed

logger = logging.getLogger(__name__)


def log_user_login_failure(sender, credentials, **kwargs):
    """Signal for user login failure"""
    logger.info("User login failed: {}".format(credentials.get("username")))


user_login_failed.connect(log_user_login_failure)
