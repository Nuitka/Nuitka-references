find . -name Doc -exec rm -rf {} \;
find . -name InternalDocs -exec rm -rf {} \;
find . -name .devcontainer -exec rm -rf {} \;
find . -name Tools -exec rm -rf {} \;
find . -name .mailmap -delete
find . -name .pre-commit-config.yaml -delete
find . -name .readthedocs.yml -delete
find . -name aclocal.m4 -delete
find . -name config.guess -delete
find . -name config.sub -delete
find . -name configure -delete
find . -name configure.ac -delete
find . -name pyconfig.h.in -delete
find . -name install-sh -delete
find . -name Makefile.pre.in -delete