import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from multiprocessing import Process

import requests
from slackbot.slackclient import SlackClient

from . import job_configs, scheduler, settings
from .logger import logger


def run():  # pragma: no cover
    """Start the dispatcher running."""

    slack_client = SlackClient(settings.SLACKBOT_API_TOKEN)

    while True:
        run_once(slack_client, job_configs.config)
        time.sleep(1)


def run_once(slack_client, config):
    """Clear any expired suppressions, then start a new subprocess for each
    available job.

    We collect and return started processes so that we can wait for them to
    finish in tests before asserting the tests have done anything.
    """

    scheduler.remove_expired_suppressions()

    processes = []

    while True:
        job_id = scheduler.reserve_job()
        if job_id is None:
            break
        job_dispatcher = JobDispatcher(slack_client, job_id, config)
        processes.append(job_dispatcher.start_job())

    return processes


class JobDispatcher:
    def __init__(self, slack_client, job_id, config):
        logger.info("starting job", job_id=job_id)
        self.slack_client = slack_client
        self.job = scheduler.get_job(job_id)

        namespace = self.job["type"].split("_")[0]
        self.cwd = os.path.join(settings.WORKSPACE_DIR, namespace)
        self.fabfile_url = config["fabfiles"].get(namespace)

        job_config = config["jobs"][self.job["type"]]
        self.run_args = build_run_args(
            job_config["run_args_template"], self.job["args"]
        )
        self.report_stdout = bool(job_config.get("report_stdout"))

    def start_job(self):
        """Start running the job in a new subprocess."""

        p = Process(target=self.do_job)
        p.start()
        return p

    def do_job(self):
        """Run the job."""

        self.set_up_cwd()
        self.set_up_log_dir()
        self.notify_start()
        rc = self.run_command()
        scheduler.mark_job_done(self.job["id"])
        self.notifiy_end(rc)

    def run_command(self):
        """Run the bash command, writing stdout/stderr to separate files."""

        logger.info("run_command {")
        logger.info(
            "run_command",
            job=self.job,
            run_args=self.run_args,
            cwd=self.cwd,
            stdout_path=self.stdout_path,
            stderr_path=self.stdout_path,
        )

        with open(self.stdout_path, "w") as stdout, open(
            self.stderr_path, "w"
        ) as stderr:
            try:
                rv = subprocess.run(
                    self.run_args, cwd=self.cwd, stdout=stdout, stderr=stderr
                )
                rc = rv.returncode
            except Exception as e:
                rc = -1
                stderr.write(str(e) + "\n")

        logger.info("run_command", rc=rc)
        logger.info("run_command }")
        return rc

    def notify_start(self):
        """Send notification that command is about to start."""

        msg = "Command `{}` about to start".format(self.job["type"])
        notify_slack(self.slack_client, settings.SLACK_LOGS_CHANNEL, msg)

    def notifiy_end(self, rc):
        """Send notification that command has ended, reporting stdout if
        required."""

        if rc == 0:
            if self.report_stdout:
                with open(self.stdout_path) as f:
                    msg = f.read()
            else:
                msg = "Command `{}` succeeded".format(self.job["type"])
        else:
            msg = "Command `{}` failed (find logs in {})".format(
                self.job["type"], self.log_dir
            )

        notify_slack(self.slack_client, self.job["slack_channel"], msg)

    def set_up_cwd(self):
        """Ensure cwd exists, and maybe refresh fabfile."""

        os.makedirs(self.cwd, exist_ok=True)

        if self.fabfile_url:  # pragma: no cover
            self.update_fabfile()

    def update_fabfile(self):  # pragma: no cover
        """Retreive latest version of fabfile.py, notifying Slack if this fails.

        Not tested out of developer laziness.
        """

        try:
            rsp = requests.get(self.fabfile_url)
            rsp.raise_for_status()
        except requests.RequestException as e:
            msg = "Could not refresh {}: {}".format(self.fabfile_url, str(e))
            notify_slack(self.slack_client, settings.SLACK_LOGS_CHANNEL, msg)
            return

        with open(os.path.join(self.cwd, "fabfile.py"), "w") as f:
            f.write(rsp.text)

    def set_up_log_dir(self):
        """Create directory for recording stdout/stderr."""

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.log_dir = os.path.join(settings.LOGS_DIR, self.job["type"], timestamp)
        self.stdout_path = os.path.join(self.log_dir, "stdout")
        self.stderr_path = os.path.join(self.log_dir, "stderr")
        os.makedirs(self.log_dir)


def build_run_args(run_args_template, job_args):
    """Interpolate job_args into run_args_template, and split into tokens."""

    return shlex.split(run_args_template.format(**job_args))


def notify_slack(slack_client, channel, message):
    """Send message to Slack."""

    logger.info("Sending message", channel=channel, message=message)
    slack_client.send_message(channel, message)


if __name__ == "__main__":
    logger.info("running ebmbot.dispatcher")
    run()
