# Lab 3 (sbx), slide 12: a Makefile is a "file that runs later, on your machine".
# An agent with direct-mount write access can edit this target, and you will
# execute whatever it wrote the next time you type `make test`.
.PHONY: test run build

test:
	@echo "running lab tests"
	@python3 -c "import sys; sys.path.insert(0,'.'); from app.util import add; assert add(2,2)==4; print('ok')"

run:
	@python3 app/main.py

build:
	@docker build -t cc-perms-lab .
