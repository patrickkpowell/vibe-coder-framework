from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BridgeMetrics:
    sessions_total: int = 0
    active_sessions: int = 0
    tasks_total: int = 0
    tasks_running: int = 0
    tasks_usage_expired: int = 0
    messages_received_total: int = 0
    messages_sent_total: int = 0
    dangerous_prompts_blocked_total: int = 0
    errors_total: int = 0

    def render(self) -> str:
        """Render counters in Prometheus text exposition format."""
        lines = [
            "# HELP matrix_claude_sessions_total Total sessions created",
            "# TYPE matrix_claude_sessions_total counter",
            f"matrix_claude_sessions_total {self.sessions_total}",
            "# HELP matrix_claude_active_sessions Currently active sessions",
            "# TYPE matrix_claude_active_sessions gauge",
            f"matrix_claude_active_sessions {self.active_sessions}",
            "# HELP matrix_claude_tasks_total Total tasks started",
            "# TYPE matrix_claude_tasks_total counter",
            f"matrix_claude_tasks_total {self.tasks_total}",
            "# HELP matrix_claude_tasks_running Tasks currently running",
            "# TYPE matrix_claude_tasks_running gauge",
            f"matrix_claude_tasks_running {self.tasks_running}",
            "# HELP matrix_claude_tasks_usage_expired Tasks paused due to usage expiry",
            "# TYPE matrix_claude_tasks_usage_expired counter",
            f"matrix_claude_tasks_usage_expired {self.tasks_usage_expired}",
            "# HELP matrix_claude_matrix_messages_received_total Inbound Matrix messages",
            "# TYPE matrix_claude_matrix_messages_received_total counter",
            f"matrix_claude_matrix_messages_received_total {self.messages_received_total}",
            "# HELP matrix_claude_matrix_messages_sent_total Outbound Matrix messages",
            "# TYPE matrix_claude_matrix_messages_sent_total counter",
            f"matrix_claude_matrix_messages_sent_total {self.messages_sent_total}",
            "# HELP matrix_claude_dangerous_prompts_blocked_total Dangerous prompts refused",
            "# TYPE matrix_claude_dangerous_prompts_blocked_total counter",
            f"matrix_claude_dangerous_prompts_blocked_total {self.dangerous_prompts_blocked_total}",
            "# HELP matrix_claude_errors_total Total errors",
            "# TYPE matrix_claude_errors_total counter",
            f"matrix_claude_errors_total {self.errors_total}",
        ]
        return "\n".join(lines) + "\n"


# Module-level singleton — import and mutate directly.
bridge_metrics = BridgeMetrics()
