"""
mcp1/tools/recommendation_tools.py
------------------------------------
3 tools for the recommendation MCP server:
  tool1 - process_text   : tokenize input text → word frequency dict
  tool2 - get_count      : return total unique word count from processed result
  tool3 - print_count_html: render the word:count map as an HTML table
"""

from collections import Counter
import re


def process_text(text: str) -> dict:
    """
    Tool 1: Tokenize input text and count word frequencies.

    Args:
        text: raw input string from user

    Returns:
        dict of {word: count} e.g. {"hello": 2, "world": 1}
    """
    # Lowercase everything so "Hello" and "hello" are same word
    text = text.lower()

    # Remove punctuation using regex, keep only word characters and spaces
    words = re.findall(r'\b[a-z]+\b', text)

    # Count frequency of each word using Counter
    word_counts = dict(Counter(words))

    return word_counts  # e.g. {"apple": 3, "banana": 1}


def get_count(word_counts: dict) -> dict:
    """
    Tool 2: Get summary counts from a word frequency dict.

    Args:
        word_counts: dict returned by process_text e.g. {"apple": 3, "banana": 1}

    Returns:
        dict with total_words (sum of all counts) and unique_words (distinct words)
    """
    # Sum all frequency values → total word count including duplicates
    total_words = sum(word_counts.values())

    # Number of distinct keys → unique words
    unique_words = len(word_counts)

    return {
        "total_words": total_words,    # e.g. 10
        "unique_words": unique_words   # e.g. 7
    }


def print_count_html(word_counts: dict) -> str:
    """
    Tool 3: Render word frequency dict as an HTML table.

    Args:
        word_counts: dict of {word: count}

    Returns:
        HTML string with a styled table of word → count
    """
    # Start building HTML string
    rows = ""

    # Sort by count descending so highest frequency word shows first
    for word, count in sorted(word_counts.items(), key=lambda x: -x[1]):
        # Each row: <tr><td>word</td><td>count</td></tr>
        rows += f"<tr><td>{word}</td><td>{count}</td></tr>\n"

    # Wrap rows in a full HTML table with basic inline styling
    html = f"""
<html>
<body>
<h2>Word Frequency Report</h2>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; font-family:monospace;">
  <thead>
    <tr style="background:#4CAF50; color:white;">
      <th>Word</th>
      <th>Count</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
</body>
</html>
"""
    return html  # caller can write this to a .html file or return as response
