{pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  # 1. 运行时的系统依赖（C 库和头文件）
  buildInputs = with pkgs; [
    libevdev
    libxkbcommon
    evtest
    linuxHeaders
  ];

  # 2. 告诉 Python 到哪里找内核头文件
  shellHook = ''
    # 告诉编译器去哪里找 linux/input.h
    export C_INCLUDE_PATH="${pkgs.linuxHeaders}/include:${pkgs.libevdev}/include/libevdev-1.0:$C_INCLUDE_PATH"
    # 如果还需要链接库文件
    export LIBRARY_PATH="${pkgs.libevdev}/lib:$LIBRARY_PATH"
  '';
}