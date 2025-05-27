def unsigned_to_signed(number, bit_length):
    mask = (2**bit_length) - 1
    if number & (1 << (bit_length - 1)):
        return number | ~mask
    else:
        return number & mask


def map_num(num, i_min, i_max, o_min, o_max):
    return o_min + (float(num - i_min) / float(i_max - i_min) * (o_max - o_min))


def clamp(value, min, max):
    if value >= max:
        value = max

    if value <= min:
        value = min

    return value


def apply_gain(value, gain, min, max):
    return clamp(((value * gain) / 100), min, max)
