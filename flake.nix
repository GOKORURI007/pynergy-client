{
  description = ''
    A python client for synergy protocol. Compatible with Deskflow.
  '';

  inputs = {
    nixpkgs.url = "nixpkgs";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python313;
      # 把当前目录当 Python 包构建
      pynergy-client = python.pkgs.buildPythonApplication rec {
        pname = "pynergy-client";
        version = "0.0.5";
        src = ./.;

        format = "pyproject"; # 使用 pyproject.toml

        nativeBuildInputs = [
          pkgs.makeWrapper
          python.pkgs.setuptools
          python.pkgs.wheel
        ];

        propagatedBuildInputs = [
          python.pkgs.evdev
          python.pkgs.loguru
          python.pkgs.toml
          python.pkgs.click
          python.pkgs.pynput
          python.pkgs.xlib
 	  python.pkgs.platformdirs

          pkgs.libevdev
          pkgs.libxkbcommon
          pkgs.evtest
          pkgs.linuxHeaders
          pkgs.libinput
        ];

        # 使用 postFixup 在构建最后阶段“注入”环境变量
        postFixup = ''
          wrapProgram $out/bin/pynergy-client \
            --set C_INCLUDE_PATH "${pkgs.linuxHeaders}/include:${pkgs.libevdev}/include/libevdev-1.0" \
            --set LIBRARY_PATH "${pkgs.libevdev}/lib" \
            --prefix LD_LIBRARY_PATH : "${pkgs.libevdev}/lib:${pkgs.libxkbcommon}/lib"
        '';

        meta.mainProgram = "pynergy-client"; # 让 nix run 知道主命令
      };
    in
    {
      packages.${system} = {
        default = pynergy-client;
      };

      apps.${system}.default = {
        type = "app";
        program = "${pynergy-client}/bin/pynergy-client";
      };
    };
}
