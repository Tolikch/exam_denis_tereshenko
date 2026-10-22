TASKS = [
    {
        "id": 1, "title": "Сумма протокола", "points": 5,
        "description": "Даны два целых числа через пробел. Верните их сумму.",
        "examples": "Ввод: 7 13 → Вывод: 20",
        "tests": [("7 13", "20"), ("-8 3", "-5"), ("100000 900000", "1000000")],
        "reference": "def solve(s):\n    a, b = map(int, s.split())\n    return str(a + b)"
    },
    {
        "id": 2, "title": "Палиндром канала", "points": 5,
        "description": "Дана строка из латинских букв. Верните YES, если она читается одинаково слева направо и справа налево, иначе NO.",
        "examples": "Ввод: level → Вывод: YES",
        "tests": [("level", "YES"), ("hacker", "NO"), ("a", "YES")],
        "reference": "def solve(s):\n    s = s.strip()\n    return 'YES' if s == s[::-1] else 'NO'"
    },
    {
        "id": 3, "title": "Максимум пакета", "points": 5,
        "description": "В первой позиции — количество чисел N, далее N целых чисел. Верните максимальное число.",
        "examples": "Ввод: 5 3 -1 9 0 4 → Вывод: 9",
        "tests": [("5 3 -1 9 0 4", "9"), ("1 -99", "-99"), ("4 8 8 2 7", "8")],
        "reference": "def solve(s):\n    values = list(map(int, s.split()))[1:]\n    return str(max(values))"
    },
    {
        "id": 4, "title": "Баланс скобок", "points": 5,
        "description": "Дана строка из круглых скобок. Верните YES, если каждая открывающая скобка правильно закрыта, иначе NO.",
        "examples": "Ввод: (()()) → Вывод: YES",
        "tests": [("(()())", "YES"), ("(()", "NO"), (")(", "NO"), ("", "YES")],
        "reference": "def solve(s):\n    b = 0\n    for c in s.strip():\n        b += 1 if c == '(' else -1\n        if b < 0: return 'NO'\n    return 'YES' if b == 0 else 'NO'"
    },
    {
        "id": 5, "title": "Два индекса", "points": 10,
        "description": "Ввод: N, затем N чисел, затем target. Найдите индексы двух разных чисел (с нуля), сумма которых равна target. Верните индексы через пробел в возрастающем порядке. Решение гарантированно существует.",
        "examples": "Ввод: 4 2 7 11 15 9 → Вывод: 0 1",
        "tests": [("4 2 7 11 15 9", "два корректных индекса"), ("5 3 2 4 6 8 10", "два корректных индекса"), ("6 1 8 3 4 5 2 7 9", "два корректных индекса")],
        "reference": "def solve(s):\n    x = list(map(int, s.split())); n = x[0]; a = x[1:n+1]; t = x[-1]\n    seen = {}\n    for i, v in enumerate(a):\n        if t-v in seen: return f'{seen[t-v]} {i}'\n        seen[v] = i"
    }
]

PYTHON_TEMPLATE = "def solve(input_data):\n    # Верните строковый результат\n    pass\n"
JAVA_TEMPLATE = "public class Solution {\n    public static String solve(String inputData) {\n        // Верните строковый результат\n        return \"\";\n    }\n}\n"
