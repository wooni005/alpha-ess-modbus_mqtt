import sys
import struct


if sys.version > "3":
    long = int
MAX_NUMBER_OF_DECIMALS = 10  # Some instrument might store 0.00000154 Ampere as 154 etc

CRC16TABLE = (
    0,
    49345,
    49537,
    320,
    49921,
    960,
    640,
    49729,
    50689,
    1728,
    1920,
    51009,
    1280,
    50625,
    50305,
    1088,
    52225,
    3264,
    3456,
    52545,
    3840,
    53185,
    52865,
    3648,
    2560,
    51905,
    52097,
    2880,
    51457,
    2496,
    2176,
    51265,
    55297,
    6336,
    6528,
    55617,
    6912,
    56257,
    55937,
    6720,
    7680,
    57025,
    57217,
    8000,
    56577,
    7616,
    7296,
    56385,
    5120,
    54465,
    54657,
    5440,
    55041,
    6080,
    5760,
    54849,
    53761,
    4800,
    4992,
    54081,
    4352,
    53697,
    53377,
    4160,
    61441,
    12480,
    12672,
    61761,
    13056,
    62401,
    62081,
    12864,
    13824,
    63169,
    63361,
    14144,
    62721,
    13760,
    13440,
    62529,
    15360,
    64705,
    64897,
    15680,
    65281,
    16320,
    16000,
    65089,
    64001,
    15040,
    15232,
    64321,
    14592,
    63937,
    63617,
    14400,
    10240,
    59585,
    59777,
    10560,
    60161,
    11200,
    10880,
    59969,
    60929,
    11968,
    12160,
    61249,
    11520,
    60865,
    60545,
    11328,
    58369,
    9408,
    9600,
    58689,
    9984,
    59329,
    59009,
    9792,
    8704,
    58049,
    58241,
    9024,
    57601,
    8640,
    8320,
    57409,
    40961,
    24768,
    24960,
    41281,
    25344,
    41921,
    41601,
    25152,
    26112,
    42689,
    42881,
    26432,
    42241,
    26048,
    25728,
    42049,
    27648,
    44225,
    44417,
    27968,
    44801,
    28608,
    28288,
    44609,
    43521,
    27328,
    27520,
    43841,
    26880,
    43457,
    43137,
    26688,
    30720,
    47297,
    47489,
    31040,
    47873,
    31680,
    31360,
    47681,
    48641,
    32448,
    32640,
    48961,
    32000,
    48577,
    48257,
    31808,
    46081,
    29888,
    30080,
    46401,
    30464,
    47041,
    46721,
    30272,
    29184,
    45761,
    45953,
    29504,
    45313,
    29120,
    28800,
    45121,
    20480,
    37057,
    37249,
    20800,
    37633,
    21440,
    21120,
    37441,
    38401,
    22208,
    22400,
    38721,
    21760,
    38337,
    38017,
    21568,
    39937,
    23744,
    23936,
    40257,
    24320,
    40897,
    40577,
    24128,
    23040,
    39617,
    39809,
    23360,
    39169,
    22976,
    22656,
    38977,
    34817,
    18624,
    18816,
    35137,
    19200,
    35777,
    35457,
    19008,
    19968,
    36545,
    36737,
    20288,
    36097,
    19904,
    19584,
    35905,
    17408,
    33985,
    34177,
    17728,
    34561,
    18368,
    18048,
    34369,
    33281,
    17088,
    17280,
    33601,
    16640,
    33217,
    32897,
    16448,
)


