from typing import Annotated

XPad = Annotated[None, 'x']
Char = Annotated[str, 'c']
Bool = Annotated[bool, '?']
Int8 = Annotated[int, 'b']
UInt8 = Annotated[int, 'B']
Int16 = Annotated[int, 'h']
UInt16 = Annotated[int, 'H']
Int32 = Annotated[int, 'i']
UInt32 = Annotated[int, 'I']
LInt32 = Annotated[int, 'l']
ULInt32 = Annotated[int, 'L']
Int64 = Annotated[int, 'q']
UInt64 = Annotated[int, 'Q']
SSizeT = Annotated[int, 'n']
SizeT = Annotated[int, 'N']
Float16 = Annotated[float, 'e']
Float = Annotated[float, 'f']
FloatComplex = Annotated[complex, 'F']
Double = Annotated[float, 'd']
DoubleComplex = Annotated[complex, 'D']
SString = Annotated[str, 'p']
String = Annotated[str, 's']
VarString = Annotated[str, 'Is']  # 特殊标记：变量长度字符串（Synergy 常用）


class FixedString:
    def __class_getitem__(cls, length: int):
        # 这样返回的是一个标准的类型对象，get_origin 识别率 100%
        return Annotated[str, f'{length}s']
