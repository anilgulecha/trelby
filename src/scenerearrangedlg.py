import gutil
import misc
import util

import wx

# dragliststriped.py

class DragList(wx.ListCtrl):
    def __init__(self, *arg, **kw):
        wx.ListCtrl.__init__(self, *arg, **kw)

        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnDrag)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
        self.Bind(wx.EVT_LEFT_UP,self.OnMouseUp)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterWindow)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.dragging = False
        self.dragItemPos = 0
        self.initialPositions = None

        # column headings
        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Scene")
        self.InsertColumn(2, "From")
        self.InsertColumn(3, "To")

    def setItems(self, items):
        for index in range(len(items)):
            self.InsertStringItem(index, items[index][0])
            self.SetStringItem(index, 1, items[index][1])
            self.SetStringItem(index, 2, str(items[index][2]))
            self.SetStringItem(index, 3, str(items[index][3]))

        self.initialPositions = self.getPositions()

    def getPositions(self):
        poslist =[]
        for i in range(self.GetItemCount()):
            a = int(self.GetItem(i, 2).GetText())
            b = int(self.GetItem(i, 3).GetText()) + 1
            poslist.append((a, b))

        return poslist

    def OnSize(self, event):
        w = self.GetClientSize().width
        self.SetColumnWidth(1, w - 130)
        self.SetColumnWidth(0, 40)
        self.SetColumnWidth(2, 40)
        self.SetColumnWidth(3, 40)

        event.Skip()

    def OnLeaveWindow(self, event):
        self.dragging = False
        event.Skip()

    def OnEnterWindow(self, event):
        event.Skip()

    def OnDrag(self, event):
        event.Skip()
        pass

    def OnSelect(self, event):
        event.Skip()

    def OnMouseUp(self, event):
        self.dragging = False
        event.Skip()

    def OnMouseDown(self, event):
        self.dragging = True
        self.dragItemPos = self.HitTest(event.GetPosition())[0]
        event.Skip()

    def OnMotion(self, event):
        if not self.dragging:
            return
        #get current position
        curPos = self.HitTest(event.GetPosition())[0]
        if curPos == -1:
            return
        if curPos != self.dragItemPos:
            self.move(self.dragItemPos, curPos)

    def move(self, oldPos, newPos):
        if newPos < oldPos:
            inc = -1
        else:
            inc = 1

        while oldPos != newPos:
            self.swap(oldPos, oldPos + inc)
            oldPos += inc

        self.dragItemPos = newPos
        self.Select(newPos)

    def swap(self, oldPos, newPos):
        temp = []
        for x in range(self.GetColumnCount()):
            temp.append(self.GetItem(oldPos,x).GetText())

        #move new to old
        for x in range(self.GetColumnCount()):
            self.SetStringItem(oldPos,x, self.GetItem(newPos,x).GetText())

        #move temp to new
        for x in range(self.GetColumnCount()):
            self.SetStringItem(newPos,x,temp.pop(0))

    def OnInsert(self, event):
        event.Skip()

    def OnDelete(self, event):
        event.Skip()

class SceneRearrangeDlg(wx.Dialog):
    def __init__(self, parent, sp):
        wx.Dialog.__init__(self, parent, -1, "Scene Rearrange",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.sp = sp

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Click and drag to rearrange scenes"),
        0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        self.sceneListCtrl = DragList(self,
                    style = wx.LC_REPORT|wx.LC_SINGLE_SEL, size = (400, 400))

        vsizer.Add(self.sceneListCtrl, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "Apply")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        items = self.getRearrangeItems()
        if not items:
            wx.MessageBox("Nothing to rearrange", "Error", wx.OK, self)
        else:
            self.sceneListCtrl.setItems(items)
            # note where the first item begins.
            self.firstLineNo = items[0][2]

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def getRearrangeItems(self):
        navlist = self.sp.getNavigatorElements()
        # a list of [scene_number, scene_heading, startline, endline] items.
        sceneList = []
        for item in navlist:
            if item.sceneText:
                if item.sceneNo != -1:
                    sno = str(item.sceneNo)
                else:
                    sno = ""
                sceneList.append([sno, item.sceneText, item.lineNo])

        # now also append endline
        lastLine = len(self.sp.lines) - 1
        ln = len(sceneList)
        for i in range(ln):
            if i == (ln - 1):
                sceneList[i].append(lastLine)
            else:
                sceneList[i].append(sceneList[i+1][2]-1)

        return sceneList

    def OnOK(self, event):
        pos = self.sceneListCtrl.getPositions()
        if pos == self.sceneListCtrl.initialPositions:
           wx.MessageBox("Nothing has been changed.", "Information", wx.OK, self)
           return

        if wx.MessageBox( "Are you sure you want to apply these changes?",
            "Confirm", wx.YES_NO | wx.NO_DEFAULT, self) == wx.YES:
            pos = self.sceneListCtrl.getPositions()
            newlines = []
            if self.firstLineNo != 0:
                newlines += self.sp.lines[0:self.firstLineNo]
            for i in pos:
                newlines += self.sp.lines[i[0]:i[1]]
            self.sp.lines = newlines
            self.sp.markChanged()
        else:
            return

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