def _check_string(
    inputstring,
    description,
    minlength=0,
    maxlength=None,
    force_ascii=False,
    exception_type=ValueError,
):
    """Check that the given string is valid.
    Args:
        * inputstring (string): The string to be checked
        * description (string): Used in error messages for the checked inputstring
        * minlength (int): Minimum length of the string
        * maxlength (int or None): Maximum length of the string
        * force_ascii (bool): Enforce that the string is ASCII
        * exception_type (Exception): The type of exception to raise for length errors
    The force_ascii argument is valid only for Python3, as all strings are ASCII in Python2.
    Raises:
        TypeError, ValueError or the one given by exception_type
    Uses the function :func:`_check_int` internally.
    """
    # Type checking
    if not isinstance(description, str):
        raise TypeError(
            "The description should be a string. Given: {0!r}".format(description)
        )

    if not isinstance(inputstring, str):
        raise TypeError(
            "The {0} should be a string. Given: {1!r}".format(description, inputstring)
        )

    if not isinstance(maxlength, (int, type(None))):
        raise TypeError(
            "The maxlength must be an integer or None. Given: {0!r}".format(maxlength)
        )
    try:
        issubclass(exception_type, Exception)
    except TypeError:
        raise TypeError(
            "The exception_type must be an exception class. It not even a class. Given: {0!r}".format(type(exception_type))
        )
    if not issubclass(exception_type, Exception):
        raise TypeError(
            "The exception_type must be an exception class. Given: {0!r}".format(
                type(exception_type)
            )
        )

    # Check values
    _check_int(minlength, minvalue=0, maxvalue=None, description="minlength")

    if len(inputstring) < minlength:
        raise exception_type(
            "The {0} is too short: {1}, but minimum value is {2}. Given: {3!r}".format(
                description, len(inputstring), minlength, inputstring
            )
        )

    if maxlength is not None:
        if maxlength < 0:
            raise ValueError(
                "The maxlength must be positive. Given: {0}".format(maxlength)
            )

        if maxlength < minlength:
            raise ValueError(
                "The maxlength must not be smaller than minlength. Given: {0} and {1}".format(
                    maxlength, minlength
                )
            )

        if len(inputstring) > maxlength:
            raise exception_type(
                "The {0} is too long: {1}, but maximum value is {2}. Given: {3!r}".format(
                    description, len(inputstring), maxlength, inputstring
                )
            )

    if force_ascii and sys.version > "3":
        try:
            inputstring.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError(
                "The {0} must be ASCII. Given: {1!r}".format(description, inputstring)
            )


def _check_int(inputvalue, minvalue=None, maxvalue=None, description="inputvalue"):
    """Check that the given integer is valid.
    Args:
        * inputvalue (int or long): The integer to be checked
        * minvalue (int or long, or None): Minimum value of the integer
        * maxvalue (int or long, or None): Maximum value of the integer
        * description (string): Used in error messages for the checked inputvalue
    Raises:
        TypeError, ValueError
    Note: Can not use the function :func:`_check_string`, as that function uses this
    function internally.
    """
    if not isinstance(description, str):
        raise TypeError(
            "The description should be a string. Given: {0!r}".format(description)
        )

    if not isinstance(inputvalue, (int, long)):
        raise TypeError(
            "The {0} must be an integer. Given: {1!r}".format(description, inputvalue)
        )

    if not isinstance(minvalue, (int, long, type(None))):
        raise TypeError(
            "The minvalue must be an integer or None. Given: {0!r}".format(minvalue)
        )

    if not isinstance(maxvalue, (int, long, type(None))):
        raise TypeError(
            "The maxvalue must be an integer or None. Given: {0!r}".format(maxvalue)
        )

    _check_numerical(inputvalue, minvalue, maxvalue, description)


def _check_numerical(
    inputvalue, minvalue=None, maxvalue=None, description="inputvalue"
):
    """Check that the given numerical value is valid.
    Args:
        * inputvalue (numerical): The value to be checked.
        * minvalue (numerical): Minimum value  Use None to skip this part of the test.
        * maxvalue (numerical): Maximum value. Use None to skip this part of the test.
        * description (string): Used in error messages for the checked inputvalue
    Raises:
        TypeError, ValueError
    Note: Can not use the function :func:`_check_string`, as it uses this function
    internally.
    """
    # Type checking
    if not isinstance(description, str):
        raise TypeError(
            "The description should be a string. Given: {0!r}".format(description)
        )

    if not isinstance(inputvalue, (int, long, float)):
        raise TypeError(
            "The {0} must be numerical. Given: {1!r}".format(description, inputvalue)
        )

    if not isinstance(minvalue, (int, float, long, type(None))):
        raise TypeError(
            "The minvalue must be numeric or None. Given: {0!r}".format(minvalue)
        )

    if not isinstance(maxvalue, (int, float, long, type(None))):
        raise TypeError(
            "The maxvalue must be numeric or None. Given: {0!r}".format(maxvalue)
        )

    # Consistency checking
    if (minvalue is not None) and (maxvalue is not None):
        if maxvalue < minvalue:
            raise ValueError(
                "The maxvalue must not be smaller than minvalue. Given: {0} and {1}, respectively.".format(maxvalue, minvalue)
            )

    # Value checking
    if minvalue is not None:
        if inputvalue < minvalue:
            raise ValueError(
                "The {0} is too small: {1}, but minimum value is {2}.".format(
                    description, inputvalue, minvalue
                )
            )

    if maxvalue is not None:
        if inputvalue > maxvalue:
            raise ValueError(
                "The {0} is too large: {1}, but maximum value is {2}.".format(
                    description, inputvalue, maxvalue
                )
            )


