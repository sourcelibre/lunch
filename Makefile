all:
	@echo Usage:
	@echo sudo make install
	python setup.py build
	
install: all
	install scripts/lunch /usr/local/bin/lunch
	install scripts/lunch-slave /usr/local/bin/lunch-slave
	install lunch.desktop /usr/local/share/applications/
	install -d /usr/local/share/pixmaps/
	install lunch.png /usr/local/share/pixmaps/
	install lunch.1 /usr/local/share/man/man1/lunch.1
	install lunch-slave.1 /usr/local/share/man/man1/lunch-slave.1
	python setup.py install --prefix=/usr/local

uninstall:
	rm -f /usr/local/bin/lunch
	rm -f /usr/local/bin/lunch-slave
	rm -f /usr/local/share/applications/lunch.desktop
	rm -f /usr/local/share/pixmaps/lunch.png
	@echo You need to manually uninstall lunch from /usr/local/lib/python2.5/site-packages
	@echo Do not forget to remove it from the easy-install.pth

html: all
	mkdir -p html
	mkdir -p html-slave
	epydoc --html --output=html --verbose --show-imports --name="Lunch" lunch
	epydoc --html --output=html-slave --verbose --show-imports --name="Lunch Slave" scripts/lunch-slave
	rst2html README lunch-readme.html

clean:
	rm -f lunch-readme.html lunch.html lunchc lunch.1 lunch-slave.1 lunch.png
	rm -rf html

check:
	trial lunch/test

