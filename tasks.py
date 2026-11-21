TASKS = [
    {
        "name": "add",
        "function": "add",
        "prompt": "Write a Python function add(a, b) that returns the sum of a and b.",
        "tests": [((2, 3), 5), ((-1, 1), 0), ((2.5, 2.5), 5.0)],
    },
    {
        "name": "palindrome",
        "function": "is_palindrome",
        "prompt": "Write a Python function is_palindrome(text) that returns True if text is a palindrome, ignoring case, spaces and punctuation, and False otherwise.",
        "tests": [
            (("racecar",), True),
            (("A man, a plan, a canal: Panama",), True),
            (("hello",), False),
            (("",), True),
            (("No 'x' in Nixon",), True),
        ],
    },
    {
        "name": "second_largest",
        "function": "second_largest",
        "prompt": "Write a Python function second_largest(numbers) that returns the second largest distinct number in a list. If there is no such number, return None.",
        "tests": [
            (([3, 1, 4, 1, 5],), 4),
            (([5, 5, 5],), None),
            (([7],), None),
            (([],), None),
            (([-2, -1, -3],), -2),
        ],
    },
    {
        "name": "roman_to_int",
        "function": "roman_to_int",
        "prompt": "Write a Python function roman_to_int(s) that converts a Roman numeral string to an integer.",
        "tests": [
            (("III",), 3),
            (("IV",), 4),
            (("IX",), 9),
            (("LVIII",), 58),
            (("MCMXCIV",), 1994),
        ],
    },
    {
        "name": "compress",
        "function": "compress",
        "prompt": "Write a Python function compress(text) that compresses repeated characters: 'aaabcc' becomes 'a3b1c2'. Return an empty string for empty input.",
        "tests": [
            (("aaabcc",), "a3b1c2"),
            (("abc",), "a1b1c1"),
            (("",), ""),
            (("zzzz",), "z4"),
            (("aabbaa",), "a2b2a2"),
        ],
    },
]