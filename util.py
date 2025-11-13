#!/usr/bin/env python3
"""
Utility functions for TV Show Organizer
Provides helper functions for parsing and processing.
"""

import re


# Chinese numeral mappings
CHINESE_NUMERALS = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,  # Traditional
    '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
}


def parse_chinese_number(chinese_text: str) -> int:
    """Convert Chinese numerals to Arabic numbers"""
    if not chinese_text:
        return 0
    
    # Handle pure Arabic numbers
    if chinese_text.isdigit():
        return int(chinese_text)
    
    # Handle mixed Chinese-Arabic (like "第1集")
    arabic_match = re.search(r'\d+', chinese_text)
    if arabic_match:
        return int(arabic_match.group())
    
    result = 0
    temp = 0
    
    for char in chinese_text:
        if char in CHINESE_NUMERALS:
            num = CHINESE_NUMERALS[char]
            if num == 10:  # 十
                if temp == 0:
                    temp = 10  # 十 = 10
                else:
                    temp *= 10  # 二十 = 2 * 10
            elif num == 0:  # 零
                continue
            else:
                if temp == 10 or temp == 0:
                    temp += num  # 十五 = 10 + 5, or just 五 = 5
                else:
                    result += temp
                    temp = num
    
    result += temp
    return result if result > 0 else temp