def _check_bool(inputvalue, description="inputvalue"):
    """Check that the given inputvalue is a boolean.
    Args:
        * inputvalue (boolean): The value to be checked.
        * description (string): Used in error messages for the checked inputvalue.
    Raises:
        TypeError, ValueError
    """
    _check_string(description, minlength=1, description="description string")
    if not isinstance(inputvalue, bool):
        raise TypeError(
            "The {0} must be boolean. Given: {1!r}".format(description, inputvalue)
        )


def numToTwoByteString(value, number_of_decimals=0, lsb_first=False, signed=False):
    _check_numerical(value, description="inputvalue")
    _check_int(
        number_of_decimals,
        minvalue=0,
        maxvalue=MAX_NUMBER_OF_DECIMALS,
        description="number of decimals",
    )
    _check_bool(lsb_first, description="lsb_first")
    _check_bool(signed, description="signed parameter")

    multiplier = 10 ** number_of_decimals
    integer = int(float(value) * multiplier)

    if lsb_first:
        formatcode = "<"  # Little-endian
    else:
        formatcode = ">"  # Big-endian
    if signed:
        formatcode += "h"  # (Signed) short (2 bytes)
    else:
        formatcode += "H"  # Unsigned short (2 bytes)

    outstring = _pack(formatcode, integer)
    assert len(outstring) == 2
    return outstring


def _pack(formatstring, value):
    """Pack a value into a bytestring.
    Uses the built-in :mod:`struct` Python module.
    Args:
        * formatstring (str): String for the packing. See the :mod:`struct` module
          for details.
        * value (depends on formatstring): The value to be packed
    Returns:
        A bytestring (str).
    Raises:
        ValueError
    Note that the :mod:`struct` module produces byte buffers for Python3,
    but bytestrings for Python2. This is compensated for automatically.
    """
    _check_string(formatstring, description="formatstring", minlength=1)

    try:
        result = struct.pack(formatstring, value)
    except Exception:
        errortext = (
            "The value to send is probably out of range, as the num-to-bytestring "
        )
        errortext += "conversion failed. Value: {0!r} Struct format code is: {1}"
        raise ValueError(errortext.format(value, formatstring))

    if sys.version_info[0] > 2:
        return str(
            result, encoding="latin1"
        )  # Convert types to make it Python3 compatible
    return result


def calculateCRC(inputstring):
    """Calculate CRC-16 for Modbus.
    Args:
        inputstring (str): An arbitrary-length message (without the CRC).
    Returns:
        A two-byte CRC string, where the least significant byte is first.
    """
    _check_string(inputstring, description="input CRC string")

    # Preload a 16-bit register with ones
    register = 0xFFFF

    for char in inputstring:
        register = (register >> 8) ^ CRC16TABLE[(register ^ ord(char)) & 0xFF]

    return numToTwoByteString(register, lsb_first=True)


def checkRecvMsgCRC(recvMsg, debug=False):
    crcStr = recvMsg[-2:]
    # Convert from bytes to string, without conversion
    crcStr = "".join([chr(i) for i in crcStr])

    recvMsgWithoutCRC = recvMsg[0:-2]
    # Convert from bytes to string, without conversion
    recvMsgWithoutCRC = "".join([chr(i) for i in recvMsgWithoutCRC])
    calcCRC = calculateCRC(recvMsgWithoutCRC)

    if calcCRC == crcStr:
        if debug:
            # print("->CRC OK: ", end='')
            print(": ", end='')
        return True
    else:
        if debug:
            print(": CRC is NOT OK!!!: ", end='')
        return False
