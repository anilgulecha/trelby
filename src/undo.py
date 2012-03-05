import screenplay

DIFF_DELETE = 0
DIFF_INSERT = 1
DIFF_REPLACE = 2

# return a pretty representation of lines.
def _lnstr(lines):
    text = "["
    for line in lines:
        text = text + line.text + "(%s)," % id(line.text)
    text = text + "]"
    return text

# function to create a deepcopy of passed list of lines (linesToCopy)
def _copylines(linesToCopy):
    lines = []
    if linesToCopy:
        for i in xrange(len(linesToCopy)):
            ln = linesToCopy[i]
            lines.append(screenplay.Line(ln.lb, ln.lt, ln.text))
    return lines


# Our own implementation of difflib.SequenceMatcher, since the actual one
# is too slow for our needs.
#
# l1, l2 = lists to diff. List elements must have __eq__ defined.
#
# Return a, b, c, d such that l1[a:b] could be replaced
# with l2[c:d] to convert l1 into l2.
#
# This function can also be completed in constant time, if you know that only
# a single item at position 'line' has changed. Call with fast set to True,
# then only worries about items from line - 1 to line + 1.

def mySequenceMatcher(l1, l2, fast = False, line = -1):
    len1 = len(l1)
    len2 = len(l2)

    if len1 >= len2:
        bigger = l1
        smaller = l2
        biglen = len1
        smalllen = len2
        l1IsBig = True
    else:
        bigger = l2
        smaller = l1
        biglen = len2
        smalllen = len1
        l1IsBig = False

    i = 0
    a = b = 0

    if fast and line > 0:
        # no need to start from the beginning.. assume everything matches
        # until line - 1
        a = b = line - 1
        #print "left set to ", a, b

    m1found = m2found = False
    while a < smalllen:
        if not m1found and not bigger[a].__eq__(smaller [a]):
            b = a
            m1found = True
            break
        a += 1

    if not m1found:
        a = b = smalllen

    i = 0
    c = biglen
    d = smalllen

    if fast and line < smalllen - 1:
        # assume things match till we traverse down to upto line + 1
        d = line + 1
        c = d + (biglen - smalllen)
        #print "right set to ", c, d


    while i <= smalllen - a + 1:
        if not bigger[-i].__eq__(smaller[-i]):
            c = biglen - i + 1
            d = smalllen - i + 1
            m2found = True
            break
        i += 1

    if not l1IsBig:
        a, c, b, d = a, d, b, c

    removed = not (a == c)
    inserted = not (b == d)

    if not removed and not inserted:
        tag = "equal"
    elif removed and inserted:
        tag = "replace"
    elif removed and not inserted:
        tag = "delete"
    else:
        tag = "insert"

    return tag, a, c, b, d

# A class to hold screenplay state for undo/redo
class UndoItem:
    # lines/line/column - screenplay lines, line, column
    def __init__(self, lines, line, column):
        self.lines = lines
        self.line = line
        self.column = column

    # return bool - compares text our lines and passed lines.
    def areLinesSame(self, lns):
        l1 = len(self.lines)
        l2 = len(lns)

        if l1 != l2:
            return False

        while l2 > 0:
            l2 = l2 - 1
            if not self.lines[l2].__eq__(lns[l2]):
                return False

        return True

    def __str__(self):
        ret = "["
        for line in self.lines:
            ret += line.text + ","
        return ret + "] %d:%d" % (self.line, self.column)

# objects that make up an UndoDiffItem
class diffOp:
    # [a:b] and [x:y] represent the indexes of transformed elements.
    # removed holds [a:b] contents, and inserted holds [x:y] contents.
    # oper represents one of DIFF_* operations.
    def __init__(self, oper, a, b, x, y, removed, inserted):
        self.operation = oper
        self.a = a
        self.b = b
        self.x = x
        self.y = y
        self.removed = removed
        self.inserted = inserted

    def __str__(self):
        return "type = %d (%d,%d)[%s] (%d,%d)[%s]" % ( self.operation,
                self.a, self.b, _lnstr(self.removed), self.x, self.y,
                _lnstr(self.inserted))


# Objects that make up the undo/redo stack
class UndoDiffItem:
    # line, column - line/column number to set after this diff is applied.
    def __init__(self, line, column):
        self.operations = []
        self.line = line
        self.column = column

    # add an diff operation.
    def addOp(self, op):
        self.operations.append(op)

    # patch this diff onto pass lines (ls).
    def applyDiff(self, ls):
        for op in self.operations:
            if op.operation == DIFF_DELETE:
                del ls[op.a:op.b]

            else: #insert or replace
                ls[op.a:op.b] = _copylines(op.inserted)

    # depatch this diff from passes lines (ls).
    def unapplyDiff(self, ls):
        # unapply in reverse
        self.operations.reverse()

        for op in self.operations:

            if op.operation == DIFF_DELETE:
                ls[op.a:op.a] = _copylines(op.removed)

            elif op.operation == DIFF_INSERT:
                del ls[op.a:op.b + op.y - op.x]

            else: # DIFF_REPLACE
                ls[op.x:op.y] = _copylines(op.removed)

        # set ops back to original state.
        self.operations.reverse()

    def __str__(self):
        return "%d ops, %d:%d" % (len(self.operations), self.line, self.column)

