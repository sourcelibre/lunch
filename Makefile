all:
	@echo Usage:
	@echo sudo make install
	help2man -N -i man_lunch.txt -n "The Lunch Distributed Process Manager" scripts/lunch > lunch.1
	convert -geometry 48x48 -background none lunch.svg lunch.png
	python setup.py build
	
install: all
	install scripts/lunch /usr/local/bin/lunch
	install lunch.desktop /usr/local/share/applications/
	mkdir -p /usr/local/share/pixmaps/
	install lunch.png /usr/local/share/pixmaps/
	install lunch.1 /usr/local/share/man/man1/lunch.1
	python setup.py install --prefix=/usr/local

uninstall:
	rm -f /usr/local/bin/lunch
	rm -f /usr/local/share/applications/lunch.desktop
	rm -f /usr/local/share/pixmaps/lunch.png
	@echo You need to manually uninstall lunch from /usr/local/lib/python2.5/site-packages
	@echo Do not forget to remove it from the easy-install.pth

doc: all
	mkdir -p html
	epydoc --html --output=html --verbose --show-imports --name=Lunch lunch
	rst2html README.txt lunch-readme.html

clean:
	rm -f lunch-readme.html lunch.html lunchc lunch.1 lunch.png
	rm -rf html

deb:
	dpkg-buildpackage -r 

check:
	trial lunch/test

