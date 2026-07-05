from core_api import api_call

class WindowClassifier:
    def __init__(self):
        self.model_name = 'openbmb/MiniCPM5-1B'

    def _get_response(self, messages, max_tokens=50):
        try:
            return api_call(messages, model_name=self.model_name, max_tokens=max_tokens)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_window_classification(self, title):
        messages = [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Classify this window title into a category: {title}"}]
        return self._get_response(messages)

    def complete_text(self, goal):
        messages = [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Only return the user's message of the goal: {goal}"}]
        return self._get_response(messages)

    def get_window_info(self, window_title):
        open_windows = self.get_open_windows()
        for window_info in open_windows:
            if window_title.lower() in window_info[0].lower():
                return window_info
        return None
