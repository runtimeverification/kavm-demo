{
  description = "Python shell flake";

  inputs = {
    avm-semantics.url = "/home/geo2a/Workspace/RV/avm-semantics";
    nixpkgs.url = "nixpkgs/nixos-22.05";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = { self, nixpkgs, flake-utils, avm-semantics, ... }:
    let
      overlay = final: prev:
        {
          kavm-demo = prev.poetry2nix.mkPoetryApplication {
            projectDir = ./.;
            python = prev.python311;
            overrides = prev.poetry2nix.overrides.withDefaults
              (finalPython: prevPython: { kavm = prev.python3.pkgs.toPythonModule avm-semantics.packages.${prev.system}.kavm;
                                          # exceptiongroup = prevPython.exceptiongroup.overridePythonAttrs (old: {
                                          #                    propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [ finalPython.flit-scm ];
                                          #                  });
                                        });
            # overrides =
            #   [ pkgs.poetry2nix.defaultPoetryOverrides packageOverrides ];
          };
        };
      system = "x86_64-linux";
    in
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ overlay ];
        };
        # python = pkgs.python3.withPackages (ps: with ps; [ pkgs.kavm ]);
        # packageOverrides = final: prev : {
        #   kavm = pkgs.python3.pkgs.toPythonModule pkgs.kavm;
        #   exceptiongroup = prev.exceptiongroup.overridePythonAttrs (old: {
        #     propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [ final.flit-scm ];
        #   });
        # };
        # python = pkgs.python3.override { inherit packageOverrides; self = python;};
        packageName = "kavm-demo";
        # app = pkgs.poetry2nix.mkPoetryApplication {
        #   projectDir = ./.;
        #   groups = [ ];
        #   # We remove `"dev"` from `checkGroups`, so that poetry2nix does not try to resolve dev dependencies.
        #   checkGroups = [ ];
        #   overrides =
        #     [ pkgs.poetry2nix.defaultPoetryOverrides packageOverrides ];
        # };
      in
      {
        packages.${system}.default = pkgs.kavm-demo;
        packages = {
          inherit (pkgs) avm-semantics kavm kavm-demo;
        };
        devShell.${system} = pkgs.mkShell {
          shellHook = ''
          '';
          buildInputs = with pkgs; [poetry];
          inputsFrom = builtins.attrValues self.packages.${system};
        };
      };
}
