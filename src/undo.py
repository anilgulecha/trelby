import screenplay

import difflib

DIFF_DELETE = 0
DIFF_INSERT = 1
DIFF_REPLACE = 2

class diffOp:
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

# A class to hold screenplay state for undo/redo
class UndoItem:
    def __init__(self, lines, line, column):
        self.lines = lines
        self.line = line
        self.column = column

    def areLinesSame(self, lns):
        l1 = len(self.lines)
        l2 = len(lns)

        if l1 != l2:
            return False

        while l2 > 0:
            l2 = l2 - 1
            if self.lines[l2].__str__() != lns[l2].__str__():
                return False

        return True

    def __str__(self):
        ret = "["
        for line in self.lines:
            ret += line.text + ","
        return ret + "] %d:%d" % (self.line, self.column)

def _lnstr(lines):
    text = "["
    for line in lines:
        text = text + line.text + "(%s)," % id(line.text)
    text = text + "]"
    return text

# Objects that make up the undo/redo stack
class UndoDiffItem:
    def __init__(self, line, column):
        self.operations = []
        self.line = line
        self.column = column

    def addOp(self, op):
        self.operations.append(op)

    # apply operations to this
    def applyDiff(self, ls):
        for op in self.operations:
            if op.operation == DIFF_DELETE:
                print " >apply removed>" , _lnstr(ls[op.a:op.b])
                del ls[op.a:op.b]
            else: #insert or replace
                ls[op.a:op.b] = op.inserted
                print " >apply ins/rplc>" , _lnstr(op.inserted)
            #print "after apply", op, " list is \n", ls

    def unapplyDiff(self, ls):
        self.operations.reverse()
        for op in self.operations:
            if op.operation == DIFF_DELETE:
                ls[op.a:op.a] = op.removed
                print " >unapply readd>" , _lnstr(op.removed)
            elif op.operation == DIFF_INSERT:
                print " >unapply uninsert>" , _lnstr(ls[op.a:op.b + op.y - op.x])
                del ls[op.a:op.b + op.y - op.x]
            else: # DIFF_REPLACE
                print " >unapply unreplace" , _lnstr(ls[op.x:op.y]), _lnstr(op.removed)
                print op
                ls[op.x:op.y] = op.removed
            #print "after unapply", op, " list is \n", ls
        self.operations.reverse()

    def __str__(self):
        return "%d ops, %d:%d" % (len(self.operations), self.line, self.column)

# A class to handle undo/redo stacks
class UndoBuffer:
    # size - maximum size of undo buffer.
    # initial - list of lines when buffer is initialized.
    def __init__(self, size, initial):
        # setup undo/redo stacks.
        # the top element (list of lines) of undo stack signifies the program state.
        self.undodata = []
        self.redodata = []
        self.top = UndoItem(self._copylines(initial.lines),
                    initial.line, initial.column)
        print "top set to ", self.top
        self.size = size

    def _copylines(self, linesToCopy):
        lines = []
        if linesToCopy:
            for i in xrange(len(linesToCopy)):
                ln = linesToCopy[i]
                lines.append(screenplay.Line(ln.lb, ln.lt, ln.text))
        return lines


    def printbuffer(self):
        print "undo (%d)" % len(self.undodata), [item.__str__() for item in self.undodata]
        print "redo (%d)" % len(self.redodata), [item.__str__() for item in self.redodata]
        print "top", self.top
        print

    # deletes the item at the bottom of the undo stack
    def _delOldest(self):
        self.undodata.pop(0)

    # add an undo point.
    # item - newly created UndoDiffItem with line/column set.
    # lines - latest screenplay lines. diff our 'top' against this
    def add(self, item):

        # return if no buffer
        if self.size == 0:
            return

        lines = item.lines
        di = UndoDiffItem(item.line, item.column)
        # build list of operations to turn 'top.lines' into 'lines'
        print "comparing"
        print self.top
        print "with"
        print item

        matcher = difflib.SequenceMatcher(None, self.top.lines, lines)
        for tag, a, b, x, y in reversed(matcher.get_opcodes()):
            if tag == "delete":
                removed = self._copylines(lines[a:b])
                di.addOp(diffOp(DIFF_DELETE, a, b, x, y, removed, None))
                print "deleted ", _lnstr(removed)
            elif tag == "insert":
                inserted = self._copylines(lines[x:y])
                di.addOp(diffOp(DIFF_INSERT, a, b, x, y, None, inserted))
                print "inserted ", _lnstr(inserted)
            elif tag == "replace":
                removed = self._copylines(self.top.lines[a:b])
                inserted = self._copylines(lines[x:y])
                di.addOp(diffOp(DIFF_REPLACE, a, b, x, y, removed, inserted))
                print "replaced ", _lnstr(removed), " with ", _lnstr(inserted)

        if not di.operations:
            # nothing changed
            return

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

        self.printbuffer()

    def _moveUndoToRedo(self):
        self.redodata.append(self.undodata.pop())
        self.redodata[-1].unapplyDiff(self.top.lines)
        if self.undodata:
            self.top.line = self.undodata[-1].line
            self.top.column = self.undodata[-1].column
        else:
            self.top.line = 0
            self.top.column = 0

    def _moveRedoToUndo(self):
        self.undodata.append(self.redodata.pop())
        self.undodata[-1].applyDiff(self.top.lines)
        self.top.line = self.undodata[-1].line
        self.top.column = self.undodata[-1].column

    # return a copy of the top item.
    def _getTopItem(self):
        return UndoItem(self._copylines(self.top.lines), self.top.line,
                    self.top.column)

    # return an UndoItem, or None if cannot undo
    # currentItem (UndoItem) is the active screenplay
    #  - this may or may not have changed from the top of undo stack.
    def undo(self, currentItem):
        if self.size == 0 or len(self.undodata) == 0:
            # No undo buffer.
            return None

        itemSame = currentItem.areLinesSame(self.top.lines)

        if itemSame:
            print ">>> item was same"
            # if same, move item from undo stack into redo stack
            self._moveUndoToRedo()
        else:
            print ">>> item was not same"
            # empty redo stack and add current to it
            self.add(currentItem)
            self._moveUndoToRedo()

        self.printbuffer()
        ret = self._getTopItem()
        print "\nundo called. returning"
        print ret
        return ret

    # return redo item, or None if cannot redo
    # currentItem is the active object.
    def redo(self, currentItem):
        if not self.redodata:
            print "nothing to redo"
            return None

        itemSame = currentItem.areLinesSame(self.top.lines)

        if itemSame:
            # In the middle of a undo/redo
            self._moveRedoToUndo()
            return self._getTopItem()
        else:
            # So the changes have gone in a different direction!
            self.redodata = []
            self.printbuffer()
            return None

