from datetime import datetime, timedelta

class ErrorBudget:
    def __init__(self, initial_budget:int, window_start:datetime):
        self.budget = initial_budget
        self.window_start = window_start

class ErrorBudgetManager:

    def __init__(self, max_errors:int = 1, time_window: timedelta = timedelta(seconds=60)):
        self._devices_budget={}
        self._window = time_window
        self._max_errors = max_errors

    def _get_update_budget_window(self, device_uuid: str) -> ErrorBudget:
        dev_budget = self._devices_budget.get(device_uuid)
        if dev_budget is None:
            dev_budget = ErrorBudget(self._max_errors, datetime.utcnow())

        # Re-init the error budget if window expired
        if datetime.utcnow() > (dev_budget.window_start + self._window):
            dev_budget.budget = self._max_errors
            dev_budget.window_start = datetime.utcnow()

        return dev_budget

    def notify_error(self, device_uuid: str):
        dev_budget = self._get_update_budget_window(device_uuid)
        if dev_budget.budget < 1:
            return
        else:
            dev_budget.budget -= 1

    def is_out_of_budget(self, device_uuid: str) -> bool:
        budget = self._get_update_budget_window(device_uuid)
        return budget.budget < 1

