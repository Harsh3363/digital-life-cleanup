"""
Scheduler — Generate Cron and Windows Task Scheduler Jobs

Generates schedule configurations for automated periodic cleanup runs.
Supports both Unix cron syntax and Windows Task Scheduler XML.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class SchedulerGenerator:
    """Generate scheduling configurations for automated cleanup."""

    def __init__(self):
        self.python_executable = sys.executable
        self.project_root = Path(__file__).parent.parent.resolve()
        self.main_script = self.project_root / "main.py"

    # ── Cron (Linux / macOS) ─────────────────────────────────────

    def generate_cron(
        self,
        folder_path: str,
        frequency: str = "weekly",
        hour: int = 2,
        minute: int = 0,
    ) -> str:
        """
        Generate a crontab entry for periodic cleanup.

        Args:
            folder_path: Target folder to clean.
            frequency: 'daily', 'weekly', or 'monthly'.
            hour: Hour to run (0-23).
            minute: Minute to run (0-59).

        Returns:
            Crontab entry string.
        """
        cron_schedules = {
            "daily": f"{minute} {hour} * * *",
            "weekly": f"{minute} {hour} * * 0",  # Sunday
            "monthly": f"{minute} {hour} 1 * *",  # 1st of month
        }

        schedule = cron_schedules.get(frequency, cron_schedules["weekly"])
        command = (
            f'{self.python_executable} "{self.main_script}" '
            f'--cli --folder "{folder_path}"'
        )

        cron_line = f"{schedule} {command}"

        logger.info(f"Generated cron entry ({frequency}): {cron_line}")
        return cron_line

    def generate_cron_install_instructions(
        self,
        folder_path: str,
        frequency: str = "weekly",
    ) -> str:
        """Generate instructions for installing the cron job."""
        cron_entry = self.generate_cron(folder_path, frequency)

        return (
            "# Digital Life Cleanup — Cron Installation\n"
            "# ─────────────────────────────────────────\n"
            f"# Frequency: {frequency}\n"
            f"# Target: {folder_path}\n"
            "#\n"
            "# To install, run:\n"
            f'#   (crontab -l 2>/dev/null; echo "{cron_entry}") | crontab -\n'
            "#\n"
            "# To verify:\n"
            "#   crontab -l\n"
            "#\n"
            "# To remove:\n"
            "#   crontab -e  (then delete the line)\n"
            "#\n"
            f"# Entry:\n{cron_entry}\n"
        )

    # ── Windows Task Scheduler ───────────────────────────────────

    def generate_windows_task_xml(
        self,
        folder_path: str,
        frequency: str = "weekly",
        hour: int = 2,
        minute: int = 0,
        task_name: str = "DigitalLifeCleanup",
    ) -> str:
        """
        Generate Windows Task Scheduler XML for periodic cleanup.

        Args:
            folder_path: Target folder to clean.
            frequency: 'daily', 'weekly', or 'monthly'.
            hour: Hour to run (0-23).
            minute: Minute to run (0-59).
            task_name: Name for the scheduled task.

        Returns:
            XML string for Windows Task Scheduler.
        """
        start_time = f"{hour:02d}:{minute:02d}:00"
        start_date = datetime.now().strftime("%Y-%m-%d")

        # Build trigger based on frequency
        if frequency == "daily":
            trigger_xml = f"""    <CalendarTrigger>
      <StartBoundary>{start_date}T{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""
        elif frequency == "weekly":
            trigger_xml = f"""    <CalendarTrigger>
      <StartBoundary>{start_date}T{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Sunday />
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>"""
        elif frequency == "monthly":
            trigger_xml = f"""    <CalendarTrigger>
      <StartBoundary>{start_date}T{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth>
          <Day>1</Day>
        </DaysOfMonth>
        <Months>
          <January /><February /><March /><April />
          <May /><June /><July /><August />
          <September /><October /><November /><December />
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>"""
        else:
            trigger_xml = f"""    <CalendarTrigger>
      <StartBoundary>{start_date}T{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Sunday />
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>"""

        xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Digital Life Cleanup &amp; Protection System - Automated cleanup powered by Accomplish</Description>
    <Author>DigitalLifeCleanup</Author>
    <Date>{datetime.now().isoformat()}</Date>
  </RegistrationInfo>
  <Triggers>
{trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{self.python_executable}</Command>
      <Arguments>"{self.main_script}" --cli --folder "{folder_path}"</Arguments>
      <WorkingDirectory>{self.project_root}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

        logger.info(f"Generated Windows Task Scheduler XML ({frequency})")
        return xml_content

    def save_windows_task_xml(
        self,
        folder_path: str,
        frequency: str = "weekly",
        output_path: Optional[str] = None,
        task_name: str = "DigitalLifeCleanup",
    ) -> str:
        """
        Save the Windows Task Scheduler XML to a file.

        Returns:
            Path to the saved XML file.
        """
        xml_content = self.generate_windows_task_xml(
            folder_path=folder_path,
            frequency=frequency,
            task_name=task_name,
        )

        if output_path is None:
            output_path = str(self.project_root / f"{task_name}.xml")

        with open(output_path, "w", encoding="utf-16") as f:
            f.write(xml_content)

        logger.info(f"Saved task XML to: {output_path}")
        return output_path

    def generate_install_instructions(
        self,
        folder_path: str,
        frequency: str = "weekly",
        task_name: str = "DigitalLifeCleanup",
    ) -> str:
        """Generate platform-appropriate installation instructions."""
        if os.name == "nt":
            xml_path = self.project_root / f"{task_name}.xml"
            return (
                "# Digital Life Cleanup — Windows Task Scheduler\n"
                "# ─────────────────────────────────────────────\n"
                f"# Frequency: {frequency}\n"
                f"# Target: {folder_path}\n"
                "#\n"
                "# Steps:\n"
                f'# 1. Save XML: python main.py --schedule --folder "{folder_path}"\n'
                f'# 2. Import task: schtasks /create /xml "{xml_path}" /tn "{task_name}"\n'
                f'# 3. Verify: schtasks /query /tn "{task_name}"\n'
                f'# 4. Remove: schtasks /delete /tn "{task_name}" /f\n'
            )
        else:
            return self.generate_cron_install_instructions(folder_path, frequency)
