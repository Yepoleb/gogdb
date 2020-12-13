import string


def normalize_system(system_name):
    system_name = system_name.lower()
    if system_name == "mac":
        return "osx"
    else:
        return system_name

NORMALIZED_CHARS = set(string.ascii_lowercase + string.digits)
def normalize_search(search_str):
    if search_str is None:
        return ""
    return "".join(c for c in search_str.lower() if c in NORMALIZED_CHARS)

def compress_systems(systems):
    """Compressed systems is just a string of the first letters"""
    compressed = ""
    for system in systems:
        compressed += system[0]
    return compressed

def decompress_systems(compressed):
    systems = []
    decompress_map = {
        "w": "windows",
        "l": "linux",
        "o": "osx"
    }
    for letter in compressed:
        systems.append(decompress_map[letter])
    return systems
