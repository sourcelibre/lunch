#!/bin/bash
# Create a tarball of the lunch project with a given tag as suffix
# Usage: ./make-tarball.sh 0.4.2
# (where 0.4.2 is the version of the current tag)

if [ $# -ne 1 ]
then
    echo "Usage: $0 <tag>"
    exit 65
fi

PREFIX=lunch
FULLNAME=$PREFIX-$1

git archive --prefix=$FULLNAME/ --format=tar -o $FULLNAME.tar HEAD
gzip -c $FULLNAME.tar > $FULLNAME.tar.gz
rm $FULLNAME.tar
echo "Done creating $FULLNAME.tar.gz"

