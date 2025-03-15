class HistoryManager:
    def __init__(self, text_edit):
        self.text_edit = text_edit
        self.history = []

    def add_entry(self, user_text, assistant_text):
        self.history.append(f"Usuário: {user_text}")
        self.history.append(f"Assistente: {assistant_text}")
        self.update_history_display()

    def update_history_display(self):
        self.text_edit("<br>".join(self.history))