# A class to handle undo/redo stacks
class UndoBuffer:
    # size - maximum size of undo buffer.
    # initial - initial state of the screenplay, in an UndoItem
    def __init__(self, size, initial):
        # setup undo/redo stacks.
        self.undodata = []
        self.redodata = []

        # the top item saves the state at the top of our undo stack.
        self.top = UndoItem(_copylines(initial.lines),
                    initial.line, initial.column)

        # bottom maintains initial information.
        # (also updated when items are from the bottom when stack is full).
        self.bottom = UndoItem([], initial.line, initial.column)

        self.size = size

    # deletes the item at the bottom of the undo stack
    def _delOldest(self):
        self.bottom.line = self.undodata[0].line
        self.bottom.column = self.undodata[0].column
        self.undodata.pop(0)

    # add an undo point.
    # item - current screenplay state, represented via an UndoItem.
    def add(self, item, fast = False):

        # return if undo disabled.
        if self.size == 0:
            return

        lines = item.lines

        # build list of operations to turn 'top.lines' into 'lines'
        di = UndoDiffItem(item.line, item.column)

        # find differences between our top, and passed lines.
        tag, a, b, x, y = mySequenceMatcher(self.top.lines, lines, fast, item.line)
        if tag == "delete":
            removed = _copylines(self.top.lines[a:b])
            di.addOp(diffOp(DIFF_DELETE, a, b, x, y, removed, None))

        elif tag == "insert":
            inserted = _copylines(lines[x:y])
            di.addOp(diffOp(DIFF_INSERT, a, b, x, y, None, inserted))

        elif tag == "replace":
            removed = _copylines(self.top.lines[a:b])
            inserted = _copylines(lines[x:y])
            di.addOp(diffOp(DIFF_REPLACE, a, b, x, y, removed, inserted))

        if len(self.undodata) == self.size:
            # buffer full. delete old item.
            self._delOldest()

        # append item to undo stack, and update top element.
        self.undodata.append(di)
        di.applyDiff(self.top.lines)
        self.top.line = di.line
        self.top.column = di.column

        # clear redo buffer
        self.redodata = []

    # Move an item from the undo stack to redo. Update item as well.
    def _moveUndoToRedo(self, item):
        self.redodata.append(self.undodata.pop())
        self.redodata[-1].unapplyDiff(self.top.lines)
        self.redodata[-1].unapplyDiff(item.lines)

        if self.undodata:
            item.line = self.top.line = self.undodata[-1].line
            item.column = self.top.column = self.undodata[-1].column
        else:
            item.line = self.top.line = self.bottom.line
            item.column = self.top.column = self.bottom.column

    # Move an item from the redo stack to undo. Update item as well.
    def _moveRedoToUndo(self, item):
        self.undodata.append(self.redodata.pop())
        self.undodata[-1].applyDiff(self.top.lines)
        self.undodata[-1].applyDiff(item.lines)
        item.line = self.top.line = self.undodata[-1].line
        item.column = self.top.column = self.undodata[-1].column

    # Return True on undo success, else False
    # currentItem is the active object. On successful undo, this will
    # be modified.
    def undo(self, currentItem):

        # undo disabled?
        if self.size == 0:
            return False

        itemSame = currentItem.areLinesSame(self.top.lines)

        if itemSame:
            # if same, move item from undo stack into redo stack
            if self.undodata:
                self._moveUndoToRedo(currentItem)
        else:
            # empty redo stack and add currentItem to it
            self.add(currentItem)
            self._moveUndoToRedo(currentItem)

        return True

    # return True on redo success, else False
    # currentItem is the active object. On successful redo, this will
    # be modified.
    def redo(self, currentItem):
        if not self.redodata:
            return False

        itemSame = currentItem.areLinesSame(self.top.lines)

        if itemSame:
            # In the middle of a undo/redo
            self._moveRedoToUndo(currentItem)
        else:
            # So the changes have gone in a different direction!
            self.redodata = []
        return True

    # return the number of Line objects that the UndoBuffer holds.
    # used for debugging, and approximating additional memory allocated.
    def getLinesCount(self):
        lc = 0

        # lines in undo stack.
        for item in self.undodata:
            for op in item.operations:
                if op.removed:
                    lc += len(op.removed)
                if op.inserted:
                    lc += len(op.inserted)

        # lines in redo stack.
        for item in self.redodata:
            for op in item.operations:
                if op.removed:
                    lc += len(op.removed)
                if op.inserted:
                    lc += len(op.inserted)

        # lines in our top.
        lc += len(self.top.lines)
        return lc
