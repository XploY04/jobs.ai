"""Urgency detection for job postings"""

import re
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone


class UrgencyDetector:
    """Detect urgency level and deadlines from job descriptions"""

    # Urgent keywords and phrases
    URGENT_KEYWORDS = [
        r'\burgent\b',
        r'\basap\b',
        r'\bas soon as possible\b',
        r'\bimmediate\b',
        r'\bimmediately\b',
        r'\bright away\b',
        r'\btime-sensitive\b',
        r'\bfast-paced\b',
        r'\bhiring now\b',
        r'\bstart immediately\b'
    ]

    # Deadline patterns
    DEADLINE_PATTERNS = [
        # "Apply by March 15"
        r'apply by\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)',
        # "Deadline: 2024-03-15"
        r'deadline[:\s]+(\d{4}-\d{2}-\d{2})',
        # "Closes March 15th"
        r'closes?\s+(?:on\s+)?(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)',
        # "Applications due March 15"
        r'applications?\s+due\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)',
        # "Accepting applications until March 15"
        r'until\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)',
    ]

    # Rolling/ongoing patterns
    ROLLING_PATTERNS = [
        r'\brolling basis\b',
        r'\brolling deadline\b',
        r'\bongoing\b',
        r'\bopen until filled\b',
        r'\bno deadline\b'
    ]

    def detect_urgency(self, title: str, description: str) -> str:
        """
        Detect urgency level: urgent, normal, low
        """
        
        text = f"{title} {description}".lower()
        
        # Check for urgent keywords
        for pattern in self.URGENT_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                return 'urgent'
        
        # Check for rolling/ongoing (low urgency)
        for pattern in self.ROLLING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 'low'
        
        # Check if recently posted (within 7 days)
        # If posted very recently, might be more urgent
        # This would require posted_at date
        
        return 'normal'

    def extract_deadline(self, description: str) -> Tuple[Optional[datetime], str]:
        """
        Extract application deadline from description
        Returns: (deadline_datetime, confidence_level)
        """
        
        text = description.lower()
        
        # Check for rolling/no deadline first
        for pattern in self.ROLLING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return (None, 'high')  # High confidence there's no deadline
        
        # Try to find specific deadline
        for pattern in self.DEADLINE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline_str = match.group(1)
                try:
                    deadline_dt = self._parse_deadline_string(deadline_str)
                    if deadline_dt:
                        return (deadline_dt, 'high')
                except:
                    continue
        
        return (None, 'none')

    def _parse_deadline_string(self, deadline_str: str) -> Optional[datetime]:
        """Parse various deadline string formats"""
        
        # Try ISO format first (2024-03-15)
        try:
            return datetime.fromisoformat(deadline_str).replace(tzinfo=timezone.utc)
        except:
            pass
        
        # Try common date formats
        formats = [
            '%B %d, %Y',  # March 15, 2024
            '%B %d %Y',   # March 15 2024
            '%b %d, %Y',  # Mar 15, 2024
            '%b %d %Y',   # Mar 15 2024
            '%B %d',      # March 15 (assume current year)
            '%b %d',      # Mar 15 (assume current year)
        ]
        
        # Clean the string
        deadline_str = re.sub(r'(st|nd|rd|th)', '', deadline_str, flags=re.IGNORECASE)
        
        for fmt in formats:
            try:
                dt = datetime.strptime(deadline_str.strip(), fmt)
                # If no year specified, assume current year
                if '%Y' not in fmt:
                    dt = dt.replace(year=datetime.now().year)
                return dt.replace(tzinfo=timezone.utc)
            except:
                continue
        
        return None

    def is_deadline_soon(self, deadline: Optional[datetime], days: int = 7) -> bool:
        """Check if deadline is within specified days"""
        
        if not deadline:
            return False
        
        now = datetime.now(timezone.utc)
        return deadline - now <= timedelta(days=days)
