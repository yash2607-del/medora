from langchain_community.chat_message_histories import FileChatMessageHistory
import os

class SlidingWindowFileChatMessageHistory(FileChatMessageHistory):
    """
    Extends FileChatMessageHistory to maintain complete persistence on disk
    while returning the most recent N messages (default 10) to prevent
    context bloat and ensure fast, accurate contextualization for longer conversations.
    """
    def __init__(self, file_path: str, max_messages: int = 10):
        super().__init__(file_path)
        self.max_messages = max_messages

    @property
    def messages(self):
        all_messages = super().messages
        if self.max_messages and len(all_messages) > self.max_messages:
            return all_messages[-self.max_messages:]
        return all_messages

def get_session_history(session_id: str):
    """
    Returns a SlidingWindowFileChatMessageHistory object for the given session_id.
    Stores the JSON files in the Server/data/history/ directory.
    This provides persistent conversation memory across user sessions with long dependency support.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    history_dir = os.path.join(base_dir, 'data', 'history')
    os.makedirs(history_dir, exist_ok=True)
    
    # Clean the session_id to prevent directory traversal
    safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_')).rstrip()
    if not safe_session_id:
        safe_session_id = "default"
        
    file_path = os.path.join(history_dir, f"{safe_session_id}.json")
    return SlidingWindowFileChatMessageHistory(file_path, max_messages=10)
