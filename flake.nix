{
  description = "Python shell flake";

  inputs = {
    avm-semantics.url = "/home/geo2a/Workspace/RV/avm-semantics";
    # avm-semantics.url = "github:runtimeverification/avm-semantics";
    nixpkgs.url = "nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = { self, nixpkgs, flake-utils, avm-semantics, ... }:
    let
      overlay = final: prev:
        {
          kavm-demo = prev.poetry2nix.mkPoetryEnv {
            projectDir = ./.;
            python = prev.python311;
            overrides = prev.poetry2nix.overrides.withDefaults
              (finalPython: prevPython: { exceptiongroup = prevPython.exceptiongroup.overridePythonAttrs (old: {
                                                             propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [ finalPython.flit-scm ];
                                                           });
                                          py-algorand-sdk = prevPython.py-algorand-sdk.overridePythonAttrs (old: {
                                                             propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [ finalPython.setuptools ];
                                                           });
                                        });
          };
        };
      system = "x86_64-linux";
    in
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ overlay ];
        };
        packageName = "kavm-demo";
      in
      {
        packages.${system}.default = pkgs.kavm-demo;
        packages = {
          inherit (self) kavm-demo;
        };
        devShell.${system} = pkgs.kavm-demo.env.overrideAttrs(old: {
          shellHook = ''
          echo "Welcome to KAVM demo!"
          echo ${avm-semantics.packages.${system}.avm-semantics}
          export KAVM_DEFINITION_DIR=${(toString avm-semantics.packages.${system}.avm-semantics) + "/lib/kavm/avm-llvm/avm-testing-kompiled"}
          '';
          buildInputs = [avm-semantics.packages.${system}.kavm];
          });
      };
}
