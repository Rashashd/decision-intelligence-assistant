import re
from datetime import datetime, timezone

import numpy as np
from textblob import TextBlob

# The saved scaler/imputer were fit on this column order, changing it breaks inference silently.
ENGINEERED_COLS = [
    "char_count",
    "word_count",
    "exclamation_count",
    "question_count",
    "caps_ratio",
    "mention_count",
    "has_url",
    "sentiment_polarity",
    "hour_of_day",
    "day_of_week",
]


def extract_features(text: str, now: datetime | None = None) -> np.ndarray:
    # Return a (1, 10) float array in ENGINEERED_COLS order.
    # hour_of_day and day_of_week use `now` (UTC) so inference is  reproducible in tests.
    
    if now is None:
        now = datetime.now(timezone.utc)

    row = {
        "char_count": len(text),
        "word_count": len(text.split()),
        "exclamation_count": text.count("!"),
        "question_count": text.count("?"),
        "caps_ratio": sum(1 for c in text if c.isupper()) / max(len(text), 1),
        "mention_count": len(re.findall(r"@\w+", text)),
        "has_url": int(bool(re.search(r"https?://", text))),
        "sentiment_polarity": TextBlob(text).sentiment.polarity,  # type: ignore[union-attr]
        "hour_of_day": now.hour,
        "day_of_week": now.weekday(),
    }

    return np.array([[row[col] for col in ENGINEERED_COLS]], dtype=float)