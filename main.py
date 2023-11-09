import random
import string

def generate_unique_code(size=40):
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(size))
    return code

# Example usage
unique_code = generate_unique_code()
print(unique_code)