{
  description = ''
    A python client for synergy pynergy_protocol. Compatible with Deskflow.
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

      pynergy-protocol = python.pkgs.buildPythonPackage {
        pname = "pynergy-protocol";
        version = "0.1.0";
        src = ./packages/pynergy_protocol;
        format = "pyproject";
        nativeBuildInputs = with python.pkgs; [ hatchling ];
        propagatedBuildInputs = with python.pkgs; [ loguru ];
      };

      # 2. 定义 Client 应用
      pynergy-client = python.pkgs.buildPythonApplication {
        pname = "pynergy-client";
        version = "0.1.5";
        # 指向 client 的实际目录
        src = ./packages/pynergy_client;
        format = "pyproject";

        nativeBuildInputs = [
          pkgs.makeWrapper
          python.pkgs.hatchling
        ];

        propagatedBuildInputs = [
          pynergy-protocol

          # 其他第三方依赖
          python.pkgs.evdev
          python.pkgs.loguru
          python.pkgs.platformdirs
          python.pkgs.typer
          python.pkgs.cryptography
          python.pkgs.questionary

          # 系统库依赖
          pkgs.libevdev
          pkgs.libxkbcommon
          pkgs.linuxHeaders
          pkgs.libinput
        ];

        # 使用 postFixup 在构建最后阶段“注入”环境变量
postFixup = ''
          if [ -e "$out/bin/pynergy-client" ]; then
            wrapProgram $out/bin/pynergy-client \
              --set C_INCLUDE_PATH "${pkgs.linuxHeaders}/include:${pkgs.libevdev}/include/libevdev-1.0" \
              --set LIBRARY_PATH "${pkgs.libevdev}/lib" \
              --prefix LD_LIBRARY_PATH : "${pkgs.libevdev}/lib:${pkgs.libxkbcommon}/lib"
          else
            echo "Error: /bin/pynergy-client not found. Available files in $out/bin/:"
            ls $out/bin/
            exit 1
          fi
        '';

        meta.mainProgram = "pynergy-client"; # 让 nix run 知道主命令
      };
    in
    {
      packages.${system} = {
        default = pynergy-client;
        pynergy-client = pynergy-client;
        pynergy-protocol = pynergy-protocol;
      };

      # 运行设置
      apps.${system}.default = {
        type = "app";
        program = "${pynergy-client}/bin/pynergy-client";
      };
    };
}
