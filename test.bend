def Sum(start, target):
    if start == target:
        return start
    else:
        half = (start + target) / 2
        left = Sum(start, half)
        right = Sum(half + 1, target)
        return left + right

def main():
    return Sum(1, 1_000_000)