# Some development notes about the Lunch project

## The release process

Update the documentation if needed:

* scripts/lunch
* scripts/lunch-slave
* man\_lunch.txt
* README

Make sure the version number is the next release's:

* scripts/lunch-slave
* lunch/__init__.py

Run the unit tests::

```
trial lunch
```

Update the release notes:

* NEWS

Update the ChangeLog::

```
git log --pretty=medium > ChangeLog
```

Create the tag and a tarball:

* Make sure you are in the right branch. (develop)
* Commit any change::

```
git checkout -b release-0.4.0 (in this example, we release 0.4.0)
```

* Increase the version number to the next even micro version number (see "Files with version number")
* Make any additional change
* Do (wisely and step by step) this::

```
git checkout master
git merge --no-ff release-0.4.0
git tag 0.4.0
./utils/make-tarball.sh 0.4.0
git checkout develop
git merge --no-ff release-0.4.0
git branch -d release-0.4.0
git push --tags origin master:master develop:develop
```

* Increase the version number to the next odd micro version number (never to be released) (0.4.1 in this example)
* Commit with "post-release version bump" message.

Oh! and in that case, since its a release in a stable branch, we should also create or update a "0.4" branch. (with the major.micro version numbers) Here is how to create one::

```
git checkout master
git checkout -b 0.4
git push origin 0.4
```

And here is how to update it once it already exists::

```
git checkout 0.4
git merge --no-ff master
git push origin 0.4
```

Don't forget to go back working in the develop branch once you are done creating a release.::

```
git checkout develop
```


## Files with version number

* scripts/lunch-slave
* lunch/__init__.py

