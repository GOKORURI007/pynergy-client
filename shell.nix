{pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    libevdev
    libxkbcommon
    evtest
    linuxHeaders
    libinput
  ];

  shellHook = ''
    export C_INCLUDE_PATH="${pkgs.linuxHeaders}/include:${pkgs.libevdev}/include/libevdev-1.0:$C_INCLUDE_PATH"
    export LIBRARY_PATH="${pkgs.libevdev}/lib:$LIBRARY_PATH"
  '';
}
