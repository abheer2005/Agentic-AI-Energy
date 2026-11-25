# ============================================================
# P_308 - Alert / Event Configuration
# ============================================================

# Re-publish an unchanged active alert only after this interval.
# Prevents MQTT alert spam while still providing periodic reminders.
ALERT_REMINDER_SECONDS = 60

# SQLite history retention is intentionally not auto-deleted.
# A later maintenance job can archive old records if required.
EVENT_DATABASE_NAME = "energy_events.db"

# Severity ordering used by alert lifecycle logic.
SEVERITY_RANK = {
    "NONE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}
