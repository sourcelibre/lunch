all:
	@echo Usage:
	@echo sudo make install
install:
	install lunch /usr/local/bin/lunch
uninstall:
	rm -f /usr/local/bin/lunch

