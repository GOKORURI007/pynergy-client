### Format Characters[¶](https://docs.python.org/3/library/struct.html#format-characters "Link to this heading")

Format characters have the following meaning; the conversion between C and Python values should be
obvious given their types. The ‘Standard size’ column refers to the size of the packed value in
bytes when using standard size; that is, when the format string starts with one of `'<'`, `'>'`,
`'!'` or `'='`. When using native size, the size of the packed value is platform-dependent.

| Format | C Type             | Python type       | Standard size | Notes    |
|--------|--------------------|-------------------|---------------|----------|
| x      | pad byte           | no value          |               | (7)      |
| c      | char               | bytes of length 1 | 1             |          |
| b      | signed char        | integer           | 1             | (1), (2) |
| B      | unsigned char      | integer           | 1             | (2)      |
| ?      | _Bool              | bool              | 1             | (1)      |
| h      | short              | integer           | 2             | (2)      |
| H      | unsigned short     | integer           | 2             | (2)      |
| i      | int                | integer           | 4             | (2)      |
| I      | unsigned int       | integer           | 4             | (2)      |
| l      | long               | integer           | 4             | (2)      |
| L      | unsigned long      | integer           | 4             | (2)      |
| q      | long long          | integer           | 8             | (2)      |
| Q      | unsigned long long | integer           | 8             | (2)      |
| n      | ssize_t            | integer           |               | (3)      |
| N      | size_t             | integer           |               | (3)      |
| e      | (6)                | float             | 2             | (4)      |
| f      | float              | float             | 4             | (4)      |
| d      | double             | float             | 8             | (4)      |
| F      | float complex      | complex           | 8             | (10)     |
| D      | double complex     | complex           | 16            | (10)     |
| s      | char[]             | bytes             |               | (9)      |
| p      | char[]             | bytes             |               | (8)      |
| P      | void*              | integer           |               | (5)      |

Changed in version 3.3: Added support for the `'n'` and `'N'` formats.

Changed in version 3.6: Added support for the `'e'` format.

Changed in version 3.14: Added support for the `'F'` and `'D'` formats.

Notes:

1. The `'?'` conversion code corresponds to the \_Bool type defined by C standards since C99. In
   standard mode, it is represented by one byte.

2. When attempting to pack a non-integer using any of the integer conversion codes, if the
   non-integer has a [
   `__index__()`](https://docs.python.org/3/reference/datamodel.html#object.__index__ "object.__index__")
   method then that method is called to convert the argument to an integer before packing.

   Changed in version 3.2: Added use of the [
   `__index__()`](https://docs.python.org/3/reference/datamodel.html#object.__index__ "object.__index__")
   method for non-integers.

3. The `'n'` and `'N'` conversion codes are only available for the native size (selected as the
   default or with the `'@'` byte order character). For the standard size, you can use whichever of
   the other integer formats fits your application.

4. For the `'f'`, `'d'` and `'e'` conversion codes, the packed representation uses the IEEE 754
   binary32, binary64 or binary16 format (for `'f'`, `'d'` or `'e'` respectively), regardless of the
   floating-point format used by the platform.

5. The `'P'` format character is only available for the native byte ordering (selected as the
   default or with the `'@'` byte order character). The byte order character `'='` chooses to use
   little- or big-endian ordering based on the host system. The struct module does not interpret
   this as native ordering, so the `'P'` format is not available.

6. The IEEE 754 binary16 “half precision” type was introduced in the 2008 revision of
   the [IEEE 754 standard](https://en.wikipedia.org/wiki/IEEE_754-2008_revision). It has a sign bit,
   a 5-bit exponent and 11-bit precision (with 10 bits explicitly stored), and can represent numbers
   between approximately `6.1e-05` and `6.5e+04` at full precision. This type is not widely
   supported by C compilers: on a typical machine, an unsigned short can be used for storage, but
   not for math operations. See the Wikipedia page on
   the [half-precision floating-point format](https://en.wikipedia.org/wiki/Half-precision_floating-point_format)
   for more information.

7. When packing, `'x'` inserts one NUL byte.

8. The `'p'` format character encodes a “Pascal string”, meaning a short variable-length string
   stored in a _fixed number of bytes_, given by the count. The first byte stored is the length of
   the string, or 255, whichever is smaller. The bytes of the string follow. If the string passed in
   to [`pack()`](https://docs.python.org/3/library/struct.html#struct.pack "struct.pack")is too
   long (longer than the count minus 1), only the leading `count-1` bytes of the string are stored.
   If the string is shorter than `count-1`, it is padded with null bytes so that exactly count bytes
   in all are used. Note that for [
   `unpack()`](https://docs.python.org/3/library/struct.html#struct.unpack "struct.unpack"), the
   `'p'` format character consumes `count` bytes, but that the string returned can never contain
   more than 255 bytes.

9. For the `'s'` format character, the count is interpreted as the length of the bytes, not a repeat
   count like for the other format characters; for example, `'10s'` means a single 10-byte string
   mapping to or from a single Python byte string, while `'10c'` means 10 separate one byte
   character elements (e.g., `cccccccccc`) mapping to or from ten different Python byte objects. (
   See [Examples](https://docs.python.org/3/library/struct.html#struct-examples) for a concrete
   demonstration of the difference.) If a count is not given, it defaults to 1. For packing, the
   string is truncated or padded with null bytes as appropriate to make it fit. For unpacking, the
   resulting bytes object always has exactly the specified number of bytes. As a special case,
   `'0s'` means a single, empty string (while `'0c'` means 0 characters).

10. For the `'F'` and `'D'` format characters, the packed representation uses the IEEE 754 binary32
    and binary64 format for components of the complex number, regardless of the floating-point
    format used by the platform. Note that complex types (`F` and `D`) are available
    unconditionally, despite complex types being an optional feature in C. As specified in the C11
    standard, each complex type is represented by a two-element C array containing, respectively,
    the real and imaginary parts.

A format character may be preceded by an integral repeat count. For example, the format string
`'4h'` means exactly the same as `'hhhh'`.

Whitespace characters between formats are ignored; a count and its format must not contain
whitespace though.

When packing a value `x` using one of the integer formats (`'b'`, `'B'`, `'h'`, `'H'`, `'i'`, `'I'`,
`'l'`, `'L'`, `'q'`, `'Q'`), if `x` is outside the valid range for that format then [
`struct.error`](https://docs.python.org/3/library/struct.html#struct.error "struct.error") is
raised.

Changed in version 3.1: Previously, some of the integer formats wrapped out-of-range values and
raised [
`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning "DeprecationWarning")
instead of [
`struct.error`](https://docs.python.org/3/library/struct.html#struct.error "struct.error").

For the `'?'` format character, the return value is either [
`True`](https://docs.python.org/3/library/constants.html#True "True")or [
`False`](https://docs.python.org/3/library/constants.html#False "False"). When packing, the truth
value of the argument object is used. Either 0 or 1 in the native or standard bool representation
will be packed, and any non-zero value will be `True` when unpacking.
