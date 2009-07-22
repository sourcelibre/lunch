all:
	@echo Usage:
	@echo sudo make install
install:
	install lunch /usr/local/bin/lunch
uninstall:
	rm -f /usr/local/bin/lunch
doc:
	pydoc -w ./lunch
	rst2html README.txt lunch-readme.html

