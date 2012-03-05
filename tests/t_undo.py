import u

# test calls to undo functions.
def testUndoAlgo():
    sp = u.load()
    ls = sp.lines

    if sp.cfgGl.undoBufferSize <5:
        print "skipping this test"
        return

    linesBefore = len(ls)
    lineBefore = sp.line
    textBefore = ls[lineBefore].text

    # now destroy 3 lines
    sp.lines = sp.lines[3:]
    sp.addUndoPoint()

    # add some text to the first line.
    sp.lines[0].text += "blah"
    # mark check, and do a fast undo.
    sp.addUndoPoint(fast = True)

    # delete 5 lines in the middle, and another undo.
    sp.lines = sp.lines[:5]+ sp.lines[10:]
    sp.addUndoPoint()

    # delete the last five lines
    sp.lines = sp.lines[:-5]
    sp.addUndoPoint()

    # now undo 4 times, and check against initial values
    for i in xrange(4):
        sp.undo()

    assert linesBefore == len(sp.lines)
    assert lineBefore == sp.line
    assert textBefore == sp.lines[sp.line].text

