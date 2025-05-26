
def unsigned_to_signed(number, bitLength):
    mask = (2**bitLength) - 1
    if number & (1 << (bitLength - 1)):
        return number | ~mask
    else:
        return number & mask
    

def map_num(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


def clamp(value, min, max):
    if value >= max:
        value = max

    if value <= min:
        value = min

    return value
