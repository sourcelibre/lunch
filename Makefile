all:
	@echo Usage:
	@echo sudo make install
	help2man -N -n "The Lunch Distributed Process Manager" bin/lunch > lunch.1
	convert -geometry 48x48 -background none lunch.svg lunch.png
	
install: all
	install bin/lunch /usr/local/bin/lunch
	install lunch.desktop /usr/local/share/applications/
	mkdir -p /usr/local/share/pixmaps/
	install lunch.png /usr/local/share/pixmaps/
	install lunch.1 /usr/local/share/man/man1/lunch.1
	
uninstall:
	rm -f /usr/local/bin/lunch
	rm -f /usr/local/share/applications/lunch.desktop
	rm -f /usr/local/share/icons/hicolor/48x48/apps/lunch.png

doc:
	#pydoc -w ./lunch
	epydoc --html --output=html --verbose --show-imports --name=Lunch lunch
	rst2html README.txt lunch-readme.html

clean:
	rm -f lunch-readme.html lunch.html lunchc lunch.1 lunch.png

deb:
	dpkg-buildpackage -r 

