#
# To include these variables in other scripts, you add the following:
#
# import os
# execfile(os.path.join(os.path.dirname(__file__), "postures.py"))
#
# Then, you can access the variables like this:
#
# posture.user
#

class postures:

    user = "postures"

    srcPath = "/home/%s/src" % (user)
    posturesPath = "%s/postures/trunk" % (srcPath)
    ntaPath = "%s/nta" % (srcPath)
    spinwidgetsPath = "%s/spinwidgets" % (srcPath)
    spinPath = "%s/spinframework/trunk" % (srcPath)

    pd = "%s/pd-0.41-4/bin/pd -jack -r 16000 -inchannels 3 -outchannels 3" % (srcPath)
    ntaClientDebug = "%s %s/ntaClient.pd" % (pd, ntaPath)
    ntaClient = "%s -send 'init! bang' %s/ntaClient.pd" % (pd, ntaPath)
    spinEditorDebug = "%s %s/patches/spinEdit.pd %s/milhouseTest.pd" % (pd, spinwidgetsPath, ntaPath)
    spinEditor = "%s -send 'init! bang' %s/patches/spinEdit.pd %s/milhouseTest.pd" % (pd, spinwidgetsPath, ntaPath)



