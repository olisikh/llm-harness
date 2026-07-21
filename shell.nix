{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    git
    (python3.withPackages (ps: [ ps.pyyaml ]))
    uv
  ];
}
