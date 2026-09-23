"""План дня для утреннего брифа."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from plan_utils import get_today_plan, format_plan_for_brief, PlanItem


def get_plan_block() -> str:
    """Вернуть блок плана дня для вставки в утренний бриф.

    Returns:
        Markdown-строка с таблицей плана или сообщением что плана нет.
    """
    items = get_today_plan()
    return format_plan_for_brief(items)


if __name__ == "__main__":
    print(get_plan_block())
