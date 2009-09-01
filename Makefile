all:
	@echo Usage:
	@echo sudo make install
install:
	install lunch /usr/local/bin/lunch
	install Lunch.desktop /usr/local/share/applications/Lunch.desktop
	mkdir -p /usr/local/share/icons/
	install Lunch.svg /usr/local/share/icons/Lunch.svg
uninstall:
	rm -f /usr/local/bin/lunch
	rm -f /usr/local/share/applications/Lunch.desktop
	rm -f /usr/local/share/icons/Lunch.svg
doc:
	pydoc -w ./lunch
	rst2html README.txt lunch-readme.html
clean:
	rm -f lunch-readme.html lunch.html lunchc

